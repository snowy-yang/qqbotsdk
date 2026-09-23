"""连接适配器：把两种接入方式（WebSocket / Webhook）归一为业务事件流入、出站帧流出。

每条帧先交给本适配器注入的协议处理器（`BaseProtocol.on_frame`）处理协议语义，
只有业务事件（op=0）才入队交给 emitter 分发给用户 handler——协议帧与业务事件
因此不共享分发路径。

- WebsocketConnecter：gateway 握手 + ws 长连接，指数退避重连（连接稳定
  存活才把退避归一，抖动的服务端不会被 1s 间隔反复探测）；心跳任务随
  连接生灭——HELLO 给出间隔后周期投递，断线即取消，不在出站缓冲堆积
  过期心跳；看门狗两层互补——receive 的静默超时抓"连接彻底静默"，
  收到消息时的 ACK 期限检查抓"有事件流但心跳已死"；另外服务端约 1 小时
  会主动断开连接，故临到期前主动重连（经 RESUME 补发消息），不等被掐断；
- WebhookConnecter：aiohttp server 接收回调，验签失败 401，
  按 payload id 做 60s TTL 去重，正常推送进事件队列；op=13 验证请求
  由协议处理器就地应答（HTTP 响应不走队列）。
"""

import asyncio
from abc import ABC, abstractmethod
from time import monotonic
from typing import cast

import aiohttp
import ujson
from aiohttp import WSMsgType, web
from loguru import logger

from .config import Config
from .crypto import verify_sig
from .model import NOT_SET, Opcode, Payload, payload_of
from .protocol import BaseProtocol
from .queue import EventQueue
from .session import Session
from .token import AccessToken


class Connecter(ABC):
    """连接适配器接口：两种接入方式都实现 `run()` 常驻运行。"""

    @abstractmethod
    async def run(self) -> None: ...


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
                self._interval = d.get("heartbeat_interval", 41_250) / 1000
                if not self._interval_fut.done():
                    self._interval_fut.set_result(self._interval)
        elif op == Opcode.HEARTBEAT_ACK:
            self._last_ack = monotonic()

    def ack_expired(self) -> bool:
        """距最近一次 ACK 是否已超过期限（× 心跳间隔）。"""
        return monotonic() - self._last_ack > self._interval * self._ack_factor


