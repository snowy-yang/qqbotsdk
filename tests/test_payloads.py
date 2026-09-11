from qqbotsdk.emitter import EventEmitter
from qqbotsdk.model import Opcode
from qqbotsdk.payloads import (
    C2CMessage,
    GroupAtMessage,
    Ready,
    parse_event,
)
from qqbotsdk.queue import EventQueue


def test_parse_group_at_message():
    msg = parse_event(
        "GROUP_AT_MESSAGE_CREATE",
        {
            "author": {"id": None, "member_openid": "M1"},
            "content": "hi",
            "group_openid": "G1",
            "id": "msgid-1",
            "timestamp": "2026-01-01",
        },
    )
    assert isinstance(msg, GroupAtMessage)
    assert msg.group_openid == "G1"
    assert msg.user_openid == "M1"
    assert msg.id == "msgid-1"
    assert msg.author is not None and msg.author.member_openid == "M1"


def test_parse_c2c_message():
    msg = parse_event(
        "C2C_MESSAGE_CREATE",
        {"author": {"user_openid": "U1"}, "content": "hello", "id": "m2"},
    )
    assert isinstance(msg, C2CMessage)
    assert msg.user_openid == "U1"


def test_parse_ready():
    ready = parse_event(
        "READY", {"session_id": "s1", "version": 1, "user": {"id": "b"}}
    )
    assert isinstance(ready, Ready)
    assert ready.session_id == "s1"


def test_parse_unknown_type_returns_dict():
    d = {"whatever": 1}
    assert parse_event("SOME_FUTURE_EVENT", d) is d
    assert parse_event(None, d) is d


def test_parse_ignores_extra_and_missing_fields():
    msg = parse_event("GROUP_AT_MESSAGE_CREATE", {"content": "x", "future_field": 9})
    assert isinstance(msg, GroupAtMessage)
    assert msg.content == "x"
    assert msg.group_openid is None


def test_parse_non_dict_d_returns_dict():
    d = 42  # 心跳等 opcode 的 d 是数字
    assert parse_event("GROUP_AT_MESSAGE_CREATE", d) == 42


async def test_typed_annotation_receives_dataclass():
    queue = EventQueue()
    emitter = EventEmitter(queue)
    received: list[GroupAtMessage] = []

    @emitter.on("GROUP_AT_MESSAGE_CREATE")
    async def handler(msg: GroupAtMessage):
        received.append(msg)

    await emitter.emit(
        {
            "op": Opcode.DISPATCH,
            "t": "GROUP_AT_MESSAGE_CREATE",
            "d": {"content": "hi", "group_openid": "G1"},
        }
    )
    assert len(received) == 1
    assert received[0].content == "hi"
    assert received[0].group_openid == "G1"


async def test_untyped_annotation_still_receives_raw_dict():
    queue = EventQueue()
    emitter = EventEmitter(queue)
    received: list[dict] = []

    @emitter.on("GROUP_AT_MESSAGE_CREATE")
    async def handler(d):
        received.append(d)

    await emitter.emit(
        {"op": Opcode.DISPATCH, "t": "GROUP_AT_MESSAGE_CREATE", "d": {"content": "x"}}
    )
    assert received == [{"content": "x"}]
