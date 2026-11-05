"""Intents 订阅位的契约测试.

重点守住 ``GROUP_MEMBER_EVENT = 1 << 24``: 官方「事件订阅与通知」总表没有收录这一位,
但 ``GROUP_MEMBER_ADD`` 与 ``GROUP_JOIN_REQUEST`` 的事件文档标注的 Intent 都是它,
所以它必须有具名成员, 不能靠调用方手写 ``Intents(1 << 24)``.
"""

from qqbotsdk.ws import DEFAULT_INTENTS, Intents
from qqbotsdk.ws.intents import __all__ as INTENTS_ALL


def test_group_member_event_bit_is_24() -> None:
    """GROUP_MEMBER_EVENT 的位值必须是 1<<24."""
    assert Intents.GROUP_MEMBER_EVENT == 1 << 24
    assert int(Intents.GROUP_MEMBER_EVENT) == 16777216


def test_group_member_event_composes_with_others() -> None:
    """与其它位按位或组合后仍是 Intents, 且不串位."""
    combined = Intents.GROUP_AND_C2C_EVENT | Intents.GROUP_MEMBER_EVENT
    assert int(combined) == (1 << 25) | (1 << 24)
    assert Intents.GROUP_MEMBER_EVENT in combined
    assert Intents.INTERACTION not in combined


def test_group_member_event_is_not_in_default_intents() -> None:
    """默认订阅不包含 1<<24: 它是需要额外申请权限的事件类."""
    assert not Intents.GROUP_MEMBER_EVENT & DEFAULT_INTENTS


def test_all_intent_bits_are_unique() -> None:
    """每一位只对应一个成员, 防止把新位误加到已有值上."""
    bits = [int(member) for member in Intents]
    assert len(bits) == len(set(bits))
    assert all(bit > 0 and bit & (bit - 1) == 0 for bit in bits)


def test_group_member_event_is_exported() -> None:
    """具名成员不能只活类里, 也要能从包顶层按名字取到."""
    assert "Intents" in INTENTS_ALL
