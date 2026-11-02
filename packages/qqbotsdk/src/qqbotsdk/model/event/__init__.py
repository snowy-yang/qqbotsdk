"""群聊 / 单聊 / 好友 / 订阅消息 / 互动 事件模型与事件注册表.

网关帧形如 ``{"id": ..., "op": 0, "s": 1, "t": "GROUP_AT_MESSAGE_CREATE", "d": {...}}``.
本包的事件模型只描述事件体 ``d``, 信封由 ``qqbotsdk.ws.payload.GatewayPayload``
承载. 用 ``parse_event`` 可以按事件名一次性拿到解析好的事件对象::

    payload = GatewayPayload.model_validate(raw_frame)
    event = parse_event(payload)
    if isinstance(event, GroupAtMessageCreateEvent):
        print(event.content, event.group_openid)
"""

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.event.c2c import (
    C2CMessageCreateEvent,
    C2CMsgReceiveEvent,
    C2CMsgRejectEvent,
    FriendAddEvent,
    FriendAuthor,
    FriendDelEvent,
    SubscribeMessageStatusEvent,
    SubscribeMsgTemplateResult,
)
from qqbotsdk.model.event.group import (
    EventArkData,
    EventMessageAttachment,
    EventMessageScene,
    EventMsgElement,
    EventUser,
    GroupAddRobotEvent,
    GroupAtMessageCreateEvent,
    GroupAutoApproved,
    GroupDelRobotEvent,
    GroupJoinRequestEvent,
    GroupMemberAddEvent,
    GroupMemberChangeEvent,
    GroupMemberRemoveEvent,
    GroupMessageCreateEvent,
    GroupMessageEventBase,
    GroupMsgReceiveEvent,
    GroupMsgRejectEvent,
    GroupRobotOperationEvent,
)
from qqbotsdk.model.event.interaction import (
    InteractionAuthorizeData,
    InteractionCreateEvent,
    InteractionData,
    InteractionMessageScene,
    InteractionResolved,
)
from qqbotsdk.ws.payload import GatewayPayload

EVENT_MODELS: dict[str, type[QQBotBaseModel]] = {
    "C2C_MESSAGE_CREATE": C2CMessageCreateEvent,
    "C2C_MSG_RECEIVE": C2CMsgReceiveEvent,
    "C2C_MSG_REJECT": C2CMsgRejectEvent,
    "FRIEND_ADD": FriendAddEvent,
    "FRIEND_DEL": FriendDelEvent,
    "GROUP_ADD_ROBOT": GroupAddRobotEvent,
    "GROUP_AT_MESSAGE_CREATE": GroupAtMessageCreateEvent,
    "GROUP_DEL_ROBOT": GroupDelRobotEvent,
    "GROUP_JOIN_REQUEST": GroupJoinRequestEvent,
    "GROUP_MEMBER_ADD": GroupMemberAddEvent,
    "GROUP_MEMBER_REMOVE": GroupMemberRemoveEvent,
    "GROUP_MESSAGE_CREATE": GroupMessageCreateEvent,
    "GROUP_MSG_RECEIVE": GroupMsgReceiveEvent,
    "GROUP_MSG_REJECT": GroupMsgRejectEvent,
    "INTERACTION_CREATE": InteractionCreateEvent,
    "SUBSCRIBE_MESSAGE_STATUS": SubscribeMessageStatusEvent,
}


def parse_event(payload: GatewayPayload) -> QQBotBaseModel | None:
    """按 payload.t 解析事件体; 未建模的事件返回 None."""
    model = EVENT_MODELS.get(payload.t or "")
    if model is None:
        return None
    return model.model_validate(payload.d)


__all__ = [
    "EVENT_MODELS",
    "C2CMessageCreateEvent",
    "C2CMsgReceiveEvent",
    "C2CMsgRejectEvent",
    "EventArkData",
    "EventMessageAttachment",
    "EventMessageScene",
    "EventMsgElement",
    "EventUser",
    "FriendAddEvent",
    "FriendAuthor",
    "FriendDelEvent",
    "GroupAddRobotEvent",
    "GroupAtMessageCreateEvent",
    "GroupAutoApproved",
    "GroupDelRobotEvent",
    "GroupJoinRequestEvent",
    "GroupMemberAddEvent",
    "GroupMemberChangeEvent",
    "GroupMemberRemoveEvent",
    "GroupMessageCreateEvent",
    "GroupMessageEventBase",
    "GroupMsgReceiveEvent",
    "GroupMsgRejectEvent",
    "GroupRobotOperationEvent",
    "InteractionAuthorizeData",
    "InteractionCreateEvent",
    "InteractionData",
    "InteractionMessageScene",
    "InteractionResolved",
    "SubscribeMessageStatusEvent",
    "SubscribeMsgTemplateResult",
    "parse_event",
]
