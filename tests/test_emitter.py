import asyncio

import pytest

from qqbotsdk.emitter import EventEmitter
from qqbotsdk.events import Event
from qqbotsdk.model import Opcode
from qqbotsdk.payloads import GroupAtMessage
from qqbotsdk.queue import EventQueue
from qqbotsdk.session import Session


def test_sequence_only_moves_forward():
    s = Session()
    assert s.seq == 0
    s.update_sequence(5)
    s.update_sequence(3)  # 回退被忽略
    assert s.seq == 5
    s.update_sequence(7)
    assert s.seq == 7


@pytest.mark.asyncio
async def test_handler_exception_is_isolated():
    queue = EventQueue()
    emitter = EventEmitter(queue)
    called: list[str] = []

    @emitter.on("READY")
    async def bad(_):
        raise RuntimeError("boom")

    @emitter.on("READY")
    async def good(_):
        called.append("ok")

    await emitter.emit({"op": Opcode.DISPATCH, "t": "READY", "d": {}})
    assert called == ["ok"]


@pytest.mark.asyncio
async def test_protocol_frame_never_reaches_business_handler():
    """协议帧不进分发路径：即使注册了同名 handler 也不该被调用。"""
    emitter = EventEmitter()
    called: list[object] = []

    @emitter.on(Opcode.HEARTBEAT)
    async def beat(d):
        called.append(d)

    await emitter.emit({"op": Opcode.HEARTBEAT, "d": 0})
    assert called == []


@pytest.mark.asyncio
async def test_service_annotation_resolves_from_services():
    queue = EventQueue()
    emitter = EventEmitter(queue)

    class Store:
        pass

    store = Store()
    emitter.services[Store] = store
    received: list[tuple[GroupAtMessage, Store, dict]] = []

    @emitter.on("GROUP_AT_MESSAGE_CREATE")
    async def handler(msg: GroupAtMessage, st: Store, d):
        received.append((msg, st, d))

    await emitter.emit(
        {
            "op": Opcode.DISPATCH,
            "t": "GROUP_AT_MESSAGE_CREATE",
            "d": {"content": "hi", "group_openid": "G1"},
        }
    )
    assert len(received) == 1
    msg, got, d = received[0]
    assert got is store
    assert isinstance(msg, GroupAtMessage) and msg.content == "hi"
    assert d == {"content": "hi", "group_openid": "G1"}


@pytest.mark.asyncio
async def test_unregistered_annotation_falls_back_to_raw_dict():
    queue = EventQueue()
    emitter = EventEmitter(queue)
    received: list[dict] = []

    @emitter.on("READY")
    async def handler(dep: Session):  # Session 未登记进 services
        received.append(dep)

    await emitter.emit({"op": Opcode.DISPATCH, "t": "READY", "d": {"session_id": "s1"}})
    assert received == [{"session_id": "s1"}]


@pytest.mark.asyncio
async def test_service_registered_after_handler_still_injects():
    """回归：形参解析被缓存（签名+标注），但 services 命中必须在每条事件时判定。

    先注册 handler、后登记组件是 run_loop 里的真实时序（用户 handler 在
    main() 之前注册）；若缓存把"已解析好的实参"也存下来，这里会永远拿不到
    实例。同一 handler 连发两条也一并覆盖缓存复用路径。
    """
    emitter = EventEmitter()

    class Store:
        pass

    store = Store()
    got: list[Store] = []

    @emitter.on("READY")
    async def handler(st: Store):
        got.append(st)

    emitter.services[Store] = store  # 登记晚于 handler 注册
    await emitter.emit({"op": Opcode.DISPATCH, "t": "READY", "d": {}})
    await emitter.emit({"op": Opcode.DISPATCH, "t": "READY", "d": {}})
    assert got == [store, store]


@pytest.mark.asyncio
async def test_typed_and_data_see_same_content():
    """`.typed` 与 `.data` 均可用且一致；只取 `.typed` 的 handler 不触发 data 拷贝。"""
    emitter = EventEmitter()
    seen: list[tuple[str | None, str | None]] = []

    @emitter.on("GROUP_AT_MESSAGE_CREATE")
    async def handler(msg: GroupAtMessage, event: Event):
        seen.append((msg.content, event.data["content"]))

    await emitter.emit(
        {
            "op": Opcode.DISPATCH,
            "t": "GROUP_AT_MESSAGE_CREATE",
            "d": {"content": "hi", "group_openid": "G1"},
        }
    )
    assert seen == [("hi", "hi")]


@pytest.mark.asyncio
async def test_background_handler_does_not_block_dispatch():
    """background=True：慢 handler 进后台任务，不阻塞同一事件的后续 handler。"""
    emitter = EventEmitter()
    slow_done = asyncio.Event()
    quick_done = asyncio.Event()

    @emitter.on("GROUP_AT_MESSAGE_CREATE", background=True)
    async def slow(msg: GroupAtMessage):
        await asyncio.sleep(0.05)
        slow_done.set()

    @emitter.on("GROUP_AT_MESSAGE_CREATE")
    async def quick(msg: GroupAtMessage):
        quick_done.set()

    await emitter.emit(
        {
            "op": Opcode.DISPATCH,
            "t": "GROUP_AT_MESSAGE_CREATE",
            "d": {"content": "hi"},
        }
    )
    # emit 返回时快 handler 已跑完，慢 handler 仍在后台
    assert quick_done.is_set()
    assert not slow_done.is_set()
    await asyncio.wait_for(slow_done.wait(), timeout=2)
    await asyncio.sleep(0)  # 让已完成任务的 done_callback 清理 _bg_tasks
    await emitter.close()
    assert not emitter._bg_tasks  # 收尾后在飞任务清空


@pytest.mark.asyncio
async def test_close_cancels_inflight_background_tasks():
    emitter = EventEmitter()
    cancelled = asyncio.Event()

    @emitter.on("READY", background=True)
    async def forever():
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    await emitter.emit({"op": Opcode.DISPATCH, "t": "READY", "d": {}})
    await asyncio.sleep(0)  # 让后台任务实际启动（未启动的任务被 cancel 不会执行函数体）
    await emitter.close()
    assert cancelled.is_set()
