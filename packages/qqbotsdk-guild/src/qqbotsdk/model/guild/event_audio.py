"""音频事件模型.

AUDIO_START / AUDIO_FINISH / AUDIO_ON_MIC / AUDIO_OFF_MIC 四个事件的事件体结构
完全一致, 都是文档中的 AudioAction 对象, 因此共用一个基类 ``AudioAction``,
四个事件类只在语义上区分.

参考: https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/content/audio/model.html
"""

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class AudioAction(QQBotBaseModel):
    """音视频子频道音频事件体, 对应文档的 AudioAction 对象."""

    guild_id: str | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: str | None = Field(
        default=None,
        description="子频道 ID",
    )
    audio_url: str | None = Field(
        default=None,
        description="音频数据的 URL, 仅在开始播放时下发",
    )
    text: str | None = Field(
        default=None,
        description="状态文本, 比如 简单爱-周杰伦",
    )


class AudioStartEvent(AudioAction):
    """AUDIO_START: 音频开始播放时触发."""


class AudioFinishEvent(AudioAction):
    """AUDIO_FINISH: 音频播放结束时触发."""


class AudioOnMicEvent(AudioAction):
    """AUDIO_ON_MIC: 机器人上麦时触发."""


class AudioOffMicEvent(AudioAction):
    """AUDIO_OFF_MIC: 机器人下麦时触发."""


__all__ = [
    "AudioAction",
    "AudioFinishEvent",
    "AudioOffMicEvent",
    "AudioOnMicEvent",
    "AudioStartEvent",
]
