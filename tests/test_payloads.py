from qqbotsdk.emitter import EventEmitter
from qqbotsdk.model import Opcode
from qqbotsdk.payloads import (
    _PARSE_PLANS,
    C2CMessage,
    GroupAtMessage,
    Interaction,
    Ready,
    parse_event,
)
from qqbotsdk.queue import EventQueue


def test_parse_ignores_unknown_fields():
    """回归：线上 payload 会带未收录字段（如 author.union_openid），
    解析必须忽略而非透传给 dataclass 构造（那会直接报错）。"""
    msg = parse_event(
        "GROUP_AT_MESSAGE_CREATE",
        {
            "id": "msgid-9",
            "content": "hi",
            "group_openid": "G1",
            "unknown_top_level": {"whatever": 1},
            "author": {"member_openid": "M9", "union_openid": "U-should-be-dropped"},
        },
    )
    assert isinstance(msg, GroupAtMessage)
    assert msg.content == "hi"
    assert msg.author is not None and msg.author.member_openid == "M9"


def test_parse_plan_is_cached_per_class():
    """解析计划按类缓存，且二次解析结果与首次一致。"""
    d = {"content": "x", "group_openid": "G"}
    first = parse_event("GROUP_AT_MESSAGE_CREATE", d)
    second = parse_event("GROUP_AT_MESSAGE_CREATE", d)
    assert isinstance(first, GroupAtMessage) and isinstance(second, GroupAtMessage)
    assert first.content == second.content == "x"
    assert GroupAtMessage in _PARSE_PLANS

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


def test_parse_group_full_message():
    msg = parse_event(
        "GROUP_MESSAGE_CREATE",
        {
            "author": {"member_openid": "M2"},
            "content": "大家好",
            "group_openid": "G1",
            "id": "msgid-2",
            "timestamp": "2026-01-01",
            "message_type": 0,
            "message_scene": {"unknown": False},
            "attachments": [{"content_type": 1, "url": "https://x/img.png"}],
            "mentions": [{"id": "U1"}],
            "msg_elements": [{"type": 1, "text_element": {"content": "大家好"}}],
        },
    )
    assert isinstance(msg, GroupAtMessage)
    assert msg.group_openid == "G1"
    assert msg.user_openid == "M2"
    assert msg.message_type == 0
    assert msg.message_scene == {"unknown": False}
    assert msg.attachments == [{"content_type": 1, "url": "https://x/img.png"}]
    assert msg.mentions == [{"id": "U1"}]
    assert msg.msg_elements == [{"type": 1, "text_element": {"content": "大家好"}}]


async def test_group_full_message_reaches_typed_handler():
    queue = EventQueue()
    emitter = EventEmitter(queue)
    received: list[GroupAtMessage] = []

    @emitter.on("GROUP_MESSAGE_CREATE")
    async def handler(msg: GroupAtMessage):
        received.append(msg)

    await emitter.emit(
        {
            "op": Opcode.DISPATCH,
            "t": "GROUP_MESSAGE_CREATE",
            "d": {"content": "hi", "group_openid": "G1"},
        }
    )
    assert len(received) == 1
    assert received[0].content == "hi"
    assert received[0].group_openid == "G1"


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


def test_interaction_button_data():
    inter = parse_event(
        "INTERACTION_CREATE",
        {
            "id": "i1",
            "chat_type": 1,
            "group_openid": "G1",
            "data": {"resolved": {"button_data": "btn|like"}},
        },
    )
    assert isinstance(inter, Interaction)
    assert inter.button_data == "btn|like"


def test_interaction_button_data_defaults_to_empty():
    inter = Interaction(id="i2", data=None)
    assert inter.button_data == ""
    inter = Interaction(id="i3", data={"resolved": None})
    assert inter.button_data == ""


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


def test_parse_group_member_and_join_request_events():
    from qqbotsdk.payloads import (
        GroupJoinRequest,
        GroupMemberChange,
        SubscribeMessageStatus,
    )

    change = parse_event(
        "GROUP_MEMBER_ADD",
        {
            "timestamp": 1784276757,
            "group_openid": "G1",
            "member_openid": "M1",
            "user_openid": "U1",
        },
    )
    assert isinstance(change, GroupMemberChange)
    assert change.member_openid == "M1"
    # 两事件 d 结构一致，共用 dataclass
    remove = parse_event(
        "GROUP_MEMBER_REMOVE",
        {"timestamp": 1, "group_openid": "G1", "member_openid": "M2"},
    )
    assert isinstance(remove, GroupMemberChange)
    assert remove.user_openid is None

    req = parse_event(
        "GROUP_JOIN_REQUEST",
        {
            "group_openid": "G1",
            "join_request_id": "j1",
            "member_openid": "M1",
            "username": "小明",
            "apply_source": "self_apply",
            "verify_info": {"method": "verify_message", "verify_message": "来了"},
            "auto_approved": {"strategy_id": "st1"},
            "unknown_field": 1,
        },
    )
    assert isinstance(req, GroupJoinRequest)
    assert req.join_request_id == "j1"
    assert req.verify_info == {"method": "verify_message", "verify_message": "来了"}
    assert req.auto_approved == {"strategy_id": "st1"}

    status = parse_event(
        "SUBSCRIBE_MESSAGE_STATUS",
        {
            "openid": "U1",
            "result": [{"template_id": 10001, "op": 1, "subscribe_id": "sub1"}],
        },
    )
    assert isinstance(status, SubscribeMessageStatus)
    assert status.group_openid is None
    assert status.result[0]["subscribe_id"] == "sub1"
