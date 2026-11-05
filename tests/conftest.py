"""pytest 全局夹具."""

from collections.abc import Iterator

import pytest

from qqbotsdk.api import core
from qqbotsdk.api.auth import reset_access_token
from qqbotsdk.app.bot import reset_msg_seq_cache


@pytest.fixture(autouse=True)
def _reset_token_cache() -> Iterator[None]:
    """每个用例前后清空 token 缓存, 避免用例之间互相影响."""
    reset_access_token()
    yield
    reset_access_token()


@pytest.fixture(autouse=True)
def _reset_session_and_msg_seq() -> Iterator[None]:
    """每个用例前后还原注入的会话与全局 msg_seq 计数.

    两者都是模块级状态: 会话注入会让后续用例误用上一条用例的假服务端,
    msg_seq 计数会让后续用例看到别处累加出来的序号. 前后都清一次最稳.
    """
    core.reset_session()
    reset_msg_seq_cache()
    yield
    core.reset_session()
    reset_msg_seq_cache()
