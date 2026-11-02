"""事件分发: handler 注册表, 洋葱中间件, 错误处理与事件解析.

这里只做"收到一个 Context 之后怎么跑"这件事, 连接与生命周期在
:mod:`qqbotsdk.app.bot`.

分发语义:

- 同一个事件名可以注册多个 handler, 按注册顺序执行; ``"*"`` 的通配 handler
  在精确匹配的 handler 之后执行;
- 中间件是洋葱模型: 先注册的在最外层(先进入, 后退出), ``await call_next()``
  继续向内, 不调用即拦截后续的 handler 与更内层的中间件;
- handler 返回 ``False`` 时不再执行该事件后面的 handler, 中间件照常收尾;
- handler 或中间件抛出的异常交给 ``on_error`` 注册的函数, 没有注册则记日志,
  异常不会冒泡到 WebSocket 收包循环.
"""

import asyncio
import importlib.util
from collections.abc import Awaitable, Callable
from typing import Final

from loguru import logger

from qqbotsdk.app.context import Context
from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.event import parse_event
from qqbotsdk.ws.payload import GatewayPayload

type Handler = Callable[[Context], Awaitable[bool | None]]
"""事件处理器: 入参是 Context, 返回 ``False`` 表示阻断后续 handler."""

type Middleware = Callable[[Context, Callable[[], Awaitable[None]]], Awaitable[None]]
"""中间件: 第二个入参是``继续向内``的回调, 不调用即拦截."""

type ErrorHandler = Callable[[Context | None, BaseException], Awaitable[None]]
"""错误处理器: 入参是出错的 Context(取不到时为 None) 与异常对象."""

WILDCARD: Final = "*"
"""通配事件名: 注册它即可收到全部 Dispatch 事件(含 READY / RESUMED)."""

# 分发任务的名字前缀, 便于排查残留任务
TASK_NAME: Final = "qqbotsdk-app-dispatch"

# 频道域(guild)事件注册表所在模块, 它是 optional extra, 只能惰性导入
_GUILD_EVENT_MODULE: Final = "qqbotsdk.model.guild.event"


def _parse_guild_event(payload: GatewayPayload) -> QQBotBaseModel | None:
    """惰性调用频道域的事件解析, 没装 ``qqbotsdk-guild-py`` 时返回 None.

    模块顶层不会 import guild 包, 所以只装 ``qqbotsdk-py`` 的环境照常可用.
    """
    try:
        if importlib.util.find_spec(_GUILD_EVENT_MODULE) is None:
            return None
        from qqbotsdk.model.guild.event import parse_event as parse_guild_event
    except (ImportError, ValueError):
        return None
    try:
        return parse_guild_event(payload)
    except Exception:
        logger.opt(exception=True).warning(f"频道事件解析失败：事件={payload.t}")
        return None


def resolve_event(payload: GatewayPayload) -> QQBotBaseModel | None:
    """按事件名解析事件体: 先查本包, 再降级到频道域包, 都失败返回 None.

    解析异常不会向上抛, 只会记日志并返回 None, 保证分发链路不被打断.
    """
    try:
        event = parse_event(payload)
    except Exception:
        logger.opt(exception=True).warning(f"事件解析失败：事件={payload.t}")
        return None
    if event is not None:
        return event
    return _parse_guild_event(payload)


class Dispatcher:
    """handler / 中间件 / 错误处理器注册表与执行器."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}
        self._middlewares: list[Middleware] = []
        self._error_handlers: list[ErrorHandler] = []
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def tasks(self) -> set[asyncio.Task[None]]:
        """尚未完成的处理任务, 供生命周期层取消与回收."""
        return self._tasks

    @property
    def handler_count(self) -> int:
        """已注册的 handler 数量, 用于日志与调试."""
        return sum(len(items) for items in self._handlers.values())

    @property
    def middleware_count(self) -> int:
        """已注册的中间件数量, 用于日志与调试."""
        return len(self._middlewares)

    def add_handler(self, event_name: str, handler: Handler) -> None:
        """注册事件处理器, 同名事件按注册顺序执行."""
        self._handlers.setdefault(event_name, []).append(handler)

    def add_middleware(self, middleware: Middleware) -> None:
        """注册中间件, 先注册的在洋葱外层."""
        self._middlewares.append(middleware)

    def add_error_handler(self, handler: ErrorHandler) -> None:
        """注册错误处理器, 按注册顺序依次调用."""
        self._error_handlers.append(handler)

    def handlers_for(self, event_name: str | None) -> list[Handler]:
        """返回该事件的处理器: 先精确匹配, 后通配."""
        wildcard = list(self._handlers.get(WILDCARD, ()))
        if event_name is None:
            return wildcard
        return [*self._handlers.get(event_name, ()), *wildcard]

    def submit(self, context: Context) -> None:
        """把一次事件处理丢进独立任务, 不阻塞 WebSocket 收包循环."""
        task = asyncio.create_task(self._run(context), name=TASK_NAME)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def cancel_tasks(self) -> None:
        """取消并回收全部未完成的处理任务, 可重复调用.

        当前任务本身不取消, 因此允许在 handler 里直接调 ``bot.stop()``.
        """
        current = asyncio.current_task()
        pending = [task for task in self._tasks if task is not current]
        self._tasks.clear()
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def _run(self, context: Context) -> None:
        """执行一个 Context 的完整处理链路, 异常统一交给错误处理器."""
        if not self.handlers_for(context.event_name):
            return
        try:
            await self._build(0, context)()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._handle_error(context, exc)

    def _build(
        self,
        index: int,
        context: Context,
    ) -> Callable[[], Awaitable[None]]:
        """构造洋葱链路: 第 ``index`` 层中间件包住更内层, 最内层是 handler 链."""
        if index >= len(self._middlewares):
            return self._terminal(context)
        middleware = self._middlewares[index]
        inner = self._build(index + 1, context)

        async def call_next() -> None:
            await inner()

        async def run() -> None:
            await middleware(context, call_next)

        return run

    def _terminal(self, context: Context) -> Callable[[], Awaitable[None]]:
        """最内层: 按顺序执行 handler, 遇到返回 False 的立即停止."""
        handlers = self.handlers_for(context.event_name)

        async def run() -> None:
            for handler in handlers:
                result = await handler(context)
                if result is False:
                    logger.debug(
                        f"handler 返回 False，阻断后续处理：事件={context.event_name}"
                    )
                    return

        return run

    async def _handle_error(self, context: Context | None, exc: BaseException) -> None:
        """把异常交给 on_error 注册的函数; 没有注册则记日志, 绝不抛出."""
        event_name = context.event_name if context is not None else None
        if not self._error_handlers:
            logger.opt(exception=exc).error(
                f"事件处理异常，未注册错误处理器：{event_name}"
            )
            return
        for handler in self._error_handlers:
            try:
                await handler(context, exc)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.opt(exception=True).error(f"错误处理器自身异常：{event_name}")


__all__ = [
    "TASK_NAME",
    "WILDCARD",
    "Dispatcher",
    "ErrorHandler",
    "Handler",
    "Middleware",
    "resolve_event",
]
