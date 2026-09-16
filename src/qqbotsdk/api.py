"""OpenAPI 客户端：自动附带鉴权头，HTTP ≥400 抛 ApiError。

消息接口按接入面分组：v2 群/单聊（openid）、频道（channel_id）。
被动回复规则（官方文档 2026-09 核对）：携带 msg_id（或 event_id，
二选一）为被动回复——单聊 60 分钟内最多 4 次，群聊 5 分钟内最多 5 次；
同一条消息多次回复需递增 msg_seq（相同 msg_id+msg_seq 会发送失败）；
不携带则为主动消息（另有频控，群/单聊每日每对象 1000 条）。
"""

from typing import Any

from aiohttp import ClientSession
from loguru import logger

from .config import Config
from .token import AccessToken

# msg_type 取值
MSG_TYPE_TEXT = 0
MSG_TYPE_MARKDOWN = 2
MSG_TYPE_MEDIA = 7
# file_type 取值（富媒体上传）
FILE_TYPE_IMAGE = 1
FILE_TYPE_VIDEO = 2
FILE_TYPE_VOICE = 3
FILE_TYPE_FILE = 4


class ApiError(RuntimeError):
    """OpenAPI 调用失败：HTTP 非 2xx 或业务 code 非 0。"""

    def __init__(self, status: int, code: Any, message: Any) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"API 调用失败: HTTP {status}, code={code}, message={message}")


