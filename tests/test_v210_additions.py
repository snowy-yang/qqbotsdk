"""2.1.0 新增能力的测试: 便捷属性、错误码常量、intents 预设与环境变量、测试辅助.

对应四个改动:
- 事件便捷属性 ``sender_openid`` / ``button_data`` / ``button_id`` / ``clicker_openid``
- ``qqbotsdk.errors.codes`` 常量模块
- ``GROUP_BOT_INTENTS`` 预设与 ``INTENTS`` 环境变量
- ``Bot.dispatch`` / ``qqbotsdk.testing``
"""

import pytest

from qqbotsdk.app import Bot, Context
from qqbotsdk.app.bot import INTENTS_ENV, resolve_intents
from qqbotsdk.app.dispatch import resolve_event
from qqbotsdk.errors import QQBotAPIError, codes
from qqbotsdk.model.event.c2c import C2CMessageCreateEvent
from qqbotsdk.model.event.group import GroupMessageEventBase
from qqbotsdk.model.event.interaction import InteractionCreateEvent
from qqbotsdk.testing import (
    DEFAULT_EVENT_ID,
    dispatch,
    dispatch_frame,
    make_payload,
    parse_frame,
)
from qqbotsdk.ws import DEFAULT_INTENTS, GROUP_BOT_INTENTS, Intents
from qqbotsdk.ws.payload import OpCode

# ---------------------------------------------------------------- 便捷属性


def _group_event(data: object) -> GroupMessageEventBase:
    """解析一条群消息事件, 并断言类型以便类型检查器收窄."""
    event = resolve_event(make_payload("GROUP_AT_MESSAGE_CREATE", data))
    assert isinstance(event, GroupMessageEventBase)
    return event


def _c2c_event(data: object) -> C2CMessageCreateEvent:
    event = resolve_event(make_payload("C2C_MESSAGE_CREATE", data))
    assert isinstance(event, C2CMessageCreateEvent)
    return event


def _interaction_event(data: object) -> InteractionCreateEvent:
    event = resolve_event(make_payload("INTERACTION_CREATE", data))
    assert isinstance(event, InteractionCreateEvent)
    return event


def test_group_message_sender_openid_prefers_member_openid() -> None:
    """群聊取 author.member_openid."""
    event = _group_event(
        {"id": "m1", "author": {"member_openid": "M1", "user_openid": "U1"}}
    )
    assert event.sender_openid == "M1"


def test_group_message_sender_openid_falls_back() -> None:
    """没有 member_openid 时回退 user_openid, 再回退 id."""
    assert _group_event({"author": {"user_openid": "U1"}}).sender_openid == "U1"
    assert _group_event({"author": {"id": "ID1"}}).sender_openid == "ID1"


def test_group_message_sender_openid_without_author() -> None:
    """author 缺失时返回 None, 不抛异常."""
    assert _group_event({"id": "m1"}).sender_openid is None


def test_c2c_message_sender_openid_prefers_user_openid() -> None:
    """单聊取 author.user_openid."""
    assert _c2c_event({"author": {"user_openid": "U1"}}).sender_openid == "U1"


def test_interaction_button_helpers() -> None:
    """互动事件的 button_data / button_id / clicker_openid."""
    event = _interaction_event(
        {
            "id": "i1",
            "type": 11,
            "group_openid": "G1",
            "group_member_openid": "GM1",
            "data": {"type": 11, "resolved": {"button_data": "act", "button_id": "b1"}},
        }
    )
    assert event.button_data == "act"
    assert event.button_id == "b1"
    assert event.clicker_openid == "GM1"


def test_interaction_clicker_openid_for_c2c() -> None:
    """单聊互动事件取 user_openid."""
    event = _interaction_event({"id": "i1", "type": 11, "user_openid": "U1"})
    assert event.clicker_openid == "U1"


def test_interaction_helpers_without_data() -> None:
    """没有 data / resolved 时返回 None."""
    event = _interaction_event({"id": "i1", "type": 14})
    assert event.button_data is None
    assert event.button_id is None
    assert event.clicker_openid is None


# ---------------------------------------------------------------- 错误码常量


def test_error_codes_are_ints() -> None:
    """常量都是 int, 可以直接和 err_code 比较."""
    assert codes.MSG_DEDUPLICATED == 40054005
    assert codes.EVENT_ID_INVALID == 40034025
    assert codes.EVENT_NOT_REPLYABLE == 40034027
    assert isinstance(codes.MSG_DEDUPLICATED, int)


def test_error_codes_match_api_error() -> None:
    """常量能与 QQBotAPIError.err_code 直接比对."""
    exc = QQBotAPIError(200, codes.MSG_DEDUPLICATED, "duplicated")
    assert exc.err_code == codes.MSG_DEDUPLICATED


def test_error_codes_exported_from_package() -> None:
    """codes 从 qqbotsdk.errors 直接可取."""
    from qqbotsdk.errors import codes as exported

    assert exported is codes


# ---------------------------------------------------------------- intents


