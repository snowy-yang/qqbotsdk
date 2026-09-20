"""v2 群聊/单聊方法集（openid 接入面）：消息、富媒体上传、撤回、禁言，
以及内嵌按钮/键盘的快捷构造。

被动回复规则（官方文档 2026-09 核对）：携带 msg_id（或 event_id，
二选一）为被动回复——单聊 60 分钟内最多 4 次，群聊 5 分钟内最多 5 次；
同一条消息多次回复需递增 msg_seq（相同 msg_id+msg_seq 会发送失败）；
不携带则为主动消息（另有频控，群/单聊每日每对象 1000 条）。
"""

from typing import Any
from uuid import uuid4

from .core import BaseApi

# msg_type 取值
MSG_TYPE_TEXT = 0
MSG_TYPE_MARKDOWN = 2
MSG_TYPE_MEDIA = 7
# file_type 取值（富媒体上传）
FILE_TYPE_IMAGE = 1
FILE_TYPE_VIDEO = 2
FILE_TYPE_VOICE = 3
FILE_TYPE_FILE = 4


def button(
    label: str,
    data: str = "",
    *,
    type: int = 1,
    permission: int = 2,
    style: int = 1,
    id: str | None = None,
) -> dict:
    """构造单个内嵌按钮 dict，供 keyboard() 组装后传入 keyboard= 参数。

    type: 1 回调（点击推 INTERACTION_CREATE）/ 0 跳转链接（data 为 url）/
    2 指令（data 插入输入框）。permission: 2 所有人 / 1 管理员 / 0 指定
    用户。label 官方限 10 字以内；要补嵌套字段（如 visited_label、
    prompt）直接修改返回的 dict。
    """
    return {
        "id": id or uuid4().hex[:8],
        "render_data": {"label": label, "style": style},
        "action": {"type": type, "permission": {"type": permission}, "data": data},
    }


def keyboard(*rows: dict | list[dict]) -> dict:
    """组装内嵌键盘（keyboard= 参数）：每个位置参数为一行，
    单个按钮独占一行，按钮列表同行并排。"""
    return {
        "content": {
            "rows": [
                {"buttons": row if isinstance(row, list) else [row]} for row in rows
            ]
        }
    }


class V2Api(BaseApi):
    """v2 群聊/单聊方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

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
        return await self._upload_v2_file(
            f"/v2/users/{openid}", file_type, url, srv_send_msg
        )

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
        return await self._upload_v2_file(
            f"/v2/groups/{group_openid}", file_type, url, srv_send_msg
        )

    async def _upload_v2_file(
        self, base: str, file_type: int, url: str, srv_send_msg: bool
    ) -> dict:
        return await self.post(
            f"{base}/files",
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
                "markdown": markdown
                if isinstance(markdown, dict)
                else {"content": markdown},
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
