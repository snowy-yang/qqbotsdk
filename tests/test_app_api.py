"""qqbotsdk.app.api.SceneApi (ctx.api) 的测试.

不启动网关: 直接构造 ``Context``, 用 monkeypatch 替换底层 api 函数, 断言路由与
请求体. 只有上传分片走 ``qqbotsdk.app.api.session.put``, 那里也用假会话替换.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from qqbotsdk.api import interaction as interaction_api
from qqbotsdk.api import user as user_api
from qqbotsdk.api.group import join_request as join_request_api
from qqbotsdk.api.group import messages as group_messages
from qqbotsdk.app import Bot, Context
from qqbotsdk.app import api as app_api
from qqbotsdk.model.event import parse_event
from qqbotsdk.model.group.messages import (
    PrepareGroupUploadResponse,
    SendGroupMessagesResponse,
    UploadGroupFileResponse,
)
from qqbotsdk.model.user.messages import (
    PrepareUserUploadResponse,
    SendUserMessagesResponse,
    UploadUserFileResponse,
)
from qqbotsdk.ws.payload import GatewayPayload

GROUP_OPENID = "GROUP-1"
USER_OPENID = "USER-1"
TIMESTAMP = "2026-11-01T10:00:00+08:00"


# ---------------------------------------------------------------- 上下文构造


def _frame(
    event_name: str,
    event_d: dict[str, Any],
    event_id: str | None = "evt-1",
) -> GatewayPayload:
    frame: dict[str, Any] = {"op": 0, "s": 1, "t": event_name, "d": event_d}
    if event_id is not None:
        frame["id"] = event_id
    return GatewayPayload.model_validate(frame)


def _group_context(message_id: str = "MSG-1") -> Context:
    payload = _frame(
        "GROUP_AT_MESSAGE_CREATE",
        {
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
        },
    )
    return Context(bot=Bot(), payload=payload, event=parse_event(payload))


def _c2c_context() -> Context:
    payload = _frame(
        "C2C_MESSAGE_CREATE",
        {
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
        },
    )
    return Context(bot=Bot(), payload=payload, event=parse_event(payload))


def _join_request_context(member_openid: str | None = "APPLICANT-1") -> Context:
    event_d: dict[str, Any] = {
        "group_openid": GROUP_OPENID,
        "join_request_id": "REQ-1",
        "apply_source": "self_apply",
        "username": "申请人",
        "apply_at": TIMESTAMP,
    }
    if member_openid is not None:
        event_d["member_openid"] = member_openid
    payload = _frame("GROUP_JOIN_REQUEST", event_d)
    return Context(bot=Bot(), payload=payload, event=parse_event(payload))


def _interaction_context(interaction_id: str = "INT-1") -> Context:
    payload = _frame(
        "INTERACTION_CREATE",
        {
            "id": interaction_id,
            "type": 11,
            "scene": "c2c",
            "chat_type": 2,
            "user_openid": USER_OPENID,
            "timestamp": TIMESTAMP,
            "data": {"type": 11, "resolved": {"button_id": "b1"}},
        },
    )
    return Context(bot=Bot(), payload=payload, event=parse_event(payload))


def _other_context() -> Context:
    # 既没有 group_openid 也没有任何用户 openid 的事件, 场景无法判定
    payload = _frame("SOME_UNKNOWN_EVENT", {"foo": "bar"})
    return Context(bot=Bot(), payload=payload, event=parse_event(payload))


def _friend_add_context() -> Context:
    # FRIEND_ADD 只有顶层 openid, 视为单聊场景
    payload = _frame(
        "FRIEND_ADD", {"openid": "FRIEND-1", "timestamp": 1, "scene": 1000}
    )
    return Context(bot=Bot(), payload=payload, event=parse_event(payload))


# ---------------------------------------------------------------- 假 api


def _patch_group_send(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    sent: list[tuple[str, Any]] = []

    async def fake(group_openid: str, payload: Any) -> SendGroupMessagesResponse:
        sent.append((group_openid, payload))
        return SendGroupMessagesResponse(id=f"sent-{len(sent)}", timestamp=TIMESTAMP)

    monkeypatch.setattr(group_messages, "send_group_messages", fake)
    return sent


def _patch_user_send(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    sent: list[tuple[str, Any]] = []

    async def fake(user_openid: str, payload: Any) -> SendUserMessagesResponse:
        sent.append((user_openid, payload))
        return SendUserMessagesResponse(id=f"sent-{len(sent)}", timestamp=TIMESTAMP)

    monkeypatch.setattr(user_api, "send_user_messages", fake)
    return sent


# ---------------------------------------------------------------- 场景判定


def test_scene_group() -> None:
    assert _group_context().api.scene == "group"


def test_scene_c2c() -> None:
    assert _c2c_context().api.scene == "c2c"


def test_scene_other() -> None:
    assert _other_context().api.scene == "other"


def test_api_is_lazy_and_cached() -> None:
    """ctx.api 首次访问才构造, 且同一个 ctx 上始终是同一个实例."""
    ctx = _group_context()
    assert ctx._api is None
    first = ctx.api
    assert ctx._api is first
    assert ctx.api is first


async def test_other_scene_methods_raise() -> None:
    """场景不明时所有场景相关方法都抛 ValueError, 并提示需要群/单聊事件."""
    api = _other_context().api
    calls = [
        api.send("x"),
        api.send_markdown("x"),
        api.send_card(
            title="t",
            description="d",
            url="https://example.com",
            pic_url="https://example.com/p.png",
        ),
        api.send_media("FILE-INFO"),
        api.recall("MSG-1"),
        api.upload_image("whatever.png"),
    ]
    for coro in calls:
        with pytest.raises(ValueError, match="group_openid"):
            await coro


# ---------------------------------------------------------------- 发消息


async def test_send_group(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _patch_group_send(monkeypatch)

    message_id = await _group_context().api.send("主动文本")

    assert message_id == "sent-1"
    openid, request = sent[0]
    assert openid == GROUP_OPENID
    assert request.msg_type == 0
    assert request.content == "主动文本"
    # 主动消息不带锚点
    dumped = request.model_dump(exclude_none=True)
    assert dumped == {"msg_type": 0, "content": "主动文本"}


async def test_send_c2c(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _patch_user_send(monkeypatch)

    message_id = await _c2c_context().api.send("主动文本")

    assert message_id == "sent-1"
    openid, request = sent[0]
    assert openid == USER_OPENID
    assert request.msg_type == 0
    assert request.content == "主动文本"
    assert "event_id" not in request.model_dump(exclude_none=True)


async def test_send_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _patch_group_send(monkeypatch)

    await _group_context().api.send_markdown("**加粗**")

    _, request = sent[0]
    assert request.msg_type == 2
    assert request.markdown is not None
    assert request.markdown.content == "**加粗**"
    assert request.content is None
    assert "event_id" not in request.model_dump(exclude_none=True)


async def test_send_card(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _patch_group_send(monkeypatch)

    await _group_context().api.send_card(
        title="标题",
        description="描述",
        url="https://example.com/a",
        pic_url="https://example.com/p.png",
    )

    _, request = sent[0]
    assert request.msg_type == 8
    card = request.card
    assert card is not None
    assert card.type == "tuwen"
    content = card.content
    assert content is not None
    assert content.title == "标题"
    assert content.description == "描述"
    assert content.url == "https://example.com/a"
    assert content.pic_url == "https://example.com/p.png"


async def test_send_media(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _patch_group_send(monkeypatch)

    await _group_context().api.send_media("FILE-INFO", content="看图")

    _, request = sent[0]
    assert request.msg_type == 7
    assert request.media is not None
    assert request.media.file_info == "FILE-INFO"
    assert request.content == "看图"


async def test_send_media_without_content(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _patch_group_send(monkeypatch)

    await _group_context().api.send_media("FILE-INFO")

    _, request = sent[0]
    assert request.model_dump(exclude_none=True) == {
        "msg_type": 7,
        "media": {"file_info": "FILE-INFO"},
    }


async def test_reply_delegates_to_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """ctx.api.reply 直接走 Context.reply 的锚点与 msg_seq 逻辑."""
    sent = _patch_group_send(monkeypatch)
    ctx = _group_context()

    first = await ctx.api.reply("第一次")
    second = await ctx.api.reply("第二次")

    assert (first, second) == ("sent-1", "sent-2")
    _, first_request = sent[0]
    _, second_request = sent[1]
    assert first_request.event_id == "evt-1"
    assert first_request.msg_id is None
    assert (first_request.msg_seq, second_request.msg_seq) == (1, 2)


async def test_recall_group(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    async def fake(group_openid: str, message_id: str) -> None:
        calls.append((group_openid, message_id))

    monkeypatch.setattr(group_messages, "recall_group_messages", fake)

    await _group_context().api.recall("MSG-9")

    assert calls == [(GROUP_OPENID, "MSG-9")]


async def test_recall_c2c(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    async def fake(user_openid: str, message_id: str) -> None:
        calls.append((user_openid, message_id))

    monkeypatch.setattr(user_api, "recall_user_messages", fake)

    await _c2c_context().api.recall("MSG-9")

    assert calls == [(USER_OPENID, "MSG-9")]


# ---------------------------------------------------------------- 入群申请审批


def _patch_review(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, Any]]:
    calls: list[tuple[str, str, Any]] = []

    async def fake(group_openid: str, member_openid: str, payload: Any) -> None:
        calls.append((group_openid, member_openid, payload))

    monkeypatch.setattr(join_request_api, "review_group_join_request", fake)
    return calls


async def test_approve_join_request_uses_event_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_review(monkeypatch)

    await _join_request_context().api.approve_join_request(join_request_id="REQ-1")

    group_openid, member_openid, request = calls[0]
    assert group_openid == GROUP_OPENID
    assert member_openid == "APPLICANT-1"
    assert request.op == "approve"
    assert request.join_request_id == "REQ-1"
    assert request.reject_reason is None
    assert request.model_dump(exclude_none=True) == {
        "op": "approve",
        "join_request_id": "REQ-1",
    }


async def test_decline_join_request_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_review(monkeypatch)

    await _join_request_context(member_openid=None).api.decline_join_request(
        "MEMBER-2",
        reject_reason="不符合条件",
        add_to_blacklist=True,
        join_request_id="REQ-2",
    )

    group_openid, member_openid, request = calls[0]
    assert group_openid == GROUP_OPENID
    assert member_openid == "MEMBER-2"
    assert request.op == "decline"
    assert request.reject_reason == "不符合条件"
    assert request.add_to_member_blacklist is True
    assert request.join_request_id == "REQ-2"


async def test_approve_join_request_without_member_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_review(monkeypatch)

    with pytest.raises(ValueError, match="member_openid"):
        await _join_request_context(member_openid=None).api.approve_join_request()

    assert calls == []


async def test_join_request_methods_require_group_scene() -> None:
    with pytest.raises(ValueError, match="群聊"):
        await _c2c_context().api.approve_join_request("MEMBER-1")


async def test_friend_add_is_not_join_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """FRIEND_ADD 是好友通知, 没有审批接口, 走这里会明确报错."""
    calls = _patch_review(monkeypatch)

    with pytest.raises(ValueError):
        await _other_context().api.approve_join_request("FRIEND-1")

    assert calls == []


# ---------------------------------------------------------------- 互动回包


def _patch_confirm(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    calls: list[tuple[str, Any]] = []

    async def fake(interaction_id: str, payload: Any) -> None:
        calls.append((interaction_id, payload))

    monkeypatch.setattr(interaction_api, "confirm_interactions", fake)
    return calls


async def test_ack_interaction(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_confirm(monkeypatch)

    await _interaction_context().api.ack_interaction(2)

    interaction_id, request = calls[0]
    assert interaction_id == "INT-1"
    assert request.code == 2


async def test_ack_interaction_strips_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """个别推送的 id 带 INTERACTION_CREATE: 前缀, 要剥掉再回包."""
    calls = _patch_confirm(monkeypatch)

    await _interaction_context("INTERACTION_CREATE:INT-2").api.ack_interaction()

    interaction_id, request = calls[0]
    assert interaction_id == "INT-2"
    assert request.code == 0


async def test_ack_interaction_rejects_invalid_code() -> None:
    with pytest.raises(ValidationError):
        await _interaction_context().api.ack_interaction(9)


async def test_ack_interaction_requires_interaction_event() -> None:
    with pytest.raises(ValueError, match="INTERACTION_CREATE"):
        await _group_context().api.ack_interaction()


# ---------------------------------------------------------------- 上传图片


class _FakeResponse:
    async def read(self) -> bytes:
        return b""


class _FakePut:
    def __init__(self, sink: list[tuple[str, bytes]], url: str, data: bytes) -> None:
        self._sink = sink
        self._url = url
        self._data = data

    async def __aenter__(self) -> _FakeResponse:
        self._sink.append((self._url, self._data))
        return _FakeResponse()

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes]] = []

    def put(self, url: str, *, data: bytes) -> _FakePut:
        return _FakePut(self.uploads, url, data)


def _patch_group_upload(
    monkeypatch: pytest.MonkeyPatch,
    parts: list[dict[str, Any]],
) -> tuple[list[Any], list[Any], list[Any], _FakeSession]:
    """替换群的预上传 / 分片完成 / 合并上传, 并返回捕获列表."""
    prepared_calls: list[Any] = []
    finish_calls: list[Any] = []
    upload_calls: list[Any] = []
    fake_session = _FakeSession()

    async def fake_prepare(group_openid: str, payload: Any) -> Any:
        prepared_calls.append((group_openid, payload))
        return PrepareGroupUploadResponse.model_validate(
            {"upload_id": "UP-1", "block_size": "4", "parts": parts}
        )

    async def fake_finish(group_openid: str, payload: Any) -> None:
        finish_calls.append((group_openid, payload))

    async def fake_upload(group_openid: str, payload: Any) -> Any:
        upload_calls.append((group_openid, payload))
        return UploadGroupFileResponse.model_validate({"file_info": "FILE-INFO"})

    monkeypatch.setattr(group_messages, "prepare_group_upload", fake_prepare)
    monkeypatch.setattr(group_messages, "finish_group_upload_part", fake_finish)
    monkeypatch.setattr(group_messages, "upload_group_file", fake_upload)
    monkeypatch.setattr(app_api, "session", fake_session)
    return prepared_calls, finish_calls, upload_calls, fake_session


def _parts(*sizes: int) -> list[dict[str, Any]]:
    """按给定分片大小造预上传响应里的 parts."""
    return [
        {
            "index": index,
            "presigned_url": f"https://cos.example.com/part-{index}",
            "block_size": str(size),
        }
        for index, size in enumerate(sizes)
    ]


async def test_upload_image_orders_parts_by_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """预上传返回的 parts 顺序错乱时, 按 index 升序切片上传."""
    data = b"0123456789"
    image = tmp_path / "pic.png"
    image.write_bytes(data)
    shuffled = list(reversed(_parts(4, 6)))
    _, finish_calls, _, fake_session = _patch_group_upload(monkeypatch, shuffled)

    await _group_context().api.upload_image(image)

    assert fake_session.uploads == [
        ("https://cos.example.com/part-0", data[:4]),
        ("https://cos.example.com/part-1", data[4:]),
    ]
    assert [call[1].part_index for call in finish_calls] == [0, 1]


async def test_upload_image_group_two_parts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data = b"0123456789"
    image = tmp_path / "pic.png"
    image.write_bytes(data)
    # 两片: 前 4 字节 + 剩余 6 字节
    prepared_calls, finish_calls, upload_calls, fake_session = _patch_group_upload(
        monkeypatch, _parts(4, 6)
    )

    file_info = await _group_context().api.upload_image(image)

    assert file_info == "FILE-INFO"
    # 预上传请求: 摘要按文件内容算
    group_openid, prepare = prepared_calls[0]
    assert group_openid == GROUP_OPENID
    assert prepare.file_type == 1
    assert prepare.file_size == str(len(data))
    assert prepare.file_name == "pic.png"
    assert prepare.md5 == hashlib.md5(data).hexdigest()
    assert prepare.sha1 == hashlib.sha1(data).hexdigest()
    assert prepare.md5_10m == hashlib.md5(data).hexdigest()
    # 分片按 block_size 切开并按顺序 PUT
    assert fake_session.uploads == [
        ("https://cos.example.com/part-0", data[:4]),
        ("https://cos.example.com/part-1", data[4:]),
    ]
    # 每片上传完都要通知服务端
    assert [call[1].part_index for call in finish_calls] == [0, 1]
    assert [call[1].block_size for call in finish_calls] == ["4", "6"]
    assert finish_calls[0][1].md5 == hashlib.md5(data[:4]).hexdigest()
    assert finish_calls[1][1].md5 == hashlib.md5(data[4:]).hexdigest()
    assert all(call[1].upload_id == "UP-1" for call in finish_calls)
    # 合并文件拿 file_info
    _, upload_request = upload_calls[0]
    assert upload_request.upload_id == "UP-1"
    assert upload_request.file_type == 1
    assert upload_request.file_name == "pic.png"


async def test_upload_image_single_part(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image = tmp_path / "tiny.png"
    image.write_bytes(b"abc")
    _, finish_calls, _, fake_session = _patch_group_upload(monkeypatch, _parts(5))

    await _group_context().api.upload_image(image)

    assert len(fake_session.uploads) == 1
    assert fake_session.uploads[0][1] == b"abc"
    assert len(finish_calls) == 1
    assert finish_calls[0][1].block_size == "3"


async def test_upload_image_md5_10m_uses_first_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """md5_10m 只取前 10002432 字节, 这里把它改小以验证截断逻辑."""
    data = b"0123456789"
    image = tmp_path / "pic.png"
    image.write_bytes(data)
    prepared_calls, _, _, _ = _patch_group_upload(monkeypatch, _parts(len(data)))
    monkeypatch.setattr(app_api, "MD5_10M_BYTES", 4)

    await _group_context().api.upload_image(image)

    _, prepare = prepared_calls[0]
    assert prepare.md5_10m == hashlib.md5(data[:4]).hexdigest()
    assert prepare.md5 == hashlib.md5(data).hexdigest()


async def test_upload_image_c2c(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "pic.png"
    image.write_bytes(b"abcd")
    prepared_calls: list[Any] = []
    finish_calls: list[Any] = []
    upload_calls: list[Any] = []
    fake_session = _FakeSession()

    async def fake_prepare(user_openid: str, payload: Any) -> Any:
        prepared_calls.append((user_openid, payload))
        return PrepareUserUploadResponse.model_validate(
            {"upload_id": "UP-2", "block_size": "4", "parts": _parts(4)}
        )

    async def fake_finish(user_openid: str, payload: Any) -> None:
        finish_calls.append((user_openid, payload))

    async def fake_upload(user_openid: str, payload: Any) -> Any:
        upload_calls.append((user_openid, payload))
        return UploadUserFileResponse.model_validate({"file_info": "C2C-FILE"})

    monkeypatch.setattr(user_api, "prepare_user_upload", fake_prepare)
    monkeypatch.setattr(user_api, "finish_user_upload_part", fake_finish)
    monkeypatch.setattr(user_api, "upload_user_file", fake_upload)
    monkeypatch.setattr(app_api, "session", fake_session)

    file_info = await _c2c_context().api.upload_image(image)

    assert file_info == "C2C-FILE"
    assert prepared_calls[0][0] == USER_OPENID
    assert len(fake_session.uploads) == 1
    assert finish_calls[0][1].upload_id == "UP-2"
    assert upload_calls[0][0] == USER_OPENID


async def test_upload_image_without_parts_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image = tmp_path / "pic.png"
    image.write_bytes(b"abcd")
    _patch_group_upload(monkeypatch, [])

    with pytest.raises(Exception, match="分片"):
        await _group_context().api.upload_image(image)


async def test_upload_image_without_file_info_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image = tmp_path / "pic.png"
    image.write_bytes(b"abcd")
    _, _, _, _ = _patch_group_upload(monkeypatch, _parts(4))

    async def fake_upload(_group_openid: str, _payload: Any) -> Any:
        return UploadGroupFileResponse.model_validate({"file_id": "x"})

    monkeypatch.setattr(group_messages, "upload_group_file", fake_upload)

    with pytest.raises(Exception, match="file_info"):
        await _group_context().api.upload_image(image)


def test_request_body_is_json_serializable() -> None:
    """发送请求体最终要能序列化成 JSON, 这里顺手校验一下嵌套模型."""
    from qqbotsdk.model.sub.messages import MessageCard, MessageCardContent

    card = MessageCard.model_validate(
        {
            "type": "tuwen",
            "content": MessageCardContent.model_validate(
                {
                    "title": "t",
                    "description": "d",
                    "url": "https://example.com",
                    "pic_url": "https://example.com/p.png",
                }
            ),
        }
    )
    dumped = card.model_dump(exclude_none=True)
    assert dumped["type"] == "tuwen"
    assert dumped["content"]["title"] == "t"
    assert json.dumps(dumped)


# ---------------------------------------------------------------- 单聊兜底与键盘


def test_friend_add_is_c2c_scene() -> None:
    """FRIEND_ADD 只有顶层 openid, 也应视为单聊, 否则这类事件里发不出消息."""
    assert _friend_add_context().api.scene == "c2c"


async def test_send_uses_top_level_openid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent = _patch_user_send(monkeypatch)
    ctx = _friend_add_context()
    msg_id = await ctx.api.send("你好")
    assert msg_id
    assert sent[0][0] == "FRIEND-1"
    assert sent[0][1].model_dump(exclude_none=True) == {
        "msg_type": 0,
        "content": "你好",
    }


async def test_send_with_keyboard(monkeypatch: pytest.MonkeyPatch) -> None:
    """按钮挂在文本消息上, 请求体要带 keyboard."""
    from qqbotsdk.model.sub.messages import (
        Action,
        Button,
        Keyboard,
        KeyboardContent,
        RenderData,
        Row,
    )

    sent = _patch_group_send(monkeypatch)
    keyboard = Keyboard(
        content=KeyboardContent(
            rows=[
                Row(
                    buttons=[
                        Button(
                            id="b1",
                            render_data=RenderData(label="点我", style=1),
                            action=Action(type=1, data="/ping"),
                        )
                    ]
                )
            ]
        )
    )
    await _group_context().api.send("带按钮", keyboard=keyboard)
    body = sent[0][1]
    assert body.msg_type == 0
    assert body.keyboard is not None
    assert body.keyboard.content is not None
    assert body.keyboard.content.rows is not None
    assert body.keyboard.content.rows[0].buttons is not None
    assert body.keyboard.content.rows[0].buttons[0].action is not None
    assert body.keyboard.content.rows[0].buttons[0].action.data == "/ping"


async def test_send_markdown_with_keyboard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qqbotsdk.model.sub.messages import Keyboard, KeyboardContent, Row

    sent = _patch_group_send(monkeypatch)
    keyboard = Keyboard(content=KeyboardContent(rows=[Row(buttons=[])]))
    await _group_context().api.send_markdown("## hi", keyboard=keyboard)
    body = sent[0][1]
    assert body.msg_type == 2
    assert body.keyboard is not None
    assert body.markdown is not None
    assert body.markdown.content == "## hi"
