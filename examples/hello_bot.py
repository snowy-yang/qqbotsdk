"""最小回声机器人.

配置好 .env 里的 APPID / APPSECRET 后运行::

    python examples/hello_bot.py
"""

import asyncio

from loguru import logger

from qqbotsdk.app import Bot, Context
from qqbotsdk.errors import QQBotAPIError

bot = Bot()


@bot.on_message()
async def on_message(ctx: Context) -> None:
    """群 @ 消息 / 群消息 / 单聊消息都会进来."""
    content = getattr(ctx.event, "content", "") or ""
    logger.info(f"收到 {ctx.event_name}: {content!r}")

    # reply 会自动挑 send_group_messages / send_user_messages,
    # 并处理 event_id / msg_id 与递增的 msg_seq.
    await ctx.reply(f"收到：{content}")


@bot.on_error()
async def on_error(ctx: Context | None, exc: BaseException) -> None:
    if isinstance(exc, QQBotAPIError):
        logger.warning(
            f"{ctx.event_name if ctx else '-'} 调用失败: "
            f"err_code={exc.err_code} message={exc.message} trace_id={exc.trace_id}"
        )
        return
    logger.exception(exc)


def main() -> None:
    bot.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        asyncio.run(bot.stop())
