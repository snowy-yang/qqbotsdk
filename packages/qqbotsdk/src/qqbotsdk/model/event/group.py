"""群聊事件模型.

这里的每个模型都只描述网关帧的 ``d`` 字段, 信封(``id``/``op``/``s``/``t``)由
``qqbotsdk.ws.payload.GatewayPayload`` 承载.

本模块同时承载群聊与单聊消息共用的子对象(``EventUser`` / ``EventMessageScene``
/ ``EventMessageAttachment`` / ``EventArkData`` / ``EventMsgElement``),
``qqbotsdk.model.event.c2c`` 直接复用它们.
"""

from typing import Any, Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.group.join_request import JoinRequest


class EventUser(QQBotBaseModel):
    """群聊与单聊事件里的发送者 / 被@用户.

    与 ``qqbotsdk.model.guild.member.User`` 不同: 这里带有 ``user_openid`` /
    ``member_openid`` / ``member_role`` 三个 QQ 单群聊场景专用字段, 且不含
    ``avatar``. guild 包是可选依赖, 本包不能反向引用.
    """

    id: str | None = Field(
        default=None,
        description="用户唯一标识（OpenID 格式）",
    )
    username: str | None = Field(
        default=None,
        description="用户昵称",
    )
    bot: bool | None = Field(
        default=None,
        description="是否为机器人",
    )
    union_openid: str | None = Field(
        default=None,
        description="跨应用统一用户 OpenID（可能为空）",
    )
    union_user_account: str | None = Field(
        default=None,
        description="跨应用统一用户账号（可能为空）",
    )
    user_openid: str | None = Field(
        default=None,
        description="用户 OpenID（单聊场景使用）",
    )
    member_openid: str | None = Field(
        default=None,
        description="群成员 OpenID（群聊场景使用）",
    )
    member_role: Literal["member", "admin", "owner"] | None = Field(
        default=None,
        description="群内角色：member=普通成员，admin=管理员，owner=群主",
    )


class EventMessageScene(QQBotBaseModel):
    """消息场景上下文."""

    source: str | None = Field(
        default=None,
        description="场景来源。default=默认聊天窗口",
    )
    ext: list[str] | None = Field(
        default=None,
        description="扩展数据列表，key=value 格式：msg_idx=消息索引，ref_msg_idx=引用的消息索引，auth_token=鉴权令牌",
    )


class EventMessageAttachment(QQBotBaseModel):
    """消息附件."""

    url: str | None = Field(
        default=None,
        description="附件下载 URL",
    )
    filename: str | None = Field(
        default=None,
        description="文件名",
    )
    width: int | None = Field(
        default=None,
        description="图片宽度（像素），非图片附件无此字段",
    )
    height: int | None = Field(
        default=None,
        description="图片高度（像素），非图片附件无此字段",
    )
    size: int | None = Field(
        default=None,
        description="文件大小（字节）",
    )
    content_type: str | None = Field(
        default=None,
        description="附件内容类型（MIME 类型）：voice=语音消息，image/jpeg，image/png，image/gif，video/mp4，file=群文件",
    )
    voice_wav_url: str | None = Field(
        default=None,
        description="语音消息 SILK 等转换后的 WAV 文件 URL",
    )
    asr_refer_text: str | None = Field(
        default=None,
        description="语音消息 ASR 参考结果",
    )


class EventArkData(QQBotBaseModel):
    """结构化卡片消息数据."""

    prompt: str | None = Field(
        default=None,
        description="卡片消息中的用户操作提示文本",
    )
    ark_type: str | None = Field(
        default=None,
        description="卡片消息类型标识：tuwen=图文 H5，feed=图文卡片，miniapp=小程序，map=位置卡片，contact_card=好友名片，video_share=视频分享，music_together=一起听歌，picture=图片",
    )
    ark_name: str | None = Field(
        default=None,
        description="卡片消息类型的中文名称，如 图文 H5 / 小程序 / 图文卡片",
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description="卡片消息字段，常见键名：tag/tags，title，desc，jump_url，preview，source，source_logo，tag_icon，nickname，avatar，address",
    )


class EventMsgElement(QQBotBaseModel):
    """消息元素, 用于引用消息与嵌套消息的展示."""

    msg_idx: str | None = Field(
        default=None,
        description="消息元素在列表中的引用消息索引",
    )
    author: EventUser | None = Field(
        default=None,
        description="该元素对应的消息发送者",
    )
    message_type: int | None = Field(
        default=None,
        description="消息内容类型：0=普通文本，3=结构化卡片，101=并行消息，102=聊天记录，103=引用消息",
    )
    content: str | None = Field(
        default=None,
        description="消息正文内容",
    )
    attachments: list[EventMessageAttachment] | None = Field(
        default=None,
        description="该元素携带的附件",
    )
    ark_data: EventArkData | None = Field(
        default=None,
        description="结构化卡片消息数据，message_type=3 时有值",
    )
    msg_elements: list["EventMsgElement"] | None = Field(
        default=None,
        description="嵌套消息元素列表（递归结构）",
    )


