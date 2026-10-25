"""全局配置：启动时从环境变量一次性读齐（校验缺失/非法值），由 run_loop 装配到各组件。"""

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
    """SDK 全局配置：启动时从环境变量一次性读齐，由 run_loop 装配到各组件。"""

    app_id: str
    app_secret: str
    base_url: str
    timeout: ClientTimeout
    intents_file: str
    intents: int | None = None

    @classmethod
    def load(cls) -> "Config":
        # TIMEOUT 以毫秒配置
        raw_timeout = os.getenv("TIMEOUT", "5000")
        try:
            timeout = float(raw_timeout) / 1000
        except ValueError:
            raise ValueError(f"TIMEOUT 应为毫秒数，实际: {raw_timeout!r}") from None
        intents_raw = os.getenv("INTENTS", "")
        if intents_raw:
            try:
                intents = int(intents_raw, 0)  # 十进制或 0x 十六进制
            except ValueError:
                raise ValueError(
                    f"INTENTS 应为十进制或 0x 十六进制掩码，实际: {intents_raw!r}"
                ) from None
        else:
            intents = None
        return cls(
            app_id=_required_env("APPID"),
            app_secret=_required_env("APPSECRET"),
            base_url=os.getenv("BASE_URL", "https://api.bot.qq.com"),
            timeout=ClientTimeout(total=timeout),
            intents_file=os.getenv("INTENTS_FILE", "intents.toml"),
            intents=intents,
        )
