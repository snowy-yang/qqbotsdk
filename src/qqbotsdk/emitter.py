"""事件分发主体：路由 payload → 触发 handler → 协议层应答回流。

- `dispatch()` 泵循环消费 EventQueue.msg_queue，`emit()` 按
  op（DISPATCH 用 t 名、其余用 Opcode 名）路由到 `@on` 注册的 handler；
- handler 参数按形参标注注入：payload dataclass → 解析对象，`Event` →
  事件封装，`services` 里登记的组件类型 → 实例，其余直传原始 d
  （可能是 dict、标量甚至 None，协议事件的 d 不保证是 dict）；
- 业务 handler（op=0）返回值不回流；协议层（op≠0）返回的 payload
  进 reply 队列由 ws 发出。handler 异常就地隔离，不影响其他 handler。
- `on(..., background=True)` 把 handler 放进后台任务并发执行：
  不阻塞事件流，但同事件 handler 间失去先后保证，返回值不回流；
  进程退出经 `close()` 统一取消在飞任务。
"""

import asyncio
import inspect
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast, get_type_hints, overload

from loguru import logger
from pyee.asyncio import AsyncIOEventEmitter

from .events import Event
from .model import Opcode, Payload
from .payloads import PAYLOAD_TYPES
from .queue import EventQueue

Handler = TypeVar("Handler", bound=Callable[..., Awaitable[Any]])


class BaseProtocol(ABC):
    """协议层处理器接口：具体接入方式（websocket/webhook）实现后注册到主体。"""

    @abstractmethod
    def register(self, emitter: "EventEmitter") -> None: ...

    def on_payload(self, payload: Payload) -> None:  # noqa: B027
        """路由后的每条 payload 回调，供协议类跟踪协议级状态（如 s 序列号）。"""


class EventEmitter:
    def __init__(self, queue: EventQueue | None = None) -> None:
        self._ee = AsyncIOEventEmitter()
        self._queue = queue if queue is not None else EventQueue()
        self.services: dict[type, Any] = {}
        self._protocol: BaseProtocol | None = None
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

    def register_protocol(self, protocol: BaseProtocol) -> None:
        self._protocol = protocol
        protocol.register(self)

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

    def _route(self, data: Payload) -> tuple[int, str, Event] | None:
        op = data.get("op")
        if not isinstance(op, int):
            return None

        # 线上 payload 反序列化出来是 int，Opcode(9) 取名供非 DISPATCH 事件路由
        event_name: str | None
        if op == Opcode.DISPATCH:
            t = data.get("t")
            event_name = t if isinstance(t, str) else None
        else:
            try:
                event_name = Opcode(op).name
            except ValueError:
                return None
        if not isinstance(event_name, str):
            return None

        return op, event_name, Event(data)

    async def emit(self, data: Payload) -> None:
        routed = self._route(data)
        if routed is None:
            logger.warning(f"无法确定事件名，已跳过: {data}")
            return
        op, event_name, event = routed

        if self._protocol is not None:
            self._protocol.on_payload(data)

        listeners = self._ee.listeners(event_name)
        if not listeners:
            return

        reply = op != Opcode.DISPATCH
        for fn in listeners:
            if fn in self._background:
                self._spawn(fn, event)
            else:
                await self._invoke(fn, event, reply=reply)

    async def handle(self, data: Payload) -> Any:
        """同步分发事件并返回首个处理器的非空返回值，用于 op=13 等需要应答的协议事件。"""
        routed = self._route(data)
        if routed is None:
            return None
        _, event_name, event = routed

        for fn in self._ee.listeners(event_name):
            ret = await fn(*self._resolve_params(fn, event))
            if ret is not None:
                return ret
        return None

    async def _invoke(
        self, fn: Callable[..., Awaitable[Any]], event: Event, reply: bool
    ) -> None:
        # 用户 handler 的异常在这里就地隔离，不影响同一事件的其他 handler
        try:
            ret: Any = await fn(*self._resolve_params(fn, event))
        except Exception as e:
            logger.exception(f"事件处理器 {getattr(fn, '__qualname__', fn)} 异常: {e}")
            return
        if reply and isinstance(ret, dict):
            await self._queue.put_reply(cast(Payload, ret))

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
