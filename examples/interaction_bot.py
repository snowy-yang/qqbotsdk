"""按钮互动 + 入群申请审批示例.

配置好 .env 后运行::

    python examples/interaction_bot.py

交互流程:
- 用户点消息里的按钮 -> INTERACTION_CREATE -> ctx.api.ack_interaction 立刻回包
- 有人申请入群 -> GROUP_JOIN_REQUEST -> ctx.api.approve_join_request 通过
- 用户添加机器人 -> FRIEND_ADD (只是通知, QQ 没有好友申请审核接口)
"""

from loguru import logger

from qqbotsdk.app import (
    Bot,
    Context,
    callback,
    command,
    confirm_modal,
    keyboard,
    link,
    only_admin,
    row,
)
from qqbotsdk.model.event import InteractionCreateEvent

bot = Bot()

# 键盘用 helper 拼, 不用手写 Keyboard -> KeyboardContent -> Row -> Button -> Action
KEYBOARD = keyboard(
    row(
        callback("签到", "/signin", style="primary"),
        link("官网", "https://example.com"),
    ),
    row(
        command("帮助", "/help"),
        callback(
            "清空",
            "/clear",
            style="danger",
            modal=confirm_modal("确定清空会话吗？"),
            permission=only_admin(),  # 仅管理员可点击 (= Permission(type=1))
        ),
    ),
)


@bot.on_message()
async def on_message(ctx: Context) -> None:
    await ctx.api.send_markdown("## 今日签到\n\n点击下面的按钮试试", keyboard=KEYBOARD)


@bot.on("INTERACTION_CREATE")
async def on_interaction(ctx: Context) -> None:
    if not isinstance(ctx.event, InteractionCreateEvent):
        return

    # 必须在有效时间内回包, 否则客户端一直转圈; 同一 interaction_id 只能回应一次
    await ctx.api.ack_interaction(0)

    resolved = ctx.event.data.resolved if ctx.event.data else None
    button = resolved.button_data if resolved else None
    logger.info(f"按钮点击: interaction={ctx.event.id} data={button!r}")

    if button == "/signin":
        await ctx.api.send("签到成功，明天再来～")


@bot.on("GROUP_JOIN_REQUEST")
async def on_join_request(ctx: Context) -> None:
    logger.info("有人申请入群，自动通过")
    await ctx.api.approve_join_request()  # member_openid 默认取自事件

    # 想拒绝时:
    # await ctx.api.decline_join_request(reject_reason="暂时不开放", add_to_blacklist=True)


@bot.on("FRIEND_ADD")
async def on_friend_add(ctx: Context) -> None:
    # 加机器人即自动成为好友, 这里只是通知; 想打招呼直接发消息即可.
    logger.info("新用户添加了机器人")
    await ctx.api.send("你好，我是机器人～")


@bot.on_error()
async def on_error(ctx: Context | None, exc: BaseException) -> None:
    logger.exception(f"{ctx.event_name if ctx else '-'} 处理失败: {exc!r}")


def main() -> None:
    bot.run()


if __name__ == "__main__":
    main()
