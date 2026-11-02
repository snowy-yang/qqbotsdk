"""频道域事件模型注册表, 以及频道/子频道生命周期事件.

网关帧形如 ``{"id": ..., "op": 0, "s": 1, "t": "GUILD_CREATE", "d": {...}}``.
本模块只描述事件体 ``d``, 信封由 ``qqbotsdk.ws.payload.GatewayPayload`` 承载.
用 ``parse_event`` 可以按事件名一次性拿到解析好的事件对象::

    payload = GatewayPayload.model_validate(raw_frame)
    event = parse_event(payload)
    if isinstance(event, AtMessageCreateEvent):
        print(event.content, event.channel_id)

本模块自己定义 ``GUILD_*`` / ``CHANNEL_*`` 六个事件, 其余事件按主题拆到
``event_message`` / ``event_member`` / ``event_forum`` / ``event_audio``.
"""

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.guild.channel import Channel
from qqbotsdk.model.guild.event_audio import (
    AudioAction,
    AudioFinishEvent,
    AudioOffMicEvent,
    AudioOnMicEvent,
    AudioStartEvent,
)
from qqbotsdk.model.guild.event_forum import (
    EventAuditResult,
    EventOpenForum,
    EventPost,
    EventPostInfo,
    EventReply,
    EventReplyInfo,
    EventThread,
    EventThreadInfo,
    ForumAtGuildInfo,
    ForumAtInfo,
    ForumAtRoleInfo,
    ForumAtUserInfo,
    ForumChannelInfo,
    ForumElem,
    ForumEmojiInfo,
    ForumID,
    ForumImageElem,
    ForumParagraph,
    ForumParagraphProps,
    ForumPlatImage,
    ForumPlatVideo,
    ForumPostCreateEvent,
    ForumPostDeleteEvent,
    ForumPublishAuditResultEvent,
    ForumReplyCreateEvent,
    ForumReplyDeleteEvent,
    ForumRichObject,
    ForumRichText,
    ForumTextElem,
    ForumTextInfo,
    ForumTextProps,
    ForumThreadCreateEvent,
    ForumThreadDeleteEvent,
    ForumThreadUpdateEvent,
    ForumURLElem,
    ForumURLInfo,
    ForumVideoElem,
    OpenForumPostCreateEvent,
    OpenForumPostDeleteEvent,
    OpenForumReplyCreateEvent,
    OpenForumReplyDeleteEvent,
    OpenForumThreadCreateEvent,
    OpenForumThreadDeleteEvent,
    OpenForumThreadUpdateEvent,
)
from qqbotsdk.model.guild.event_member import (
    AudioOrLiveChannelMemberEnterEvent,
    AudioOrLiveChannelMemberEvent,
    AudioOrLiveChannelMemberExitEvent,
    GuildMemberAddEvent,
    GuildMemberEvent,
    GuildMemberRemoveEvent,
    GuildMemberUpdateEvent,
)
from qqbotsdk.model.guild.event_message import (
    AtMessageCreateEvent,
    DirectMessageCreateEvent,
    DirectMessageDeleteEvent,
    EventMessage,
    MessageAudited,
    MessageAuditPassEvent,
    MessageAuditRejectEvent,
    MessageCreateEvent,
    MessageDelete,
    MessageDeleteEvent,
    MessageReaction,
    MessageReactionAddEvent,
    MessageReactionRemoveEvent,
    PublicMessageDeleteEvent,
    ReactionEmoji,
    ReactionTarget,
)
from qqbotsdk.model.guild.guild import Guild
from qqbotsdk.ws.payload import GatewayPayload


class GuildEvent(Guild):
    """频道事件体, 在 Guild 基础上补充操作人."""

    op_user_id: str | None = Field(
        default=None,
        description="操作人 ID",
    )


class GuildCreateEvent(GuildEvent):
    """GUILD_CREATE: 机器人被加入某个频道时触发, intents=GUILDS."""


class GuildUpdateEvent(GuildEvent):
    """GUILD_UPDATE: 频道资料变更时触发, 事件体为变更后的数据, intents=GUILDS."""


class GuildDeleteEvent(GuildEvent):
    """GUILD_DELETE: 频道被解散或机器人被移出时触发, 事件体为变更前的数据, intents=GUILDS."""


class ChannelEvent(Channel):
    """子频道事件体, 在 Channel 基础上补充操作人."""

    op_user_id: str | None = Field(
        default=None,
        description="操作人 ID",
    )


class ChannelCreateEvent(ChannelEvent):
    """CHANNEL_CREATE: 子频道被创建时触发, intents=GUILDS."""


class ChannelUpdateEvent(ChannelEvent):
    """CHANNEL_UPDATE: 子频道信息变更时触发, intents=GUILDS."""


class ChannelDeleteEvent(ChannelEvent):
    """CHANNEL_DELETE: 子频道被删除时触发, intents=GUILDS."""