class WebsocketConnecter(Connecter):
    # 看门狗阈值（× 心跳间隔）：贴着 ACK 的自然节奏（1×）跑，误杀由 RESUME 兜底不丢消息；
    # 不能压到 1× 整——ACK 的自然间隔就是 1×，正常抖动会贴边误杀；TCP 下丢包表现为延迟而非静默
    _SILENCE_FACTOR = 1.1
    _ACK_FACTOR = 1.2
    # 连接存活超过该时长才算稳定，才把退避归一
    _STABLE_SECONDS = 60.0
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
        protocol: BaseProtocol,
    ) -> None:
        self._config = config
        self._http = http
        self._token = token
        self._session = session
        self._queue = queue
        self._protocol = protocol
        # 出站帧缓冲（心跳 + 协议应答）：由 send_helper 单任务发送，
        # 维持 aiohttp ws 单写者不变量，生产者（心跳）也不会被发送阻塞
        self._outbound: asyncio.Queue[Payload] = asyncio.Queue()

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
                logger.warning("心跳超时，触发看门狗重连")
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
            data = await resp.json(loads=ujson.loads)

        if data.get("code") == 100017:
            raise RateLimitError
        gateway = data.get("url")
        if not gateway:
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
            if await self._process_frame(msg.json(loads=ujson.loads), heartbeat):
                break
            if heartbeat.ack_expired():
                raise TimeoutError  # ACK 超期 → 交给 run() 走看门狗重连

    async def _wait_frame(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        interval: float,
        remaining: float,
    ) -> aiohttp.WSMessage | None:
        """等待下一帧：静默阈值与寿命余量两个截止取先到者。

        超时落在静默阈值上说明连接彻底静默，抛 TimeoutError 交 run() 走看门狗
        重连；落在寿命余量上返回 None，由调用方回循环顶部主动收尾重连。
        """
        silence = interval * self._SILENCE_FACTOR
        watchdog = bool(silence) and silence < remaining
        try:
            return await ws.receive(timeout=silence if watchdog else remaining)
        except TimeoutError:
            if watchdog:
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
            await self._outbound.put(cast(Payload, response))
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
            await self._outbound.put(payload_of(Opcode.HEARTBEAT, self._session.seq))

    async def send_helper(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """唯一的 ws 写者：从出站缓冲取帧发送（保持 aiohttp 单写者约束）。"""
        while not ws.closed:
            payload = await self._outbound.get()
            body = {k: v for k, v in payload.items() if v != NOT_SET}
            try:
                await ws.send_json(body)
            except (aiohttp.ClientError, ConnectionError) as e:
                logger.warning(f"WebSocket 发送失败，丢弃该帧: {body} ({e})")


class WebhookConnecter(Connecter):
    _DEDUP_TTL = 60
    # 去重表长度达到该值才做一次过期清理（摊还 O(1)，避免每请求全表扫描）
    _DEDUP_SWEEP_AT = 1024

    def __init__(
        self,
        config: Config,
        queue: EventQueue,
        protocol: BaseProtocol,
    ) -> None:
        """protocol 为本接入方式的协议处理器（WebhookProtocol），op=13 验证
        请求由它就地应答；本类只依赖队列与该处理器，不感知 EventEmitter。"""
        self._config = config
        self._queue = queue
        self._protocol = protocol
        self._seen: dict[str, float] = {}

    def _make_app(self) -> web.Application:
        app = web.Application()
        app.add_routes([web.post(self._config.webhook_path, self._handle)])
        return app

    async def run(self) -> None:
        runner = web.AppRunner(self._make_app())
        await runner.setup()
        site = web.TCPSite(runner, self._config.webhook_host, self._config.webhook_port)
        await site.start()
        logger.info(
            f"Webhook 回调服务已启动: "
            f"http://{self._config.webhook_host}:{self._config.webhook_port}"
            f"{self._config.webhook_path}"
        )
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()

    def _duplicated(self, event_id: str | None) -> bool:
        """TTL 内见过的同 id 视为重复推送。

        过期判断按当前 id 单独做（O(1)），保证 TTL 外重发的同一 id 会被当作
        新事件处理；整表清过期项只在表长到阈值时做一次，避免每请求 O(n) 扫描。
        """
        if not event_id:
            return False
        now = monotonic()
        seen_at = self._seen.get(event_id)
        if seen_at is not None and now - seen_at <= self._DEDUP_TTL:
            return True
        if len(self._seen) >= self._DEDUP_SWEEP_AT:
            self._seen = {
                k: ts for k, ts in self._seen.items() if now - ts <= self._DEDUP_TTL
            }
        self._seen[event_id] = now
        return False

    async def _handle(self, request: web.Request) -> web.Response:
        body = await request.read()
        payload: Payload = ujson.loads(body)

        if payload.get("op") == Opcode.VALIDATION:
            logger.info("收到 Webhook 验证请求")
            ret = await self._protocol.on_frame(payload)
            if ret is None:
                return web.json_response(
                    {"error": "missing validation handler"}, status=500
                )
            return web.json_response(ret)

        timestamp = request.headers.get("X-Signature-Timestamp", "")
        signature = request.headers.get("X-Signature-Ed25519", "")
        if not verify_sig(self._config.app_secret, timestamp, signature, body):
            logger.warning("Webhook 验签失败")
            return web.json_response({"error": "invalid signature"}, status=401)

        event_id = payload.get("id")
        if isinstance(event_id, str) and self._duplicated(event_id):
            logger.info(f"Webhook 重复推送已跳过: {event_id}")
            return web.json_response({"opcode": 12})

        if payload.get("op") == Opcode.DISPATCH:
            await self._queue.put_event(payload)
        else:
            logger.warning(f"Webhook 收到非业务帧，已忽略: op={payload.get('op')}")
        return web.json_response({"opcode": 12})