class GroupMessageEventBase(QQBotBaseModel):
    """群聊消息事件体公共部分.

    ``GROUP_AT_MESSAGE_CREATE`` 与 ``GROUP_MESSAGE_CREATE`` 的事件体结构完全一致,
    差别只在触发条件(是否@机器人 / 是否开启接收全部消息).
    """

    id: str | None = Field(
        default=None,
        description="消息 ID，可用于被动回复和撤回",
    )
    author: EventUser | None = Field(
        default=None,
        description="发送者，群聊场景下 member_openid 有值",
    )
    content: str | None = Field(
        default=None,
        description="消息文本内容；@成员展示为 <@member_openid>，@全体成员展示为 <@all>",
    )
    group_openid: str | None = Field(
        default=None,
        description="群 OpenID",
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
        description="消息场景上下文",
    )
    attachments: list[EventMessageAttachment] | None = Field(
        default=None,
        description="消息附件",
    )
    mentions: list[EventUser] | None = Field(
        default=None,
        description="消息中@的用户列表，不含@机器人自身",
    )
    ark_data: EventArkData | None = Field(
        default=None,
        description="结构化卡片消息数据，message_type=3 时有值",
    )
    msg_elements: list[EventMsgElement] | None = Field(
        default=None,
        description="消息元素列表，message_type=103 引用消息时包含被引用内容",
    )

    @property
    def sender_openid(self) -> str | None:
        """发送者的 openid, 不用自己判断该取哪个字段.

        群聊场景取 ``author.member_openid``, 没有则回退 ``author.user_openid``,
        最后才回退 ``author.id``; 取不到时返回 None.
        """
        author = self.author
        if author is None:
            return None
        return author.member_openid or author.user_openid or author.id


class GroupAtMessageCreateEvent(GroupMessageEventBase):
    """用户在群里@机器人发送消息 (GROUP_AT_MESSAGE_CREATE)."""


class GroupMessageCreateEvent(GroupMessageEventBase):
    """群内全量消息 (GROUP_MESSAGE_CREATE), 需要开启接收所有消息."""


class GroupRobotOperationEvent(QQBotBaseModel):
    """机器人进出群 / 群消息接收开关事件的公共部分.

    ``GROUP_ADD_ROBOT`` / ``GROUP_DEL_ROBOT`` / ``GROUP_MSG_RECEIVE`` /
    ``GROUP_MSG_REJECT`` 四个事件体字段完全相同.
    """

    timestamp: int | None = Field(
        default=None,
        description="事件时间戳（Unix 秒）",
    )
    group_openid: str | None = Field(
        default=None,
        description="群 OpenID",
    )
    op_member_openid: str | None = Field(
        default=None,
        description="执行操作的群成员 OpenID",
    )


class GroupAddRobotEvent(GroupRobotOperationEvent):
    """机器人被添加到群聊 (GROUP_ADD_ROBOT)."""


class GroupDelRobotEvent(GroupRobotOperationEvent):
    """机器人被移出群聊 (GROUP_DEL_ROBOT)."""


class GroupMsgReceiveEvent(GroupRobotOperationEvent):
    """群管理员在机器人资料页开启消息通知 (GROUP_MSG_RECEIVE)."""


class GroupMsgRejectEvent(GroupRobotOperationEvent):
    """群管理员在机器人资料页关闭消息通知 (GROUP_MSG_REJECT)."""


class GroupMemberChangeEvent(QQBotBaseModel):
    """群成员进出事件的公共部分."""

    timestamp: int | None = Field(
        default=None,
        description="事件时间戳（Unix 秒）",
    )
    group_openid: str | None = Field(
        default=None,
        description="群 OpenID",
    )
    member_openid: str | None = Field(
        default=None,
        description="成员的 OpenID",
    )


class GroupMemberAddEvent(GroupMemberChangeEvent):
    """有新成员加入群聊 (GROUP_MEMBER_ADD)."""


class GroupMemberRemoveEvent(GroupMemberChangeEvent):
    """群成员退出或被移出群聊 (GROUP_MEMBER_REMOVE)."""

    user_openid: str | None = Field(
        default=None,
        description="退出成员的用户 OpenID（可能为空）",
    )


class GroupAutoApproved(QQBotBaseModel):
    """入群申请自动审批通过的扩展信息, 只在下行事件中携带."""

    strategy_id: str | None = Field(
        default=None,
        description="自动审批通过的策略 ID",
    )


class GroupJoinRequestEvent(JoinRequest):
    """用户申请加群 (GROUP_JOIN_REQUEST), 机器人是群管理员时才会收到.

    复用 ``qqbotsdk.model.group.join_request.JoinRequest`` 的全部字段,
    仅在事件上追加 ``group_openid`` 与 ``auto_approved``.
    """

    group_openid: str | None = Field(
        default=None,
        description="群 OpenID",
    )
    auto_approved: GroupAutoApproved | None = Field(
        default=None,
        description="自动审批通过的扩展信息，只有在下行事件中会携带",
    )


__all__ = [
    "EventArkData",
    "EventMessageAttachment",
    "EventMessageScene",
    "EventMsgElement",
    "EventUser",
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
]
