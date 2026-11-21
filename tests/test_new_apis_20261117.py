"""2026-11 官方新接口 / 新字段的契约测试.

覆盖:
- ``GET /v2/users/{user_openid}/info`` 与 ``UserInfo`` 模型;
- 消息事件新字段 ``author.avatar`` / ``author.member_nickname``;
- ``mentions`` 元素类型 ``EventMentionUser`` 及其 ``is_you`` / ``scope``;
- 群消息事件 / 机器人进出群 / 群成员增减 / 群信息上的 ``union_group_openid``;
- 新增错误码的取值.
"""

from typing import Any

import pytest

from qqbotsdk.api import core
from qqbotsdk.api import user as user_api
from qqbotsdk.errors import codes
from qqbotsdk.model.event import parse_event
from qqbotsdk.model.event.group import (
    EventMentionUser,
    GroupAddRobotEvent,
    GroupAtMessageCreateEvent,
    GroupMemberAddEvent,
)
from qqbotsdk.model.group.member import GetGroupInfoResponse
from qqbotsdk.model.user.info import GetUserInfoResponse, UserInfo
from qqbotsdk.ws.payload import GatewayPayload


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def json(self) -> dict[str, Any]:
        return self._payload


class _FakeContext:
    def __init__(
        self,
        calls: list[tuple[str, str]],
        method: str,
        url: str,
        payload: dict[str, Any],
    ) -> None:
        self._calls = calls
        self._method = method
        self._url = url
        self._payload = payload

    async def __aenter__(self) -> _FakeResponse:
        self._calls.append((self._method, self._url))
        return _FakeResponse(self._payload)

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FakeSession:
    """只实现 get: 用户信息接口没有请求体."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.calls: list[tuple[str, str]] = []
        self.payload = payload

    def get(self, url: str, **_kwargs: Any) -> _FakeContext:
        return _FakeContext(self.calls, "GET", url, self.payload)


async def test_get_user_info_route_and_fields() -> None:
    """打的是 /v2/users/{openid}/info, 四个字段都要落到模型上."""
    fake = _FakeSession(
        {
            "union_openid": "UNION-1",
            "username": "小明",
            "avatar": "https://example.com/a.png",
            "allow_proactive_msg": True,
        }
    )
    core.set_session(fake)  # type: ignore[arg-type]

    info = await user_api.get_user_info("U1")

    assert fake.calls == [("GET", "/v2/users/U1/info")]
    assert isinstance(info, GetUserInfoResponse)
    assert info.union_openid == "UNION-1"
    assert info.username == "小明"
    assert info.avatar == "https://example.com/a.png"
    assert info.allow_proactive_msg is True


def test_user_info_all_fields_optional() -> None:
    """平台可能只回部分字段, 不能因为缺字段就抛."""
    info = UserInfo.model_validate({})
    assert info.union_openid is None
    assert info.username is None
    assert info.avatar is None
    assert info.allow_proactive_msg is None


def test_group_message_event_new_author_fields() -> None:
    """群消息事件新增头像与群昵称, 且 union_group_openid 落在事件体上."""
    event = GroupAtMessageCreateEvent.model_validate(
        {
            "id": "MSG-1",
            "group_openid": "G1",
            "union_group_openid": "UG1",
            "author": {
                "id": "A1",
                "username": "小明",
                "member_openid": "M1",
                "avatar": "https://example.com/a.png",
                "member_nickname": "群名片",
            },
        }
    )
    assert event.union_group_openid == "UG1"
    assert event.author is not None
    assert event.author.avatar == "https://example.com/a.png"
    assert event.author.member_nickname == "群名片"
    # 原有便捷属性不受影响
    assert event.sender_openid == "M1"


def test_mentions_parse_as_mention_user() -> None:
    """mentions 元素是 EventMentionUser, 带 is_you 与 scope; 旧字段照旧可用."""
    event = GroupAtMessageCreateEvent.model_validate(
        {
            "id": "MSG-1",
            "group_openid": "G1",
            "mentions": [
                {"id": "A1", "member_openid": "M1", "scope": "all", "is_you": False},
                {
                    "id": "A2",
                    "member_openid": "M2",
                    "scope": "single",
                    "is_you": True,
                    "member_nickname": "群名片",
                },
            ],
        }
    )
    first, second = event.mentions or []
    assert isinstance(first, EventMentionUser)
    assert first.scope == "all"
    assert first.member_openid == "M1"
    assert second.is_you is True
    assert second.scope == "single"
    assert second.member_nickname == "群名片"


def test_group_robot_and_member_events_union_group_openid() -> None:
    """机器人进出群与群成员增减事件同样带 union_group_openid."""
    robot = GroupAddRobotEvent.model_validate(
        {"timestamp": 1, "group_openid": "G1", "union_group_openid": "UG1"}
    )
    member = GroupMemberAddEvent.model_validate(
        {"timestamp": 1, "group_openid": "G1", "union_group_openid": "UG1"}
    )
    assert robot.union_group_openid == "UG1"
    assert member.union_group_openid == "UG1"


def test_parse_event_keeps_new_fields() -> None:
    """走注册表解析也不能丢新字段."""
    payload = {
        "op": 0,
        "t": "GROUP_AT_MESSAGE_CREATE",
        "id": "EVT-1",
        "d": {
            "id": "MSG-1",
            "group_openid": "G1",
            "union_group_openid": "UG1",
            "author": {"id": "A1", "member_openid": "M1", "avatar": "https://x/a.png"},
        },
    }
    event = parse_event(GatewayPayload.model_validate(payload))
    assert isinstance(event, GroupAtMessageCreateEvent)
    assert event.union_group_openid == "UG1"
    assert event.author is not None
    assert event.author.avatar == "https://x/a.png"


def test_group_info_union_group_openid() -> None:
    resp = GetGroupInfoResponse.model_validate(
        {"group_openid": "G1", "union_group_openid": "UG1", "group_name": "群"}
    )
    assert resp.union_group_openid == "UG1"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MSG_NO_FRIENDSHIP", 40054004),
        ("MSG_FRIEND_VERIFY_FAILED", 40054006),
        ("MSG_USER_REJECTED", 40054013),
        ("MSG_TOO_LONG_OR_ABNORMAL", 40054018),
        ("MSG_INPUT_TYPE_INVALID", 50059),
        ("MSG_SUBSCRIBE_BUTTON_LIMIT", 304062),
        ("USER_NO_FRIENDSHIP", 40184001),
    ],
)
def test_new_error_codes(name: str, value: int) -> None:
    assert getattr(codes, name) == value
    assert name in codes.__all__
