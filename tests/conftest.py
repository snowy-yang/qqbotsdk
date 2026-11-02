"""pytest 全局夹具."""

from collections.abc import Iterator

import pytest

from qqbotsdk.api.auth import reset_access_token


@pytest.fixture(autouse=True)
def _reset_token_cache() -> Iterator[None]:
    """每个用例前后清空 token 缓存, 避免用例之间互相影响."""
    reset_access_token()
    yield
    reset_access_token()