EVENT_MODELS: dict[str, type[QQBotBaseModel]] = {
    "AT_MESSAGE_CREATE": AtMessageCreateEvent,
    "AUDIO_FINISH": AudioFinishEvent,
    "AUDIO_OFF_MIC": AudioOffMicEvent,
    "AUDIO_ON_MIC": AudioOnMicEvent,
    "AUDIO_OR_LIVE_CHANNEL_MEMBER_ENTER": AudioOrLiveChannelMemberEnterEvent,
    "AUDIO_OR_LIVE_CHANNEL_MEMBER_EXIT": AudioOrLiveChannelMemberExitEvent,
    "AUDIO_START": AudioStartEvent,
    "CHANNEL_CREATE": ChannelCreateEvent,
    "CHANNEL_DELETE": ChannelDeleteEvent,
    "CHANNEL_UPDATE": ChannelUpdateEvent,
    "DIRECT_MESSAGE_CREATE": DirectMessageCreateEvent,
    "DIRECT_MESSAGE_DELETE": DirectMessageDeleteEvent,
    "FORUM_POST_CREATE": ForumPostCreateEvent,
    "FORUM_POST_DELETE": ForumPostDeleteEvent,
    "FORUM_PUBLISH_AUDIT_RESULT": ForumPublishAuditResultEvent,
    "FORUM_REPLY_CREATE": ForumReplyCreateEvent,
    "FORUM_REPLY_DELETE": ForumReplyDeleteEvent,
    "FORUM_THREAD_CREATE": ForumThreadCreateEvent,
    "FORUM_THREAD_DELETE": ForumThreadDeleteEvent,
    "FORUM_THREAD_UPDATE": ForumThreadUpdateEvent,
    "GUILD_CREATE": GuildCreateEvent,
    "GUILD_DELETE": GuildDeleteEvent,
    "GUILD_MEMBER_ADD": GuildMemberAddEvent,
    "GUILD_MEMBER_REMOVE": GuildMemberRemoveEvent,
    "GUILD_MEMBER_UPDATE": GuildMemberUpdateEvent,
    "GUILD_UPDATE": GuildUpdateEvent,
    "MESSAGE_AUDIT_PASS": MessageAuditPassEvent,
    "MESSAGE_AUDIT_REJECT": MessageAuditRejectEvent,
    "MESSAGE_CREATE": MessageCreateEvent,
    "MESSAGE_DELETE": MessageDeleteEvent,
    "MESSAGE_REACTION_ADD": MessageReactionAddEvent,
    "MESSAGE_REACTION_REMOVE": MessageReactionRemoveEvent,
    "OPEN_FORUM_POST_CREATE": OpenForumPostCreateEvent,
    "OPEN_FORUM_POST_DELETE": OpenForumPostDeleteEvent,
    "OPEN_FORUM_REPLY_CREATE": OpenForumReplyCreateEvent,
    "OPEN_FORUM_REPLY_DELETE": OpenForumReplyDeleteEvent,
    "OPEN_FORUM_THREAD_CREATE": OpenForumThreadCreateEvent,
    "OPEN_FORUM_THREAD_DELETE": OpenForumThreadDeleteEvent,
    "OPEN_FORUM_THREAD_UPDATE": OpenForumThreadUpdateEvent,
    "PUBLIC_MESSAGE_DELETE": PublicMessageDeleteEvent,
}


def parse_event(payload: GatewayPayload) -> QQBotBaseModel | None:
    """按 payload.t 解析事件体; 未建模的事件返回 None."""
    model = EVENT_MODELS.get(payload.t or "")
    if model is None:
        return None
    return model.model_validate(payload.d)


__all__ = [
    "EVENT_MODELS",
    "AtMessageCreateEvent",
    "AudioAction",
    "AudioFinishEvent",
    "AudioOffMicEvent",
    "AudioOnMicEvent",
    "AudioOrLiveChannelMemberEnterEvent",
    "AudioOrLiveChannelMemberEvent",
    "AudioOrLiveChannelMemberExitEvent",
    "AudioStartEvent",
    "ChannelCreateEvent",
    "ChannelDeleteEvent",
    "ChannelEvent",
    "ChannelUpdateEvent",
    "DirectMessageCreateEvent",
    "DirectMessageDeleteEvent",
    "EventAuditResult",
    "EventMessage",
    "EventOpenForum",
    "EventPost",
    "EventPostInfo",
    "EventReply",
    "EventReplyInfo",
    "EventThread",
    "EventThreadInfo",
    "ForumAtGuildInfo",
    "ForumAtInfo",
    "ForumAtRoleInfo",
    "ForumAtUserInfo",
    "ForumChannelInfo",
    "ForumElem",
    "ForumEmojiInfo",
    "ForumID",
    "ForumImageElem",
    "ForumParagraph",
    "ForumParagraphProps",
    "ForumPlatImage",
    "ForumPlatVideo",
    "ForumPostCreateEvent",
    "ForumPostDeleteEvent",
    "ForumPublishAuditResultEvent",
    "ForumReplyCreateEvent",
    "ForumReplyDeleteEvent",
    "ForumRichObject",
    "ForumRichText",
    "ForumTextElem",
    "ForumTextInfo",
    "ForumTextProps",
    "ForumThreadCreateEvent",
    "ForumThreadDeleteEvent",
    "ForumThreadUpdateEvent",
    "ForumURLElem",
    "ForumURLInfo",
    "ForumVideoElem",
    "GuildCreateEvent",
    "GuildDeleteEvent",
    "GuildEvent",
    "GuildMemberAddEvent",
    "GuildMemberEvent",
    "GuildMemberRemoveEvent",
    "GuildMemberUpdateEvent",
    "GuildUpdateEvent",
    "MessageAuditPassEvent",
    "MessageAuditRejectEvent",
    "MessageAudited",
    "MessageCreateEvent",
    "MessageDelete",
    "MessageDeleteEvent",
    "MessageReaction",
    "MessageReactionAddEvent",
    "MessageReactionRemoveEvent",
    "OpenForumPostCreateEvent",
    "OpenForumPostDeleteEvent",
    "OpenForumReplyCreateEvent",
    "OpenForumReplyDeleteEvent",
    "OpenForumThreadCreateEvent",
    "OpenForumThreadDeleteEvent",
    "OpenForumThreadUpdateEvent",
    "PublicMessageDeleteEvent",
    "ReactionEmoji",
    "ReactionTarget",
    "parse_event",
]
