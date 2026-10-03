"""Bot 门面：构造校验、注册转发、注入约定与装配产物。"""

import pytest
from aiohttp import ClientSession

from qqbotsdk import (
    AccessToken,
    Bot,
    BotApi,
    Config,
    EventEmitter,
    EventQueue,
    Session,
    WebhookConnecter,
    WebsocketConnecter,
)
from qqbotsdk.payloads import GroupAtMessage


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPID", "102000000")
    monkeypatch.setenv("APPSECRET", "test-secret")


def test_construction_loads_config(env: None) -> None:
    bot = Bot()
    assert bot.config.app_id == "102000000"
    assert bot.config.connecter == "websocket"


def test_missing_credentials_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPID", raising=False)
    monkeypatch.delenv("APPSECRET", raising=False)
    with pytest.raises(ValueError):
        Bot()


async def test_on_registers_handler(env: None) -> None:
    bot = Bot()
    seen: list[str] = []

    @bot.on("GROUP_AT_MESSAGE_CREATE")
    async def on_message(msg: GroupAtMessage) -> None:
        seen.append(msg.content or "")

    payload = {
        "op": 0,
        "id": "evt-1",
        "t": "GROUP_AT_MESSAGE_CREATE",
        "d": {"id": "msg-1", "content": "你好", "group_openid": "g1"},
    }
    await bot._emitter.emit(payload)
    assert seen == ["你好"]


async def test_assemble_websocket_registers_all_services(
    env: None,
) -> None:
    bot = Bot()
    connecter = bot._assemble()
    assert isinstance(connecter, WebsocketConnecter)

    services = bot.services
    assert services[Bot] is bot
    assert services[EventEmitter] is bot._emitter
    assert services[EventQueue] is bot.queue
    assert services[Config] is bot.config
    assert isinstance(services[Session], Session)
    assert isinstance(services[ClientSession], ClientSession)
    assert isinstance(services[AccessToken], AccessToken)
    assert bot.api is services[BotApi]

    await bot._http.close()  # 清理装配出的连接池


async def test_assemble_webhook_builds_webhook_connecter(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONNECTER", "webhook")
    bot = Bot()
    connecter = bot._assemble()
    assert isinstance(connecter, WebhookConnecter)
    await bot._http.close()


async def test_bot_instance_injectable_into_handler(env: None) -> None:
    bot = Bot()
    bot._assemble()
    got: list[object] = []

    @bot.on("FRIEND_ADD")
    async def on_friend_add(bot: Bot) -> None:
        got.append(bot)

    payload = {
        "op": 0,
        "id": "evt-2",
        "t": "FRIEND_ADD",
        "d": {"openid": "u1"},
    }
    await bot._emitter.emit(payload)
    assert got == [bot]
    await bot._http.close()


def test_api_requires_start(env: None) -> None:
    bot = Bot()
    with pytest.raises(RuntimeError):
        _ = bot.api


async def test_call_api_delegates_to_api_request(env: None) -> None:
    bot = Bot()
    calls: list[tuple[str, str, dict]] = []

    class FakeApi:
        async def request(self, method: str, path: str, **kwargs: object) -> dict:
            calls.append((method, path, dict(kwargs)))
            return {"ok": True}

    bot._api = FakeApi()  # type: ignore[assignment]
    result = await bot.call_api("GET", "/users/@me", params={"a": "1"})
    assert result == {"ok": True}
    assert calls == [("GET", "/users/@me", {"params": {"a": "1"}})]
