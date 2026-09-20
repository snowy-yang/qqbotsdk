"""WebSocket 接入的端到端集成测试：起一个假网关（token 接口 + gateway + ws），
真实跑通 HELLO → IDENTIFY → READY → 心跳 ACK → 业务事件分发的完整时序。"""

import asyncio
import json
from typing import Any

import pytest
from aiohttp import ClientSession, WSMsgType, web

from qqbotsdk.config import Config
from qqbotsdk.connecter import WebsocketConnecter
from qqbotsdk.emitter import EventEmitter
from qqbotsdk.payloads import GroupAtMessage
from qqbotsdk.queue import EventQueue
from qqbotsdk.session import Session
from qqbotsdk.token import AccessToken
from qqbotsdk.ws_protocol import WebsocketProtocol


class FakeGateway:
    """模拟 QQ 开放平台的鉴权、gateway 与 ws 协议行为。"""

    def __init__(self) -> None:
        self.identifies: list[dict] = []
        self.heartbeats = 0
        self.runner: web.AppRunner | None = None
        self.port = 0
        # 测试用同步点
        self.ready_sent = asyncio.Event()
        self.got_dispatch = asyncio.Event()

    async def start(self) -> None:
        app = web.Application()
        app.router.add_post("/app/getAppAccessToken", self._token)
        app.router.add_get("/gateway", self._gateway)
        app.router.add_get("/ws", self._ws)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        assert site._server is not None
        self.port = site._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        assert self.runner is not None
        await self.runner.cleanup()

    async def _token(self, request: web.Request) -> web.Response:
        return web.json_response({"access_token": "test-token", "expires_in": 9999999})

    async def _gateway(self, request: web.Request) -> web.Response:
        return web.json_response({"url": f"http://127.0.0.1:{self.port}/ws"})

    async def _ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        await ws.send_json({"op": 10, "d": {"heartbeat_interval": 300}})
        s = 0

        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                break
            payload: dict[str, Any] = json.loads(msg.data)
            op = payload.get("op")
            if op == 2:  # IDENTIFY
                self.identifies.append(payload)
                s += 1
                await ws.send_json(
                    {
                        "op": 0,
                        "s": s,
                        "t": "READY",
                        "d": {"session_id": "S1", "user": {"id": "bot"}},
                    }
                )
                self.ready_sent.set()
                # READY 之后立刻推一条业务事件
                s += 1
                await ws.send_json(
                    {
                        "op": 0,
                        "s": s,
                        "t": "GROUP_AT_MESSAGE_CREATE",
                        "d": {"content": "ping", "group_openid": "G1"},
                    }
                )
            elif op == 1:  # HEARTBEAT
                self.heartbeats += 1
                await ws.send_json({"op": 11})
        return ws


@pytest.mark.asyncio
async def test_websocket_end_to_end():
    gw = FakeGateway()
    await gw.start()
    try:
        config = Config(
            app_id="app",
            app_secret="secret",
            base_url=f"http://127.0.0.1:{gw.port}",
            timeout=None,  # type: ignore[arg-type]
            connecter="websocket",
            intents_file="no-such-intents.toml",  # 测试环境无配置，intents=0
            webhook_host="127.0.0.1",
            webhook_port=0,
            webhook_path="/x",
        )

        http = ClientSession(timeout=config.timeout)
        token = AccessToken(config, http)
        queue = EventQueue()
        session = Session()
        emitter = EventEmitter(queue)
        protocol = WebsocketProtocol(config, session, token)
        emitter.register_protocol(protocol)
        connecter = WebsocketConnecter(config, http, token, session, queue)

        received: list[GroupAtMessage] = []

        @emitter.on("GROUP_AT_MESSAGE_CREATE")
        async def on_msg(msg: GroupAtMessage) -> None:
            received.append(msg)
            gw.got_dispatch.set()

        dispatch_task = asyncio.create_task(emitter.dispatch())
        connect_task = asyncio.create_task(connecter.run())
        try:
            await asyncio.wait_for(gw.ready_sent.wait(), timeout=10)
            await asyncio.wait_for(gw.got_dispatch.wait(), timeout=10)
            await asyncio.sleep(0.5)  # 留出至少一个心跳周期（300ms）

            # READY 已被协议层捕获，session_id 用于后续 RESUME
            assert session.session_id == "S1"
            # 心跳定时器真实运行，服务端收到了 HEARTBEAT
            assert gw.heartbeats >= 1
            # IDENTIFY 形态正确（token 前缀 / shard / intents）
            identify = gw.identifies[0]
            assert identify["op"] == 2
            assert identify["d"]["token"] == "QQBot test-token"
            assert identify["d"]["intents"] == 0
            assert identify["d"]["shard"] == [0, 1]
            # 业务事件以 dataclass 形式分发到 handler
            assert len(received) == 1
            assert received[0].content == "ping"
            assert received[0].group_openid == "G1"
        finally:
            dispatch_task.cancel()
            connect_task.cancel()
            await asyncio.gather(dispatch_task, connect_task, return_exceptions=True)
            await http.close()
    finally:
        await gw.stop()