class BotApi:
    """通用 REST 封装；具体的业务接口在此之上做薄封装。"""

    def __init__(self, config: Config, http: ClientSession, token: AccessToken) -> None:
        self._config = config
        self._http = http
        self._token = token

    async def request(self, method: str, path: str, **kwargs) -> Any:
        access_token = await self._token.get_access_token()
        headers = {"Authorization": f"QQBot {access_token}"}
        async with self._http.request(
            method,
            f"{self._config.base_url}{path}",
            headers=headers,
            **kwargs,
        ) as resp:
            data = await resp.json()
            if resp.status >= 400:
                logger.warning(f"{method} {path} 失败: {data}")
                code = data.get("code") if isinstance(data, dict) else None
                message = data.get("message") if isinstance(data, dict) else data
                raise ApiError(resp.status, code, message)
            return data

    async def get(self, path: str, **kwargs) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Any:
        return await self.request("POST", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> Any:
        return await self.request("DELETE", path, **kwargs)

    async def put(self, path: str, **kwargs) -> Any:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> Any:
        return await self.request("PATCH", path, **kwargs)

    # ---------- 通用 ----------

    async def me(self) -> dict:
        """机器人自身信息（GET /users/@me）。"""
        return await self.get("/users/@me")

    async def respond_interaction(self, interaction_id: str, code: int = 0) -> dict:
        """回应互动事件（PUT /interactions/{interaction_id}）。

        按钮点击（INTERACTION_CREATE type=11）等互动收到后必须回应，
        否则客户端一直 loading 直到超时；同一 id 只能回应一次。
        """
        return await self.put(f"/interactions/{interaction_id}", json={"code": code})

    # ---------- v2 单聊（C2C） ----------

    async def post_c2c_message(
        self,
        openid: str,
        content: str = "",
        msg_id: str | None = None,
        msg_seq: int = 1,
        media: dict | None = None,
        event_id: str | None = None,
        markdown: str | dict | None = None,
        keyboard: dict | None = None,
        **extra: Any,
    ) -> dict:
        """发单聊消息（POST /v2/users/{openid}/messages）。

        media 为富媒体上传接口返回的 {"file_info": ...} 结构，
        此时 content 作媒体下方文本。msg_id（回复消息）与 event_id
        （响应事件）二选一，均为被动回复。markdown 为字符串或完整
        dict（msg_type=2，与 content 互斥）；keyboard 为内嵌键盘
        结构（{"content": {"rows": [...]}} 或 {"id": ...}）。
        """
        return await self._post_message(
            f"/v2/users/{openid}/messages",
            content=content,
            msg_id=msg_id,
            msg_seq=msg_seq,
            media=media,
            event_id=event_id,
            markdown=markdown,
            keyboard=keyboard,
            **extra,
        )

    async def upload_c2c_file(
        self, openid: str, file_type: int, url: str, srv_send_msg: bool = False
    ) -> dict:
        """上传单聊富媒体（POST /v2/users/{openid}/files）。

        返回含 file_info，可传入 post_c2c_message 的 media 直接发送，
        或 srv_send_msg=True 直接作为消息发出。
        """
        return await self.post(
            f"/v2/users/{openid}/files",
            json={"file_type": file_type, "url": url, "srv_send_msg": srv_send_msg},
        )

    # ---------- v2 群聊 ----------

    async def post_group_message(
        self,
        group_openid: str,
        content: str = "",
        msg_id: str | None = None,
        msg_seq: int = 1,
        media: dict | None = None,
        event_id: str | None = None,
        markdown: str | dict | None = None,
        keyboard: dict | None = None,
        **extra: Any,
    ) -> dict:
        """发群消息（POST /v2/groups/{group_openid}/messages）。

        msg_id（回复消息）与 event_id（响应 GROUP_ADD_ROBOT /
        INTERACTION_CREATE 等事件）二选一。markdown 为字符串或完整
        dict（msg_type=2，与 content 互斥）；keyboard 为内嵌键盘
        结构（{"content": {"rows": [...]}} 或 {"id": ...}）。
        """
        return await self._post_message(
            f"/v2/groups/{group_openid}/messages",
            content=content,
            msg_id=msg_id,
            msg_seq=msg_seq,
            media=media,
            event_id=event_id,
            markdown=markdown,
            keyboard=keyboard,
            **extra,
        )

    async def upload_group_file(
        self, group_openid: str, file_type: int, url: str, srv_send_msg: bool = False
    ) -> dict:
        """上传群富媒体（POST /v2/groups/{group_openid}/files）。"""
        return await self.post(
            f"/v2/groups/{group_openid}/files",
            json={"file_type": file_type, "url": url, "srv_send_msg": srv_send_msg},
        )

    async def _post_message(
        self,
        path: str,
        content: str,
        msg_id: str | None,
        msg_seq: int,
        media: dict | None,
        event_id: str | None,
        markdown: str | dict | None = None,
        keyboard: dict | None = None,
        **extra: Any,
    ) -> dict:
        # media > markdown > 纯文本；markdown 与 content 互斥（官方约定）
        if media is not None:
            body: dict[str, Any] = {"msg_type": MSG_TYPE_MEDIA, "media": media}
            if content:
                body["content"] = content
        elif markdown is not None:
            body = {
                "msg_type": MSG_TYPE_MARKDOWN,
                "markdown": markdown if isinstance(markdown, dict) else {"content": markdown},
            }
        else:
            body = {"msg_type": MSG_TYPE_TEXT}
            if content:
                body["content"] = content
        if msg_id:
            body["msg_id"] = msg_id
            body["msg_seq"] = msg_seq
        elif event_id:
            body["event_id"] = event_id
            body["msg_seq"] = msg_seq
        if keyboard is not None:
            body["keyboard"] = keyboard
        body.update(extra)
        return await self.post(path, json=body)

    async def _withdraw_v2_message(self, path: str, message_id: str) -> dict:
        # 发送超过 2 分钟的消息不可撤回
        return await self.delete(f"{path}/messages/{message_id}")

    async def withdraw_group_message(self, group_openid: str, message_id: str) -> dict:
        """撤回群消息（DELETE /v2/groups/{group_openid}/messages/{message_id}）。

        群管理员可撤回自己与普通成员的消息；普通成员仅能撤回自己的。
        """
        return await self._withdraw_v2_message(f"/v2/groups/{group_openid}", message_id)

    async def withdraw_c2c_message(self, openid: str, message_id: str) -> dict:
        """撤回单聊消息（DELETE /v2/users/{openid}/messages/{message_id}）。"""
        return await self._withdraw_v2_message(f"/v2/users/{openid}", message_id)

    async def mute_group_member(self, group_openid: str, mute_expire_at: str) -> dict:
        """群成员禁言（POST /v2/groups/{group_openid}/restrict_chat_setting）。

        mute_expire_at 为禁言到期时间（RFC3339 格式，如
        "2026-01-01T12:00:00+08:00"）；传当前时间之前即解除禁言。
        """
        return await self.post(
            f"/v2/groups/{group_openid}/restrict_chat_setting",
            json={"mute_expire_at": mute_expire_at},
        )

    # ---------- 频道 ----------

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

    # ---------- 频道管理 ----------

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

    # ---------- 频道信息查询 ----------

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