def test_group_bot_intents_has_no_guild_bits() -> None:
    """GROUP_BOT_INTENTS 不含任何频道位, 且包含群聊与互动."""
    assert GROUP_BOT_INTENTS & Intents.GUILD_MEMBERS == 0
    assert GROUP_BOT_INTENTS & Intents.PUBLIC_GUILD_MESSAGES == 0
    assert GROUP_BOT_INTENTS & Intents.GROUP_AND_C2C_EVENT
    assert GROUP_BOT_INTENTS & Intents.INTERACTION


def test_resolve_intents_prefers_explicit_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """显式入参优先于环境变量."""
    monkeypatch.setenv(INTENTS_ENV, "1")
    assert resolve_intents(Intents.INTERACTION) == Intents.INTERACTION


def test_resolve_intents_reads_env_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    """环境变量支持 0x 十六进制掩码."""
    monkeypatch.setenv(INTENTS_ENV, "0x2000000")
    assert resolve_intents() == Intents.GROUP_AND_C2C_EVENT


def test_resolve_intents_reads_env_decimal(monkeypatch: pytest.MonkeyPatch) -> None:
    """环境变量支持十进制掩码."""
    monkeypatch.setenv(INTENTS_ENV, str(1 << 25))
    assert resolve_intents() == Intents.GROUP_AND_C2C_EVENT


def test_resolve_intents_defaults_when_env_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """没有环境变量时回退 DEFAULT_INTENTS."""
    monkeypatch.delenv(INTENTS_ENV, raising=False)
    assert resolve_intents() == DEFAULT_INTENTS


def test_resolve_intents_rejects_bad_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """非法环境变量给出明确 ValueError, 而不是静默用默认值."""
    monkeypatch.setenv(INTENTS_ENV, "not-a-number")
    with pytest.raises(ValueError, match="十进制或 0x 十六进制"):
        resolve_intents()


def test_bot_intents_property_reflects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bot() 的 intents 会读环境变量, 并通过属性暴露."""
    monkeypatch.setenv(INTENTS_ENV, "0x2000000")
    assert Bot().intents == Intents.GROUP_AND_C2C_EVENT


def test_bot_intents_property_reflects_argument() -> None:
    """显式传入的 intents 生效."""
    assert Bot(intents=GROUP_BOT_INTENTS).intents == GROUP_BOT_INTENTS


# ---------------------------------------------------------------- 测试辅助


def test_make_payload_builds_dispatch_frame() -> None:
    """make_payload 产出 op=0 的 Dispatch 帧."""
    payload = make_payload("READY", {"session_id": "s1"})
    assert payload.op == OpCode.DISPATCH
    assert payload.t == "READY"
    assert payload.id == DEFAULT_EVENT_ID


def test_make_payload_can_omit_event_id() -> None:
    """event_id=None 时不带信封 id, 用于验证回退 msg_id 的分支."""
    assert make_payload("READY", {}, event_id=None).id is None


def test_parse_frame_accepts_json_and_dict() -> None:
    """parse_frame 同时接受 JSON 文本与 dict."""
    frame = '{"op": 0, "t": "READY", "d": {}}'
    assert parse_frame(frame).t == "READY"
    assert parse_frame({"op": 0, "t": "RESUMED", "d": ""}).t == "RESUMED"


async def test_dispatch_runs_handlers() -> None:
    """dispatch 喂一帧并等待 handler 跑完."""
    bot = Bot()
    seen: list[str | None] = []

    @bot.on("GROUP_AT_MESSAGE_CREATE")
    async def handler(ctx: Context) -> None:
        seen.append(ctx.payload.id)

    await dispatch(bot, "GROUP_AT_MESSAGE_CREATE", {"id": "m1", "content": "hi"})
    assert seen == [DEFAULT_EVENT_ID]


async def test_dispatch_frame_from_raw_json() -> None:
    """dispatch_frame 直接吃网关原始报文."""
    bot = Bot()
    seen: list[str] = []

    @bot.on("READY")
    async def handler(ctx: Context) -> None:
        seen.append(ctx.event_name or "")

    await dispatch_frame(bot, '{"op": 0, "t": "READY", "d": {"session_id": "s1"}}')
    assert seen == ["READY"]


async def test_dispatch_ignores_non_dispatch_opcode() -> None:
    """非 Dispatch 帧不会触发任何 handler."""
    bot = Bot()
    called: list[str] = []

    @bot.on("*")
    async def handler(ctx: Context) -> None:
        called.append(ctx.event_name or "")

    from qqbotsdk.ws.payload import GatewayPayload

    payload = GatewayPayload.model_validate({"op": OpCode.HEARTBEAT, "d": 1})
    assert bot.dispatch(payload) is None
    assert called == []


async def test_dispatch_returns_task_that_can_be_awaited() -> None:
    """Bot.dispatch 返回的任务可以 await, 也可以不 await."""
    bot = Bot()
    seen: list[str] = []

    @bot.on("GROUP_AT_MESSAGE_CREATE")
    async def handler(ctx: Context) -> None:
        seen.append("ran")

    task = bot.dispatch(make_payload("GROUP_AT_MESSAGE_CREATE", {"id": "m1"}))
    assert task is not None
    await task
    assert seen == ["ran"]
