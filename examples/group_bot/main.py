"""群机器人示例：@消息回复、富媒体图片回复、入群欢迎、单聊回复。

运行前提：
1. 项目根目录 .env 配好 APPID/APPSECRET（CONNECTER 用默认 websocket）；
2. intents.toml 开启 GROUP_AND_C2C_EVENT 分组的事件；
3. 机器人已在开放平台开通群聊能力，并被拉入测试群。

运行：uv run python examples/group_bot/main.py
"""

from loguru import logger

from qqbotsdk import EventEmitter, EventQueue, main
from qqbotsdk.api import BotApi
from qqbotsdk.events import Event
from qqbotsdk.payloads import C2CMessage, GroupAtMessage

ee = EventEmitter(EventQueue())


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

    # 普通文本：带 msg_id 被动回复（5 分钟内有效，同一条消息多次回复递增 msg_seq）
    await api.post_group_message(
        msg.group_openid, content=f"你说：{msg.content}", msg_id=msg.id,
    )


@ee.on("GROUP_ADD_ROBOT")
async def on_robot_added(event: Event, api: BotApi) -> None:
    group_openid = event.group_id
    # 入群是事件而非消息：事件 ID 在推送 envelope 顶层 id 字段，
    # 作 event_id 即可在 5 分钟内被动回复欢迎语（拿不到则跳过）
    event_id = event.raw.get("id")
    if not (group_openid and isinstance(event_id, str) and event_id):
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
