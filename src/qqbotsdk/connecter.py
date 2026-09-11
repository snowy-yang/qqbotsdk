"""连接适配器：把两种接入方式（WebSocket / Webhook）归一为事件流入、reply 队列流出。

- WebsocketConnecter：gateway 握手 + ws 长连接，指数退避重连；
  看门狗两层互补——receive 的静默超时抓"连接彻底静默"，
  收到消息时的 ACK 期限检查抓"有事件流但心跳已死"；
- WebhookConnecter：aiohttp server 接收回调，验签失败 401，
  按 payload id 做 60s TTL 去重，正常推送进事件队列。
"""

import asyncio
import json
from time import monotonic
from typing import Protocol

import aiohttp
from aiohttp import WSMsgType, web
from loguru import logger

from .config import Config
from .crypto import verify_sig
from .emitter import EventEmitter
from .model import NOT_SET, Opcode, Payload
from .queue import EventQueue
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

    def __init__(
        self,
        config: Config,
        http: aiohttp.ClientSession,
        token: AccessToken,
        queue: EventQueue,
    ) -> None:
        self._config = config
        self._http = http
        self._token = token
        self._queue = queue

    async def run(self) -> None:
        backoff: float = 1
        while True:
            try:
                await self._connect()
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

    async def _connect(self) -> None:
        access_token = await self._token.get_access_token()
        headers = {"Authorization": f"QQBot {access_token}"}

        async with self._http.get(
            f"{self._config.base_url}/gateway", headers=headers
        ) as resp:
            data = await resp.json()

        if data.get("code") == 100017:
            raise RateLimitError
        gateway = data.get("url")
        if not gateway:
            raise RuntimeError(f"获取 gateway 失败: {data}")

        async with self._http.ws_connect(gateway, headers=headers) as ws:
            logger.info("WebSocket 已连接")
            receive = asyncio.create_task(self.receive_helper(ws))
            reply = asyncio.create_task(self.reply_helper(ws))
            try:
                await receive
            finally:
                reply.cancel()
            logger.info("WebSocket 已断开")

    async def receive_helper(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        interval: float = 0
        last_ack = monotonic()
        while not ws.closed:
            # HELLO 前不设超时；之后按看门狗阈值等待任何消息
            msg = await ws.receive(timeout=interval * self._SILENCE_FACTOR or None)
            if msg.type != WSMsgType.TEXT:
                logger.warning(f"WebSocket 收到非文本帧，连接终止: {msg.type}")
                break
            data: Payload = msg.json()
            op = data.get("op")
            if op == Opcode.HELLO:
                d = data.get("d")
                if isinstance(d, dict):
                    interval = d.get("heartbeat_interval", 41_250) / 1000
            elif op == Opcode.HEARTBEAT_ACK:
                last_ack = monotonic()
            await self._queue.put_event(data)
            if op in (Opcode.RECONNECT, Opcode.INVALID_SESSION):
                break
            if monotonic() - last_ack > interval * self._ACK_FACTOR:
                raise TimeoutError

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
        self, config: Config, emitter: EventEmitter, queue: EventQueue
    ) -> None:
        self._config = config
        self._emitter = emitter
        self._queue = queue
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
        payload: Payload = json.loads(body)

        if payload.get("op") == Opcode.VALIDATION:
            logger.info("收到 Webhook 验证请求")
            ret = await self._emitter.handle(payload)
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
