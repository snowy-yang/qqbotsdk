"""连接适配器：gateway 握手 + 长连接，业务事件流入、出站帧流出。

每条帧先交给协议处理器（`Protocol.on_frame`）处理协议语义，只有业务事件
（op=0）才入队交给 emitter 分发给用户 handler——协议帧与业务事件因此不共享
分发路径。

连接策略：指数退避重连（连接稳定存活才把退避归一，抖动的服务端不会被 1s
间隔反复探测）；心跳任务随连接生灭——HELLO 给出间隔后周期投递，断线即取消，
不在出站缓冲堆积过期心跳；看门狗两层互补——receive 的静默超时抓"连接彻底
静默"，收到消息时的 ACK 期限检查抓"有事件流但心跳已死"；HELLO 未到时另有
握手期限，避免对端不发言时按寿命余量傻等。服务端约 1 小时会主动断开连接，
故临到期前主动重连（经 RESUME 补发消息），不等被掐断。
"""

import asyncio
from time import monotonic
from typing import cast

import aiohttp
import ujson
from aiohttp import WSMsgType
from loguru import logger

from .config import Config
from .model import Opcode, OutgoingFrame, Payload, heartbeat_frame
from .protocol import Protocol
from .queue import EventQueue
from .session import Session
from .token import AccessToken


class RateLimitError(RuntimeError):
    """gateway 接口触发频率限制（code=100017）。"""


class _Heartbeat:
    """接收循环与心跳任务之间的联动状态（ws 传输层专属）。

    HELLO 给出心跳间隔：提取后经 Future 唤醒心跳任务，同时驱动接收循环的
    静默看门狗；HEARTBEAT_ACK 刷新活性，超期即"有事件流但心跳已死"。
    """

    def __init__(self, interval_fut: asyncio.Future[float], ack_factor: float) -> None:
        self._interval_fut = interval_fut
        self._ack_factor = ack_factor
        self._interval = 0.0
        self._last_ack = monotonic()

    @property
    def interval(self) -> float:
        return self._interval

    def observe(self, data: Payload) -> None:
        """从一帧提取心跳信息：HELLO 的间隔、HEARTBEAT_ACK 的活性。"""
        op = data.get("op")
        if op == Opcode.HELLO:
            d = data.get("d")
            if isinstance(d, dict):
                raw = d.get("heartbeat_interval", 41_250)
                if (
                    not isinstance(raw, (int, float))
                    or isinstance(raw, bool)
                    or raw <= 0
                ):
                    raise RuntimeError(f"HELLO 的 heartbeat_interval 非法: {raw!r}")
                self._interval = raw / 1000
                if not self._interval_fut.done():
                    self._interval_fut.set_result(self._interval)
        elif op == Opcode.HEARTBEAT_ACK:
            self._last_ack = monotonic()

    def ack_expired(self) -> bool:
        """距最近一次 ACK 是否已超过期限（× 心跳间隔）。"""
        return monotonic() - self._last_ack > self._interval * self._ack_factor


