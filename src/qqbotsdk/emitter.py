"""事件分发主体：路由业务事件 → 触发 handler → 异常隔离与后台并发。

- `dispatch()` 泵循环消费 EventQueue.msg_queue，`emit()` 把 op=0 的业务事件
  按 t 名路由到 `@on` 注册的 handler；协议帧（HELLO/INVALID_SESSION/op=13 等）
  不进队列，由连接适配器的协议处理器就地处理（见 protocol.py）；
- handler 参数按形参标注注入：payload dataclass → 解析对象，`Event` →
  事件封装，`services` 里登记的组件类型 → 实例，其余直传原始 d
  （可能是 dict、标量甚至 None）；
- 业务 handler 返回值不回流；handler 异常就地隔离，不影响其他 handler。
- `on(..., background=True)` 把 handler 放进后台任务并发执行：
  不阻塞事件流，但同事件 handler 间失去先后保证；
  进程退出经 `close()` 统一取消在飞任务。
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, get_type_hints, overload

from loguru import logger
from pyee.asyncio import AsyncIOEventEmitter

from .events import Event
from .model import Opcode, Payload
from .payloads import PAYLOAD_TYPES
from .queue import EventQueue

Handler = TypeVar("Handler", bound=Callable[..., Awaitable[Any]])


class EventEmitter:
    def __init__(self, queue: EventQueue | None = None) -> None:
        self._ee = AsyncIOEventEmitter()
        self._queue = queue if queue is not None else EventQueue()
        self.services: dict[type, Any] = {}
        # handler → (类型标注, 形参名)：签名解析较贵，缓存后每条事件只查表
        self._signatures: dict[
            Callable[..., Any], tuple[dict[str, Any], tuple[str, ...]]
        ] = {}
        self._background: set[Callable[..., Any]] = set()
        self._bg_tasks: set[asyncio.Task[None]] = set()

    @property
    def queue(self) -> EventQueue:
        """本 emitter 消费的事件队列；未显式传入时构造即自建，run_loop 复用同一实例。"""
        return self._queue

    @overload
    def on(
        self, event: Opcode | str, *, background: bool = False
    ) -> Callable[[Handler], Handler]: ...

    @overload
    def on(
        self, event: Opcode | str, fn: Handler, *, background: bool = False
    ) -> Handler: ...

    def on(
        self,
        event: Opcode | str,
        fn: Handler | None = None,
        *,
        background: bool = False,
    ) -> Handler | Callable[[Handler], Handler]:
        name = event.name if isinstance(event, Opcode) else event

        def decorator(fn: Handler) -> Handler:
            self._ee.on(name, fn)
            if background:
                self._background.add(fn)
            return fn

        if fn is None:
            return decorator

        return decorator(fn)

    async def close(self) -> None:
        """取消全部在飞后台任务并等待收尾；run_loop 退出时先于连接池调用。"""
        if not self._bg_tasks:
            return
        for task in self._bg_tasks:
            task.cancel()
        await asyncio.gather(*self._bg_tasks, return_exceptions=True)

    async def dispatch(self) -> None:
        while True:
            data = await self._queue.get_event()
            try:
                await self.emit(data)
            except Exception as e:
                # dispatch 是主循环，单条事件路由失败不能带崩整个进程
                logger.exception(f"事件分发异常，已跳过: {data} ({e})")

    async def emit(self, data: Payload) -> None:
        # 先取事件名，无 listener 就不必构造 Event（每条未订阅/协议帧都省一次拷贝）
        op = data.get("op")
        if op != Opcode.DISPATCH:
            logger.warning(f"非业务事件不应进分发队列，已跳过: {data}")
            return
        t = data.get("t")
        if not isinstance(t, str):
            logger.warning(f"业务事件缺少 t 字段，已跳过: {data}")
            return

        listeners = self._ee.listeners(t)
        if not listeners:
            return

        event = Event(data)
        for fn in listeners:
            if fn in self._background:
                self._spawn(fn, event)
            else:
                await self._invoke(fn, event)

    async def _invoke(self, fn: Callable[..., Awaitable[Any]], event: Event) -> None:
        # 用户 handler 的异常在这里就地隔离，不影响同一事件的其他 handler
        try:
            await fn(*self._resolve_params(fn, event))
        except Exception as e:
            logger.exception(f"事件处理器 {getattr(fn, '__qualname__', fn)} 异常: {e}")

    def _spawn(self, fn: Callable[..., Awaitable[Any]], event: Event) -> None:
        """handler 进后台任务，emit 不等它；任务由 _bg_tasks 持强引用防 GC。"""
        task = asyncio.create_task(self._run_background(fn, event))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _run_background(
        self, fn: Callable[..., Awaitable[Any]], event: Event
    ) -> None:
        try:
            await fn(*self._resolve_params(fn, event))
        except Exception as e:
            logger.exception(
                f"后台事件处理器 {getattr(fn, '__qualname__', fn)} 异常: {e}"
            )

    def _resolve_params(
        self, fn: Callable[..., Awaitable[Any]], event: Event
    ) -> list[Any]:
        """按 handler 形参标注解析：payload dataclass → 解析对象，`Event` → 事件
        封装，`services` 登记的组件类型 → 实例，其余（含无标注）→ 原始 d
        （Event.data 是 dict 化视图，标量 d 如 INVALID_SESSION 的 true/false
        必须走这里才能拿到原值）。"""
        cached = self._signatures.get(fn)
        if cached is None:
            cached = (
                get_type_hints(fn),
                tuple(inspect.signature(fn).parameters),
            )
            self._signatures[fn] = cached
        hints, names = cached

        args: list[Any] = []
        for name in names:
            hint = hints.get(name)
            if hint in PAYLOAD_TYPES:
                args.append(event.typed)
            elif hint is Event:
                args.append(event)
            elif hint in self.services:
                args.append(self.services[hint])
            else:
                args.append(event.raw.get("d"))
        return args
