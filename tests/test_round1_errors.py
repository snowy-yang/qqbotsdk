"""第一轮收尾: HTTP 状态映射、网关错误类型、网关地址错误的集成验证."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from aiohttp import ClientSession, WSMsgType, web

from qqbotsdk.api.core import CHECKED_HOSTS, QQBotResponse
from qqbotsdk.errors import QQBotAPIError, QQBotGatewayError
from qqbotsdk.ws import DEFAULT_INTENTS, QQBotWebSocket
from qqbotsdk.ws import client as ws_client_module


@pytest.fixture
async def api_server() -> AsyncIterator[tuple[str, str]]:
    """本地假 OpenAPI 服务端, 返回 (base_url, host)."""
    status_holder: dict[str, Any] = {"status": 200}

    async def handler(request: web.Request) -> web.Response:
        status = status_holder["status"]
        if status == 500:
            raise web.HTTPInternalServerError(text="boom")
        return web.json_response({"id": "1", "username": "bot"}, status=status)

    async def set_status(request: web.Request) -> web.Response:
        status_holder["status"] = int(request.query["status"])
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_get("/users/@me", handler)
    app.router.add_post("/__status", set_status)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    host = f"127.0.0.1:{port}"
    CHECKED_HOSTS.add("127.0.0.1")
    try:
        yield f"http://{host}", host
    finally:
        CHECKED_HOSTS.discard("127.0.0.1")
        await runner.cleanup()


async def test_http_500_raises_api_error(api_server: tuple[str, str]) -> None:
    base_url, _host = api_server
    async with ClientSession(
        base_url=base_url,
        raise_for_status=True,
        response_class=QQBotResponse,
    ) as client:
        await client.post("/__status", params={"status": "500"})
        with pytest.raises(QQBotAPIError) as excinfo:
            async with client.get("/users/@me"):
                pass
    assert excinfo.value.status == 500
    assert "HTTP 500" in excinfo.value.message


async def test_http_200_still_works(api_server: tuple[str, str]) -> None:
    base_url, _host = api_server
    async with (
        ClientSession(
            base_url=base_url,
            raise_for_status=True,
            response_class=QQBotResponse,
        ) as client,
        client.get("/users/@me") as resp,
    ):
        assert (await resp.json())["username"] == "bot"


async def test_gateway_rejects_fatal_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """关闭码 4914 不可重连, 必须通过 last_error 暴露具体原因."""

    # 网关鉴权要真实 token: 用例自带桩, 不依赖 .env 或外部网络.
    async def fake_token(*, force: bool = False) -> str:
        _ = force
        return "fake_token"

    monkeypatch.setattr(ws_client_module, "get_access_token", fake_token)

    async def handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({"op": 10, "d": {"heartbeat_interval": 300}})
        msg = await ws.receive(timeout=10)
        assert msg.type is WSMsgType.TEXT
        await ws.close(code=4914, message=b"banned")
        return ws

    app = web.Application()
    app.router.add_get("/ws", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    try:
        ws_client = QQBotWebSocket(
            intents=DEFAULT_INTENTS,
            url=f"http://127.0.0.1:{port}/ws",
            auto_reconnect=False,
        )
        async with ws_client:
            with pytest.raises(ConnectionError):
                await ws_client.wait_ready(timeout=10)
        error = ws_client.last_error
        assert isinstance(error, QQBotGatewayError)
        assert error.code == 4914
    finally:
        await runner.cleanup()


async def test_fetch_gateway_url_missing_url_raises_gateway_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(_request: web.Request) -> web.Response:
        return web.json_response({"urls": []})

    app = web.Application()
    app.router.add_get("/gateway", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]

    import qqbotsdk.api.core as core
    import qqbotsdk.api.gateway as gateway_module

    CHECKED_HOSTS.add("127.0.0.1")
    monkeypatch.setattr(core, "BASE_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(core.session, "_client", None)

    async with ClientSession(
        base_url=f"http://127.0.0.1:{port}",
        raise_for_status=True,
        response_class=QQBotResponse,
    ) as client:
        monkeypatch.setattr(gateway_module.session, "_client", client)
        with pytest.raises(QQBotGatewayError):
            await gateway_module.fetch_gateway_url()

    CHECKED_HOSTS.discard("127.0.0.1")
    await runner.cleanup()
    await asyncio.sleep(0)
