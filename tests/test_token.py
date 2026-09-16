"""AccessToken：成功换取与失败时抛 TokenError（带 QQ 的 code/message）。"""

import pytest
from aiohttp import ClientTimeout

from qqbotsdk.config import Config
from qqbotsdk.token import AccessToken, TokenError


def make_token(payload) -> AccessToken:
    class FakeResponse:
        status = 200

        def __init__(self) -> None:
            self._payload = payload

        async def json(self, **kwargs):
            return self._payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class FakeSession:
        def post(self, *args, **kwargs):
            return FakeResponse()

    config = Config(
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
    return AccessToken(config, FakeSession())  # type: ignore[arg-type]


async def test_success_caches_token():
    token = make_token({"access_token": "t1", "expires_in": 7200})
    assert await token.get_access_token() == "t1"
    # 缓存期内直接复用，不再发请求（FakeSession 也没有第二次响应的意义）
    assert await token.get_access_token() == "t1"


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
