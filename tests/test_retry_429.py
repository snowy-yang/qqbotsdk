"""HTTP 429 自动重试的测试: 全部打本地假服务端, 不访问真实域名.

覆盖: 429 后自动重试直到成功、重试耗尽后抛 ``QQBotAPIError``、非 429 不重试、
``Retry-After`` 优先于指数退避. 测试把 ``RETRY_BASE_SECONDS`` 压到极小, 不真睡.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from aiohttp import web

from qqbotsdk.api import core
from qqbotsdk.errors import QQBotAPIError

# 本地假服务端监听的 host, 加入 CHECKED_HOSTS 以复用 OpenAPI 的响应处理逻辑
LOCAL_HOST = "127.0.0.1"


class FakeApiServer:
    """按脚本返回响应序列的本地 HTTP 服务端, 并统计请求次数."""

    def __init__(self, script: list[tuple[int, dict[str, str]]]) -> None:
        """script 为每次请求的 (状态码, 响应头), 用完后重复最后一项."""
        self._script = script
        self._runner: web.AppRunner | None = None
        self.base_url = ""
        self.requests = 0

    async def start(self) -> None:
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self._handle)
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
        index = min(self.requests, len(self._script) - 1)
        self.requests += 1
        status, headers = self._script[index]
        if status == 200:
            return web.json_response({"ok": True}, headers=headers)
        return web.json_response(
            {"message": "rate limited"},
            status=status,
            headers=headers,
        )


@asynccontextmanager
async def _fake_api(
    monkeypatch: pytest.MonkeyPatch,
    script: list[tuple[int, dict[str, str]]],
    *,
    retry_base: float = 0.0,
    max_retries: int | None = None,
) -> AsyncIterator[FakeApiServer]:
    """把全局 session 指向本地假服务端, 并压小重试退避."""
    server = FakeApiServer(script)
    await server.start()
    await core.session.close()
    monkeypatch.setattr(core, "BASE_URL", server.base_url)
    monkeypatch.setattr(core, "CHECKED_HOSTS", {LOCAL_HOST})
    monkeypatch.setattr(core, "RETRY_BASE_SECONDS", retry_base)
    if max_retries is not None:
        monkeypatch.setattr(core, "MAX_RETRIES", max_retries)
    try:
        yield server
    finally:
        await core.session.close()
        await server.stop()


async def test_retry_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """前两次 429, 第三次 200: 自动重试后成功, 且 Retry-After 优先于退避常量."""
    script: list[tuple[int, dict[str, str]]] = [
        (429, {"Retry-After": "0"}),
        (429, {"Retry-After": "0"}),
        (200, {}),
    ]
    # 退避基准故意设大: 若没优先用 Retry-After, 这里会超时失败而不是慢跑
    async with _fake_api(monkeypatch, script, retry_base=5.0) as server:
        async with asyncio.timeout(2):
            async with core.session.get("/limited") as resp:
                body: Any = await resp.json()
                assert resp.status == 200

    assert body == {"ok": True}
    assert server.requests == 3


async def test_retry_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    """一直 429: 重试耗尽后抛 QQBotAPIError(status=429), 请求次数为 MAX_RETRIES + 1."""
    script: list[tuple[int, dict[str, str]]] = [(429, {"Retry-After": "0"})]
    async with _fake_api(monkeypatch, script, max_retries=2) as server:
        with pytest.raises(QQBotAPIError) as excinfo:
            async with core.session.get("/limited") as resp:
                await resp.json()

    assert excinfo.value.status == 429
    assert server.requests == core.MAX_RETRIES + 1
    assert server.requests == 3


async def test_server_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """500 不重试: 只请求一次就抛错."""
    script: list[tuple[int, dict[str, str]]] = [(500, {})]
    async with _fake_api(monkeypatch, script) as server:
        with pytest.raises(QQBotAPIError) as excinfo:
            async with core.session.get("/broken") as resp:
                await resp.json()

    assert excinfo.value.status == 500
    assert server.requests == 1


async def test_post_is_retried_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 表示请求未被处理, POST 也会重试."""
    script: list[tuple[int, dict[str, str]]] = [
        (429, {"Retry-After": "0"}),
        (200, {}),
    ]
    async with _fake_api(monkeypatch, script) as server:
        request = core.session.post("/send", json={"content": "hi"})
        async with request as resp:
            body: Any = await resp.json()
            assert resp.status == 200

    assert body == {"ok": True}
    assert server.requests == 2


async def test_await_form_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """``resp = await session.get(...)`` 的旧写法不被重试包装破坏."""
    script: list[tuple[int, dict[str, str]]] = [(200, {})]
    async with _fake_api(monkeypatch, script) as server:
        resp = await core.session.get("/ok")
        try:
            assert resp.status == 200
            body: Any = await resp.json()
        finally:
            resp.release()

    assert body == {"ok": True}
    assert server.requests == 1
