"""访问凭证(access_token)的获取, 缓存与自动刷新.

凭证来自环境变量 ``APPID`` / ``APPSECRET``, 支持从项目根目录的 ``.env`` 读取.
按官方文档, 凭证有效期 7200 秒, 且在过期前 60 秒内换取会直接返回新凭证, 因此这里
在剩余有效时间不足 60 秒时主动刷新, 调用方无需关心过期.

``QQBotAuthError`` 定义在 :mod:`qqbotsdk.errors`, 这里 re-export, 旧的
``from qqbotsdk.api.auth import QQBotAuthError`` 仍然可用.
"""

import asyncio
import os
import time
from typing import Final

from aiohttp import ClientSession
from dotenv import load_dotenv
from loguru import logger

from qqbotsdk.errors import QQBotAuthError

# 获取凭证的接口地址, 不走 BASE_URL 以避免与 core 循环依赖
TOKEN_URL: Final = "https://api.bot.qq.com/app/getAppAccessToken"

# 提前刷新余量: 官方文档为过期前 60 秒内可换到新凭证
REFRESH_MARGIN_SECONDS: Final = 60

load_dotenv()

_lock = asyncio.Lock()
_token: str | None = None
_expires_at: float = 0.0


def _credentials() -> tuple[str, str] | None:
    """读取 appId/appSecret, 缺任一项视为未配置."""
    app_id = os.getenv("APPID") or os.getenv("QQBOT_APPID")
    app_secret = os.getenv("APPSECRET") or os.getenv("QQBOT_APPSECRET")
    if not app_id or not app_secret:
        return None
    return app_id, app_secret


def _cached_token() -> str | None:
    """命中缓存且未进入刷新窗口时返回当前凭证."""
    if _token is not None and time.monotonic() < _expires_at - REFRESH_MARGIN_SECONDS:
        return _token
    return None


async def _fetch_token() -> tuple[str, int]:
    credentials = _credentials()
    if credentials is None:
        raise QQBotAuthError(
            "缺少 APPID / APPSECRET：请在 .env 或环境变量中配置机器人凭证"
        )
    app_id, app_secret = credentials

    async with (
        ClientSession() as client,
        client.post(
            TOKEN_URL,
            json={"appId": app_id, "clientSecret": app_secret},
        ) as resp,
    ):
        body: dict[str, object] = await resp.json(content_type=None)

    # 该接口业务错误仍返回 HTTP 200, 需按 code 判定
    if (code := body.get("code")) is not None:
        message = body.get("message")
        raise QQBotAuthError(
            f"获取 access_token 失败：code={code} message={message!r}",
            code=code if isinstance(code, int) else None,
        )

    token = body.get("access_token")
    expires_in = body.get("expires_in")
    if not isinstance(token, str) or not token:
        raise QQBotAuthError(
            f"获取 access_token 失败：响应缺少 access_token（{body!r}）"
        )

    try:
        # 文档示例中 expires_in 为字符串 "7200", 两种形态都接受
        ttl = int(expires_in)  # pyright: ignore[reportArgumentType]
    except (TypeError, ValueError):
        ttl = 7200

    return token, ttl


async def get_access_token(*, force: bool = False) -> str:
    """返回可用的 access_token, 必要时刷新.

    Args:
        force: 忽略缓存强制刷新.
    """
    global _token, _expires_at

    if not force and (cached := _cached_token()) is not None:
        return cached

    async with _lock:
        # 并发进入时可能已被其他协程刷新, 二次检查避免重复请求
        if not force and (cached := _cached_token()) is not None:
            return cached

        token, ttl = await _fetch_token()
        _token = token
        _expires_at = time.monotonic() + ttl
        logger.debug(f"access_token 已刷新，有效期 {ttl} 秒")
        return token


async def get_authorization() -> str:
    """返回 Authorization 请求头的值, 格式为 ``QQBot ACCESS_TOKEN``."""
    return f"QQBot {await get_access_token()}"


def reset_access_token() -> None:
    """清空缓存凭证, 供测试或主动失效时使用."""
    global _token, _expires_at
    _token = None
    _expires_at = 0.0


__all__ = [
    "REFRESH_MARGIN_SECONDS",
    "TOKEN_URL",
    "QQBotAuthError",
    "get_access_token",
    "get_authorization",
    "reset_access_token",
]
