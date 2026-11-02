"""中间件示例: 计时 + 简易限流 + 权限过滤.

配置好 .env 后运行::

    python examples/middleware.py
"""

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from loguru import logger

from qqbotsdk.app import Bot, Context

bot = Bot()

# 每个用户 60 秒内最多 5 次
RATE_LIMIT = 5
RATE_WINDOW_SECONDS = 60.0

_hits: dict[str, list[float]] = defaultdict(list)


def _rate_limited(openid: str) -> bool:
    now = time.monotonic()
    hits = [t for t in _hits[openid] if now - t < RATE_WINDOW_SECONDS]
    if len(hits) >= RATE_LIMIT:
        _hits[openid] = hits
        return True
    hits.append(now)
    _hits[openid] = hits
    return False


@bot.middleware
async def timing(ctx: Context, call_next: Callable[[], Awaitable[None]]) -> None:
    """洋葱模型: 先注册的在外层, await call_next() 才继续向内."""
    ctx.state["start"] = time.perf_counter()
    await call_next()
    cost = time.perf_counter() - ctx.state["start"]
    logger.debug(f"{ctx.event_name} 处理耗时 {cost * 1000:.1f} ms")


@bot.middleware
async def guard(ctx: Context, call_next: Callable[[], Awaitable[None]]) -> None:
    """限流 + 关键词过滤: 不调用 call_next 即拦截该事件."""
    openid = ctx.group_openid or ctx.user_openid or ""
    if _rate_limited(openid):
        logger.info(f"{openid} 触发限流, 丢弃 {ctx.event_name}")
        return

    content = (getattr(ctx.event, "content", "") or "").strip()
    if not content:
        logger.debug("空消息, 跳过")
        return

    await call_next()


@bot.on_message()
async def on_message(ctx: Context) -> None:
    content = (getattr(ctx.event, "content", "") or "").strip()

    if content in {"/help", "帮助"}:
        await ctx.reply("可用命令：/help")
        return False  # 阻断后续 handler

    await ctx.reply(f"你说：{content}")
    return None


@bot.on_message()
async def fallback(ctx: Context) -> None:
    logger.debug("上一个 handler 没阻断时才会到这儿")


def main() -> None:
    bot.run()


if __name__ == "__main__":
    main()
