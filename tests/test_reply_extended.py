"""被动回复扩展能力的测试: Markdown / 富媒体 / 卡片 / build_reply.

覆盖 ``msg_type`` 自动推导、内容互斥校验、``build_reply`` 只算不发、
``send_reply`` 一步发送, 以及四种回复在锚点与 msg_seq 上的一致性.
"""

import pytest

from qqbotsdk.api import user as user_api
from qqbotsdk.api.group import messages as group_messages
from qqbotsdk.app import Bot, Context, callback, keyboard, row
from qqbotsdk.app.context import PreparedReply
from qqbotsdk.app.dispatch import resolve_event
from qqbotsdk.model.group.messages import (
    SendGroupMessagesRequest,
    SendGroupMessagesResponse,
)
from qqbotsdk.model.sub.messages import MessageMarkdown
from qqbotsdk.model.user.messages import SendUserMessagesResponse
from qqbotsdk.testing import make_payload

TIMESTAMP = "2026-11-01T10:00:00+08:00"
GROUP_OPENID = "GROUP-1"
USER_OPENID = "USER-1"


def _group_payload() -> dict[str, object]:
    return {
        "id": "MSG-1",
        "content": "你好",
        "group_openid": GROUP_OPENID,
        "author": {"member_openid": "MEMBER-1"},
        "timestamp": TIMESTAMP,
    }


def _c2c_payload() -> dict[str, object]:
    return {
        "id": "C2C-1",
        "content": "hi",
        "author": {"user_openid": USER_OPENID},
        "timestamp": TIMESTAMP,
    }


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, object]]:
    """把群聊 / 单聊发送接口替换成记录器."""
    calls: list[tuple[str, object]] = []

    async def fake_group(
        group_openid: str,
        payload: object,
    ) -> SendGroupMessagesResponse:
        calls.append(("group", payload))
        return SendGroupMessagesResponse(id="msg-1", timestamp=TIMESTAMP)

    async def fake_user(user_openid: str, payload: object) -> SendUserMessagesResponse:
        calls.append(("c2c", payload))
        return SendUserMessagesResponse(id="msg-2", timestamp=TIMESTAMP)

    monkeypatch.setattr(group_messages, "send_group_messages", fake_group)
    monkeypatch.setattr(user_api, "send_user_messages", fake_user)
    return calls


def _ctx(
    payload: dict[str, object],
    *,
    event_name: str = "GROUP_AT_MESSAGE_CREATE",
    event_id: str | None = "evt-1",
) -> Context:
    """按生产路径构造 Context: 信封 + 已解析事件, 与 Bot.dispatch 一致."""
    gateway_payload = make_payload(event_name, payload, event_id=event_id)
    return Context(
        bot=Bot(),
        payload=gateway_payload,
        event=resolve_event(gateway_payload),
    )


def test_msg_type_is_inferred_for_every_content_kind() -> None:
    """填了哪个内容字段就推导出对应 msg_type, 不用手写."""
    assert SendGroupMessagesRequest(content="hi").msg_type == 0
    assert (
        SendGroupMessagesRequest(
            markdown=MessageMarkdown.model_validate({"content": "hi"})
        ).msg_type
        == 2
    )
    assert (
        SendGroupMessagesRequest.model_validate({"media": {"file_info": "F"}}).msg_type
        == 7
    )
    assert (
        SendGroupMessagesRequest.model_validate({"card": {"type": "tuwen"}}).msg_type
        == 8
    )


def test_content_with_media_infers_media_and_keeps_caption() -> None:
    """富媒体可以带附带文本, 这时 msg_type 取 7 而不是 0."""
    request = SendGroupMessagesRequest.model_validate(
        {"content": "看图", "media": {"file_info": "F"}}
    )
    assert request.msg_type == 7
    assert request.content == "看图"


