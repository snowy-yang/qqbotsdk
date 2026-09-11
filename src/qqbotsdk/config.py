"""全局配置：启动时从环境变量一次性读齐（校验缺失/非法值），经 DI 注入各组件。"""

import os
from dataclasses import dataclass

from aiohttp import ClientTimeout


def _required_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise ValueError(f"缺少必需的环境变量 {name}")
    return value


@dataclass(frozen=True, slots=True)
class Config:
    """SDK 全局配置：启动时从环境变量一次性读齐，经 DI 注入各组件。"""

    app_id: str
    app_secret: str
    base_url: str
    timeout: ClientTimeout
    connecter: str
    intents_file: str
    webhook_host: str
    webhook_port: int
    webhook_path: str

    @classmethod
    def load(cls) -> "Config":
        connecter = os.getenv("CONNECTER", "websocket")
        if connecter not in ("websocket", "webhook"):
            raise ValueError(f"未知的接入方式: {connecter}")
        # TIMEOUT 以毫秒配置
        timeout = float(os.getenv("TIMEOUT", "5000")) / 1000
        return cls(
            app_id=_required_env("APPID"),
            app_secret=_required_env("APPSECRET"),
            base_url=os.getenv("BASE_URL", "https://api.bot.qq.com"),
            timeout=ClientTimeout(total=timeout),
            connecter=connecter,
            intents_file=os.getenv("INTENTS_FILE", "intents.toml"),
            webhook_host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
            webhook_port=int(os.getenv("WEBHOOK_PORT", "8080")),
            webhook_path=os.getenv("WEBHOOK_PATH", "/qqbot/webhook"),
        )
