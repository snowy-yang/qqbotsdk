"""模型契约测试: 请求禁止未知字段, 响应宽容未知字段, 事件注册表完整."""

from typing import Any

import pytest
from pydantic import ValidationError

from qqbotsdk.model.event import EVENT_MODELS as GROUP_EVENT_MODELS
from qqbotsdk.model.event import parse_event
from qqbotsdk.model.group.messages import SendGroupMessagesRequest
from qqbotsdk.model.guild.event import EVENT_MODELS as GUILD_EVENT_MODELS
from qqbotsdk.model.guild.event import parse_event as parse_guild_event
from qqbotsdk.ws.payload import GatewayPayload


def test_request_rejects_unknown_field() -> None:
    """请求模型拼错字段名必须立刻报错, 不能静默发给服务端."""
    with pytest.raises(ValidationError) as excinfo:
        SendGroupMessagesRequest(contnet="你好", msg_type=0)
    assert "contnet" in str(excinfo.value)


def test_request_accepts_known_fields() -> None:
    request = SendGroupMessagesRequest(msg_type=0, content="hi", msg_seq=1)
    assert request.model_dump(exclude_none=True) == {
        "msg_type": 0,
        "content": "hi",
        "msg_seq": 1,
    }


def test_response_tolerates_unknown_field() -> None:
    """响应模型要容忍服务端新增字段, 否则接口一上线新字段就全崩."""
    from qqbotsdk.model.group.messages import SendGroupMessagesResponse

    response = SendGroupMessagesResponse.model_validate(
        {"id": "msg-1", "timestamp": "2026-07-21T10:00:00+08:00", "brand_new": 1}
    )
    assert response.id == "msg-1"
    assert response.model_dump()["brand_new"] == 1


def test_required_field_is_enforced() -> None:
    from qqbotsdk.model.sub.upload import UploadPrepareRequest

    with pytest.raises(ValidationError):
        UploadPrepareRequest()  # pyright: ignore[reportCallIssue]

    ok = UploadPrepareRequest(
        file_type=1,
        file_size="1024",
        file_name="a.png",
        md5="m",
        sha1="s",
        md5_10m="m",
    )
    assert ok.file_type == 1


def test_group_event_registry() -> None:
    assert len(GROUP_EVENT_MODELS) == 16
    payload = GatewayPayload.model_validate(
        {
            "op": 0,
            "s": 2,
            "t": "GROUP_AT_MESSAGE_CREATE",
            "id": "evt-1",
            "d": {
                "content": "hi",
                "group_openid": "G1",
                "author": {"member_openid": "m-1", "member_role": "owner"},
            },
        }
    )
    event = parse_event(payload)
    assert event is not None
    assert type(event).__name__ == "GroupAtMessageCreateEvent"
    assert event.model_dump()["content"] == "hi"


def test_guild_event_registry() -> None:
    assert len(GUILD_EVENT_MODELS) == 40
    payload = GatewayPayload.model_validate(
        {
            "op": 0,
            "s": 3,
            "t": "GUILD_CREATE",
            "id": "evt-2",
            "d": {"id": "123456", "name": "技术交流频道", "member_count": 100},
        }
    )
    event = parse_guild_event(payload)
    assert event is not None
    assert type(event).__name__ == "GuildCreateEvent"
    assert event.model_dump()["name"] == "技术交流频道"


@pytest.mark.parametrize("event_name", ["NOT_A_REAL_EVENT", "READY", ""])
def test_unknown_event_returns_none(event_name: str) -> None:
    payload = GatewayPayload.model_validate({"op": 0, "t": event_name, "d": {}})
    assert parse_event(payload) is None
    assert parse_guild_event(payload) is None


def test_event_registries_do_not_overlap() -> None:
    overlap = set(GROUP_EVENT_MODELS) & set(GUILD_EVENT_MODELS)
    assert overlap == set()


def test_all_models_share_base() -> None:
    from qqbotsdk.model.core import QQBotBaseModel

    for registry in (GROUP_EVENT_MODELS, GUILD_EVENT_MODELS):
        for name, model in registry.items():
            assert issubclass(model, QQBotBaseModel), f"{name} 未继承 QQBotBaseModel"


def test_request_model_dump_is_json_serializable() -> None:
    """请求体最终要交给 aiohttp 的 json=, 必须能被 json.dumps 直接序列化."""
    import json

    request = SendGroupMessagesRequest(msg_type=0, content="中文", msg_seq=1)
    dumped: dict[str, Any] = request.model_dump(exclude_none=True)
    assert json.loads(json.dumps(dumped))["content"] == "中文"
