"""v2 群聊/单聊方法集（openid 接入面）：消息、流式消息、富媒体上传与
大文件分片上传、撤回、禁言、分享链接，以及内嵌按钮/键盘的快捷构造。

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
# 流式消息取值
STREAM_INPUT_APPEND = "append"  # 分片内容追加到待下发正文
STREAM_INPUT_REPLACE = "replace"  # 分片内容为全量正文（须以上游已下发前缀开头）
STREAM_GENERATING = 1  # input_state：生成中
STREAM_FINISHED = 10  # input_state：生成结束
STREAM_CONTENT_TEXT = "text"
STREAM_CONTENT_MARKDOWN = "markdown"


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

    async def prepare_c2c_upload(
        self,
        openid: str,
        file_type: int,
        file_size: int | str,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
        **extra: Any,
    ) -> dict:
        """单聊大文件分片预上传（POST /v2/users/{openid}/upload_prepare）。

        用法同 prepare_group_upload；全部分片完成后携带 upload_id 调
        upload_c2c_file 完成合并。
        """
        return await self._prepare_upload(
            f"/v2/users/{openid}",
            file_type,
            file_size,
            file_name,
            md5,
            sha1,
            md5_10m,
            **extra,
        )

    async def finish_c2c_upload_part(
        self,
        openid: str,
        upload_id: str,
        part_index: int,
        block_size: int | str | None = None,
        md5: str | None = None,
    ) -> dict:
        """单聊分片上传完成确认（POST .../upload_part_finish）。"""
        return await self._finish_upload_part(
            f"/v2/users/{openid}", upload_id, part_index, block_size, md5
        )

    async def post_c2c_stream_message(
        self,
        openid: str,
        content_raw: str = "",
        *,
        stream_msg_id: str | None = None,
        index: int = 0,
        input_state: int = STREAM_GENERATING,
        input_mode: str | None = None,
        content_type: str = STREAM_CONTENT_MARKDOWN,
        msg_id: str | None = None,
        event_id: str | None = None,
        msg_seq: int | None = None,
        is_wakeup: bool | None = None,
        **extra: Any,
    ) -> dict:
        """流式分批发送单聊消息（POST /v2/users/{openid}/stream_messages）。

        每个分片使用相同 stream_msg_id、index 从 0 递增：首片不传
        stream_msg_id，响应的 id 即后续分片要携带的 stream_msg_id；
        以 input_state=STREAM_FINISHED 收尾。input_mode 默认 append
        （分片拼接），replace 时 content_raw 须以上游已下发前缀开头。
        content_type 默认 markdown；msg_id/event_id 二选一为被动回复；
        is_wakeup=True 为召回消息，不校验 msg_id/event_id 有效期。
        """
        body: dict[str, Any] = {
            "index": index,
            "input_state": input_state,
            "content_type": content_type,
        }
        if content_raw:
            body["content_raw"] = content_raw
        if stream_msg_id:
            body["stream_msg_id"] = stream_msg_id
        if input_mode:
            body["input_mode"] = input_mode
        if msg_id:
            body["msg_id"] = msg_id
        elif event_id:
            body["event_id"] = event_id
        if msg_seq is not None:
            body["msg_seq"] = msg_seq
        if is_wakeup is not None:
            body["is_wakeup"] = is_wakeup
        body.update(extra)
        return await self.post(f"/v2/users/{openid}/stream_messages", json=body)

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

    async def prepare_group_upload(
        self,
        group_openid: str,
        file_type: int,
        file_size: int | str,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
        **extra: Any,
    ) -> dict:
        """群聊大文件分片预上传（POST /v2/groups/{group_openid}/upload_prepare）。

        返回 upload_id、分块大小 block_size 与各分片预签名 URL（parts）；
        将文件按 block_size 分片逐片 PUT 到预签名 URL，每片成功后调
        finish_group_upload_part。md5/sha1 为整文件校验值，md5_10m 为
        文件前 10002432 字节（约 10MB）的 MD5。全部分片完成后携带
        upload_id 调 upload_group_file 完成合并。
        """
        return await self._prepare_upload(
            f"/v2/groups/{group_openid}",
            file_type,
            file_size,
            file_name,
            md5,
            sha1,
            md5_10m,
            **extra,
        )

    async def finish_group_upload_part(
        self,
        group_openid: str,
        upload_id: str,
        part_index: int,
        block_size: int | str | None = None,
        md5: str | None = None,
    ) -> dict:
        """群聊分片上传完成确认（POST .../upload_part_finish）。

        每个分片 PUT 到预签名 URL 成功后调用，通知服务端该分片已传完。
        """
        return await self._finish_upload_part(
            f"/v2/groups/{group_openid}", upload_id, part_index, block_size, md5
        )

    async def _upload_v2_file(
        self, base: str, file_type: int, url: str, srv_send_msg: bool
    ) -> dict:
        return await self.post(
            f"{base}/files",
            json={"file_type": file_type, "url": url, "srv_send_msg": srv_send_msg},
        )

    async def _prepare_upload(
        self,
        base: str,
        file_type: int,
        file_size: int | str,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
        **extra: Any,
    ) -> dict:
        # file_size 官方为字符串类型（字节）
        body: dict[str, Any] = {
            "file_type": file_type,
            "file_size": str(file_size),
            "file_name": file_name,
            "md5": md5,
            "sha1": sha1,
            "md5_10m": md5_10m,
        }
        body.update(extra)
        return await self.post(f"{base}/upload_prepare", json=body)

    async def _finish_upload_part(
        self,
        base: str,
        upload_id: str,
        part_index: int,
        block_size: int | str | None,
        md5: str | None,
    ) -> dict:
        body: dict[str, Any] = {"upload_id": upload_id, "part_index": part_index}
        if block_size is not None:
            body["block_size"] = str(block_size)
        if md5 is not None:
            body["md5"] = md5
        return await self.post(f"{base}/upload_part_finish", json=body)

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

    async def generate_url_link(self, callback_data: str | None = None) -> dict:
        """生成机器人分享链接（POST /v2/generate_url_link），返回 {"data": {"url": ...}}。

        用于邀请用户添加机器人为好友；callback_data（≤32 字符）在用户
        通过链接添加时透传给开发者。
        """
        body: dict[str, Any] = {}
        if callback_data:
            body["callback_data"] = callback_data
        return await self.post("/v2/generate_url_link", json=body)
