"""频道消息方法集（channel_id 接入面）：发送、撤回与表情表态。"""

from typing import Any

from .core import BaseApi


class ChannelApi(BaseApi):
    """频道消息方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

    async def post_channel_message(
        self,
        channel_id: str,
        content: str = "",
        msg_id: str | None = None,
        msg_seq: int = 1,
        image: str | None = None,
        **extra: Any,
    ) -> dict:
        """发频道消息（POST /channels/{channel_id}/messages）。

        image 为图片 URL；其余字段（embed/ark/markdown 等）经 extra 透传。
        """
        body: dict[str, Any] = {"msg_seq": msg_seq}
        if content:
            body["content"] = content
        if msg_id:
            body["msg_id"] = msg_id
        if image:
            body["image"] = image
        body.update(extra)
        return await self.post(f"/channels/{channel_id}/messages", json=body)

    async def withdraw_channel_message(
        self, channel_id: str, message_id: str, hide_tip: bool = False
    ) -> dict:
        """撤回频道消息（DELETE /channels/{channel_id}/messages/{message_id}）。

        hide_tip 控制是否隐藏撤回提示小灰条（官方参数名为 hidetip）；
        仅私域机器人可用。
        """
        return await self.delete(
            f"/channels/{channel_id}/messages/{message_id}",
            params={"hidetip": str(hide_tip).lower()},
        )

    async def put_channel_reaction(
        self, channel_id: str, message_id: str, emoji_type: int, emoji_id: str
    ) -> dict:
        """对频道消息表态（PUT .../reactions/{type}/{emoji_id}）。

        emoji_type=1 为系统表情，emoji_id 为系统表情序号（字符串）。
        """
        return await self.put(
            f"/channels/{channel_id}/messages/{message_id}"
            f"/reactions/{emoji_type}/{emoji_id}"
        )

    async def delete_channel_reaction(
        self, channel_id: str, message_id: str, emoji_type: int, emoji_id: str
    ) -> dict:
        """删除自己对该消息的表态（DELETE .../reactions/{type}/{emoji_id}）。"""
        return await self.delete(
            f"/channels/{channel_id}/messages/{message_id}"
            f"/reactions/{emoji_type}/{emoji_id}"
        )
