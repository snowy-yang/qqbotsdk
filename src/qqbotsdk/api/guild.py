"""频道（guild）管理方法集：公告、精华消息、日程、成员禁言与信息查询。"""

from typing import Any

from .core import BaseApi


class GuildApi(BaseApi):
    """频道管理与查询方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

    # ---------- 公告与精华 ----------

    async def create_guild_announce(
        self,
        guild_id: str,
        channel_id: str,
        message_id: str,
        announces_type: int = 0,
        **extra: Any,
    ) -> dict:
        """创建频道公告（POST /guilds/{guild_id}/announces）。

        announces_type: 0 成员公告（默认）、1 欢迎公告；
        recommend_channels 等经 extra 透传（与消息类公告互斥）。
        """
        body = {
            "channel_id": channel_id,
            "message_id": message_id,
            "announces_type": announces_type,
        }
        body.update(extra)
        return await self.post(f"/guilds/{guild_id}/announces", json=body)

    async def delete_guild_announce(self, guild_id: str, message_id: str) -> dict:
        """删除频道公告（DELETE /guilds/{guild_id}/announces/{message_id}）。

        删除推荐子频道类型的公告需传 message_id="all"。
        """
        return await self.delete(f"/guilds/{guild_id}/announces/{message_id}")

    async def pin_channel_message(self, channel_id: str, message_id: str) -> dict:
        """添加精华消息（PUT /channels/{channel_id}/pins/{message_id}）。"""
        return await self.put(f"/channels/{channel_id}/pins/{message_id}")

    async def unpin_channel_message(self, channel_id: str, message_id: str) -> dict:
        """移出精华消息（DELETE /channels/{channel_id}/pins/{message_id}）。"""
        return await self.delete(f"/channels/{channel_id}/pins/{message_id}")

    async def get_channel_pins(self, channel_id: str) -> dict:
        """获取精华消息列表（GET /channels/{channel_id}/pins）。"""
        return await self.get(f"/channels/{channel_id}/pins")

    # ---------- 日程 ----------

    async def get_channel_schedules(
        self, channel_id: str, since: int | None = None
    ) -> list | dict:
        """获取子频道日程列表（GET /channels/{channel_id}/schedules）。

        默认返回当天日程；传 since（毫秒级时间戳）返回结束时间在其后的日程。
        """
        params = {"since": str(since)} if since is not None else None
        return await self.get(f"/channels/{channel_id}/schedules", params=params)

    async def get_channel_schedule(self, channel_id: str, schedule_id: str) -> dict:
        """获取单个日程（GET /channels/{channel_id}/schedules/{schedule_id}）。"""
        return await self.get(f"/channels/{channel_id}/schedules/{schedule_id}")

    async def create_channel_schedule(
        self,
        channel_id: str,
        name: str,
        start_timestamp: str,
        end_timestamp: str,
        jump_channel_id: str,
        remind_type: str = "0",
        description: str = "",
    ) -> dict:
        """创建日程（POST /channels/{channel_id}/schedules）。

        时间为毫秒级时间戳字符串；remind_type: "0" 不提醒 / "1" 开始时提醒
        （官方字段为字符串）。请求体按官方约定包在 "schedule" 字段里。
        需管理频道权限；单管理员每天限 10 次。
        """
        return await self.post(
            f"/channels/{channel_id}/schedules",
            json={
                "schedule": {
                    "name": name,
                    "description": description,
                    "start_timestamp": start_timestamp,
                    "end_timestamp": end_timestamp,
                    "jump_channel_id": jump_channel_id,
                    "remind_type": remind_type,
                }
            },
        )

    async def update_channel_schedule(
        self, channel_id: str, schedule_id: str, **fields: Any
    ) -> dict:
        """修改日程（PATCH /channels/{channel_id}/schedules/{schedule_id}）。

        schedule 内的字段（name/start_timestamp/...）经 fields 透传。
        """
        return await self.patch(
            f"/channels/{channel_id}/schedules/{schedule_id}",
            json={"schedule": {"id": schedule_id, **fields}},
        )

    async def delete_channel_schedule(self, channel_id: str, schedule_id: str) -> dict:
        """删除日程（DELETE /channels/{channel_id}/schedules/{schedule_id}）。"""
        return await self.delete(f"/channels/{channel_id}/schedules/{schedule_id}")

    # ---------- 成员管理与信息查询 ----------

    async def mute_guild_member(
        self, guild_id: str, user_id: str, mute_seconds: int = 0
    ) -> dict:
        """禁言/解禁频道成员（PATCH /guilds/{guild_id}/members/{user_id}/mute）。

        mute_seconds 为禁言时长（秒），传 0 解除禁言；上限 28 天。
        """
        return await self.patch(
            f"/guilds/{guild_id}/members/{user_id}/mute",
            json={"mute_seconds": str(mute_seconds)},
        )

    async def get_guild(self, guild_id: str) -> dict:
        """获取频道信息（GET /guilds/{guild_id}）。"""
        return await self.get(f"/guilds/{guild_id}")

    async def get_me_guilds(
        self,
        before: str | None = None,
        after: str | None = None,
        limit: int | None = None,
    ) -> list | dict:
        """获取机器人加入的频道列表（GET /users/@me/guilds）。

        before/after 为分页锚点 guild_id（同时传时 after 无效）；limit
        默认 100、最大 100。
        """
        params: dict[str, Any] = {}
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        if limit is not None:
            params["limit"] = limit
        return await self.get("/users/@me/guilds", params=params or None)

    async def get_guild_channels(self, guild_id: str) -> list | dict:
        """获取频道下的子频道列表（GET /channels/{guild_id}/channels）。"""
        return await self.get(f"/channels/{guild_id}/channels")

    async def create_channel(self, guild_id: str, name: str, **fields: Any) -> dict:
        """创建子频道（POST /guilds/{guild_id}/channels）。私域接口，需管理员权限。

        fields 透传 type/sub_type/position/parent_id/private_type/
        private_user_ids/speak_permission/application_id；成功后触发
        CHANNEL_CREATE 事件。
        """
        return await self.post(
            f"/guilds/{guild_id}/channels", json={"name": name, **fields}
        )

    async def update_channel(self, channel_id: str, **fields: Any) -> dict:
        """修改子频道（PATCH /channels/{channel_id}）。私域接口，需管理员权限。

        fields 为要修改的字段（name/position/parent_id/private_type/
        speak_permission），只需传变更项；成功后触发 CHANNEL_UPDATE 事件。
        """
        return await self.patch(f"/channels/{channel_id}", json=fields)

    async def delete_channel(self, channel_id: str) -> dict:
        """删除子频道（DELETE /channels/{channel_id}）。私域接口，需管理员权限；
        删除后不可恢复，成功后触发 CHANNEL_DELETE 事件。"""
        return await self.delete(f"/channels/{channel_id}")

    async def get_channel(self, channel_id: str) -> dict:
        """获取子频道信息（GET /channels/{channel_id}）。"""
        return await self.get(f"/channels/{channel_id}")

    async def get_channel_online_nums(self, channel_id: str) -> dict:
        """获取子频道在线成员数（GET /channels/{channel_id}/online_nums）。"""
        return await self.get(f"/channels/{channel_id}/online_nums")

    async def get_guild_roles(self, guild_id: str) -> dict:
        """获取频道身份组列表（GET /guilds/{guild_id}/roles）。"""
        return await self.get(f"/guilds/{guild_id}/roles")

    async def create_guild_role(
        self,
        guild_id: str,
        name: str = "",
        color: int | None = None,
        hoist: int | None = None,
    ) -> dict:
        """创建频道身份组（POST /guilds/{guild_id}/roles）。

        color 为 ARGB HEX 十六进制颜色值转十进制；hoist=1 在成员列表
        中单独展示。返回 {"role_id": ..., "role": {...}}。需要管理员权限。
        """
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        if color is not None:
            body["color"] = color
        if hoist is not None:
            body["hoist"] = hoist
        return await self.post(f"/guilds/{guild_id}/roles", json=body)

    async def update_guild_role(
        self,
        guild_id: str,
        role_id: str,
        name: str | None = None,
        color: int | None = None,
        hoist: int | None = None,
    ) -> dict:
        """修改频道身份组（PATCH /guilds/{guild_id}/roles/{role_id}）。

        只传变更项；默认身份组（role_id=1~5，见官方文档）不可修改。
        需要管理员权限。
        """
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if color is not None:
            body["color"] = color
        if hoist is not None:
            body["hoist"] = hoist
        return await self.patch(f"/guilds/{guild_id}/roles/{role_id}", json=body)

    async def delete_guild_role(self, guild_id: str, role_id: str) -> dict:
        """删除频道身份组（DELETE /guilds/{guild_id}/roles/{role_id}）。

        只能删除自己创建的身份组；需要管理员权限。
        """
        return await self.delete(f"/guilds/{guild_id}/roles/{role_id}")

    async def add_guild_member_role(
        self, guild_id: str, user_id: str, role_id: str
    ) -> dict:
        """给成员授予身份组（PUT /guilds/{guild_id}/members/{user_id}/roles/{role_id}）。

        需要管理员权限（同身份组的成员也可操作）。
        """
        return await self.put(
            f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
        )

    async def remove_guild_member_role(
        self, guild_id: str, user_id: str, role_id: str
    ) -> dict:
        """删除成员的身份组（DELETE .../roles/{role_id}）。需要管理员权限。"""
        return await self.delete(
            f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
        )

    async def get_guild_member(self, guild_id: str, user_id: str) -> dict:
        """获取成员详情（GET /guilds/{guild_id}/members/{user_id}）。"""
        return await self.get(f"/guilds/{guild_id}/members/{user_id}")

    async def get_guild_members(self, guild_id: str) -> list | dict:
        """获取频道成员列表（GET /guilds/{guild_id}/members）。

        1 分钟内最多获取 20 次，每次最多 100 人；仅私域机器人可用。
        """
        return await self.get(f"/guilds/{guild_id}/members")

    async def remove_guild_member(
        self,
        guild_id: str,
        user_id: str,
        add_blacklist: bool = False,
        delete_history_msg_days: int = 0,
    ) -> dict:
        """踢出频道成员（DELETE /guilds/{guild_id}/members/{user_id}）。私域接口。

        需要机器人具备踢人权限（管理员）；无法移除管理员。add_blacklist
        同时拉黑；delete_history_msg_days 撤回其消息，仅支持 3/7/15/30
        或 -1（全部），默认 0 不撤回。
        """
        body: dict[str, Any] = {}
        if add_blacklist:
            body["add_blacklist"] = True
        if delete_history_msg_days:
            body["delete_history_msg_days"] = delete_history_msg_days
        return await self.delete(
            f"/guilds/{guild_id}/members/{user_id}", json=body or None
        )

    async def get_role_members(self, guild_id: str, role_id: str) -> list | dict:
        """获取身份组成员列表（GET /guilds/{guild_id}/roles/{role_id}/members）。

        1 分钟内最多获取 20 次，每次最多 100 人；仅私域机器人可用。
        """
        return await self.get(f"/guilds/{guild_id}/roles/{role_id}/members")

    # ---------- 禁言与消息设置 ----------

    async def mute_guild(
        self,
        guild_id: str,
        mute_end_timestamp: str | None = None,
        mute_seconds: str | None = None,
    ) -> dict:
        """频道全员禁言（PATCH /guilds/{guild_id}/mute）。

        mute_end_timestamp（秒级绝对时间戳）与 mute_seconds（字符串秒数）
        二选一，同时传以前者为准；解除全员禁言两个传 "0"。需要管理员权限。
        """
        body: dict[str, Any] = {}
        if mute_end_timestamp is not None:
            body["mute_end_timestamp"] = mute_end_timestamp
        if mute_seconds is not None:
            body["mute_seconds"] = mute_seconds
        return await self.patch(f"/guilds/{guild_id}/mute", json=body)

    async def mute_guild_members(
        self,
        guild_id: str,
        user_ids: list[str],
        mute_end_timestamp: str | None = None,
        mute_seconds: str | None = None,
    ) -> dict:
        """频道批量成员禁言（PATCH /guilds/{guild_id}/mute，带 user_ids）。

        一次最多禁言 20 人；时间字段规则同 mute_guild，解除时传 "0"。
        """
        body: dict[str, Any] = {"user_ids": user_ids}
        if mute_end_timestamp is not None:
            body["mute_end_timestamp"] = mute_end_timestamp
        if mute_seconds is not None:
            body["mute_seconds"] = mute_seconds
        return await self.patch(f"/guilds/{guild_id}/mute", json=body)

    async def get_guild_message_setting(self, guild_id: str) -> dict:
        """获取频道消息频率设置详情（GET /guilds/{guild_id}/message/setting）。"""
        return await self.get(f"/guilds/{guild_id}/message/setting")

    # ---------- 接口权限 ----------

    async def get_guild_api_permissions(self, guild_id: str) -> dict:
        """获取机器人在频道内的可用接口权限列表（GET .../api_permission）。"""
        return await self.get(f"/guilds/{guild_id}/api_permission")

    async def create_api_permission_demand(
        self,
        guild_id: str,
        channel_id: str,
        path: str,
        method: str,
        desc: str,
    ) -> dict:
        """申请频道接口权限（POST /guilds/{guild_id}/api_permission/demand）。

        生成权限授权链接发到子频道 channel_id，由频道管理员点击授权；
        path/method 为要申请的接口（如 "/channels/{channel_id}/messages"，
        method 为 GET/POST…），desc 说明申请后机器人能实现的功能。
        """
        return await self.post(
            f"/guilds/{guild_id}/api_permission/demand",
            json={
                "channel_id": channel_id,
                "api_identify": {"path": path, "method": method},
                "desc": desc,
            },
        )
