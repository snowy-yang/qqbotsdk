"""AccessToken：缓存复用、失败抛 TokenError、并发只换取一次、invalidate 强制刷新。"""

import asyncio

import pytest
from aiohttp import ClientTimeout

from qqbotsdk.config import Config
from qqbotsdk.token import AccessToken, TokenError


def make_config() -> Config:
    return Config(
        app_id="id",
        app_secret="s",
        base_url="https://x",
        timeout=ClientTimeout(total=5),
        connecter="websocket",
        intents_file="intents.toml",
        webhook_host="0.0.0.0",
        webhook_port=8080,
        webhook_path="/qqbot/webhook",
    )


class FakeResponse:
    def __init__(self, payload, status: int = 200) -> None:
        self.status = status
        self._payload = payload

    async def json(self, **kwargs):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """按序弹出响应体，记录 post 次数。"""

    def __init__(self, *payloads) -> None:
        self._payloads = list(payloads)
        self.posts = 0

    def post(self, *args, **kwargs):
        self.posts += 1
        return FakeResponse(self._payloads.pop(0))


def make_token(*payloads) -> AccessToken:
    return AccessToken(make_config(), FakeSession(*payloads))  # type: ignore[arg-type]


async def test_success_caches_token():
    session = FakeSession({"access_token": "t1", "expires_in": 7200})
    token = AccessToken(make_config(), session)  # type: ignore[arg-type]
    assert await token.get_access_token() == "t1"
    # 缓存期内直接复用，不再发请求
    assert await token.get_access_token() == "t1"
    assert session.posts == 1


async def test_error_payload_raises_token_error():
    token = make_token({"code": 11253, "message": "invalid appid or secret"})
    with pytest.raises(TokenError) as exc_info:
        await token.get_access_token()
    assert exc_info.value.code == 11253
    assert exc_info.value.message == "invalid appid or secret"
    assert "invalid appid or secret" in str(exc_info.value)


async def test_non_dict_payload_raises_token_error():
    token = make_token("gateway busy")
    with pytest.raises(TokenError) as exc_info:
        await token.get_access_token()
    assert exc_info.value.message == "gateway busy"


async def test_concurrent_first_fetch_only_requests_once():
    session = FakeSession({"access_token": "t1", "expires_in": 7200})
    token = AccessToken(make_config(), session)  # type: ignore[arg-type]

    results = await asyncio.gather(*(token.get_access_token() for _ in range(5)))
    assert results == ["t1"] * 5
    assert session.posts == 1  # 双重检查锁：并发首调只换取一次


async def test_invalidate_forces_refetch():
    session = FakeSession(
        {"access_token": "t1", "expires_in": 7200},
        {"access_token": "t2", "expires_in": 7200},
    )
    token = AccessToken(make_config(), session)  # type: ignore[arg-type]
    assert await token.get_access_token() == "t1"
    token.invalidate()  # 模拟服务端提前作废
    assert await token.get_access_token() == "t2"
    assert session.posts == 2
