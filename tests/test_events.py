"""Event 封装属性：message_id 取自事件体 d.id，event_id 取自信封顶层 id。"""

from qqbotsdk.events import Event


def make_event() -> Event:
    return Event(
        {
            "op": 0,
            "id": "evt-1",  # 信封顶层，与 op/t/d 平级
            "t": "GROUP_ADD_ROBOT",
            "d": {"group_openid": "G1", "op_member_openid": "M1"},
        }
    )


def test_event_id_from_envelope():
    event = make_event()
    assert event.event_id == "evt-1"
    assert event.group_id == "G1"


def test_message_id_from_event_body():
    event = Event(
        {
            "op": 0,
            "id": "evt-2",
            "t": "GROUP_AT_MESSAGE_CREATE",
            "d": {"id": "msgid-1", "group_openid": "G1", "content": "hi"},
        }
    )
    assert event.message_id == "msgid-1"  # 消息事件回复用 msg_id
    assert event.event_id == "evt-2"  # 信封顶层 id 另有其值


def test_event_id_defaults_to_none():
    event = Event({"op": 0, "t": "READY", "d": {}})
    assert event.event_id is None
    assert event.message_id is None
