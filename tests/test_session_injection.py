"""HTTP 会话注入点 (``set_session`` / ``use_session`` / ``get_session``) 的测试.

背景: ``session`` 曾经是模块级 ``QQBotSession`` 实例, 业务模块在 import 期就把
名字绑死了, 单测只能猴补各模块的模块属性, ``ctx.api`` 因此会真的连网. 现在模块级
``session`` 是稳定的转发代理, 真正的会话可以整体替换.
"""

from collections.abc import AsyncIterator

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer

from qqbotsdk.api import core
from qqbotsdk.api.core import QQBotResponse, QQBotSession


async def _ping(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


@pytest.fixture
async def fake_server() -> AsyncIterator[TestServer]:
    """本地假服务端, 不访问任何真实域名."""
    app = web.Application()
    app.router.add_get("/ping", _ping)
    server = TestServer(app)
    await server.start_server()
    try:
        yield server
    finally:
        await server.close()


def test_default_session_is_the_module_singleton() -> None:
    """没有注入时 get_session() 返回模块级默认单例."""
    assert core.get_session() is core._DEFAULT_SESSION


def test_proxy_forwards_to_injected_session() -> None:
    """模块级 session 代理把属性读取与方法调用都转发到注入的会话."""
    replacement = core.QQBotSession()
    try:
        core.set_session(replacement)
        assert core.session.closed is replacement.closed
        # 代理上没有显式定义 close 时也会转发过去
        assert core.session.close is not None
    finally:
        core.set_session(None)


def test_set_session_replaces_and_none_restores() -> None:
    """set_session 换掉会话, 传 None 恢复默认单例."""
    replacement = QQBotSession()
    try:
        core.set_session(replacement)
        assert core.get_session() is replacement
    finally:
        core.set_session(None)
    assert core.get_session() is core._DEFAULT_SESSION


def test_reset_session_restores_default() -> None:
    """reset_session 等价于 set_session(None)."""
    core.set_session(QQBotSession())
    core.reset_session()
    assert core.get_session() is core._DEFAULT_SESSION


def test_use_session_restores_on_exit() -> None:
    """use_session 退出后自动还原, 即使块内抛异常."""
    replacement = QQBotSession()
    with core.use_session(replacement) as got:
        assert got is replacement
        assert core.get_session() is replacement

    assert core.get_session() is core._DEFAULT_SESSION


def test_use_session_restores_after_exception() -> None:
    """块内抛异常时同样还原, 不把全局状态带脏."""
    replacement = QQBotSession()
    with pytest.raises(RuntimeError), core.use_session(replacement):
        raise RuntimeError("boom")
    assert core.get_session() is core._DEFAULT_SESSION


def test_proxy_delegates_to_current_session() -> None:
    """模块级 session 代理把方法调用与属性读取都转发到当前生效的会话.

    ``QQBotSession`` 带 ``__slots__`` 且方法不可重绑, 这里用一个最小的假会话替身
    验证转发链路, 不依赖真实网络.
    """

    class _FakeSession:
        @property
        def closed(self) -> bool:
            return True

        def post(self, url: str, **kwargs: object) -> tuple[str, str, object]:
            return ("post", url, kwargs)

    try:
        core.set_session(_FakeSession())  # type: ignore[arg-type]
        assert core.session.closed is True
        assert core.session.post("/x", json={"a": 1}) == (
            "post",
            "/x",
            {"json": {"a": 1}},
        )
        assert core.get_session().closed is True
    finally:
        core.set_session(None)


async def test_injected_session_is_used_by_proxy(fake_server: TestServer) -> None:
    """注入后, 通过模块级 session 发的请求真的落到注入的会话上.

    用假服务端的连接池发一次请求即可证明转发链路通了.
    """
    replacement = QQBotSession()
    replacement._client = ClientSession(  # pyright: ignore[reportPrivateUsage]
        base_url=str(fake_server.make_url("/")),
        response_class=QQBotResponse,
        raise_for_status=True,
    )
    try:
        with core.use_session(replacement):
            async with core.session.get("/ping") as response:
                payload = await response.json()
        assert payload == {"ok": True}
    finally:
        await replacement.close()


async def test_module_name_session_is_stable_across_injection() -> None:
    """注入不应改变 ``qqbotsdk.api.core.session`` 这个名字的指向.

    如果会变, 业务模块里的 ``from ... import session`` 就会继续指向旧对象.
    """
    original = core.session
    try:
        core.set_session(QQBotSession())
        assert core.session is original
    finally:
        core.set_session(None)
    assert core.session is original
