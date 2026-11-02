"""网关数据包模型与操作码.

网关上下行的每一帧都是一个 JSON 对象, 结构统一为::

    {"op": 0, "s": 1, "t": "READY", "id": "xxx", "d": {...}}

其中 ``op`` 是操作码, ``s`` 是事件序号, ``t`` 与 ``id`` 只有 Dispatch 事件才有,
``d`` 是事件数据, 其结构由 ``op`` 与 ``t`` 共同决定.
"""

from enum import IntEnum
from typing import Any

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class OpCode(IntEnum):
    """网关操作码."""

    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    RESUME = 6
    RECONNECT = 7
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11


class GatewayPayload(QQBotBaseModel):
    """网关数据包."""

    op: int = Field(
        ...,
        description="操作码, 取值见 OpCode",
    )
    s: int | None = Field(
        default=None,
        description="事件序号, 心跳与 Resume 需携带最近一次收到的值",
    )
    t: str | None = Field(
        default=None,
        description="事件类型, 仅 Dispatch 事件(op=0)有值",
    )
    id: str | None = Field(
        default=None,
        description="事件 ID",
    )
    d: Any = Field(
        default=None,
        description="事件数据, 结构由操作码与事件类型决定",
    )


class ReadyUser(QQBotBaseModel):
    """READY 事件中的机器人自身信息."""

    id: str = Field(
        ...,
        description="机器人 ID",
    )
    username: str | None = Field(
        default=None,
        description="机器人名称",
    )
    bot: bool | None = Field(
        default=None,
        description="是否为机器人, 恒为 true",
    )


class ReadyContent(QQBotBaseModel):
    """READY 事件的数据体, 网关鉴权成功后的第一个 Dispatch."""

    version: int | None = Field(
        default=None,
        description="网关协议版本",
    )
    session_id: str | None = Field(
        default=None,
        description="当前连接会话 ID, 断线重连时用于 Resume",
    )
    user: ReadyUser | None = Field(
        default=None,
        description="机器人自身信息",
    )
    shard: list[int] | None = Field(
        default=None,
        description="当前连接的分片信息, 形如 [分片序号, 分片总数]",
    )


__all__ = [
    "GatewayPayload",
    "OpCode",
    "ReadyContent",
    "ReadyUser",
]
