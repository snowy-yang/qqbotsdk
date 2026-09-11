"""事件分发主体：路由 payload → 触发 handler → 协议层应答回流。

- `dispatch()` 泵循环消费 EventQueue.msg_queue，`emit()` 按
  op（DISPATCH 用 t 名、其余用 Opcode 名）路由到 `@on` 注册的 handler；
- DI 容器在位时按 handler 参数标注注入（`Inject[T]`/`Event` 等，
  解析失败回退传原始 d），否则直传 d；
- 业务 handler（op=0）返回值不回流；协议层（op≠0）返回的 payload
  进 reply 队列由 ws 发出。handler 异常就地隔离，不影响其他 handler。
"""

import inspect
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast, get_args, get_type_hints, overload

from dishka import AsyncContainer
from dishka.exceptions import NoFactoryError
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
    def __init__(self, queue: EventQueue) -> None:
        self._ee = AsyncIOEventEmitter()
        self._queue = queue
        self._container: AsyncContainer | None = None
        self._protocol: BaseProtocol | None = None
        self._hints: dict[Callable[..., Any], dict[str, Any]] = {}

    @property
    def queue(self) -> EventQueue:
        """本 emitter 消费的事件队列；外部构造 emitter 时由容器复用同一实例。"""
        return self._queue

    def use_container(self, container: AsyncContainer) -> None:
        self._container = container

    def register_protocol(self, protocol: BaseProtocol) -> None:
        self._protocol = protocol
        protocol.register(self)

    @overload
    def on(self, event: Opcode | str) -> Callable[[Handler], Handler]: ...

    @overload
    def on(self, event: Opcode | str, fn: Handler) -> Handler: ...

    def on(
        self, event: Opcode | str, fn: Handler | None = None
    ) -> Handler | Callable[[Handler], Handler]:
        name = event.name if isinstance(event, Opcode) else event

        def decorator(fn: Handler) -> Handler:
            self._ee.on(name, fn)
            return fn

        if fn is None:
            return decorator

        self._ee.on(name, fn)
        return fn

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

        if self._container is None:
            for fn in listeners:
                await self._call_direct(fn, event, reply=op != Opcode.DISPATCH)
            return

        async with self._container({Event: event}) as scope:
            for fn in listeners:
                await self._invoke(scope, fn, event, reply=op != Opcode.DISPATCH)

    async def handle(self, data: Payload) -> Any:
        """同步分发事件并返回首个处理器的非空返回值，用于 op=13 等需要应答的协议事件。"""
        routed = self._route(data)
        if routed is None:
            return None
        _, event_name, event = routed

        for fn in self._ee.listeners(event_name):
            if self._container is None:
                args = self._direct_args(fn, event)
                ret = await fn(*args)
            else:
                async with self._container({Event: event}) as scope:
                    args, kwargs = await self._resolve_params(scope, fn, event)
                    ret = await fn(*args, **kwargs)
            if ret is not None:
                return ret
        return None

    def _direct_args(
        self, fn: Callable[..., Awaitable[Any]], event: Event
    ) -> list[Any]:
        """无 DI 容器时的参数解析：Event → 事件对象，payload 类型 → dataclass，其余 → 原始 d。"""
        hints = self._hints.get(fn)
        if hints is None:
            hints = get_type_hints(fn, include_extras=True)
            self._hints[fn] = hints

        args: list[Any] = []
        for name in inspect.signature(fn).parameters:
            hint = hints.get(name)
            if hint in PAYLOAD_TYPES:
                args.append(event.typed)
            elif hint is Event:
                args.append(event)
            else:
                args.append(event.data)
        return args

    async def _call_direct(
        self, fn: Callable[..., Awaitable[Any]], event: Event, reply: bool
    ) -> None:
        # 用户 handler 的异常在这里就地隔离（无 DI 容器的直连路径）
        try:
            ret: Any = await fn(*self._direct_args(fn, event))
        except Exception as e:
            logger.exception(f"事件处理器 {getattr(fn, '__qualname__', fn)} 异常: {e}")
            return
        if reply and isinstance(ret, dict):
            await self._queue.put_reply(cast(Payload, ret))

    async def _invoke(
        self,
        scope: AsyncContainer,
        fn: Callable[..., Awaitable[Any]],
        event: Event,
        reply: bool,
    ) -> None:
        # 用户 handler 的异常在这里就地隔离，不影响同一事件的其他 handler
        try:
            args, kwargs = await self._resolve_params(scope, fn, event)
            ret: Any = await fn(*args, **kwargs)
        except Exception as e:
            logger.exception(f"事件处理器 {getattr(fn, '__qualname__', fn)} 异常: {e}")
            return
        if reply and isinstance(ret, dict):
            await self._queue.put_reply(cast(Payload, ret))

    async def _resolve_params(
        self,
        scope: AsyncContainer,
        fn: Callable[..., Awaitable[Any]],
        event: Event,
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        hints = self._hints.get(fn)
        if hints is None:
            hints = get_type_hints(fn, include_extras=True)
            self._hints[fn] = hints

        positional: list[Any] = []
        kwargs: dict[str, Any] = {}
        for name in inspect.signature(fn).parameters:
            hint = hints.get(name)
            if hint is None:
                positional.append(event.data)
                continue

            if hint in PAYLOAD_TYPES:
                kwargs[name] = event.typed
                continue
            if hint is Event:
                kwargs[name] = event
                continue

            target = get_args(hint)[0] if hasattr(hint, "__metadata__") else hint
            try:
                kwargs[name] = await scope.get(target)
            except NoFactoryError:
                positional.append(event.data)
        return tuple(positional), kwargs
