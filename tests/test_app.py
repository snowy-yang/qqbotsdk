"""qqbotsdk.app 的测试: 全部打本地假网关, 不访问真实域名.

覆盖: 注册顺序与通配顺序, Context 解析结果与 openid 取值, 洋葱中间件顺序与
拦截, handler 返回 False 阻断, 异常进 on_error 且后续事件照常处理,
ctx.reply 的锚点与 msg_seq 递增, ctx.send 不带锚点, stop 后无残留任务.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from aiohttp import WSMsgType, web

from qqbotsdk.api import core
from qqbotsdk.api import user as user_api
from qqbotsdk.api.group import messages as group_messages
from qqbotsdk.app import Bot, Context
from qqbotsdk.app.dispatch import TASK_NAME
from qqbotsdk.model.event.group import GroupAtMessageCreateEvent
from qqbotsdk.model.group.messages import SendGroupMessagesResponse
from qqbotsdk.model.user.messages import SendUserMessagesResponse
from qqbotsdk.ws import client as client_mod

GROUP_OPENID = "GROUP-1"
USER_OPENID = "USER-1"
MESSAGE_ID = "MSG-1"
TIMESTAMP = "2026-11-01T10:00:00+08:00"


def _group_d(message_id: str = MESSAGE_ID) -> dict[str, Any]:
    return {
        "id": message_id,
        "content": "你好",
        "group_openid": GROUP_OPENID,
        "author": {
            "id": "AUTHOR-1",
            "member_openid": "MEMBER-1",
            "member_role": "member",
            "username": "小明",
            "bot": False,
        },
        "message_type": 0,
        "timestamp": TIMESTAMP,
    }


def _c2c_d() -> dict[str, Any]:
    return {
        "id": "C2C-MSG-1",
        "content": "你好",
        "author": {
            "id": "AUTHOR-1",
            "user_openid": USER_OPENID,
            "username": "小红",
            "bot": False,
        },
        "message_type": 0,
        "timestamp": TIMESTAMP,
    }


def _group_dispatch(
    event_id: str = "evt-1", message_id: str = MESSAGE_ID
) -> dict[str, Any]:
    return {"t": "GROUP_AT_MESSAGE_CREATE", "id": event_id, "d": _group_d(message_id)}


def _c2c_dispatch(event_id: str = "evt-c2c") -> dict[str, Any]:
    return {"t": "C2C_MESSAGE_CREATE", "id": event_id, "d": _c2c_d()}


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


async def _wait_until(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    """轮询等待条件成立, 不依赖任务调度顺序."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("等待条件超时")


class FakeGateway:
    """本地假网关: Hello -> Identify -> READY -> 若干 Dispatch -> 等客户端关闭."""

    def __init__(self, dispatches: list[dict[str, Any]]) -> None:
        self._dispatches = dispatches
        self._runner: web.AppRunner | None = None
        self.ws_url = ""
        self.connections = 0
        self.identify: dict[str, Any] | None = None

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
        self.connections += 1
        # 心跳间隔取大值, 让测试期间不触发心跳
        await ws.send_json({"op": 10, "d": {"heartbeat_interval": 45000}})
        self.identify = await _receive_json(ws)
        await ws.send_json(
            {"op": 0, "s": 1, "t": "READY", "d": {"session_id": "sess-1"}}
        )
        for seq, event in enumerate(self._dispatches, start=2):
            frame: dict[str, Any] = {
                "op": 0,
                "s": seq,
                "t": event["t"],
                "d": event.get("d", {}),
            }
            if event.get("id") is not None:
                frame["id"] = event["id"]
            await ws.send_json(frame)
        # 一直等到客户端主动关闭
        while True:
            msg = await ws.receive()
            if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                break
            if msg.type is WSMsgType.ERROR:
                break
        await ws.close()
        return ws


