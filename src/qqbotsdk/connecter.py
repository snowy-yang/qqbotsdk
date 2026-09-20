"""连接适配器：把两种接入方式（WebSocket / Webhook）归一为事件流入、reply 队列流出。

- WebsocketConnecter：gateway 握手 + ws 长连接，指数退避重连（连接稳定
  存活才把退避归一，抖动的服务端不会被 1s 间隔反复探测）；心跳任务随
  连接生灭——HELLO 给出间隔后周期投递，断线即取消，不在 reply 队列堆积
  过期心跳；看门狗两层互补——receive 的静默超时抓"连接彻底静默"，
  收到消息时的 ACK 期限检查抓"有事件流但心跳已死"；
- WebhookConnecter：aiohttp server 接收回调，验签失败 401，
  按 payload id 做 60s TTL 去重，正常推送进事件队列；op=13 验证请求
  经注入的 handle_event 同步取得应答（HTTP 响应不走 reply 队列）。
"""

import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any, Protocol

import aiohttp
import ujson
from aiohttp import WSMsgType, web
from loguru import logger

from .config import Config
from .crypto import verify_sig
from .model import NOT_SET, Opcode, Payload, payload_of
from .queue import EventQueue
from .session import Session
from .token import AccessToken


class Connecter(Protocol):
    async def run(self) -> None: ...


class RateLimitError(RuntimeError):
    """gateway 接口触发频率限制（code=100017）。"""


class WebsocketConnecter:
    # 看门狗阈值（× 心跳间隔）：贴着 ACK 的自然节奏（1×）跑，误杀由 RESUME 兜底不丢消息；
    # 不能压到 1× 整——ACK 的自然间隔就是 1×，正常抖动会贴边误杀；TCP 下丢包表现为延迟而非静默
    _SILENCE_FACTOR = 1.1
    _ACK_FACTOR = 1.2
    # 连接存活超过该时长才算稳定，才把退避归一
    _STABLE_SECONDS = 60.0

    def __init__(
        self,
        config: Config,
        http: aiohttp.ClientSession,
        token: AccessToken,
        session: Session,
        queue: EventQueue,
    ) -> None:
        self._config = config
        self._http = http
        self._token = token
        self._session = session
        self._queue = queue

    async def run(self) -> None:
        backoff: float = 1
        while True:
            try:
                lived = await self._connect()
                if lived >= self._STABLE_SECONDS:
                    backoff = 1
            except RateLimitError:
                logger.warning("gateway 触发频率限制")
                backoff = 60
            except TimeoutError:
                logger.warning("心跳超时，触发看门狗重连")
            except (aiohttp.ClientError, RuntimeError) as e:
                logger.warning(f"WebSocket 连接异常: {e}")
            logger.info(f"{backoff}s 后重连")
            await asyncio.sleep(backoff)
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
            logger.info("WebSocket 已连接")
            # HELLO 才给出心跳间隔；receive 解析到后经 Future 交给心跳任务
            interval: asyncio.Future[float] = asyncio.get_running_loop().create_future()
            receive = asyncio.create_task(self.receive_helper(ws, interval))
            reply = asyncio.create_task(self.reply_helper(ws))
            heartbeat = asyncio.create_task(self.heartbeat_helper(interval))
            try:
                await receive
            finally:
                reply.cancel()
                heartbeat.cancel()
            logger.info("WebSocket 已断开")
        return monotonic() - started

    async def receive_helper(
        self, ws: aiohttp.ClientWebSocketResponse, interval_fut: asyncio.Future[float]
    ) -> None:
        interval: float = 0
        last_ack = monotonic()
        while not ws.closed:
            # HELLO 前不设超时；之后按看门狗阈值等待任何消息
            msg = await ws.receive(timeout=interval * self._SILENCE_FACTOR or None)
            if msg.type != WSMsgType.TEXT:
                logger.warning(f"WebSocket 收到非文本帧，连接终止: {msg.type}")
                break
            data: Payload = msg.json(loads=ujson.loads)
            op = data.get("op")
            if op == Opcode.HELLO:
                d = data.get("d")
                if isinstance(d, dict):
                    interval = d.get("heartbeat_interval", 41_250) / 1000
                    if not interval_fut.done():
                        interval_fut.set_result(interval)
            elif op == Opcode.HEARTBEAT_ACK:
                last_ack = monotonic()
            await self._queue.put_event(data)
            if op in (Opcode.RECONNECT, Opcode.INVALID_SESSION):
                break
            if monotonic() - last_ack > interval * self._ACK_FACTOR:
                raise TimeoutError

    async def heartbeat_helper(self, interval_fut: asyncio.Future[float]) -> None:
        """HELLO 给出间隔后周期投递心跳；断线随任务取消，不堆积过期心跳。"""
        interval = await interval_fut
        while True:
            await asyncio.sleep(interval)
            # 服务端不会推送 op=1，心跳只由本任务经 reply 队列发出
            await self._queue.put_reply(payload_of(Opcode.HEARTBEAT, self._session.seq))

    async def reply_helper(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while not ws.closed:
            payload: Payload = await self._queue.get_reply()
            body = {k: v for k, v in payload.items() if v != NOT_SET}
            try:
                await ws.send_json(body)
            except (aiohttp.ClientError, ConnectionError) as e:
                logger.warning(f"WebSocket 发送失败，丢弃该帧: {body} ({e})")


class WebhookConnecter:
    _DEDUP_TTL = 60

    def __init__(
        self,
        config: Config,
        queue: EventQueue,
        handle_event: Callable[[Payload], Awaitable[Any]],
    ) -> None:
        """handle_event 供 op=13 验证请求同步取应答（通常传 emitter.handle）；
        与 ws 侧对齐，本类只依赖队列与该回调，不感知 EventEmitter。"""
        self._config = config
        self._queue = queue
        self._handle_event = handle_event
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
        if not event_id:
            return False
        now = monotonic()
        for key in [k for k, ts in self._seen.items() if now - ts > self._DEDUP_TTL]:
            del self._seen[key]
        if event_id in self._seen:
            return True
        self._seen[event_id] = now
        return False

    async def _handle(self, request: web.Request) -> web.Response:
        body = await request.read()
        payload: Payload = ujson.loads(body)

        if payload.get("op") == Opcode.VALIDATION:
            logger.info("收到 Webhook 验证请求")
            ret = await self._handle_event(payload)
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

        await self._queue.put_event(payload)
        return web.json_response({"opcode": 12})
