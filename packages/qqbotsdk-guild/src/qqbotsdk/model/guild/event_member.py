"""频道成员类事件模型.

覆盖以下事件的事件体 ``d``:

- ``GUILD_MEMBER_ADD`` / ``GUILD_MEMBER_UPDATE`` / ``GUILD_MEMBER_REMOVE``: 事件体为
  文档的 MemberWithGuildID 对象再加一个 ``op_user_id``, 复用
  ``qqbotsdk.model.guild.member.Member``;
- ``AUDIO_OR_LIVE_CHANNEL_MEMBER_ENTER`` / ``_EXIT``: 音视频/直播子频道成员进出.

参考:

- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/role/guild_member.html
- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/role/member/model.html
- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/role/audio_or_live_channel_member.html
"""

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.guild.member import Member


class GuildMemberEvent(Member):
    """频道成员事件体, 在 Member 基础上补充 guild_id 与操作人."""

    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    op_user_id: str | None = Field(
        default=None,
        description="操作人 ID",
    )


class GuildMemberAddEvent(GuildMemberEvent):
    """GUILD_MEMBER_ADD: 新用户加入频道时触发, intents=GUILD_MEMBERS."""


class GuildMemberUpdateEvent(GuildMemberEvent):
    """GUILD_MEMBER_UPDATE: 成员的频道属性(昵称/身份组等)变化时触发, intents=GUILD_MEMBERS."""


class GuildMemberRemoveEvent(GuildMemberEvent):
    """GUILD_MEMBER_REMOVE: 用户离开频道时触发, intents=GUILD_MEMBERS."""


class AudioOrLiveChannelMemberEvent(QQBotBaseModel):
    """音视频/直播子频道成员进出事件体."""

    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    channel_type: int | None = Field(
        default=None,
        description="子频道类型: 文档标注 2=音视频子频道, 5=直播子频道; 直播子频道实际也可能是 10005, 故用 int 承载",
    )
    user_id: str | None = Field(
        default=None,
        description="进出子频道的用户 ID",
    )


class AudioOrLiveChannelMemberEnterEvent(AudioOrLiveChannelMemberEvent):
    """AUDIO_OR_LIVE_CHANNEL_MEMBER_ENTER: 用户进入音视频/直播子频道时触发."""


class AudioOrLiveChannelMemberExitEvent(AudioOrLiveChannelMemberEvent):
    """AUDIO_OR_LIVE_CHANNEL_MEMBER_EXIT: 用户离开音视频/直播子频道时触发."""


__all__ = [
    "AudioOrLiveChannelMemberEnterEvent",
    "AudioOrLiveChannelMemberEvent",
    "AudioOrLiveChannelMemberExitEvent",
    "GuildMemberAddEvent",
    "GuildMemberEvent",
    "GuildMemberRemoveEvent",
    "GuildMemberUpdateEvent",
]
