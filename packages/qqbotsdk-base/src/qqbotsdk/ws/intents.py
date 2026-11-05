"""网关事件订阅位(Intents).

Intents 是一个位掩码, 在 Identify 时上报给网关, 声明机器人希望订阅哪些事件;
未订阅的事件不会下发. 用按位或组合多个位::

    from qqbotsdk.ws import Intents

    intents = Intents.GROUP_AND_C2C_EVENT | Intents.PUBLIC_GUILD_MESSAGES

``GROUP_MEMBER_EVENT`` (1<<24) 没有出现在官方「事件订阅与通知」的总表里, 但
``GROUP_MEMBER_ADD`` 与 ``GROUP_JOIN_REQUEST`` 两篇事件文档标注的 intent 都是它;
官方 Python SDK (botpy) 至今也没有这一位. 需要群成员进出 / 入群申请事件时显式
订阅它.
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
    GROUP_MEMBER_EVENT = 1 << 24
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
