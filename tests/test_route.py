import pytest

from qqbotsdk.emitter import EventEmitter
from qqbotsdk.model import Opcode
from qqbotsdk.queue import EventQueue


@pytest.fixture
def emitter() -> EventEmitter:
    return EventEmitter(EventQueue())


def test_route_dispatch_uses_t(emitter: EventEmitter):
    routed = emitter._route({"op": Opcode.DISPATCH, "t": "READY", "d": {}})
    assert routed is not None
    op, name, event = routed
    assert op == Opcode.DISPATCH
    assert name == "READY"
    assert event.type == "READY"


def test_route_non_dispatch_uses_opcode_name(emitter: EventEmitter):
    routed = emitter._route({"op": Opcode.HELLO, "d": {"heartbeat_interval": 1}})
    assert routed is not None
    assert routed[1] == "HELLO"


def test_route_rejects_missing_op(emitter: EventEmitter):
    assert emitter._route({"d": {}}) is None


def test_route_rejects_unknown_opcode(emitter: EventEmitter):
    assert emitter._route({"op": 999}) is None


def test_route_rejects_dispatch_without_t(emitter: EventEmitter):
    assert emitter._route({"op": Opcode.DISPATCH, "d": {}}) is None
