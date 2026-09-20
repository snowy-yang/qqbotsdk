"""群机器人示例：@消息回复、富媒体图片、按钮卡片与点击回调、入群欢迎、单聊回复。

运行前提：
1. 项目根目录 .env 配好 APPID/APPSECRET（CONNECTER 用默认 websocket）；
2. intents.toml 开启 GROUP_AND_C2C_EVENT 与 INTERACTION 分组的事件；
3. 机器人已在开放平台开通群聊能力，并被拉入测试群。

运行：uv run python examples/group_bot/main.py
"""

from loguru import logger

from qqbotsdk import EventEmitter, main
from qqbotsdk.api import BotApi, button, keyboard
from qqbotsdk.events import Event
from qqbotsdk.payloads import C2CMessage, GroupAtMessage, Interaction

ee = EventEmitter()


@ee.on("GROUP_AT_MESSAGE_CREATE")
async def on_group_message(msg: GroupAtMessage, api: BotApi) -> None:
    if not (msg.group_openid and msg.id):
        return

    # "/img <图片url>"：上传富媒体后随消息发出（msg_type 自动置为 7）
    if (msg.content or "").startswith("/img "):
        url = (msg.content or "").removeprefix("/img ").strip()
        if not url:
            return
        upload = await api.upload_group_file(msg.group_openid, file_type=1, url=url)
        await api.post_group_message(
            msg.group_openid, content="图来了", msg_id=msg.id, media=upload,
        )
        return

    # "/btn"：发一张带回调按钮的 Markdown 卡片
    if (msg.content or "").strip() == "/btn":
        await api.post_group_message(
            msg.group_openid,
            markdown="## 按钮示例\n点下面的按钮试试：",
            keyboard=keyboard(
                button("打个招呼", data="btn|hello"),
                [button("赞", data="btn|like"), button("踩", data="btn|dislike")],
            ),
            msg_id=msg.id,
        )
        return

    # 普通文本：带 msg_id 被动回复（5 分钟内有效，同一条消息多次回复递增 msg_seq）
    await api.post_group_message(
        msg.group_openid, content=f"你说：{msg.content}", msg_id=msg.id,
    )


@ee.on("INTERACTION_CREATE")
async def on_button_click(inter: Interaction, event: Event, api: BotApi) -> None:
    if inter.chat_type != 1 or not inter.group_openid:
        return  # 本示例只处理群聊的按钮回调
    # 必须应答，否则用户端按钮一直 loading（这里的 id 是事件体里的互动 id）
    await api.respond_interaction(inter.id)
    # 被动回复的 event_id 是网关帧最外层的 id（形如 INTERACTION_CREATE:uuid），
    # 不是事件体里的裸 UUID——官方文档点名的常见坑
    await api.post_group_message(
        inter.group_openid, content=f"你点了：{inter.button_data}",
        event_id=event.event_id,
    )


@ee.on("GROUP_ADD_ROBOT")
async def on_robot_added(event: Event, api: BotApi) -> None:
    group_openid = event.group_id
    # 入群是事件而非消息：用信封顶层的事件 id 作 event_id 被动回复（拿不到则跳过）
    event_id = event.event_id
    if not (group_openid and event_id):
        logger.info(f"机器人加入群聊 {group_openid}（无事件 ID，跳过欢迎语）")
        return
    await api.post_group_message(
        group_openid, content="大家好，我是本群机器人，@我即可体验～", event_id=event_id,
    )


@ee.on("C2C_MESSAGE_CREATE")
async def on_c2c_message(msg: C2CMessage, api: BotApi) -> None:
    user_openid = msg.user_openid
    if not (user_openid and msg.id):
        return
    # 单聊被动回复 60 分钟内有效，同一 msg_id 最多回复 4 次
    await api.post_c2c_message(user_openid, content=f"你说：{msg.content}", msg_id=msg.id)


@ee.on("FRIEND_ADD")
async def on_friend_add(d: dict) -> None:
    logger.info(f"新增用户：{d.get('user_openid')}")


if __name__ == "__main__":
    main(ee)
