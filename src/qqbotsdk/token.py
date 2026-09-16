"""access_token 获取与缓存：到期前直接复用，过期自动重新换取。"""

import time
from typing import Any

import ujson
from aiohttp import ClientSession

from .config import Config


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
    def __init__(self, config: Config, http: ClientSession) -> None:
        self._config = config
        self._http = http
        self._access_token = ""
        self._expires_at = 0.0

    async def get_access_token(self) -> str:
        if time.time() < self._expires_at:
            return self._access_token

        payload = {
            "appId": self._config.app_id,
            "clientSecret": self._config.app_secret,
        }

        async with self._http.post(
            f"{self._config.base_url}/app/getAppAccessToken",
            json=payload,
        ) as resp:
            # 与 request() 同理：个别接口以非 JSON Content-Type 返回 JSON body
            data = await resp.json(loads=ujson.loads, content_type=None)
            # 失败时 QQ 返回 code/message 且 HTTP 可能仍是 200，
            # 以 access_token 是否在为准判断成败，抛出真实原因
            if not isinstance(data, dict) or "access_token" not in data:
                code = data.get("code") if isinstance(data, dict) else None
                message = data.get("message") if isinstance(data, dict) else data
                raise TokenError(resp.status, code, message)
            self._access_token = data["access_token"]
            self._expires_at = time.time() + int(data["expires_in"])

        return self._access_token
