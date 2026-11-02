"""频道消息类事件模型.

覆盖以下事件的事件体 ``d``:

- ``AT_MESSAGE_CREATE`` / ``MESSAGE_CREATE`` / ``DIRECT_MESSAGE_CREATE``: 事件体即
  文档的 Message 对象, 复用 ``SendChannelMessagesResponse`` 并补齐 ``mentions`` /
  ``member`` / ``seq`` 三个事件专有字段;
- ``MESSAGE_DELETE`` / ``PUBLIC_MESSAGE_DELETE`` / ``DIRECT_MESSAGE_DELETE``: 事件体
  为文档的 MessageDelete 对象;
- ``MESSAGE_REACTION_ADD`` / ``MESSAGE_REACTION_REMOVE``: 事件体为 MessageReaction 对象;
- ``MESSAGE_AUDIT_PASS`` / ``MESSAGE_AUDIT_REJECT``: 事件体为 MessageAudited 对象.

参考:

- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/message/event.html
- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/template/model.html
- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/trans/emoji.html
- https://bot.q.qq.com/wiki/develop/api-v2/openapi/reaction/model.html
"""

from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.guild.member import Member, User
from qqbotsdk.model.guild.messages import MessageAuthor, SendChannelMessagesResponse


class EventMessage(SendChannelMessagesResponse):
    """频道消息事件体, 对应文档的 Message 对象.

    复用 ``SendChannelMessagesResponse``(它和 Message 的字段集一致), 只补上文档
    Message 里存在、而发送接口回包里没有的三个字段.
    """

    mentions: list[MessageAuthor] | None = Field(
        default=None,
        description="消息中@的人",
    )
    member: Member | None = Field(
        default=None,
        description="消息创建者的 member 信息",
    )
    seq: int | None = Field(
        default=None,
        description="消息序号, 同一子频道内按从先到后递增; 2022-08-01 后废弃, 请改用 seq_in_channel",
    )


class AtMessageCreateEvent(EventMessage):
    """AT_MESSAGE_CREATE: 用户@机器人或回复机器人消息时触发, intents=PUBLIC_GUILD_MESSAGES."""


class MessageCreateEvent(EventMessage):
    """MESSAGE_CREATE: 文字子频道内的全部消息, 仅私域, intents=GUILD_MESSAGES."""


class DirectMessageCreateEvent(EventMessage):
    """DIRECT_MESSAGE_CREATE: 用户给机器人发私信时触发, intents=DIRECT_MESSAGE."""


class MessageDelete(QQBotBaseModel):
    """撤回(删除)消息事件体, 对应文档的 MessageDelete 对象."""

    message: EventMessage | None = Field(
        default=None,
        description="被删除的消息内容",
    )
    op_user: User | None = Field(
        default=None,
        description="执行删除操作的用户",
    )


class MessageDeleteEvent(MessageDelete):
    """MESSAGE_DELETE: 私域频道内消息被撤回时触发, intents=GUILD_MESSAGES."""


class PublicMessageDeleteEvent(MessageDelete):
    """PUBLIC_MESSAGE_DELETE: 公域频道内消息被删除时触发, intents=PUBLIC_GUILD_MESSAGES."""


class DirectMessageDeleteEvent(MessageDelete):
    """DIRECT_MESSAGE_DELETE: 私信消息被撤回时触发, intents=DIRECT_MESSAGE."""


class ReactionEmoji(QQBotBaseModel):
    """表情表态所用的表情, 对应文档的 Emoji 对象."""

    id: str | None = Field(
        default=None,
        description="表情 ID; 系统表情用数字 ID, emoji 用 emoji 本身作为 id",
    )
    type: Literal[1, 2] | None = Field(
        default=None,
        description="表情类型: 1=系统表情, 2=emoji 表情",
    )


class ReactionTarget(QQBotBaseModel):
    """表态对象, 对应文档的 ReactionTarget 对象."""

    id: str | None = Field(
        default=None,
        description="表态对象 ID",
    )
    type: Literal[0, 1, 2, 3] | None = Field(
        default=None,
        description="表态对象类型: 0=消息, 1=帖子, 2=评论, 3=回复",
    )


class MessageReaction(QQBotBaseModel):
    """表情表态事件体, 对应文档的 MessageReaction 对象."""

    user_id: str | None = Field(
        default=None,
        description="用户 ID",
    )
    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    target: ReactionTarget | None = Field(
        default=None,
        description="表态对象",
    )
    emoji: ReactionEmoji | None = Field(
        default=None,
        description="表态所用表情",
    )


class MessageReactionAddEvent(MessageReaction):
    """MESSAGE_REACTION_ADD: 用户为消息添加表情表态时触发, intents=GUILD_MESSAGE_REACTIONS."""


class MessageReactionRemoveEvent(MessageReaction):
    """MESSAGE_REACTION_REMOVE: 用户取消消息表情表态时触发, intents=GUILD_MESSAGE_REACTIONS."""


class MessageAudited(QQBotBaseModel):
    """消息审核事件体, 对应文档的 MessageAudited 对象."""

    audit_id: str | None = Field(
        default=None,
        description="消息审核 ID",
    )
    message_id: str | None = Field(
        default=None,
        description="消息 ID, 只有审核通过事件才会有值",
    )
    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    audit_time: str | None = Field(
        default=None,
        description="消息审核时间, ISO8601 格式",
    )
    create_time: str | None = Field(
        default=None,
        description="消息创建时间, ISO8601 格式",
    )
    seq_in_channel: str | None = Field(
        default=None,
        description="子频道消息 seq, 用于同一子频道内排序",
    )


class MessageAuditPassEvent(MessageAudited):
    """MESSAGE_AUDIT_PASS: 消息审核通过时触发, intents=MESSAGE_AUDIT."""


class MessageAuditRejectEvent(MessageAudited):
    """MESSAGE_AUDIT_REJECT: 消息审核不通过时触发, intents=MESSAGE_AUDIT."""


__all__ = [
    "AtMessageCreateEvent",
    "DirectMessageCreateEvent",
    "DirectMessageDeleteEvent",
    "EventMessage",
    "MessageAuditPassEvent",
    "MessageAuditRejectEvent",
    "MessageAudited",
    "MessageCreateEvent",
    "MessageDelete",
    "MessageDeleteEvent",
    "MessageReaction",
    "MessageReactionAddEvent",
    "MessageReactionRemoveEvent",
    "PublicMessageDeleteEvent",
    "ReactionEmoji",
    "ReactionTarget",
]
