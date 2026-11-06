"""QQ 机器人网关 WebSocket 客户端.

连接流程: 建立 WebSocket -> 收到 op=10 Hello 得到心跳间隔 -> 发送 op=2 Identify 鉴权
-> 收到 op=0 t=READY 开始下发事件. 断线后若仍持有 session_id 与 seq 则发送 op=6 Resume
由服务端补发遗漏事件, 否则重新 Identify; 关闭码决定是重连还是彻底终止.

用法::

    from qqbotsdk.ws import DEFAULT_INTENTS, QQBotWebSocket

    async with QQBotWebSocket(intents=DEFAULT_INTENTS) as ws:
        await ws.wait_ready()
        async for event in ws:
            print(event.t, event.d)

也可以注册回调代替手写分发循环, 两种方式并存 (回调以独立任务派发, 不阻塞收包)::

    ws.on("GROUP_AT_MESSAGE_CREATE", handle_group_message)  # 精确事件名
    ws.on("*", log_every_event)                             # 所有 Dispatch

网关地址在 ``url`` 省略时, 于每次建立连接前调用
``qqbotsdk.api.gateway.fetch_gateway_url()`` 实时获取 (``GET /gateway``),
因此服务端调整地址后无需改代码; 也可以显式传入 ``url`` 跳过这一步.
"""

import asyncio
import json
import platform
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from typing import Any, Final, Self, cast

from aiohttp import ClientError, ClientWebSocketResponse, WSMsgType
from loguru import logger
from pydantic import ValidationError

from qqbotsdk.api.auth import QQBotAuthError, get_access_token
from qqbotsdk.api.core import session
from qqbotsdk.api.gateway import fetch_gateway_url
from qqbotsdk.errors import QQBotGatewayError
from qqbotsdk.ws.intents import DEFAULT_INTENTS, Intents
from qqbotsdk.ws.payload import GatewayPayload, OpCode

# 事件回调: 入参是 Dispatch 数据包, 不需要返回值
type Handler = Callable[[GatewayPayload], Awaitable[None]]

# 通配事件名: 注册它即可收到全部 Dispatch 事件 (含 READY / RESUMED)
WILDCARD_EVENT: Final = "*"

# 心跳间隔兜底值(毫秒), 正常情况下以 Hello 下发的 heartbeat_interval 为准
DEFAULT_HEARTBEAT_INTERVAL_MS: Final = 45000

# 握手(等 Hello 并发出鉴权)的超时秒数
HANDSHAKE_TIMEOUT_SECONDS: Final = 30.0

# 重连退避: 第 n 次等待 min(BACKOFF_BASE_SECONDS * 2 ** (n - 1), BACKOFF_MAX_SECONDS)
BACKOFF_BASE_SECONDS: Final = 1.0
BACKOFF_MAX_SECONDS: Final = 60.0

# 指数退避的指数上限, 避免无限重连时指数运算溢出
_MAX_BACKOFF_EXPONENT: Final = 16

# 主动关闭时使用的正常关闭码
_NORMAL_CLOSE_CODE: Final = 1000

# 这些关闭码可以保留会话, 重连后走 Resume
_RESUMABLE_CLOSE_CODES: Final = frozenset({4009})

# 这些关闭码不可重连, 直接终止客户端
_FATAL_CLOSE_CODES: Final = frozenset(
    {4001, 4002, 4010, 4011, 4012, 4013, 4014, 4914, 4915}
)

# 不可重连关闭码的可读原因, 让报错直接指向怎么修
_FATAL_CLOSE_REASONS: Final = {
    4001: "无效的 opcode",
    4002: "无效的 payload",
    4010: "无效的 shard",
    4011: "连接数超过限制",
    4012: "无效的 API 版本",
    4013: (
        "无效的 intents：其中有当前应用不可订阅的事件位；"
        "到开放平台确认该 intents 已在「事件订阅」中开通"
    ),
    4014: (
        "无权限的 intents：该 intents 未在开放平台开通；"
        "到「开发设置 → 事件订阅」申请对应事件，或改用 "
        "GROUP_BOT_INTENTS 收窄订阅范围"
    ),
    4914: "机器人已下架, 请到开放平台检查应用状态",
    4915: "机器人已被封禁",
}

# 其余关闭码(含 4006, 4007, 4900~4913)一律清空会话后重新 Identify


class _StopGateway(Exception):
    """不可重试的关闭码, 需要彻底停止客户端."""


