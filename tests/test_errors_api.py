"""OpenAPI 统一错误体系与空响应(204)处理的回归测试.

所有场景都在 ``127.0.0.1`` 的本地假服务端上运行, 不访问任何真实域名, 也不读取凭证.
"""

from collections.abc import AsyncIterator

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer

from qqbotsdk.api import core
from qqbotsdk.api.core import QQBotResponse
from qqbotsdk.errors import QQBotAPIError

# 本地假服务端监听的 host, 测试里临时加入 CHECKED_HOSTS 以走同一条检查逻辑
LOCAL_HOST = "127.0.0.1"


async def _ok(_request: web.Request) -> web.Response:
    return web.json_response({"id": "123", "username": "test-bot"})


async def _ok_zero_code(_request: web.Request) -> web.Response:
    return web.json_response({"code": 0, "data": {"id": "123"}})


async def _err_code(_request: web.Request) -> web.Response:
    return web.json_response(
        {
            "err_code": 40034005,
            "message": "回复消息msg_id已过期",
            "trace_id": "abc",
        }
    )


async def _err_code_with_header(_request: web.Request) -> web.Response:
    return web.json_response(
        {"err_code": 40034005, "message": "回复消息msg_id已过期", "trace_id": "body"},
        headers={"X-Tps-trace-ID": "header-trace"},
    )


async def _code(_request: web.Request) -> web.Response:
    return web.json_response({"code": 100016, "message": "invalid appid or secret"})


async def _empty(_request: web.Request) -> web.Response:
    return web.Response(status=204)


async def _accepted(_request: web.Request) -> web.Response:
    return web.Response(status=202)


async def _created_error(_request: web.Request) -> web.Response:
    return web.json_response(
        {"err_code": 40054003, "message": "消息已过期", "trace_id": "created"},
        status=201,
    )


async def _accepted_error(_request: web.Request) -> web.Response:
    return web.json_response({"message": "请求过于频繁"}, status=202)


async def _plain_text(_request: web.Request) -> web.Response:
    return web.Response(text="upstream timeout", content_type="text/plain")


@pytest.fixture
async def api_server() -> AsyncIterator[TestServer]:
    """本地假 OpenAPI 服务端."""
    app = web.Application()
    app.router.add_get("/ok", _ok)
    app.router.add_get("/ok-zero-code", _ok_zero_code)
    app.router.add_get("/err-code", _err_code)
    app.router.add_get("/err-code-header", _err_code_with_header)
    app.router.add_get("/code", _code)
    app.router.add_delete("/empty", _empty)
    app.router.add_post("/accepted", _accepted)
    app.router.add_post("/created-error", _created_error)
    app.router.add_post("/accepted-error", _accepted_error)
    app.router.add_get("/plain", _plain_text)

    server = TestServer(app)
    await server.start_server()
    try:
        yield server
    finally:
        await server.close()


def _client(server: TestServer) -> ClientSession:
    return ClientSession(
        base_url=str(server.make_url("/")),
        response_class=QQBotResponse,
        raise_for_status=True,
    )


@pytest.fixture
async def api_session(
    api_server: TestServer,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[ClientSession]:
    """把本地 host 加入检查名单, 从而复用 OpenAPI 的响应处理逻辑."""
    monkeypatch.setattr(core, "CHECKED_HOSTS", {LOCAL_HOST})
    client = _client(api_server)
    try:
        yield client
    finally:
        await client.close()


async def test_err_code_body_raises(api_session: ClientSession) -> None:
    """200 也可能是业务错误: err_code 非零要抛 QQBotAPIError."""
    with pytest.raises(QQBotAPIError) as excinfo:
        async with api_session.get("/err-code") as resp:
            await resp.json()

    error = excinfo.value
    assert error.status == 200
    assert error.err_code == 40034005
    assert error.message == "回复消息msg_id已过期"
    assert error.trace_id == "abc"
    assert "40034005" in str(error)
    assert "abc" in str(error)


async def test_code_body_raises(api_session: ClientSession) -> None:
    """换取凭证接口用 code 表示错误, 同样要覆盖."""
    with pytest.raises(QQBotAPIError) as excinfo:
        async with api_session.get("/code") as resp:
            await resp.json()

    error = excinfo.value
    assert error.status == 200
    assert error.err_code == 100016
    assert error.message == "invalid appid or secret"
    assert error.trace_id is None


async def test_success_body_returned(api_session: ClientSession) -> None:
    async with api_session.get("/ok") as resp:
        result = await resp.json()

    assert isinstance(result, dict)
    assert result == {"id": "123", "username": "test-bot"}


async def test_zero_code_is_not_error(api_session: ClientSession) -> None:
    async with api_session.get("/ok-zero-code") as resp:
        result = await resp.json()

    assert result == {"code": 0, "data": {"id": "123"}}


async def test_204_empty_body_returns_empty_dict(api_session: ClientSession) -> None:
    """回归: 204 无 body 时原来的实现会抛 ContentTypeError, 删除类接口必崩."""
    async with api_session.delete("/empty") as resp:
        assert resp.status == 204
        result = await resp.json()

    assert result == {}


async def test_201_error_body_raises(api_session: ClientSession) -> None:
    with pytest.raises(QQBotAPIError) as excinfo:
        async with api_session.post("/created-error") as resp:
            await resp.json()

    error = excinfo.value
    assert error.status == 201
    assert error.err_code == 40054003
    assert error.message == "消息已过期"
    assert error.trace_id == "created"


async def test_202_empty_body_returns_empty_dict(api_session: ClientSession) -> None:
    async with api_session.post("/accepted") as resp:
        assert resp.status == 202
        result = await resp.json()

    assert result == {}


async def test_202_error_body_raises(api_session: ClientSession) -> None:
    with pytest.raises(QQBotAPIError) as excinfo:
        async with api_session.post("/accepted-error") as resp:
            await resp.json()

    error = excinfo.value
    assert error.status == 202
    assert error.message == "请求过于频繁"


async def test_non_json_content_type_returns_empty_dict(
    api_session: ClientSession,
) -> None:
    async with api_session.get("/plain") as resp:
        result = await resp.json()

    assert result == {}


async def test_trace_id_header_takes_precedence(api_session: ClientSession) -> None:
    with pytest.raises(QQBotAPIError) as excinfo:
        async with api_session.get("/err-code-header") as resp:
            await resp.json()

    assert excinfo.value.trace_id == "header-trace"


async def test_unchecked_host_skips_error_check(api_server: TestServer) -> None:
    """默认只检查 OpenAPI 域名, 其它域名(COS 等)保持 aiohttp 原行为."""
    client = _client(api_server)
    try:
        async with client.get("/err-code") as resp:
            result = await resp.json()
    finally:
        await client.close()

    assert isinstance(result, dict)
    assert result["err_code"] == 40034005


async def test_session_injects_response_class() -> None:
    """业务代码使用的单例会话必须注入 QQBotResponse, 否则上面的检查不会生效."""
    bot_session = core.QQBotSession()
    try:
        # aiohttp 没有公开的 response_class 读取入口, 这里直接看私有属性
        assert bot_session.client._response_class is QQBotResponse
    finally:
        await bot_session.close()
