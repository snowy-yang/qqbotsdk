"""单聊 / 好友 / 订阅消息事件模型.

这里的每个模型都只描述网关帧的 ``d`` 字段, 信封(``id``/``op``/``s``/``t``)由
``qqbotsdk.ws.payload.GatewayPayload`` 承载.

单聊消息事件体与群聊消息事件体结构一致, 只是少了 ``group_openid`` 与
``mentions``, 因此复用 ``qqbotsdk.model.event.group`` 中的子对象.
"""

from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.event.group import (
    EventArkData,
    EventMessageAttachment,
    EventMessageScene,
    EventMsgElement,
    EventUser,
)

FriendScene = Literal[1000, 1001, 1002, 1003, 1004, 2001, 2002, 2003, 2004]


class C2CMessageCreateEvent(QQBotBaseModel):
    """用户给机器人发送单聊消息 (C2C_MESSAGE_CREATE)."""

    id: str | None = Field(
        default=None,
        description="消息 ID，可用于被动回复和撤回",
    )
    author: EventUser | None = Field(
        default=None,
        description="发送者，单聊场景下 user_openid 有值",
    )
    content: str | None = Field(
        default=None,
        description="消息文本内容",
    )
    timestamp: str | None = Field(
        default=None,
        description="消息发送时间，RFC3339 格式",
    )
    message_type: int | None = Field(
        default=None,
        description="消息内容类型：0=普通文本，3=结构化卡片，101=并行消息，102=聊天记录，103=引用消息",
    )
    message_scene: EventMessageScene | None = Field(
        default=None,
        description="消息场景上下文（含消息索引、鉴权令牌等）",
    )
    attachments: list[EventMessageAttachment] | None = Field(
        default=None,
        description="消息附件（图片、文件、语音等）",
    )
    ark_data: EventArkData | None = Field(
        default=None,
        description="结构化卡片消息数据，message_type=3 时有值",
    )
    msg_elements: list[EventMsgElement] | None = Field(
        default=None,
        description="消息元素列表，message_type=103 引用消息时包含被引用内容",
    )


class C2CMsgReceiveEvent(QQBotBaseModel):
    """用户在机器人资料卡开启主动消息推送 (C2C_MSG_RECEIVE)."""

    timestamp: int | None = Field(
        default=None,
        description="操作时间戳（Unix 秒）",
    )
    openid: str | None = Field(
        default=None,
        description="用户 OpenID",
    )


class C2CMsgRejectEvent(QQBotBaseModel):
    """用户在机器人资料卡关闭主动消息推送 (C2C_MSG_REJECT)."""

    timestamp: int | None = Field(
        default=None,
        description="操作时间戳（Unix 秒）",
    )
    openid: str | None = Field(
        default=None,
        description="用户 OpenID",
    )


class FriendAuthor(QQBotBaseModel):
    """好友事件里的用户信息."""

    union_openid: str | None = Field(
        default=None,
        description="用户统一 OpenID（跨应用标识）",
    )


class FriendAddEvent(QQBotBaseModel):
    """用户添加机器人好友 (FRIEND_ADD)."""

    openid: str | None = Field(
        default=None,
        description="用户 OpenID",
    )
    timestamp: int | None = Field(
        default=None,
        description="添加时间戳（Unix 秒）",
    )
    scene: FriendScene | None = Field(
        default=None,
        description="加好友场景值：1000=缺省默认，1001=网络搜索（全部tab），1002=网络搜索（机器人tab），1003=群场景，1004=空间场景，2001=站内分享资料页，2002=站外分享资料页，2003=开发者生成的分享链接（站内），2004=开发者生成的分享链接（站外）",
    )
    scene_param: str | None = Field(
        default=None,
        description="开发者自定义的回调数据（callback_data），用于区分不同来源",
    )
    author: FriendAuthor | None = Field(
        default=None,
        description="用户信息",
    )
    short_code: str | None = Field(
        default=None,
        description="机器人分享链接的短链 code",
    )


class FriendDelEvent(QQBotBaseModel):
    """用户删除机器人好友 (FRIEND_DEL)."""

    openid: str | None = Field(
        default=None,
        description="用户 OpenID",
    )
    timestamp: int | None = Field(
        default=None,
        description="删除时间戳（Unix 秒）",
    )
    author: FriendAuthor | None = Field(
        default=None,
        description="用户信息",
    )


class SubscribeMsgTemplateResult(QQBotBaseModel):
    """单个订阅消息模板的授权结果."""

    template_id: int | None = Field(
        default=None,
        description="平台提供的订阅模板 ID",
    )
    custom_template_id: str | None = Field(
        default=None,
        description="自定义订阅模板 ID",
    )
    op: Literal[1, 2] | None = Field(
        default=None,
        description="用户操作：1=允许订阅，2=拒绝订阅",
    )
    subscribe_id: str | None = Field(
        default=None,
        description="订阅 ID，发送订阅消息时需使用",
    )
    subscribe_ts: int | None = Field(
        default=None,
        description="订阅操作时间戳（Unix 秒）",
    )
    update_ts: int | None = Field(
        default=None,
        description="订阅状态最后更新时间戳（Unix 秒）",
    )


class SubscribeMessageStatusEvent(QQBotBaseModel):
    """用户对订阅消息模板的授权状态发生变化 (SUBSCRIBE_MESSAGE_STATUS)."""

    group_openid: str | None = Field(
        default=None,
        description="群 OpenID（群订阅场景时有值）",
    )
    openid: str | None = Field(
        default=None,
        description="用户 OpenID（个人订阅场景时有值）",
    )
    result: list[SubscribeMsgTemplateResult] | None = Field(
        default=None,
        description="各模板的授权结果列表",
    )


__all__ = [
    "C2CMessageCreateEvent",
    "C2CMsgReceiveEvent",
    "C2CMsgRejectEvent",
    "FriendAddEvent",
    "FriendAuthor",
    "FriendDelEvent",
    "FriendScene",
    "SubscribeMessageStatusEvent",
    "SubscribeMsgTemplateResult",
]
