"""频道消息方法集（channel_id 接入面）：发送、撤回、表情表态、
子频道权限与频道私信。"""

from typing import Any

from .core import BaseApi


def _message_body(
    content: str,
    msg_id: str | None,
    msg_seq: int,
    image: str | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    """频道系消息（频道/私信）的请求体：msg_seq 必带，其余按需。"""
    body: dict[str, Any] = {"msg_seq": msg_seq}
    if content:
        body["content"] = content
    if msg_id:
        body["msg_id"] = msg_id
    if image:
        body["image"] = image
    body.update(extra)
    return body


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
        body = _message_body(content, msg_id, msg_seq, image, extra)
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

    # ---------- 子频道权限 ----------

    async def get_channel_permissions(self, channel_id: str, user_id: str) -> dict:
        """获取子频道指定用户的权限（GET .../members/{user_id}/permissions）。

        返回 permissions 字符串形式的权限位图（各权限位含义见官方文档）。
        """
        return await self.get(f"/channels/{channel_id}/members/{user_id}/permissions")

    async def get_channel_role_permissions(
        self, channel_id: str, role_id: str
    ) -> dict:
        """获取子频道指定身份组的权限（GET .../roles/{role_id}/permissions）。"""
        return await self.get(f"/channels/{channel_id}/roles/{role_id}/permissions")

    async def update_channel_permissions(
        self,
        channel_id: str,
        user_id: str,
        *,
        add: str | None = None,
        remove: str | None = None,
    ) -> dict:
        """修改子频道指定用户的权限（PUT .../members/{user_id}/permissions）。

        add/remove 为字符串形式的权限位图（要赋予/删除的权限位），
        至少传一个；需要管理员权限。
        """
        body: dict[str, Any] = {}
        if add is not None:
            body["add"] = add
        if remove is not None:
            body["remove"] = remove
        return await self.put(
            f"/channels/{channel_id}/members/{user_id}/permissions", json=body
        )

    async def update_channel_role_permissions(
        self,
        channel_id: str,
        role_id: str,
        *,
        add: str | None = None,
        remove: str | None = None,
    ) -> dict:
        """修改子频道指定身份组的权限（PUT .../roles/{role_id}/permissions）。"""
        body: dict[str, Any] = {}
        if add is not None:
            body["add"] = add
        if remove is not None:
            body["remove"] = remove
        return await self.put(
            f"/channels/{channel_id}/roles/{role_id}/permissions", json=body
        )

    # ---------- 频道私信 ----------

    async def create_dms(self, recipient_id: str, source_guild_id: str) -> dict:
        """创建私信会话（POST /users/@me/dms）。

        机器人和用户存在共同频道才能创建；返回私信的 guild_id 与
        channel_id，后续发/撤私信用它作路径参数。
        """
        return await self.post(
            "/users/@me/dms",
            json={"recipient_id": recipient_id, "source_guild_id": source_guild_id},
        )

    async def post_dms_message(
        self,
        guild_id: str,
        content: str = "",
        msg_id: str | None = None,
        msg_seq: int = 1,
        image: str | None = None,
        **extra: Any,
    ) -> dict:
        """发私信消息（POST /dms/{guild_id}/messages）。

        guild_id 为 create_dms 返回（或 DIRECT_MESSAGE_CREATE 事件携带）
        的私信频道 id；参数与 post_channel_message 一致。私信每天可对单
        用户发 2 条主动消息、累计 200 条，被动消息不限。
        """
        body = _message_body(content, msg_id, msg_seq, image, extra)
        return await self.post(f"/dms/{guild_id}/messages", json=body)

    async def withdraw_dms_message(
        self, guild_id: str, message_id: str, hide_tip: bool = False
    ) -> dict:
        """撤回私信消息（DELETE /dms/{guild_id}/messages/{message_id}）。私域接口。

        只能撤回机器人自己发送的私信；hide_tip 隐藏撤回提示小灰条。
        """
        return await self.delete(
            f"/dms/{guild_id}/messages/{message_id}",
            params={"hidetip": str(hide_tip).lower()},
        )