def _token_text(token: str) -> str:
    """拼出网关鉴权用的 token 字符串, 调用方不得将其写进日志."""
    return f"QQBot {token}"


def _session_id_of(data: Any) -> str | None:
    """从 READY 事件的 d 里取出 session_id, 结构异常时返回 None."""
    if not isinstance(data, dict):
        return None
    mapping = cast("dict[str, Any]", data)
    session_id = mapping.get("session_id")
    if isinstance(session_id, str) and session_id:
        return session_id
    return None


class QQBotWebSocket:
    """QQ 机器人网关 WebSocket 客户端.

    事件有两种消费方式, 二者并存, 不互斥:

    - ``async for payload in ws``: 逐个消费 Dispatch 事件;
    - ``ws.on(event_name, handler)``: 注册回调, 每个回调单独起任务执行.

    Args:
        intents: 订阅的事件位.
        url: 网关地址, 省略时每次建立连接前自动从 ``GET /gateway`` 获取.
        auto_reconnect: 断线后是否自动重连.
        max_reconnect_attempts: 连续重连失败多少次后放弃, ``None`` 表示不限制.
        backoff_base: 重连退避的初始秒数.
        backoff_max: 重连退避的上限秒数.
    """

    def __init__(
        self,
        intents: Intents = DEFAULT_INTENTS,
        *,
        url: str | None = None,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int | None = None,
        backoff_base: float = BACKOFF_BASE_SECONDS,
        backoff_max: float = BACKOFF_MAX_SECONDS,
    ) -> None:
        self._intents = intents
        self._url = url
        self._auto_reconnect = auto_reconnect
        self._max_reconnect_attempts = max_reconnect_attempts
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max

        # 事件回调: 事件名(或 "*") -> 回调列表, 按注册顺序触发
        self._handlers: dict[str, list[Handler]] = {}
        # 已派发但尚未完成的回调任务, 保留引用避免被 GC 回收
        self._handler_tasks: set[asyncio.Task[None]] = set()

        # 事件队列, None 是结束标记
        self._queue: asyncio.Queue[GatewayPayload | None] = asyncio.Queue()
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()

        self._ws: ClientWebSocketResponse[bool] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._runner: asyncio.Task[None] | None = None

        # 会话状态, 断线重连时用于 Resume
        self._session_id: str | None = None
        self._seq: int | None = None
        self._reconnect_requested = False
        self._ack_pending = False
        self._heartbeat_interval = DEFAULT_HEARTBEAT_INTERVAL_MS / 1000
        self._reconnect_attempt = 0
        # 不可重试的终止原因, 供调用方区分 4914/4915 之类的封禁场景
        self._last_error: QQBotGatewayError | None = None

    @property
    def session_id(self) -> str | None:
        """当前网关会话 ID, 尚未收到 READY 时为 None."""
        return self._session_id

    @property
    def last_error(self) -> QQBotGatewayError | None:
        """客户端因不可重试的关闭码停止时记录的错误, 否则为 None."""
        return self._last_error

    @property
    def seq(self) -> int | None:
        """最近一次收到的事件序号."""
        return self._seq

    def on(self, event_name: str, handler: Handler) -> None:
        """注册事件回调.

        Args:
            event_name: 事件名, 例如 ``"GROUP_AT_MESSAGE_CREATE"``; 传 ``"*"`` 表示
                接收全部 Dispatch 事件 (含 READY / RESUMED).
            handler: 协程回调, 入参为 :class:`GatewayPayload`.

        Notes:
            同一个事件可以注册多个回调, 按注册顺序触发; ``"*"`` 的回调在精确匹配的
            回调之后触发. 回调以独立任务派发, 不阻塞收包循环, 也不影响 ``async for``
            (事件同样会进入迭代队列). 单个回调抛异常只记录日志, 不影响连接与其它回调.
        """
        self._handlers.setdefault(event_name, []).append(handler)

    def off(self, event_name: str, handler: Handler | None = None) -> None:
        """移除事件回调.

        Args:
            event_name: 事件名, 或 ``"*"``.
            handler: 要移除的回调; 省略时清空该事件下的全部回调.
        """
        if handler is None:
            self._handlers.pop(event_name, None)
            return
        handlers = self._handlers.get(event_name)
        if handlers is None:
            return
        with suppress(ValueError):
            handlers.remove(handler)
        if not handlers:
            self._handlers.pop(event_name, None)

    async def __aenter__(self) -> Self:
        self._ensure_started()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    def __aiter__(self) -> AsyncIterator[GatewayPayload]:
        self._ensure_started()
        return self

    async def __anext__(self) -> GatewayPayload:
        event = await self._queue.get()
        if event is None:
            raise StopAsyncIteration
        return event

    async def wait_ready(self, timeout: float | None = None) -> None:
        """等待网关就绪(已收到 READY 或 RESUMED 事件).

        Args:
            timeout: 最长等待秒数, ``None`` 表示一直等待.

        Raises:
            TimeoutError: 超时仍未就绪.
            ConnectionError: 客户端在就绪前已停止.
        """
        self._ensure_started()
        if self._ready.is_set():
            return
        ready = asyncio.ensure_future(self._ready.wait())
        stopped = asyncio.ensure_future(self._stop.wait())
        try:
            done, _pending = await asyncio.wait(
                (ready, stopped),
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for task in (ready, stopped):
                task.cancel()
        if not done:
            raise TimeoutError("等待网关就绪超时")
        if ready not in done:
            raise ConnectionError("网关客户端已停止，未能就绪")

    async def close(self) -> None:
        """关闭连接并停止后台任务, 可重复调用."""
        self._stop.set()
        await self._stop_heartbeat()
        ws = self._ws
        if ws is not None and not ws.closed:
            with suppress(Exception):
                await ws.close(code=_NORMAL_CLOSE_CODE)
        runner = self._runner
        self._runner = None
        if runner is not None and not runner.done():
            runner.cancel()
            with suppress(asyncio.CancelledError):
                await runner
        await self._cancel_handler_tasks()
        self._queue.put_nowait(None)

    async def _cancel_handler_tasks(self) -> None:
        """取消并回收尚未完成的回调任务, 避免关闭后残留后台任务."""
        tasks = list(self._handler_tasks)
        self._handler_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _ensure_started(self) -> None:
        """确保后台连接任务已启动, 关闭后再次使用时会重置内部状态."""
        if self._runner is not None:
            return
        if self._stop.is_set():
            self._queue = asyncio.Queue()
            self._ready = asyncio.Event()
            self._stop = asyncio.Event()
            self._session_id = None
            self._seq = None
            self._reconnect_attempt = 0
        self._runner = asyncio.create_task(self._run(), name="qqbotsdk-gateway")

    async def _run(self) -> None:
        """维持连接的主循环: 连接, 断线后退避重连, 直到被关闭或不可重试."""
        try:
            while not self._stop.is_set():
                try:
                    await self._connect_and_listen()
                except _StopGateway as exc:
                    logger.error(f"网关连接不可重试，停止运行：{exc}")
                    return
                except (
                    ClientError,
                    OSError,
                    TimeoutError,
                    QQBotAuthError,
                    QQBotGatewayError,
                    RuntimeError,
                ) as exc:
                    # 网关地址获取失败等属于可重试的错误, 与网络错误一样退避重连
                    logger.warning(f"网关连接异常：{exc!r}")

                if self._stop.is_set() or not self._auto_reconnect:
                    return
                if not await self._wait_backoff():
                    return
        finally:
            self._stop.set()
            self._ws = None
            self._queue.put_nowait(None)
            await self._stop_heartbeat()

    async def _resolve_url(self) -> str:
        """返回本次连接要用的网关地址: 显式传入时直接用, 否则实时向服务端获取."""
        if self._url is not None:
            return self._url
        url = await fetch_gateway_url()
        logger.debug(f"已获取网关地址：{url}")
        return url

    async def _connect_and_listen(self) -> None:
        """建立一次连接, 完成握手后持续接收事件, 直到连接结束."""
        ws = await session.client.ws_connect(
            await self._resolve_url(),
            # 心跳由本客户端按 Hello 下发的间隔自行发送, 关闭 aiohttp 的内建心跳
            heartbeat=None,
        )
        self._ws = ws
        try:
            await self._handshake(ws)
            await self._listen(ws)
        finally:
            await self._stop_heartbeat()
            self._ws = None
            with suppress(Exception):
                await ws.close()

    async def _handshake(self, ws: ClientWebSocketResponse[bool]) -> None:
        """等待 Hello, 启动心跳, 然后按会话状态发送 Identify 或 Resume."""
        async with asyncio.timeout(HANDSHAKE_TIMEOUT_SECONDS):
            hello = await self._receive(ws)
            if hello.op != OpCode.HELLO:
                raise ConnectionError(
                    f"网关握手失败：首包 op={hello.op}, 期望 op={OpCode.HELLO}"
                )
            self._heartbeat_interval = _heartbeat_seconds(hello.d)
            self._start_heartbeat(ws)

            token = await get_access_token()
            if self._session_id is not None and self._seq is not None:
                logger.info(
                    f"发送 Resume 恢复会话：session_id={self._session_id} "
                    f"seq={self._seq}"
                )
                await self._send(
                    ws,
                    {
                        "op": OpCode.RESUME,
                        "d": {
                            "token": _token_text(token),
                            "session_id": self._session_id,
                            "seq": self._seq,
                        },
                    },
                )
            else:
                logger.info("发送 Identify 鉴权")
                await self._send(
                    ws,
                    {
                        "op": OpCode.IDENTIFY,
                        "d": {
                            "token": _token_text(token),
                            "intents": int(self._intents),
                            # 本客户端不做分片(负载均衡), 固定单分片上报
                            "shard": [0, 1],
                            "properties": {
                                "$os": platform.system(),
                                "$browser": "qqbotsdk",
                                "$device": "qqbotsdk",
                            },
                        },
                    },
                )

    async def _listen(self, ws: ClientWebSocketResponse[bool]) -> None:
        """持续接收数据包, 直到连接关闭或收到重连指令."""
        while not self._stop.is_set():
            msg = await ws.receive()
            if msg.type is WSMsgType.TEXT:
                self._handle_payload(msg.data)
                if self._reconnect_requested:
                    self._reconnect_requested = False
                    return
                continue
            if msg.type is WSMsgType.ERROR:
                raise ConnectionError(f"读取 WebSocket 失败：{ws.exception()!r}")
            if msg.type is WSMsgType.BINARY:
                logger.debug("忽略二进制数据帧")
                continue
            # CLOSE / CLOSING / CLOSED: 优先取关闭帧里带的关闭码
            code = msg.data if isinstance(msg.data, int) else ws.close_code
            self._handle_close(code)
            return

    async def _receive(self, ws: ClientWebSocketResponse[bool]) -> GatewayPayload:
        """读取并解析一帧, 握手期间收到异常帧直接报错."""
        msg = await ws.receive()
        if msg.type is not WSMsgType.TEXT:
            raise ConnectionError(f"网关握手期间收到非文本帧：{msg.type!r}")
        payload = self._parse(msg.data)
        if payload is None:
            raise ConnectionError("网关握手期间收到无法解析的数据包")
        return payload

    async def _send(
        self,
        ws: ClientWebSocketResponse[bool],
        payload: dict[str, Any],
    ) -> None:
        await ws.send_str(json.dumps(payload, ensure_ascii=False))

    def _parse(self, data: str) -> GatewayPayload | None:
        """把原始帧解析成 GatewayPayload, 失败时记日志并返回 None."""
        try:
            raw = json.loads(data)
        except ValueError:
            logger.warning("收到无法解析为 JSON 的网关数据包，已忽略")
            return None
        try:
            return GatewayPayload.model_validate(raw)
        except ValidationError as exc:
            logger.warning(f"网关数据包字段校验失败，已忽略：{exc}")
            return None

    def _handle_payload(self, data: str) -> None:
        """处理一帧数据: 记录序号, 分发 Dispatch 事件, 响应控制类操作码."""
        payload = self._parse(data)
        if payload is None:
            return
        if payload.s is not None:
            self._seq = payload.s

        match payload.op:
            case OpCode.HELLO:
                logger.debug("再次收到 op=10 Hello，已忽略")
            case OpCode.HEARTBEAT_ACK:
                self._ack_pending = False
            case OpCode.DISPATCH:
                self._handle_dispatch(payload)
            case OpCode.RECONNECT:
                logger.info("网关要求重连(op=7)，保留会话以 Resume")
                self._reconnect_requested = True
            case OpCode.INVALID_SESSION:
                logger.warning("网关会话失效(op=9)，将重新 Identify")
                self._reset_session()
                self._reconnect_requested = True
            case _:
                logger.debug(f"忽略未处理的数据包：op={payload.op}")

    def _handle_dispatch(self, payload: GatewayPayload) -> None:
        """处理 Dispatch 事件, 就绪类事件额外更新会话状态."""
        if payload.t == "READY":
            session_id = _session_id_of(payload.d)
            if session_id is not None:
                self._session_id = session_id
            self._reconnect_attempt = 0
            self._ready.set()
            logger.info(f"网关已就绪：session_id={self._session_id}")
        elif payload.t == "RESUMED":
            self._reconnect_attempt = 0
            self._ready.set()
            logger.info("会话恢复完成(RESUMED)")
        self._queue.put_nowait(payload)
        self._dispatch_handlers(payload)

    def _dispatch_handlers(self, payload: GatewayPayload) -> None:
        """把事件派发给已注册的回调: 精确匹配的先触发, 通配的在后面.

        每个回调一个独立任务, 因此不会阻塞收包循环; 任务保留在集合里防止被 GC.
        """
        if not self._handlers:
            return
        handlers = list(self._handlers.get(WILDCARD_EVENT, ()))
        if payload.t is not None:
            handlers = [*self._handlers.get(payload.t, ()), *handlers]
        for handler in handlers:
            task = asyncio.create_task(self._run_handler(handler, payload))
            self._handler_tasks.add(task)
            task.add_done_callback(self._handler_tasks.discard)

    async def _run_handler(self, handler: Handler, payload: GatewayPayload) -> None:
        """执行单个回调, 异常记日志后吞掉, 不影响连接与其它回调."""
        try:
            await handler(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"事件回调执行失败：事件={payload.t}")

    def _handle_close(self, code: int | None) -> None:
        """按关闭码决定重连策略; 不可重连时记录错误并抛出 _StopGateway."""
        if self._stop.is_set():
            # 主动关闭, 无需重连
            return
        if code in _FATAL_CLOSE_CODES:
            reason = _FATAL_CLOSE_REASONS.get(code)
            message = "网关拒绝连接，不可重连"
            if reason is not None:
                message = f"{message}：{reason}"
            error = QQBotGatewayError(message, code=code)
            self._last_error = error
            raise _StopGateway(str(error))
        if code in _RESUMABLE_CLOSE_CODES:
            logger.warning(f"网关要求重连(关闭码 {code})，将尝试 Resume")
            return
        logger.warning(f"网关连接已关闭(关闭码 {code})，将重新 Identify")
        self._reset_session()

    def _reset_session(self) -> None:
        """清空会话状态, 下次连接走 Identify."""
        self._session_id = None
        self._seq = None
        self._ready.clear()

    def _start_heartbeat(self, ws: ClientWebSocketResponse[bool]) -> None:
        self._ack_pending = False
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(ws),
            name="qqbotsdk-heartbeat",
        )

    async def _heartbeat_loop(self, ws: ClientWebSocketResponse[bool]) -> None:
        """按 heartbeat_interval 定时发送 op=1 心跳."""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            if self._stop.is_set() or ws.closed:
                return
            if self._ack_pending:
                logger.warning("上一条心跳未收到 ACK，网关可能已失联")
            self._ack_pending = True
            await self._send(ws, {"op": OpCode.HEARTBEAT, "d": self._seq})

    async def _stop_heartbeat(self) -> None:
        task = self._heartbeat_task
        self._heartbeat_task = None
        if task is None:
            return
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task

    async def _wait_backoff(self) -> bool:
        """等待退避时间, 返回 False 表示应停止重连."""
        self._reconnect_attempt += 1
        limit = self._max_reconnect_attempts
        if limit is not None and self._reconnect_attempt > limit:
            logger.error(f"连续重连 {limit} 次仍未成功，停止重连")
            return False
        exponent = min(self._reconnect_attempt - 1, _MAX_BACKOFF_EXPONENT)
        delay = min(self._backoff_base * (2**exponent), self._backoff_max)
        logger.info(f"{delay:.1f} 秒后重连网关(第 {self._reconnect_attempt} 次)")
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=delay)
        except TimeoutError:
            return True
        return False


def _heartbeat_seconds(data: Any) -> float:
    """从 Hello 的 d 里取出心跳间隔(毫秒)并换算成秒."""
    if isinstance(data, dict):
        mapping = cast("dict[str, Any]", data)
        raw = mapping.get("heartbeat_interval")
        if isinstance(raw, int | float) and raw > 0:
            return float(raw) / 1000
    return DEFAULT_HEARTBEAT_INTERVAL_MS / 1000


__all__ = [
    "BACKOFF_BASE_SECONDS",
    "BACKOFF_MAX_SECONDS",
    "DEFAULT_HEARTBEAT_INTERVAL_MS",
    "HANDSHAKE_TIMEOUT_SECONDS",
    "WILDCARD_EVENT",
    "Handler",
    "QQBotWebSocket",
]
