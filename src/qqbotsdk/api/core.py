"""OpenAPI 请求内核：鉴权头注入、限流/鉴权失败重试与统一错误。

失败语义（官方文档 2026-07 核对）：
- 429 触发令牌桶限流，请求未被服务端处理，重试安全——优先按
  Retry-After 等待（线上见过 "30,120" 这类脏值，解析容错），缺失时
  指数退避，最多重试 `_RETRY_LIMIT` 次，等待时长封顶 `_RETRY_CAP`；
- 401 多为 token 被服务端提前作废，强制刷新 token 后重试一次；
- 其余 HTTP ≥400 抛 ApiError，code/message 取自响应体。
"""

import asyncio
from typing import Any

import ujson
from aiohttp import ClientResponse, ClientSession
from loguru import logger

from ..config import Config
from ..model import error_parts
from ..token import AccessToken


class ApiError(RuntimeError):
    """OpenAPI 调用失败：HTTP 非 2xx 或业务 code 非 0。"""

    def __init__(self, status: int, code: Any, message: Any) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"API 调用失败: HTTP {status}, code={code}, message={message}")


class BaseApi:
    """REST 请求内核；域方法集（v2/channel/guild）继承它做薄封装。"""

    # 429 重试次数上限；Retry-After 缺失时的退避基数（秒）与等待封顶
    _RETRY_LIMIT = 3
    _RETRY_BASE = 1.0
    _RETRY_CAP = 30.0

    def __init__(self, config: Config, http: ClientSession, token: AccessToken) -> None:
        self._config = config
        self._http = http
        self._token = token

    async def request(self, method: str, path: str, **kwargs) -> Any:
        auth_retried = False
        for attempt in range(self._RETRY_LIMIT + 1):
            access_token = await self._token.get_access_token()
            headers = {"Authorization": f"QQBot {access_token}"}
            async with self._http.request(
                method,
                f"{self._config.base_url}{path}",
                headers=headers,
                **kwargs,
            ) as resp:
                # 个别接口 200 响应的 Content-Type 不是 JSON（body 仍是 JSON，
                # 如回应互动返回 200 text/plain + {}），跳过标头校验
                data = await resp.json(loads=ujson.loads, content_type=None)
                if resp.status == 429 and attempt < self._RETRY_LIMIT:
                    delay = self._retry_delay(resp, attempt)
                    logger.warning(f"{method} {path} 触发频率限制，{delay:.0f}s 后重试")
                    await asyncio.sleep(delay)
                    continue
                if resp.status == 401 and not auth_retried:
                    auth_retried = True
                    self._token.invalidate()
                    logger.warning(f"{method} {path} 鉴权失效，刷新 token 后重试")
                    continue
                if resp.status >= 400:
                    logger.warning(f"{method} {path} 失败: {data}")
                    raise ApiError(resp.status, *error_parts(data))
                return data
        raise ApiError(429, None, "频率限制重试次数用尽")  # 兜底，理论不可达

    def _retry_delay(self, resp: ClientResponse, attempt: int) -> float:
        raw = resp.headers.get("Retry-After")
        if raw:
            try:
                return min(float(raw.split(",")[0].strip()), self._RETRY_CAP)
            except ValueError:
                pass
        return min(self._RETRY_BASE * 2**attempt, self._RETRY_CAP)

    # ---------- 通用 ----------

    async def me(self) -> dict:
        """机器人自身信息（GET /users/@me）。"""
        return await self.get("/users/@me")

    async def respond_interaction(self, interaction_id: str, code: int = 0) -> dict:
        """回应互动事件（PUT /interactions/{interaction_id}）。

        按钮点击（INTERACTION_CREATE type=11）等互动收到后必须回应，
        否则客户端一直 loading 直到超时；同一 id 只能回应一次。
        """
        return await self.put(f"/interactions/{interaction_id}", json={"code": code})

    async def get(self, path: str, **kwargs) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Any:
        return await self.request("POST", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> Any:
        return await self.request("DELETE", path, **kwargs)

    async def put(self, path: str, **kwargs) -> Any:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> Any:
        return await self.request("PATCH", path, **kwargs)