class Harness:
    """假网关 + Bot 的启动与收尾封装."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        dispatches: list[dict[str, Any]],
    ) -> None:
        self._monkeypatch = monkeypatch
        self.gateway = FakeGateway(dispatches)
        self.bot: Bot | None = None
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> "Harness":
        self._monkeypatch.setattr(client_mod, "get_access_token", _fake_token)
        await self.gateway.start()
        await core.session.close()
        return self

    def start(self, bot: Bot) -> Bot:
        """在后台启动 Bot, 返回它自己方便链式使用."""
        self.bot = bot
        self._task = asyncio.create_task(bot.start())
        return bot

    async def __aexit__(self, *_exc: object) -> None:
        if self.bot is not None:
            await self.bot.stop()
        if self._task is not None:
            await asyncio.wait_for(self._task, timeout=5)
        await core.session.close()
        await self.gateway.stop()


# ---------------------------------------------------------------- 注册与分发


async def test_registration_order_and_wildcard_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同一事件按注册顺序执行, 通配 handler 排在精确匹配之后."""
    calls: list[str] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on("GROUP_AT_MESSAGE_CREATE")
        async def first(ctx: Context) -> None:
            calls.append("first")

        @bot.on("GROUP_AT_MESSAGE_CREATE")
        async def second(ctx: Context) -> None:
            calls.append("second")

        @bot.on("*")
        async def wildcard(ctx: Context) -> None:
            if ctx.event_name == "GROUP_AT_MESSAGE_CREATE":
                calls.append("wildcard")

        harness.start(bot)
        await _wait_until(lambda: calls == ["first", "second", "wildcard"])

    assert calls == ["first", "second", "wildcard"]


