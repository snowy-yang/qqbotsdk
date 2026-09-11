import pytest

from qqbotsdk.emitter import EventEmitter
from qqbotsdk.model import Opcode, payload_of
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
