"""Bot: 装饰器注册 + Context 注入 + 洋葱中间件.

最小可用示例::

    from qqbotsdk.app import Bot, Context

    bot = Bot()


    @bot.on_message()
    async def echo(ctx: Context) -> None:
        content = getattr(ctx.event, "content", None)
        if isinstance(content, str):
            await ctx.reply(content)


    @bot.middleware
    async def trace(ctx: Context, call_next: Callable[[], Awaitable[None]]) -> None:
        logger.debug(f"进入中间件: 事件={ctx.event_name}")
        await call_next()


    bot.run()

``bot.run()`` 会一直阻塞到 :meth:`Bot.stop` 被调用 (通常是在 handler 里).
"""

import asyncio
import os
from collections.abc import Callable
from typing import Final

from loguru import logger

from qqbotsdk.app.context import Context
from qqbotsdk.app.dispatch import (
    WILDCARD,
    Dispatcher,
    ErrorHandler,
    Handler,
    Middleware,
    resolve_event,
)
from qqbotsdk.ws import DEFAULT_INTENTS, QQBotWebSocket
from qqbotsdk.ws.intents import Intents
from qqbotsdk.ws.payload import GatewayPayload, OpCode

MSG_SEQ_CACHE_LIMIT: Final = 512
"""msg_seq 缓存的最大锚点数, 超出后淘汰最久未使用的锚点."""

INTENTS_ENV: Final = "INTENTS"
"""环境变量名: 用十进制或 ``0x`` 十六进制掩码覆盖订阅位, 优先于代码里的默认值.

运维可以在不重新发版的情况下收窄订阅(例如临时关掉某个需要权限的事件位),
避免因 intents 无权限导致网关卡在 4013/4014.
"""

# 被动回复锚点(事件 ID 或消息 ID) -> 已用到的最大 msg_seq.
# 放模块级而不是 Bot 实例上: 平台只认「msg_id + msg_seq」是否重复, 与是哪个 Bot
# 实例发的无关. 多实例(分片 / 多机器人代管同一批会话)共用一份计数才不会各自从 1
# 重来. 键是普通字符串, 不会因此持有 Bot 或会话相关的引用.
_MSG_SEQ_CACHE: dict[str, int] = {}


def reset_msg_seq_cache() -> None:
    """清空全局 msg_seq 计数, 仅供测试与长驻进程的兜底清理使用."""
    _MSG_SEQ_CACHE.clear()


def _remember_msg_seq(key: str, seq: int) -> None:
    """写入锚点的序号(只增不减)并按上限淘汰最久未使用的条目."""
    previous = _MSG_SEQ_CACHE.pop(key, 0)
    _MSG_SEQ_CACHE[key] = seq if seq > previous else previous
    while len(_MSG_SEQ_CACHE) > MSG_SEQ_CACHE_LIMIT:
        _MSG_SEQ_CACHE.pop(next(iter(_MSG_SEQ_CACHE)))


def resolve_intents(intents: Intents | None = None) -> Intents:
    """决定本次使用的订阅位: 显式入参 > ``INTENTS`` 环境变量 > ``DEFAULT_INTENTS``.

    Args:
        intents: 代码里显式指定的订阅位, 传了就直接用, 不读环境变量.

    Returns:
        最终生效的 :class:`Intents`.

    Raises:
        ValueError: ``INTENTS`` 环境变量不是合法的十进制 / ``0x`` 十六进制掩码.
    """
    if intents is not None:
        return intents
    raw = os.getenv(INTENTS_ENV, "").strip()
    if not raw:
        return DEFAULT_INTENTS
    try:
        mask = int(raw, 0)  # 十进制或 0x 十六进制
    except ValueError:
        raise ValueError(
            f"{INTENTS_ENV} 应为十进制或 0x 十六进制掩码，实际: {raw!r}"
        ) from None
    if mask < 0:
        raise ValueError(f"{INTENTS_ENV} 不能为负数，实际: {mask}")
    return Intents(mask)


