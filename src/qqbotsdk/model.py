"""协议模型：Opcode、payload 及各事件 d 字段的 TypedDict、Intent 位掩码。

`Payload` 描述入站帧（字段可能缺失或为 null）；出站帧由
`heartbeat_frame` / `identify_frame` / `resume_frame` 按 op 显式构造，
每个应发字段都实际存在于 dict 中，因此不需要"省略字段"的哨兵。
"""

from enum import IntEnum, IntFlag
from typing import Any, TypedDict

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
    id: str | None
    # 线上 payload 反序列化出来是 int，这里按实际类型声明
    op: int | None
    d: "HelloData | IdentifyData | ResumeData | ValidationData | DispatchData | int | None"
    s: int | None
    t: str | None


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


class HeartbeatFrame(TypedDict):
    op: Opcode
    d: int | None


class IdentifyFrame(TypedDict):
    op: Opcode
    d: IdentifyData


class ResumeFrame(TypedDict):
    op: Opcode
    d: ResumeData


type OutgoingFrame = HeartbeatFrame | IdentifyFrame | ResumeFrame


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
    GROUP_MEMBER_EVENT = 1 << 24
    GROUP_AND_C2C_EVENT = 1 << 25
    INTERACTION = 1 << 26
    MESSAGE_AUDIT = 1 << 27
    FORUMS_EVENT = 1 << 28
    AUDIO_ACTION = 1 << 29
    PUBLIC_GUILD_MESSAGES = 1 << 30


def heartbeat_frame(seq: int | None) -> HeartbeatFrame:
    """心跳帧：d 为已收到的最大序列号，无历史时为 0。"""
    return {"op": Opcode.HEARTBEAT, "d": seq}


def identify_frame(access_token: str, intents: int) -> IdentifyFrame:
    return {
        "op": Opcode.IDENTIFY,
        "d": {
            "token": f"QQBot {access_token}",
            "intents": intents,
            "shard": (0, 1),
            "properties": {},
        },
    }


def resume_frame(access_token: str, session_id: str, seq: int) -> ResumeFrame:
    return {
        "op": Opcode.RESUME,
        "d": {
            "token": f"QQBot {access_token}",
            "session_id": session_id,
            "seq": seq,
        },
    }


def error_parts(data: Any) -> tuple[Any, Any]:
    """从错误响应体取 (code, message)；非 dict 响应整体作 message。

    QQ 的失败响应 HTTP 可能仍是 200 且 Content-Type 不规范，
    ApiError/TokenError 统一用它暴露真实原因。
    """
    if isinstance(data, dict):
        return data.get("code"), data.get("message")
    return None, data
