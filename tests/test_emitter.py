import pytest

from qqbotsdk.emitter import EventEmitter
from qqbotsdk.model import Opcode, payload_of
from qqbotsdk.payloads import GroupAtMessage
from qqbotsdk.queue import EventQueue
from qqbotsdk.session import Session


def test_sequence_only_moves_forward():
    s = Session()
    assert s.sequence_id is None
    s.update_sequence(5)
    s.update_sequence(3)  # 回退被忽略
    assert s.sequence_id == 5
    s.update_sequence(7)
    assert s.sequence_id == 7
    assert s.seq == 7


def test_seq_defaults_to_zero():
    s = Session()
    assert s.seq == 0


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

    await emitter.emit(
        {"op": Opcode.DISPATCH, "t": "READY", "d": {"session_id": "s1"}}
    )
    assert received == [{"session_id": "s1"}]