class Connecter:
    # 看门狗阈值（× 心跳间隔）：贴着 ACK 的自然节奏（1×）跑，误杀由 RESUME 兜底不丢消息；
    # 不能压到 1× 整——ACK 的自然间隔就是 1×，正常抖动会贴边误杀；TCP 下丢包表现为延迟而非静默
    _SILENCE_FACTOR = 1.1
    _ACK_FACTOR = 1.2
    # 连接存活超过该时长才算稳定，才把退避归一
    _STABLE_SECONDS = 60.0
    # HELLO 到达前的握手期限：对端不发 HELLO 时不能按寿命余量傻等
    _HANDSHAKE_TIMEOUT = 30.0
    # 服务端约 1 小时后会主动断开连接（无预警，实测）：临到期前留出余量主动重连，
    # 这样是正常收尾 + RESUME 补发消息，而不是被掐断后由看门狗判成异常
    _SERVER_LIFETIME = 60 * 60.0
    _RECONNECT_MARGIN = 10 * 60.0

    def __init__(
        self,
        config: Config,
        http: aiohttp.ClientSession,
        token: AccessToken,
        session: Session,
        queue: EventQueue,
        protocol: Protocol,
    ) -> None:
        self._config = config
        self._http = http
        self._token = token
        self._session = session
        self._queue = queue
        self._protocol = protocol
        # 出站帧缓冲（心跳 + 协议应答）：由 send_helper 单任务发送，
        # 维持 aiohttp ws 单写者不变量，生产者（心跳）也不会被发送阻塞
        self._outbound: asyncio.Queue[OutgoingFrame] = asyncio.Queue()

    async def run(self) -> None:
        """重连主循环。

        健康连接被服务端要求重连（如满 1 小时的连接限寿）时不等待、也不记
        连接/断开日志，直接立刻重连——这期间的事件由网关按 RESUME 补发，
        盲区最小；只有连接未能稳定存活（握手失败、看门狗超时、限流、抖动）
        才记断开并按退避等待，`_STABLE_SECONDS` 保证抖动的服务端不会被 1s
        间隔反复探测。
        """
        backoff: float = 1
        delay: float = 0  # 0 表示立刻重连（首次重试不等待）
        while True:
            if delay:
                logger.info(f"{delay}s 后重连")
                await asyncio.sleep(delay)
            try:
                lived = await self._connect()
            except RateLimitError:
                logger.warning("gateway 触发频率限制")
                delay = backoff = 60
                continue
            except TimeoutError:
                logger.warning("连接超时（握手或心跳），触发看门狗重连")
                lived = 0.0
            except (aiohttp.ClientError, RuntimeError) as e:
                logger.warning(f"WebSocket 连接异常: {e}")
                lived = 0.0

            if lived >= self._STABLE_SECONDS:
                # 连接曾稳定存活：属正常断开（服务端要求重连），立刻重连
                backoff = 1
                delay = 0
            else:
                # 没能稳定存活：需要延迟重试，此时才记断开
                logger.warning("WebSocket 已断开")
                delay = backoff
                backoff = min(backoff * 2, 60)

    async def _connect(self) -> float:
        """建立一次连接直到断开，返回存活秒数（供 run 判断是否重置退避）。"""
        started = monotonic()
        access_token = await self._token.get_access_token()
        headers = {"Authorization": f"QQBot {access_token}"}

        async with self._http.get(
            f"{self._config.base_url}/gateway", headers=headers
        ) as resp:
            status = resp.status
            try:
                data = await resp.json(loads=ujson.loads, content_type=None)
            except ValueError as e:
                body = (await resp.read())[:200].decode("utf-8", "replace")
                raise RuntimeError(
                    f"获取 gateway 失败: HTTP {status}, 响应不是合法 JSON: {body!r}"
                ) from e

        if not isinstance(data, dict):
            raise RuntimeError(f"获取 gateway 失败: HTTP {status}, body={data!r}")
        if data.get("code") == 100017:
            raise RateLimitError
        gateway = data.get("url")
        if not isinstance(gateway, str) or not gateway:
            raise RuntimeError(f"获取 gateway 失败: {data}")

        async with self._http.ws_connect(gateway, headers=headers) as ws:
            # HELLO 才给出心跳间隔；receive 解析到后经 Future 交给心跳任务
            interval: asyncio.Future[float] = asyncio.get_running_loop().create_future()
            receive = asyncio.create_task(self.receive_helper(ws, interval))
            send = asyncio.create_task(self.send_helper(ws))
            heartbeat = asyncio.create_task(self.heartbeat_helper(interval))
            try:
                await receive
            finally:
                send.cancel()
                heartbeat.cancel()
                # 取回被取消任务的结果，避免 "Task exception was never retrieved"，
                # 也确保它们在下一轮重连前真正停下
                await asyncio.gather(send, heartbeat, return_exceptions=True)
        return monotonic() - started

    async def receive_helper(
        self, ws: aiohttp.ClientWebSocketResponse, interval_fut: asyncio.Future[float]
    ) -> None:
        heartbeat = _Heartbeat(interval_fut, self._ACK_FACTOR)
        # 服务端约 1 小时后会主动断开，临到期前主动重连：return 即让 _connect 正常
        # 收尾，run() 见存活超过稳定阈值便立刻重连，经 RESUME 补发这段时间的消息
        deadline = monotonic() + self._SERVER_LIFETIME - self._RECONNECT_MARGIN
        while not ws.closed:
            remaining = deadline - monotonic()
            if remaining <= 0:
                logger.info("连接到达服务端寿命上限，主动重连")
                return
            msg = await self._wait_frame(ws, heartbeat.interval, remaining)
            if msg is None:
                continue  # 寿命余量到点 → 回顶部主动收尾
            if msg.type != WSMsgType.TEXT:
                logger.warning(f"WebSocket 收到非文本帧，连接终止: {msg.type}")
                break
            try:
                payload = msg.json(loads=ujson.loads)
            except ValueError as e:
                raw = (
                    msg.data
                    if isinstance(msg.data, str)
                    else msg.data.decode("utf-8", "replace")
                )
                logger.warning(
                    f"WebSocket 收到非法 JSON 帧，连接终止: {raw[:200]!r} ({e})"
                )
                break
            if not isinstance(payload, dict):
                logger.warning(f"WebSocket 收到非对象帧，连接终止: {payload!r}")
                break
            if await self._process_frame(cast(Payload, payload), heartbeat):
                break
            if heartbeat.ack_expired():
                raise TimeoutError  # ACK 超期 → 交给 run() 走看门狗重连

    async def _wait_frame(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        interval: float,
        remaining: float,
    ) -> aiohttp.WSMessage | None:
        """等待下一帧：静默阈值、握手期限与寿命余量三个截止取先到者。

        HELLO 未到时用固定握手期限，避免对端不发 HELLO 时按寿命余量傻等；
        超时落在静默/握手截止上抛 TimeoutError 交 run() 走看门狗重连，
        落在寿命余量上返回 None，由调用方回循环顶部主动收尾重连。
        """
        deadline = (
            interval * self._SILENCE_FACTOR if interval else self._HANDSHAKE_TIMEOUT
        )
        timeout = min(deadline, remaining)
        try:
            return await ws.receive(timeout=timeout)
        except TimeoutError:
            if deadline <= remaining:
                raise
            return None

    async def _process_frame(self, data: Payload, heartbeat: _Heartbeat) -> bool:
        """处理一条帧，返回连接是否应当终止。"""
        heartbeat.observe(data)

        # 每帧都交给本适配器的协议处理器（HELLO→IDENTIFY/RESUME、
        # READY→捕获会话、INVALID_SESSION→清会话、s→序列号）；只有业务
        # 事件（op=0）入队分发。协议帧不入队，所以 INVALID_SESSION 的
        # 会话重置在本方法返回前已同步完成，重连不会误 RESUME 死会话。
        response = await self._protocol.on_frame(data)
        if response is not None:
            await self._outbound.put(cast(OutgoingFrame, response))
        op = data.get("op")
        if op == Opcode.DISPATCH:
            await self._queue.put_event(data)
        return op in (Opcode.RECONNECT, Opcode.INVALID_SESSION)

    async def heartbeat_helper(self, interval_fut: asyncio.Future[float]) -> None:
        """HELLO 给出间隔后周期投递心跳；断线随任务取消，不堆积过期心跳。"""
        interval = await interval_fut
        while True:
            await asyncio.sleep(interval)
            # 服务端不会推送 op=1，心跳只由本任务投进出站缓冲
            await self._outbound.put(heartbeat_frame(self._session.seq))

    async def send_helper(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """唯一的 ws 写者：从出站缓冲取帧发送（保持 aiohttp 单写者约束）。"""
        while not ws.closed:
            frame = await self._outbound.get()
            try:
                await ws.send_json(frame, dumps=ujson.dumps)
            except (aiohttp.ClientError, ConnectionError) as e:
                logger.warning(f"WebSocket 发送失败，丢弃该帧: {frame} ({e})")
