"""上层框架: 装饰器注册 + Context 注入 + 洋葱中间件.

最小示例::

    from collections.abc import Awaitable, Callable

    from loguru import logger

    from qqbotsdk.app import Bot, Context

    bot = Bot()


    @bot.on_message()
    async def echo(ctx: Context) -> None:
        content = getattr(ctx.event, "content", None)
        if isinstance(content, str):
            await ctx.reply(content)


    @bot.middleware
    async def trace(ctx: Context, call_next: Callable[[], Awaitable[None]]) -> None:
        logger.debug(f"处理事件: {ctx.event_name}")
        await call_next()


    @bot.on_error()
    async def on_error(ctx: Context | None, exc: BaseException) -> None:
        logger.opt(exception=exc).error(f"处理失败: {ctx.event_name if ctx else None}")


    bot.run()

几个约定:

- handler 返回 ``False`` 会阻断同一事件后面的 handler;
- 中间件不调用 ``call_next`` 就等于拦截;
- handler 与中间件里的异常只会进 ``on_error``, 不会打断网关连接;
- 每个 Dispatch 事件都在独立任务里处理, 不阻塞收包;
- ``ctx.api`` 是绑定好场景的高层门面(发消息 / 撤回 / 上传 / 审批 / 互动回包),
  见 :class:`qqbotsdk.app.api.SceneApi`;
- ``keyboard`` / ``row`` / ``callback`` / ``link`` / ``command`` 用来快速拼内嵌键盘;
- ``everyone`` / ``only_admin`` / ``only_users`` / ``only_roles`` 是按钮权限的语法糖
  (返回 ``Permission``), 见 :mod:`qqbotsdk.app.keyboard`.
"""

from qqbotsdk.app.api import SceneApi
from qqbotsdk.app.bot import Bot
from qqbotsdk.app.context import Context
from qqbotsdk.app.dispatch import ErrorHandler, Handler, Middleware
from qqbotsdk.app.keyboard import (
    KeyboardBuilder,
    callback,
    command,
    confirm_modal,
    everyone,
    keyboard,
    link,
    only_admin,
    only_roles,
    only_users,
    row,
)
from qqbotsdk.app.types import PreparedReply, Scene

__all__ = [
    "Bot",
    "Context",
    "ErrorHandler",
    "Handler",
    "KeyboardBuilder",
    "Middleware",
    "PreparedReply",
    "Scene",
    "SceneApi",
    "callback",
    "command",
    "confirm_modal",
    "everyone",
    "keyboard",
    "link",
    "only_admin",
    "only_roles",
    "only_users",
    "row",
]
