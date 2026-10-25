"""Bot 门面：构造校验、注册转发、注入约定与装配产物。"""

import asyncio

import pytest
from aiohttp import ClientSession

from qqbotsdk import (
    AccessToken,
    Bot,
    BotApi,
    Config,
    Connecter,
    EventEmitter,
    EventQueue,
    Intent,
    Session,
)
from qqbotsdk.payloads import GroupAtMessage

intent_mask = (1 << 25) | (1 << 26)


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPID", "102000000")
    monkeypatch.setenv("APPSECRET", "test-secret")


def test_construction_loads_config(env: None) -> None:
    bot = Bot()
    assert bot.config.app_id == "102000000"


def test_intents_param_overrides_env(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("INTENTS", str(1 << 0))
    bot = Bot(intents=intent_mask)
    assert bot.config.intents == intent_mask  # Bot 参数 > INTENTS 环境变量


def test_intents_env_picked_up(env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTENTS", str(intent_mask))
    assert Bot().config.intents == intent_mask


def test_intents_accepts_intent_flag(env: None) -> None:
    bot = Bot(intents=Intent.GROUP_AND_C2C_EVENT | Intent.INTERACTION)
    assert bot.config.intents == (1 << 25) | (1 << 26)


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


async def test_assemble_registers_all_services(
    env: None,
) -> None:
    bot = Bot()
    connecter = bot._assemble()
    assert isinstance(connecter, Connecter)

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


async def test_start_rejects_reentry(env: None) -> None:
    bot = Bot()
    bot._started = True
    with pytest.raises(RuntimeError, match="已在运行"):
        await bot.start()


async def test_start_cancels_dispatch_when_connecter_fails(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """连接器异常时 gather 不会自动取消 dispatch，start() 需显式收尾。"""
    bot = Bot()
    dispatch_started = asyncio.Event()
    dispatch_cancelled = asyncio.Event()

    async def fake_dispatch() -> None:
        dispatch_started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            dispatch_cancelled.set()
            raise

    class BoomConnecter:
        async def run(self) -> None:
            await dispatch_started.wait()
            raise RuntimeError("boom")

    monkeypatch.setattr(bot._emitter, "dispatch", fake_dispatch)
    monkeypatch.setattr(bot, "_assemble", lambda: BoomConnecter())

    with pytest.raises(RuntimeError, match="boom"):
        await bot.start()

    assert dispatch_cancelled.is_set()
    assert bot._started is False
