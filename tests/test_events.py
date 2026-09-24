"""Event 封装：信封顶层 event_id 与事件体 d 的访问（.data/.typed）。"""

from qqbotsdk.events import Event
from qqbotsdk.payloads import GroupAddRobot


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


def test_message_id_from_event_body():
    event = Event(
        {
            "op": 0,
            "id": "evt-2",
            "t": "GROUP_AT_MESSAGE_CREATE",
            "d": {"id": "msgid-1", "group_openid": "G1", "content": "hi"},
        }
    )
    assert event.data["id"] == "msgid-1"  # 消息事件回复用 msg_id（事件体 d.id）
    assert event.event_id == "evt-2"  # 信封顶层 id 另有其值


def test_typed_parses_event_body():
    event = make_event()
    typed = event.typed
    assert isinstance(typed, GroupAddRobot)
    assert typed.group_openid == "G1"


def test_event_id_defaults_to_none():
    event = Event({"op": 0, "t": "READY", "d": {}})
    assert event.event_id is None
