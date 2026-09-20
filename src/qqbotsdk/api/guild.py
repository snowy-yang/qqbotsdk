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

    async def get_guild_channels(self, guild_id: str) -> list | dict:
        """获取频道下的子频道列表（GET /channels/{guild_id}/channels）。"""
        return await self.get(f"/channels/{guild_id}/channels")

    async def get_channel(self, channel_id: str) -> dict:
        """获取子频道信息（GET /channels/{channel_id}）。"""
        return await self.get(f"/channels/{channel_id}")

    async def get_guild_roles(self, guild_id: str) -> dict:
        """获取频道身份组列表（GET /guilds/{guild_id}/roles）。"""
        return await self.get(f"/guilds/{guild_id}/roles")

    async def get_guild_member(self, guild_id: str, user_id: str) -> dict:
        """获取成员详情（GET /guilds/{guild_id}/members/{user_id}）。"""
        return await self.get(f"/guilds/{guild_id}/members/{user_id}")