def test_mutually_exclusive_content_is_rejected() -> None:
    """markdown 与 content 互斥; 多个重量级字段不能同时出现."""
    with pytest.raises(ValueError, match="互斥"):
        SendGroupMessagesRequest.model_validate(
            {"content": "x", "markdown": {"content": "y"}}
        )
    with pytest.raises(ValueError, match="互斥"):
        SendGroupMessagesRequest.model_validate(
            {"media": {"file_info": "F"}, "card": {"type": "tuwen"}}
        )


def test_explicit_msg_type_must_match_content() -> None:
    """显式 msg_type 与内容对不上时报错, 而不是把矛盾发给服务端."""
    with pytest.raises(ValueError, match="不匹配"):
        SendGroupMessagesRequest.model_validate({"msg_type": 2, "content": "x"})


def test_build_reply_prepares_without_sending(sent: list[tuple[str, object]]) -> None:
    """build_reply 只产出 PreparedReply, 不产生任何请求."""
    ctx = _ctx(_group_payload())
    prepared = ctx.build_reply(
        markdown="**hi**", keyboard=keyboard(row(callback("A", "a")))
    )

    assert isinstance(prepared, PreparedReply)
    scene, openid, request = prepared
    assert scene == "group"
    assert openid == GROUP_OPENID
    assert isinstance(request, SendGroupMessagesRequest)
    assert request.msg_type == 2
    assert request.event_id == "evt-1"
    assert request.msg_seq == 1
    assert sent == []


async def test_send_reply_sends_markdown(sent: list[tuple[str, object]]) -> None:
    """send_reply(markdown=...) 走 msg_type=2 并带锚点."""
    ctx = _ctx(_group_payload())
    message_id = await ctx.send_reply(markdown="## 标题")

    assert message_id == "msg-1"
    scene, request = sent[0]
    assert scene == "group"
    assert isinstance(request, SendGroupMessagesRequest)
    assert request.msg_type == 2
    assert request.markdown is not None
    assert request.markdown.content == "## 标题"
    assert request.event_id == "evt-1"


async def test_reply_markdown_and_reply_media_share_seq(
    sent: list[tuple[str, object]],
) -> None:
    """同一锚点上 reply_markdown / reply_media 共用 msg_seq 计数."""
    ctx = _ctx(_group_payload())
    await ctx.reply_markdown("第一条")
    await ctx.reply_media("FILE-INFO", content="看图")

    first = sent[0][1]
    second = sent[1][1]
    assert isinstance(first, SendGroupMessagesRequest)
    assert isinstance(second, SendGroupMessagesRequest)
    assert first.msg_seq == 1
    assert second.msg_seq == 2
    assert second.msg_type == 7
    assert second.media is not None
    assert second.media.file_info == "FILE-INFO"
    assert second.content == "看图"


async def test_reply_media_on_c2c_uses_user_api(
    sent: list[tuple[str, object]],
) -> None:
    """单聊事件的被动富媒体回复走单聊接口."""
    ctx = _ctx(_c2c_payload(), event_name="C2C_MESSAGE_CREATE")
    message_id = await ctx.reply_media("FILE-INFO")

    assert message_id == "msg-2"
    scene, _ = sent[0]
    assert scene == "c2c"


def test_build_reply_returns_none_for_non_replyable_event() -> None:
    """不可被动回复的事件 build_reply 返回 None, 不抛异常."""
    ctx = _ctx(
        {"group_openid": "G1"},
        event_name="GROUP_ADD_ROBOT",
        event_id="evt-bot",
    )
    assert ctx.build_reply(content="x") is None


def test_build_reply_falls_back_to_msg_id() -> None:
    """信封没有事件 ID 时锚点回退到 d.id, 填 msg_id 而不是 event_id."""
    ctx = _ctx(_group_payload(), event_id=None)
    prepared = ctx.build_reply(markdown="hi")

    assert prepared is not None
    request = prepared.request
    assert isinstance(request, SendGroupMessagesRequest)
    assert request.msg_id == "MSG-1"
    assert request.event_id is None
