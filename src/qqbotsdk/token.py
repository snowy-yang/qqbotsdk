"""access_token 获取与缓存：到期前直接复用，过期自动重新换取。"""

import time

from aiohttp import ClientSession

from .config import Config
from .model import AccessTokenResponse


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
            data: AccessTokenResponse = await resp.json()
            self._access_token = data["access_token"]
            self._expires_at = time.time() + int(data["expires_in"])

        return self._access_token
