"""协议模型：Opcode、payload 及各事件 d 字段的 TypedDict、Intent 位掩码。

Payload 里 `NOT_SET` 哨兵标记"外发时应省略"的字段，由
WebsocketConnecter.reply_helper 统一过滤。
"""

from enum import IntEnum, IntFlag
from typing import Any, Literal, TypedDict


class MissingType:
    def __repr__(self) -> Literal["<NotSet>"]:
        return "<NotSet>"

    def __bool__(self) -> Literal[False]:
        return False


NOT_SET = MissingType()
type NoneType = None | MissingType

type DispatchData = Any


class Opcode(IntEnum):
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    RESUME = 6
    RECONNECT = 7
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11
    VALIDATION = 13


class Payload(TypedDict, total=False):
    id: str | NoneType
    # 线上 payload 反序列化出来是 int，这里按实际类型声明
    op: int | NoneType
    d: "HelloData | IdentifyData | ResumeData | ValidationData | DispatchData | int | NoneType"
    s: int | NoneType
    t: str | NoneType


class HelloData(TypedDict):
    heartbeat_interval: int  # ms


class IdentifyData(TypedDict):
    token: str
    intents: int
    shard: tuple[int, int]
    properties: dict[str, str]


class ResumeData(TypedDict):
    token: str
    session_id: str
    seq: int


class ReadyData(TypedDict, total=False):
    version: int
    session_id: str
    user: dict[str, Any]
    shard: tuple[int, int]
    intents: int


class ValidationData(TypedDict):
    plain_token: str
    event_ts: str


class Intent(IntFlag):
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


def payload_of(op: Opcode, d: Any = NOT_SET) -> Payload:
    return {"id": NOT_SET, "op": op, "d": d, "s": NOT_SET, "t": NOT_SET}
