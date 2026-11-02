"""网关地址获取.

网关 WebSocket 地址由 ``GET /gateway`` 下发, 可能随服务端调度变化, 因此每次建立
连接前实时获取, 不在代码里硬编码域名.
"""

from typing import Any, Final, cast

from qqbotsdk.api.core import session
from qqbotsdk.errors import QQBotGatewayError

# 网关地址接口路径
GATEWAY_PATH: Final = "/gateway"


async def fetch_gateway_url() -> str:
    """调用 ``GET /gateway`` 并返回其中的 ``url`` 字段.

    鉴权请求头由 :mod:`qqbotsdk.api.core` 的会话自动注入, HTTP 错误由该会话的
    ``raise_for_status`` 抛出, 这里不再包装.

    Returns:
        网关 WebSocket 地址, 例如 ``wss://api.sgroup.qq.com/websocket``.

    Raises:
        QQBotGatewayError: 响应体缺少可用的 ``url`` 字段.
    """
    async with session.get(GATEWAY_PATH) as resp:
        raw = await resp.json()

    if not isinstance(raw, dict):
        raise QQBotGatewayError("网关响应缺少 url")
    body = cast("dict[str, Any]", raw)
    url = body.get("url")
    if not isinstance(url, str) or not url:
        raise QQBotGatewayError("网关响应缺少 url")
    return url


__all__ = [
    "GATEWAY_PATH",
    "fetch_gateway_url",
]
