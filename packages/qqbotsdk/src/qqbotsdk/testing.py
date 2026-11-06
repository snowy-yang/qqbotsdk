"""测试辅助: 不连网关也能喂事件、不连 OpenAPI 也能断言请求.

用法::

    import pytest

    from qqbotsdk.app import Bot, Context
    from qqbotsdk.testing import dispatch

    async def test_echo() -> None:
        bot = Bot()
        seen: list[str | None] = []

        @bot.on("GROUP_AT_MESSAGE_CREATE")
        async def handler(ctx: Context) -> None:
            seen.append(ctx.payload.id)

        await dispatch(bot, "GROUP_AT_MESSAGE_CREATE", {"id": "m1", "content": "hi"})
        assert seen == ["evt-1"]

HTTP 侧的可测入口在 :mod:`qqbotsdk.api.core` 的 ``use_session`` / ``set_session``,
两边合起来就是一套完整的离网测试面: 事件用 ``dispatch``, 请求用 ``use_session``.

本模块只依赖公开 API, 不碰任何私有实现.
"""

import json
from typing import Any

from qqbotsdk.app.bot import Bot
from qqbotsdk.ws.payload import GatewayPayload, OpCode

DEFAULT_EVENT_ID = "evt-1"
"""``make_payload`` 默认使用的事件 ID."""


def make_payload(
    event_name: str,
    data: Any,
    *,
    event_id: str | None = DEFAULT_EVENT_ID,
    seq: int = 1,
) -> GatewayPayload:
    """构造一帧 Dispatch 事件.

    Args:
        event_name: 事件名, 即网关帧的 ``t``.
        data: 事件体, 即网关帧的 ``d``.
        event_id: 事件 ID(信封 ``id``), 被动回复时作为 ``event_id``; 传 None 表示
            不带事件 ID, 用于验证回退到 ``msg_id`` 的分支.
        seq: 事件序号 ``s``.

    Returns:
        可以直接交给 :meth:`Bot.dispatch` 的 :class:`GatewayPayload`.
    """
    return GatewayPayload.model_validate(
        {
            "op": OpCode.DISPATCH,
            "s": seq,
            "t": event_name,
            "id": event_id,
            "d": data,
        }
    )


def parse_frame(frame: str | bytes | dict[str, Any]) -> GatewayPayload:
    """把原始帧(JSON 文本或已解析的 dict)解析成 :class:`GatewayPayload`."""
    if isinstance(frame, dict):
        return GatewayPayload.model_validate(frame)
    return GatewayPayload.model_validate(json.loads(frame))


async def dispatch(
    bot: Bot,
    event_name: str,
    data: Any,
    *,
    event_id: str | None = DEFAULT_EVENT_ID,
    seq: int = 1,
) -> None:
    """构造一帧事件并**等待**处理完成.

    handler / 中间件抛出的异常会按正常路径交给 ``on_error``, 不会从这里冒出来;
    要断言异常请注册 ``on_error`` 并收集参数.

    Args:
        bot: 目标机器人.
        event_name: 事件名.
        data: 事件体.
        event_id: 事件 ID, 传 None 表示不带.
        seq: 事件序号.
    """
    payload = make_payload(event_name, data, event_id=event_id, seq=seq)
    task = bot.dispatch(payload)
    if task is not None:
        await task


async def dispatch_frame(bot: Bot, frame: str | bytes | dict[str, Any]) -> None:
    """把一段原始网关帧喂给 bot 并等待处理完成.

    与 :func:`dispatch` 的区别是接收**原始帧**, 便于直接把网关日志里的报文
    复制过来做回归测试.
    """
    task = bot.dispatch(parse_frame(frame))
    if task is not None:
        await task


__all__ = [
    "DEFAULT_EVENT_ID",
    "dispatch",
    "dispatch_frame",
    "make_payload",
    "parse_frame",
]