class Bot:
    """把网关连接和事件注册表绑在一起的机器人实例.

    Args:
        intents: 订阅的事件位. 省略时依次回退到 ``INTENTS`` 环境变量(十进制或
            ``0x`` 十六进制掩码)与 ``DEFAULT_INTENTS``, 见 :func:`resolve_intents`.
        url: 网关地址, 省略时由 ``QQBotWebSocket`` 在每次连接前自动获取.
        auto_reconnect: 断线后是否自动重连.
    """

    def __init__(
        self,
        *,
        intents: Intents | None = None,
        url: str | None = None,
        auto_reconnect: bool = True,
    ) -> None:
        self._intents = resolve_intents(intents)
        self._url = url
        self._auto_reconnect = auto_reconnect
        self._dispatcher = Dispatcher()
        self._ws: QQBotWebSocket | None = None
        self._stop_event = asyncio.Event()
        self._running = False

    @property
    def intents(self) -> Intents:
        """当前生效的订阅位(已解析环境变量与默认值)."""
        return self._intents

    def __repr__(self) -> str:
        return (
            f"Bot(running={self._running}, "
            f"handlers={self._dispatcher.handler_count}, "
            f"middlewares={self._dispatcher.middleware_count})"
        )

    @property
    def ws(self) -> QQBotWebSocket | None:
        """当前运行的网关客户端, 未启动或已停止时为 None."""
        return self._ws

    # ------------------------------------------------------------ 注册

    def on(self, event: str) -> Callable[[Handler], Handler]:
        """注册某个事件的处理器, 事件名可传 ``"*"`` 表示全部 Dispatch.

        同一个事件可以注册多个处理器, 按注册顺序执行; ``"*"`` 的处理器在精确
        匹配之后执行. 例::

            @bot.on("GROUP_AT_MESSAGE_CREATE")
            async def on_group(ctx: Context) -> None: ...
        """

        def decorator(handler: Handler) -> Handler:
            self._dispatcher.add_handler(event, handler)
            return handler

        return decorator

    def on_message(
        self,
        *,
        group: bool = True,
        c2c: bool = True,
    ) -> Callable[[Handler], Handler]:
        """注册消息事件处理器, 等价于同时注册群聊与单聊的消息事件.

        Args:
            group: 是否监听 ``GROUP_AT_MESSAGE_CREATE`` 与 ``GROUP_MESSAGE_CREATE``.
            c2c: 是否监听 ``C2C_MESSAGE_CREATE``.

        Raises:
            ValueError: 两个都为 False, 等于一个事件都没注册.
        """
        event_names: list[str] = []
        if group:
            event_names += ["GROUP_AT_MESSAGE_CREATE", "GROUP_MESSAGE_CREATE"]
        if c2c:
            event_names.append("C2C_MESSAGE_CREATE")
        if not event_names:
            raise ValueError("on_message 至少需要 group 或 c2c 之一")

        def decorator(handler: Handler) -> Handler:
            for event_name in event_names:
                self._dispatcher.add_handler(event_name, handler)
            return handler

        return decorator

    def on_ready(self) -> Callable[[Handler], Handler]:
        """注册就绪处理器: ``READY`` 与 ``RESUMED`` 都会触发."""

        def decorator(handler: Handler) -> Handler:
            for event_name in ("READY", "RESUMED"):
                self._dispatcher.add_handler(event_name, handler)
            return handler

        return decorator

    def on_error(self) -> Callable[[ErrorHandler], ErrorHandler]:
        """注册错误处理器: handler / 中间件抛异常时被调用.

        处理器入参是 ``(ctx, exc)``, ``ctx`` 取不到时为 None. 可以注册多个,
        按注册顺序调用; 它们自身抛出的异常只会记日志.
        """

        def decorator(handler: ErrorHandler) -> ErrorHandler:
            self._dispatcher.add_error_handler(handler)
            return handler

        return decorator

    def middleware(self, fn: Middleware) -> Middleware:
        """注册中间件(可直接当装饰器用), 先注册的在洋葱外层.

        中间件签名是 ``(ctx, call_next)``: ``await call_next()`` 继续向内,
        不调用即拦截后面所有的 handler 与更内层的中间件.
        """
        self._dispatcher.add_middleware(fn)
        return fn

    # ------------------------------------------------------------ msg_seq

    def next_msg_seq(
        self,
        anchor: str,
        msg_seq: int | None = None,
        *,
        seq_key: str | None = None,
    ) -> int:
        """返回该被动回复锚点本次使用的 ``msg_seq``, 供 :meth:`Context.reply` 调用.

        Args:
            anchor: 本次被动回复的锚点, 即事件 ID 或消息 ID.
            msg_seq: 调用方显式指定的序号; 传了就以它为准, 并把该锚点的计数
                推进到该值, 之后的自增不会回头撞上已用过的序号.
            seq_key: 计数用的键, 省略时用 ``anchor``. 自己拼请求直连
                ``send_group_messages`` 时, 用同一个键调一次本方法登记, 再回来
                的 ``ctx.reply`` 就不会从 1 重新开始而触发 40054005.

        不显式指定时按锚点自增: 同一锚点第一次是 1, 第二次是 2, 以此类推,
        避免平台返回 40054005 (相同 msg_id + msg_seq 重复发送). 计数**按锚点全局
        共享**, 不随 ``Bot`` 实例隔离: 同一进程内多个 ``Bot`` 实例命中同一锚点时
        继续往下排, 而不是各自从 1 开始. 缓存按 ``MSG_SEQ_CACHE_LIMIT`` 限制
        条目数, 超出后淘汰最久未使用的锚点.
        """
        key = seq_key or anchor
        if msg_seq is not None:
            _remember_msg_seq(key, msg_seq)
            return msg_seq
        seq = _MSG_SEQ_CACHE.get(key, 0) + 1
        _remember_msg_seq(key, seq)
        return seq

    # ------------------------------------------------------------ 生命周期

    async def start(self) -> None:
        """连接网关并一直运行, 直到 :meth:`stop` 被调用.

        Raises:
            RuntimeError: 已经在运行.
        """
        if self._running:
            raise RuntimeError("Bot 已经在运行")
        self._running = True
        self._stop_event = asyncio.Event()
        ws = QQBotWebSocket(
            intents=self._intents,
            url=self._url,
            auto_reconnect=self._auto_reconnect,
        )
        self._ws = ws
        ws.on(WILDCARD, self._on_dispatch)
        try:
            await ws.wait_ready()
            logger.info("Bot 已就绪，开始处理事件")
            await self._stop_event.wait()
        finally:
            self._running = False
            await self._shutdown()
            logger.info("Bot 已停止")

    async def stop(self) -> None:
        """停止运行: 关闭网关连接, 取消未完成的处理任务, 可重复调用.

        可以在 handler 里直接 ``await bot.stop()``: 当前处理任务不会被取消,
        其它并发中的处理任务会被取消并回收.
        """
        self._stop_event.set()
        await self._shutdown()

    def run(self) -> None:
        """阻塞式入口, 等价于 ``asyncio.run(bot.start())``."""
        asyncio.run(self.start())

    async def _shutdown(self) -> None:
        """关闭连接并回收任务; 由 ``start()`` 的 finally 与 ``stop()`` 共用."""
        ws = self._ws
        self._ws = None
        if ws is not None:
            await ws.close()
        await self._dispatcher.cancel_tasks()

    def dispatch(self, payload: GatewayPayload) -> asyncio.Task[None] | None:
        """把一帧当作网关下发的事件来处理, 返回处理任务.

        正常运行时由网关回调调用; 也可以在**不连网关**的情况下手动喂事件, 便于
        单元测试::

            payload = GatewayPayload.model_validate(
                {"op": 0, "t": "GROUP_AT_MESSAGE_CREATE", "d": {...}}
            )
            await bot.dispatch(payload)   # 等 handler / 中间件跑完

        Args:
            payload: 网关数据包; ``op`` 不是 Dispatch 时忽略并返回 None.

        Returns:
            正在处理该事件的任务, 可以直接 ``await``; 被忽略时返回 None.
            与网关路径一样, 处理是异步的, 不 ``await`` 也不影响收包。
        """
        if payload.op != OpCode.DISPATCH:
            return None
        if self._stop_event.is_set():
            return None
        context = Context(bot=self, payload=payload, event=resolve_event(payload))
        return self._dispatcher.submit(context)

    async def _on_dispatch(self, payload: GatewayPayload) -> None:
        """网关回调: 交给 :meth:`dispatch`, 不等待处理完成."""
        self.dispatch(payload)


__all__ = [
    "INTENTS_ENV",
    "MSG_SEQ_CACHE_LIMIT",
    "Bot",
    "reset_msg_seq_cache",
    "resolve_intents",
]
