import asyncio

import pytest

from qqbotsdk.config import Config
from qqbotsdk.emitter import EventEmitter
from qqbotsdk.model import Opcode, payload_of
from qqbotsdk.payloads import GroupAtMessage
from qqbotsdk.queue import EventQueue
from qqbotsdk.session import Session
from qqbotsdk.token import AccessToken
from qqbotsdk.ws_protocol import WebsocketProtocol


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
async def test_reply_payload_is_enqueued():
    queue = EventQueue()
    emitter = EventEmitter(queue)

    @emitter.on(Opcode.HEARTBEAT)
    async def beat(_):
        return payload_of(Opcode.HEARTBEAT, 42)

    await emitter.emit({"op": Opcode.HEARTBEAT, "d": 0})
    reply = await queue.get_reply()
    assert reply["op"] == Opcode.HEARTBEAT
    assert reply["d"] == 42


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
async def test_scalar_d_falls_back_to_raw_value():
    """回归：op=9 INVALID_SESSION 的 d 是布尔值，DI 回退必须传原始 d。
    此前实现把 d dict 化成 {}（恒 falsy），resumable=true 也被当成不可续传。
    走真实协议层 handler 验证路由 → 注入 → 会话状态的全链路。"""
    config = Config(
        app_id="a",
        app_secret="s",
        base_url="https://x",
        timeout=None,  # type: ignore[arg-type]
        connecter="websocket",
        intents_file="no-such.toml",
        webhook_host="0.0.0.0",
        webhook_port=8080,
        webhook_path="/x",
    )
    emitter = EventEmitter()
    session = Session()
    session.session_id = "S1"
    emitter.register_protocol(
        WebsocketProtocol(config, session, AccessToken(config, None))  # type: ignore[arg-type]
    )
    seen: list[bool] = []

    @emitter.on(Opcode.INVALID_SESSION)
    async def spy(resumable: bool):
        seen.append(resumable)

    await emitter.emit({"op": Opcode.INVALID_SESSION, "d": True})
    assert seen == [True]
    assert session.session_id == "S1"  # 可续传，会话保留

    await emitter.emit({"op": Opcode.INVALID_SESSION, "d": False})
    assert seen == [True, False]
    assert session.session_id is None  # 不可续传，会话清空


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