async def test_on_message_registers_group_and_c2c(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """on_message 同时监听群聊与单聊消息事件."""
    events: list[str | None] = []
    async with Harness(
        monkeypatch,
        [_group_dispatch(), _c2c_dispatch()],
    ) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message()
        async def handler(ctx: Context) -> None:
            events.append(ctx.event_name)

        harness.start(bot)
        await _wait_until(lambda: len(events) == 2)

    assert events == ["GROUP_AT_MESSAGE_CREATE", "C2C_MESSAGE_CREATE"]


async def test_on_message_group_only_ignores_c2c(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str | None] = []
    async with Harness(
        monkeypatch,
        [_group_dispatch(), _c2c_dispatch()],
    ) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            events.append(ctx.event_name)

        harness.start(bot)
        await _wait_until(lambda: len(events) == 1)

    assert events == ["GROUP_AT_MESSAGE_CREATE"]


def test_on_message_requires_a_target() -> None:
    """group 与 c2c 都不选等于什么都没注册, 直接报错比静默失效好."""
    bot = Bot()
    with pytest.raises(ValueError):
        bot.on_message(group=False, c2c=False)


async def test_context_carries_parsed_event(monkeypatch: pytest.MonkeyPatch) -> None:
    """ctx.event 是解析后的事件模型, ctx.group_openid 取自事件体."""
    seen: list[Context] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on("GROUP_AT_MESSAGE_CREATE")
        async def handler(ctx: Context) -> None:
            seen.append(ctx)

        harness.start(bot)
        await _wait_until(lambda: len(seen) == 1)

    ctx = seen[0]
    assert isinstance(ctx.event, GroupAtMessageCreateEvent)
    assert ctx.event is not None
    assert ctx.event.content == "你好"
    assert ctx.group_openid == GROUP_OPENID
    assert ctx.user_openid is None
    assert ctx.event_name == "GROUP_AT_MESSAGE_CREATE"
    assert ctx.payload.s == 2
    assert isinstance(ctx.state, dict)


async def test_context_user_openid_for_c2c(monkeypatch: pytest.MonkeyPatch) -> None:
    """单聊的 ctx.user_openid 取自 author.user_openid."""
    seen: list[str | None] = []
    async with Harness(monkeypatch, [_c2c_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message(group=False, c2c=True)
        async def handler(ctx: Context) -> None:
            seen.append(ctx.user_openid)

        harness.start(bot)
        await _wait_until(lambda: len(seen) == 1)

    assert seen == [USER_OPENID]


async def test_unmodelled_event_dispatched_with_none_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未建模的事件照常分发, ctx.event 为 None, openid 回退到原始 d."""
    seen: list[tuple[str | None, object, str | None]] = []
    dispatch = {
        "t": "SOME_UNMODELLED_EVENT",
        "id": "evt-x",
        "d": {"group_openid": "G-9"},
    }
    async with Harness(monkeypatch, [dispatch]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on("SOME_UNMODELLED_EVENT")
        async def handler(ctx: Context) -> None:
            seen.append((ctx.event_name, ctx.event, ctx.group_openid))

        harness.start(bot)
        await _wait_until(lambda: len(seen) == 1)

    assert seen == [("SOME_UNMODELLED_EVENT", None, "G-9")]


async def test_guild_event_resolved_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    """群聊包没有的事件交给频道包解析, 这里只断言类名, 不 import guild 包."""
    seen: list[object] = []
    dispatch = {"t": "GUILD_CREATE", "id": "evt-g", "d": {"id": "G-1", "name": "频道"}}
    async with Harness(monkeypatch, [dispatch]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on("GUILD_CREATE")
        async def handler(ctx: Context) -> None:
            seen.append(ctx.event)

        harness.start(bot)
        await _wait_until(lambda: len(seen) == 1)

    assert seen[0] is not None
    assert type(seen[0]).__name__ == "GuildCreateEvent"


async def test_on_ready_fires_for_ready_and_resumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """on_ready 对 READY 与 RESUMED 都触发."""
    calls: list[str | None] = []
    resumed = {"t": "RESUMED", "id": "evt-r", "d": {"session_id": "sess-1"}}
    async with Harness(monkeypatch, [resumed]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_ready()
        async def handler(ctx: Context) -> None:
            calls.append(ctx.event_name)

        harness.start(bot)
        await _wait_until(lambda: len(calls) == 2)

    assert calls == ["READY", "RESUMED"]


# ---------------------------------------------------------------- 中间件


async def test_middleware_onion_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """先注册的中间件在外层: 先进入, 后退出."""
    calls: list[str] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.middleware
        async def outer(
            ctx: Context,
            call_next: Callable[[], Awaitable[None]],
        ) -> None:
            calls.append("outer-in")
            await call_next()
            calls.append("outer-out")

        @bot.middleware
        async def inner(
            ctx: Context,
            call_next: Callable[[], Awaitable[None]],
        ) -> None:
            calls.append("inner-in")
            await call_next()
            calls.append("inner-out")

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            calls.append("handler")

        harness.start(bot)
        await _wait_until(
            lambda: (
                calls == ["outer-in", "inner-in", "handler", "inner-out", "outer-out"]
            )
        )

    assert calls == [
        "outer-in",
        "inner-in",
        "handler",
        "inner-out",
        "outer-out",
    ]


async def test_middleware_can_block_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    """中间件不调用 call_next 即拦截, 但外层中间件照常收尾."""
    calls: list[str] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.middleware
        async def outer(
            ctx: Context,
            call_next: Callable[[], Awaitable[None]],
        ) -> None:
            calls.append("outer-in")
            await call_next()
            calls.append("outer-out")

        @bot.middleware
        async def blocker(
            ctx: Context,
            call_next: Callable[[], Awaitable[None]],
        ) -> None:
            calls.append("block-in")
            calls.append("block-out")

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            calls.append("handler")

        harness.start(bot)
        await _wait_until(
            lambda: calls == ["outer-in", "block-in", "block-out", "outer-out"]
        )

    assert calls == ["outer-in", "block-in", "block-out", "outer-out"]


async def test_middleware_receives_shared_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """中间件可以通过 ctx.state 往内层传数据."""
    seen: list[object] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.middleware
        async def tag(
            ctx: Context,
            call_next: Callable[[], Awaitable[None]],
        ) -> None:
            ctx.state["tag"] = "outer"
            await call_next()

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            seen.append(ctx.state.get("tag"))

        harness.start(bot)
        await _wait_until(lambda: seen == ["outer"])

    assert seen == ["outer"]


# ---------------------------------------------------------------- 阻断与错误


async def test_handler_returning_false_blocks_following_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """handler 返回 False 后不再执行后续 handler, 中间件仍正常收尾."""
    calls: list[str] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.middleware
        async def mw(ctx: Context, call_next: Callable[[], Awaitable[None]]) -> None:
            calls.append("in")
            await call_next()
            calls.append("out")

        @bot.on_message(group=True, c2c=False)
        async def first(ctx: Context) -> bool:
            calls.append("first")
            return False

        @bot.on_message(group=True, c2c=False)
        async def second(ctx: Context) -> None:
            calls.append("second")

        harness.start(bot)
        await _wait_until(lambda: calls == ["in", "first", "out"])

    assert calls == ["in", "first", "out"]


async def test_exception_goes_to_error_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """handler 抛异常进 on_error, 后续事件照常处理."""
    errors: list[tuple[str | None, str]] = []
    processed: list[str] = []
    async with Harness(
        monkeypatch,
        [_group_dispatch("evt-1", "MSG-1"), _group_dispatch("evt-2", "MSG-2")],
    ) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_error()
        async def on_error(
            ctx: Context | None,
            exc: BaseException,
        ) -> None:
            errors.append((ctx.event_name if ctx is not None else None, str(exc)))

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            if ctx.payload.id == "evt-1":
                raise RuntimeError("故意抛出的异常")
            processed.append(ctx.payload.id or "")

        harness.start(bot)
        await _wait_until(lambda: bool(errors) and bool(processed))

    assert errors == [("GROUP_AT_MESSAGE_CREATE", "故意抛出的异常")]
    assert processed == ["evt-2"]
    assert harness.gateway.connections == 1


async def test_middleware_exception_goes_to_error_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """中间件抛异常同样进 on_error, 不影响连接."""
    errors: list[str] = []
    async with Harness(
        monkeypatch,
        [_group_dispatch("evt-1"), _group_dispatch("evt-2", "MSG-2")],
    ) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.middleware
        async def boom(ctx: Context, call_next: Callable[[], Awaitable[None]]) -> None:
            if ctx.payload.id == "evt-1":
                raise ValueError("中间件异常")
            await call_next()

        @bot.on_error()
        async def on_error(ctx: Context | None, exc: BaseException) -> None:
            errors.append(str(exc))

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            return None

        harness.start(bot)
        await _wait_until(lambda: errors == ["中间件异常"])

    assert errors == ["中间件异常"]


# ---------------------------------------------------------------- 快捷回复


def _patch_group_send(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, Any]]:
    sent: list[tuple[str, Any]] = []

    async def fake_send(
        group_openid: str,
        payload: Any,
    ) -> SendGroupMessagesResponse:
        sent.append((group_openid, payload))
        return SendGroupMessagesResponse(
            id=f"sent-{len(sent)}",
            timestamp=TIMESTAMP,
        )

    monkeypatch.setattr(group_messages, "send_group_messages", fake_send)
    return sent


def _patch_user_send(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, Any]]:
    sent: list[tuple[str, Any]] = []

    async def fake_send(user_openid: str, payload: Any) -> SendUserMessagesResponse:
        sent.append((user_openid, payload))
        return SendUserMessagesResponse(id=f"sent-{len(sent)}", timestamp=TIMESTAMP)

    monkeypatch.setattr(user_api, "send_user_messages", fake_send)
    return sent


async def test_reply_uses_event_id_and_increments_msg_seq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reply 优先用 event_id, 同一锚点连续回复两次 msg_seq 递增."""
    sent = _patch_group_send(monkeypatch)
    results: list[str | None] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            results.append(await ctx.reply("第一条"))
            results.append(await ctx.reply("第二条"))

        harness.start(bot)
        await _wait_until(lambda: len(results) == 2)

    assert results == ["sent-1", "sent-2"]
    first_openid, first = sent[0]
    second_openid, second = sent[1]
    assert first_openid == second_openid == GROUP_OPENID
    assert first.msg_type == 0
    assert first.content == "第一条"
    assert first.event_id == "evt-1"
    assert first.msg_id is None
    assert first.msg_seq == 1
    assert second.msg_seq == 2
    # event_id 与 msg_id 互斥
    dumped = second.model_dump(exclude_none=True)
    assert ("event_id" in dumped) != ("msg_id" in dumped)


async def test_reply_falls_back_to_msg_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """信封没有 event id 时改用 d.id 走 msg_id."""
    sent = _patch_group_send(monkeypatch)
    results: list[str | None] = []
    dispatch = {"t": "GROUP_AT_MESSAGE_CREATE", "d": _group_d()}
    async with Harness(monkeypatch, [dispatch]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            results.append(await ctx.reply("收到"))

        harness.start(bot)
        await _wait_until(lambda: len(results) == 1)

    _, request = sent[0]
    assert request.msg_id == MESSAGE_ID
    assert request.event_id is None
    assert request.msg_seq == 1


async def test_reply_explicit_msg_seq_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式 msg_seq 优先, 并把计数推进到该值之后."""
    sent = _patch_group_send(monkeypatch)
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)
        results: list[str | None] = []

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            results.append(await ctx.reply("第一条", msg_seq=7))
            results.append(await ctx.reply("第二条"))

        harness.start(bot)
        await _wait_until(lambda: len(results) == 2)

    assert sent[0][1].msg_seq == 7
    assert sent[1][1].msg_seq == 8


async def test_reply_c2c_uses_author_openid(monkeypatch: pytest.MonkeyPatch) -> None:
    """单聊回复走 send_user_messages, 目标取 author.user_openid."""
    sent = _patch_user_send(monkeypatch)
    results: list[str | None] = []
    async with Harness(monkeypatch, [_c2c_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message(group=False, c2c=True)
        async def handler(ctx: Context) -> None:
            results.append(await ctx.reply("收到"))

        harness.start(bot)
        await _wait_until(lambda: len(results) == 1)

    user_openid, request = sent[0]
    assert user_openid == USER_OPENID
    assert request.event_id == "evt-c2c"
    assert request.msg_id is None
    assert request.content == "收到"


async def test_reply_on_non_message_event_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非消息事件没有被动回复语义, reply 返回 None 且不发请求."""
    sent = _patch_group_send(monkeypatch)
    results: list[str | None] = []
    dispatch = {"t": "GROUP_ADD_ROBOT", "id": "evt-bot", "d": {"group_openid": "G1"}}
    async with Harness(monkeypatch, [dispatch]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on("GROUP_ADD_ROBOT")
        async def handler(ctx: Context) -> None:
            results.append(await ctx.reply("收到"))

        harness.start(bot)
        await _wait_until(lambda: len(results) == 1)

    assert results == [None]
    assert sent == []


async def test_send_is_proactive_without_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ctx.send 是主动消息, 不带 event_id / msg_id / msg_seq."""
    sent = _patch_group_send(monkeypatch)
    results: list[str | None] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            results.append(await ctx.send("主动消息"))

        harness.start(bot)
        await _wait_until(lambda: len(results) == 1)

    assert results == ["sent-1"]
    group_openid, request = sent[0]
    assert group_openid == GROUP_OPENID
    dumped = request.model_dump(exclude_none=True)
    assert dumped == {"msg_type": 0, "content": "主动消息"}


# ---------------------------------------------------------------- 生命周期


async def test_stop_cancels_running_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    """stop 之后不残留分发任务, 正在处理的 handler 被取消."""
    started = asyncio.Event()
    cancelled: list[str] = []
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)

        @bot.on_message(group=True, c2c=False)
        async def handler(ctx: Context) -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append("cancelled")

        harness.start(bot)
        await asyncio.wait_for(started.wait(), timeout=5)
        await bot.stop()
        leftover = [
            task for task in asyncio.all_tasks() if task.get_name() == TASK_NAME
        ]
        assert leftover == []
    assert cancelled == ["cancelled"]


async def test_stop_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """stop 可以重复调用, 已经停止的 Bot 不会报错."""
    async with Harness(monkeypatch, [_group_dispatch()]) as harness:
        bot = Bot(url=harness.gateway.ws_url, auto_reconnect=False)
        ready = asyncio.Event()

        @bot.on_ready()
        async def handler(ctx: Context) -> None:
            ready.set()

        harness.start(bot)
        await asyncio.wait_for(ready.wait(), timeout=5)
        await bot.stop()
        await bot.stop()
        assert bot.ws is None
