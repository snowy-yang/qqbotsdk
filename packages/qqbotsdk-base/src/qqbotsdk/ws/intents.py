"""网关事件订阅位(Intents).

Intents 是一个位掩码, 在 Identify 时上报给网关, 声明机器人希望订阅哪些事件;
未订阅的事件不会下发. 用按位或组合多个位::

    from qqbotsdk.ws import Intents

    intents = Intents.GROUP_AND_C2C_EVENT | Intents.PUBLIC_GUILD_MESSAGES
"""

from enum import IntFlag
from typing import Final


class Intents(IntFlag):
    """事件订阅位, 每一位对应一类事件."""

    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    DIRECT_MESSAGE = 1 << 12
    GROUP_AND_C2C_EVENT = 1 << 25
    INTERACTION = 1 << 26
    MESSAGE_AUDIT = 1 << 27
    FORUMS_EVENT = 1 << 28
    AUDIO_ACTION = 1 << 29
    PUBLIC_GUILD_MESSAGES = 1 << 30


# 默认订阅: 群与单聊消息, 公域频道消息, 频道成员变更, 交互事件
DEFAULT_INTENTS: Final = (
    Intents.GROUP_AND_C2C_EVENT
    | Intents.PUBLIC_GUILD_MESSAGES
    | Intents.GUILD_MEMBERS
    | Intents.INTERACTION
)

__all__ = [
    "DEFAULT_INTENTS",
    "Intents",
]
