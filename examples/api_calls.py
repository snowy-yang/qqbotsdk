"""API 层示例: 不走长连接, 直接调 HTTP 接口.

配置好 .env 后运行::

    python examples/api_calls.py <group_openid>
"""

import asyncio
import sys

from loguru import logger

from qqbotsdk.api.bot import get_me
from qqbotsdk.api.core import session
from qqbotsdk.api.group.manage import get_group_info, get_group_members
from qqbotsdk.api.group.messages import recall_group_messages, send_group_messages
from qqbotsdk.errors import QQBotAPIError
from qqbotsdk.model.group.member import GetGroupMembersRequest
from qqbotsdk.model.group.messages import SendGroupMessagesRequest


async def main(group_openid: str) -> None:
    me = await get_me()
    logger.info(f"机器人: {me.username} ({me.id})")

    info = await get_group_info(group_openid)
    logger.info(f"群信息: {info.group_name}")

    page = await get_group_members(group_openid, GetGroupMembersRequest(limit=20))
    logger.info(f"前 20 个成员: {len(page.members or [])} 个")

    # 主动消息: 不带 msg_id / event_id
    sent = await send_group_messages(
        group_openid,
        SendGroupMessagesRequest(
            msg_type=0, content="来自 examples/api_calls.py 的问候"
        ),
    )
    logger.info(f"已发送: {sent.id}")

    await recall_group_messages(group_openid, sent.id)
    logger.info("已撤回")

    await session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法: python examples/api_calls.py <group_openid>")

    try:
        asyncio.run(main(sys.argv[1]))
    except QQBotAPIError as exc:
        logger.error(
            f"调用失败: err_code={exc.err_code} message={exc.message} trace={exc.trace_id}"
        )
        raise SystemExit(1) from exc
