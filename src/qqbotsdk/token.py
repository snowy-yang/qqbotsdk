"""access_token 获取与缓存：到期前直接复用，过期自动重新换取。

并发安全：换取过程持 asyncio.Lock 双重检查，多个协程同时首调只发一次请求；
到期判断基于 monotonic 时钟并预留提前刷新余量，不受系统改表时间影响，
也避免卡着到期点刷新在边界上 401。
"""

import asyncio
from time import monotonic
from typing import Any

import ujson
from aiohttp import ClientSession

from .config import Config
from .model import error_parts


class TokenError(RuntimeError):
    """换取 access_token 失败：携带 QQ 返回的 code/message。

    与 ApiError 同构（appid/secret 错误等鉴权失败在此暴露真实原因，
    而不是 KeyError: 'access_token'）。
    """

    def __init__(self, status: int, code: Any, message: Any) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(
            f"获取 access_token 失败: HTTP {status}, code={code}, message={message}"
        )


class AccessToken:
    # 提前刷新余量（秒）：expires_in 末段视为不可信
    _EXPIRY_MARGIN = 30.0

    def __init__(self, config: Config, http: ClientSession) -> None:
        self._config = config
        self._http = http
        self._access_token = ""
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        if not self._expired():
            return self._access_token
        async with self._lock:
            if not self._expired():
                return self._access_token

            payload = {
                "appId": self._config.app_id,
                "clientSecret": self._config.app_secret,
            }

            async with self._http.post(
                f"{self._config.base_url}/app/getAppAccessToken",
                json=payload,
            ) as resp:
                # 与 ApiCore.request 同理：个别接口以非 JSON Content-Type 返回 JSON body
                try:
                    data = await resp.json(loads=ujson.loads, content_type=None)
                except ValueError as e:
                    body = (await resp.read())[:200].decode("utf-8", "replace")
                    raise TokenError(
                        resp.status, None, f"响应不是合法 JSON: {body!r}"
                    ) from e
                # 失败时 QQ 返回 code/message 且 HTTP 可能仍是 200，
                # 以 access_token/expires_in 是否合法为准判断成败，抛出真实原因
                if not isinstance(data, dict):
                    raise TokenError(resp.status, *error_parts(data))
                token = data.get("access_token")
                try:
                    expires_in = int(data.get("expires_in", 0))
                except (TypeError, ValueError):
                    expires_in = 0
                if not isinstance(token, str) or expires_in <= 0:
                    code, message = error_parts(data)
                    raise TokenError(
                        resp.status,
                        code,
                        message or "响应缺少合法的 access_token/expires_in",
                    )
                self._access_token = token
                self._expires_at = monotonic() + max(
                    expires_in - self._EXPIRY_MARGIN, 1
                )

        return self._access_token

    def invalidate(self) -> None:
        """作废缓存 token（如 OpenAPI 侧 401），下次获取强制重新换取。"""
        self._expires_at = 0.0

    def _expired(self) -> bool:
        return monotonic() >= self._expires_at
