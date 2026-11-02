"""网关地址获取的测试.

全部走本地假服务端 (只监听回环地址), 既不访问真实域名, 也不需要真实凭证:
- ``fetch_gateway_url()`` 能取到 ``GET /gateway`` 返回的 ``url``, 缺失时抛 RuntimeError;
- ``QQBotWebSocket`` 省略 ``url`` 时每次建连前都会取一次地址, 显式传入时不会取.
"""

import asyncio
import json
from typing import Any

import pytest
from aiohttp import WSMsgType, web

from qqbotsdk.api import core
from qqbotsdk.api.gateway import fetch_gateway_url
from qqbotsdk.errors import QQBotGatewayError
from qqbotsdk.ws import QQBotWebSocket
from qqbotsdk.ws import client as client_mod

# 假响应里的网关地址, .invalid 是保留域名, 不可能被真实解析
FAKE_GATEWAY_URL = "wss://example.invalid/websocket"


async def _receive_json(
    ws: web.WebSocketResponse,
    timeout: float = 5.0,
) -> dict[str, Any]:
    msg = await asyncio.wait_for(ws.receive(), timeout=timeout)
    assert msg.type is WSMsgType.TEXT
    payload: dict[str, Any] = json.loads(msg.data)
    return payload


async def _fake_token(*, force: bool = False) -> str:
    """替换真实的凭证获取, 保证测试不会发出取 token 的请求."""
    return "test-token"


class FakeHttpServer:
    """按预设 JSON 响应任意 GET 的本地服务端."""

    def __init__(self, body: Any) -> None:
        self._body = body
        self._runner: web.AppRunner | None = None
        self.base_url = ""
        self.paths: list[str] = []

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/{tail:.*}", self._handle)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        host, port = self._runner.addresses[0]
        self.base_url = f"http://{host}:{port}"

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _handle(self, request: web.Request) -> web.Response:
        self.paths.append(request.path)
        return web.json_response(self._body)


class FakeGateway:
    """本地假网关: Hello -> Identify -> READY, 首连后以 4009 断开以便触发 Resume."""

    def __init__(self) -> None:
        self._runner: web.AppRunner | None = None
        self.ws_url = ""
        self.connections = 0
        self.payloads: list[dict[str, Any]] = []

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/websocket", self._handle)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        host, port = self._runner.addresses[0]
        self.ws_url = f"ws://{host}:{port}/websocket"

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _handle(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        index = self.connections
        self.connections += 1
        # 心跳间隔取大值, 让测试期间不触发心跳
        await ws.send_json({"op": 10, "d": {"heartbeat_interval": 45000}})
        self.payloads.append(await _receive_json(ws))
        if index == 0:
            await ws.send_json(
                {"op": 0, "s": 1, "t": "READY", "d": {"session_id": "sess-1"}}
            )
            await asyncio.sleep(0.1)
            await ws.close(code=4009, message=b"resume please")
        else:
            await ws.send_json({"op": 0, "s": 2, "t": "RESUMED", "d": {}})
            await asyncio.sleep(0.2)
            await ws.close()
        return ws


async def test_fetch_gateway_url_returns_url(monkeypatch: pytest.MonkeyPatch) -> None:
    server = FakeHttpServer({"url": FAKE_GATEWAY_URL})
    await server.start()
    await core.session.close()
    # 把 HTTP 会话指向本地假服务端, 不碰真实域名
    monkeypatch.setattr(core, "BASE_URL", server.base_url)
    try:
        url = await fetch_gateway_url()
    finally:
        await core.session.close()
        await server.stop()

    assert url == FAKE_GATEWAY_URL
    assert server.paths == ["/gateway"]


async def test_fetch_gateway_url_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    # 没有 code 字段, 因此不会走业务错误分支, 纯粹验证 url 缺失
    server = FakeHttpServer({"message": "success"})
    await server.start()
    await core.session.close()
    monkeypatch.setattr(core, "BASE_URL", server.base_url)
    try:
        with pytest.raises(QQBotGatewayError, match="网关响应缺少 url"):
            await fetch_gateway_url()
    finally:
        await core.session.close()
        await server.stop()

    assert server.paths == ["/gateway"]


async def test_websocket_fetches_url_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway()
    await gateway.start()
    await core.session.close()
    calls: list[str] = []

    async def fake_fetch() -> str:
        calls.append("called")
        return gateway.ws_url

    monkeypatch.setattr(client_mod, "fetch_gateway_url", fake_fetch)
    monkeypatch.setattr(client_mod, "get_access_token", _fake_token)
    try:
        events: list[str] = []
        async with QQBotWebSocket(backoff_base=0.01, backoff_max=0.05) as ws:
            first = await asyncio.wait_for(anext(ws), timeout=5)
            events.append(first.t or "")
            second = await asyncio.wait_for(anext(ws), timeout=5)
            events.append(second.t or "")
    finally:
        await core.session.close()
        await gateway.stop()

    assert events == ["READY", "RESUMED"]
    # 首次建连与 4009 重连各取一次地址
    assert len(calls) >= 2
    assert len(calls) == gateway.connections
    assert gateway.payloads[0]["op"] == 2
    assert gateway.payloads[0]["d"]["shard"] == [0, 1]
    assert gateway.payloads[1]["op"] == 6
    assert gateway.payloads[1]["d"]["session_id"] == "sess-1"
    assert gateway.payloads[1]["d"]["seq"] == 1


async def test_websocket_skips_fetch_with_explicit_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway()
    await gateway.start()
    await core.session.close()

    async def fail_fetch() -> str:
        raise AssertionError("显式传入 url 时不应调用 fetch_gateway_url")

    monkeypatch.setattr(client_mod, "fetch_gateway_url", fail_fetch)
    monkeypatch.setattr(client_mod, "get_access_token", _fake_token)
    try:
        events: list[str] = []
        async with QQBotWebSocket(
            url=gateway.ws_url,
            auto_reconnect=False,
            backoff_base=0.01,
        ) as ws:
            event = await asyncio.wait_for(anext(ws), timeout=5)
            events.append(event.t or "")
            # 首连被 4009 关闭, 关闭自动重连后迭代应结束
            with pytest.raises(StopAsyncIteration):
                await asyncio.wait_for(anext(ws), timeout=5)
    finally:
        await core.session.close()
        await gateway.stop()

    assert events == ["READY"]
    assert gateway.connections == 1
    assert gateway.payloads[0]["op"] == 2
    assert gateway.payloads[0]["d"]["shard"] == [0, 1]
