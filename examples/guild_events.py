"""频道域事件示例. 需要额外安装频道包::

    pip install qqbotsdk-guild-py

配置好 .env 后运行::

    python examples/guild_events.py
"""

from loguru import logger

from qqbotsdk.app import Bot, Context
from qqbotsdk.model.guild.event import (
    ChannelCreateEvent,
    GuildCreateEvent,
    GuildMemberAddEvent,
)
from qqbotsdk.ws import Intents

# 只订阅频道相关事件, 避免申请不需要的权限
bot = Bot(
    intents=(
        Intents.GUILDS
        | Intents.GUILD_MEMBERS
        | Intents.PUBLIC_GUILD_MESSAGES
        | Intents.GUILD_MESSAGE_REACTIONS
    )
)


@bot.on("GUILD_CREATE")
async def on_guild_create(ctx: Context) -> None:
    if isinstance(ctx.event, GuildCreateEvent):
        logger.info(f"加入频道: {ctx.event.name} ({ctx.event.id})")


@bot.on("CHANNEL_CREATE")
async def on_channel_create(ctx: Context) -> None:
    if isinstance(ctx.event, ChannelCreateEvent):
        logger.info(f"新建子频道: {ctx.event.name} type={ctx.event.type}")


@bot.on("GUILD_MEMBER_ADD")
async def on_member_add(ctx: Context) -> None:
    if isinstance(ctx.event, GuildMemberAddEvent):
        logger.info(f"新成员加入: {ctx.event.user.username if ctx.event.user else '?'}")


@bot.on("AT_MESSAGE_CREATE")
async def on_at_message(ctx: Context) -> None:
    # 频道消息的回复同样可用 ctx.reply (锚点是事件 ID)
    await ctx.reply("频道里收到你的 @ 了")


@bot.on("*")
async def on_any(ctx: Context) -> None:
    logger.debug(f"事件 {ctx.event_name} / 已建模: {ctx.event is not None}")


@bot.on_error()
async def on_error(ctx: Context | None, exc: BaseException) -> None:
    logger.exception(f"{ctx.event_name if ctx else '-'} 处理失败: {exc!r}")


def main() -> None:
    bot.run()


if __name__ == "__main__":
    main()
