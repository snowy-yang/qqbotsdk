"""场景绑定的高层门面: ``ctx.api``.

handler 里不用再自己判断群聊/单聊、拼请求模型、算分片摘要, 一行就够::

    @bot.on_message()
    async def handler(ctx: Context) -> None:
        await ctx.api.reply("收到")
        await ctx.api.send_markdown("**加粗** 的文本")
        await ctx.api.ack_interaction(0)

场景判定见 :attr:`SceneApi.scene`: 事件体里有 ``group_openid`` 就是群聊, 单聊
消息(``author.user_openid``)是单聊, 其余事件属于 ``"other"``, 此时除
:meth:`SceneApi.send` 之外的所有场景方法都会抛 ``ValueError``.

关于「好友申请」: QQ 没有好友申请审核接口, ``FRIEND_ADD`` 只是**通知**(用户
添加机器人后已经是好友), 所以这里既没有 ``accept_friend`` 也没有
``decline_friend``; 机器人能审批的只有**入群申请**(``GROUP_JOIN_REQUEST``),
见 :meth:`SceneApi.approve_join_request` / :meth:`SceneApi.decline_join_request`.
"""

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from loguru import logger

from qqbotsdk.api import interaction as interaction_api
from qqbotsdk.api import user as user_api
from qqbotsdk.api.core import session
from qqbotsdk.api.group import join_request as join_request_api
from qqbotsdk.api.group import messages as group_messages
from qqbotsdk.errors import QQBotError
from qqbotsdk.model.group.join_request import ReviewGroupJoinRequest
from qqbotsdk.model.group.messages import (
    SendGroupMessagesRequest,
    UploadGroupFileRequest,
)
from qqbotsdk.model.interaction import ConfirmInteractionsRequest
from qqbotsdk.model.sub.messages import (
    Keyboard,
    MediaInfo,
    MessageCard,
    MessageCardContent,
    MessageMarkdown,
)
from qqbotsdk.model.sub.upload import (
    UploadPart,
    UploadPartFinishRequest,
    UploadPrepareRequest,
    UploadPrepareResponse,
)
from qqbotsdk.model.user.messages import SendUserMessagesRequest, UploadUserFileRequest

if TYPE_CHECKING:
    from qqbotsdk.app.context import Context

Scene = Literal["group", "c2c", "other"]
"""场景: 群聊 / 单聊 / 其它(既没有群 OpenID 也没有单聊用户 OpenID)."""

INTERACTION_EVENT: str = "INTERACTION_CREATE"
"""互动事件名."""

INTERACTION_ID_PREFIX: str = "INTERACTION_CREATE:"
"""互动回包接口要的 id 不带该前缀, 少数推送会带上, 这里统一剥掉."""

IMAGE_FILE_TYPE: int = 1
"""上传接口的文件类型: 1=图片."""

MD5_10M_BYTES: int = 10002432
"""``md5_10m`` 取文件前 10002432 字节(约 10MB)的 md5."""

_OTHER_SCENE_MESSAGE: str = (
    "当前事件既没有 group_openid 也没有单聊 author.user_openid, 无法确定发送场景; "
    "请在群聊或单聊消息事件里调用"
)


def _str_field(data: Any, key: str) -> str | None:
    """从事件的原始 ``d`` 里取一个非空字符串字段, 取不到时返回 None."""
    if not isinstance(data, dict):
        return None
    mapping = cast("dict[str, Any]", data)
    value = mapping.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _nested_str_field(data: Any, outer: str, inner: str) -> str | None:
    """取 ``data[outer][inner]`` 形式的字符串字段."""
    if not isinstance(data, dict):
        return None
    mapping = cast("dict[str, Any]", data)
    nested = mapping.get(outer)
    if not isinstance(nested, dict):
        return None
    nested_mapping = cast("dict[str, Any]", nested)
    value = nested_mapping.get(inner)
    if isinstance(value, str) and value:
        return value
    return None


def _int_or_none(value: str | None) -> int | None:
    """把 ``block_size`` 之类的字符串字段转成 int, 解析不了返回 None."""
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _even_block_size(total: int, count: int) -> int:
    """响应没给分片大小时按分片数均分, 至少 1 字节."""
    if count <= 0:
        return max(total, 1)
    return max((total + count - 1) // count, 1)


def _part_index(part: UploadPart) -> int:
    """分片排序用的 index, 缺失时排在最前面并保持原有相对顺序."""
    return part.index if part.index is not None else 0


async def _send(scene: Scene, openid: str, body: dict[str, Any]) -> str:
    """按场景调用群聊或单聊发送接口, 返回新消息 id."""
    if scene == "group":
        group_response = await group_messages.send_group_messages(
            openid,
            SendGroupMessagesRequest.model_validate(body),
        )
        return group_response.id
    user_response = await user_api.send_user_messages(
        openid,
        SendUserMessagesRequest.model_validate(body),
    )
    return user_response.id


class SceneApi:
    """绑定当前事件的场景门面, 通过 ``ctx.api`` 获取.

    所有 ``send_*`` 都是**主动消息**(不带 ``event_id`` / ``msg_id``), 受平台推送
    频次限制; 被动回复请用 :meth:`reply`, 它走 ``Context.reply`` 的锚点逻辑.

    Args:
        ctx: 当前事件的处理上下文.
    """

    __slots__ = ("_ctx",)

    def __init__(self, ctx: "Context") -> None:
        self._ctx = ctx

    def __repr__(self) -> str:
        return f"SceneApi(scene={self.scene!r})"

    @property
    def scene(self) -> Scene:
        """场景: 事件体里有 ``group_openid`` 算群聊, 有 ``author.user_openid`` 算单聊."""
        if self._ctx.group_openid:
            return "group"
        if _nested_str_field(self._ctx.payload.d, "author", "user_openid"):
            return "c2c"
        # FRIEND_ADD / C2C_MSG_RECEIVE 这类事件体只有顶层 openid, 同样视为单聊
        if _str_field(self._ctx.payload.d, "openid"):
            return "c2c"
        return "other"

    def _target(self) -> tuple[Scene, str]:
        """返回 ``(场景, openid)``; 场景不明确时抛 ``ValueError``."""
        scene = self.scene
        if scene == "group":
            openid = self._ctx.group_openid
        elif scene == "c2c":
            openid = self._ctx.user_openid or _str_field(self._ctx.payload.d, "openid")
        else:
            raise ValueError(_OTHER_SCENE_MESSAGE)
        if not openid:
            raise ValueError(_OTHER_SCENE_MESSAGE)
        return scene, openid

    def _group_openid(self) -> str:
        """群聊专用方法的 openid, 非群聊事件抛 ``ValueError``."""
        scene, openid = self._target()
        if scene != "group":
            raise ValueError("该操作只能在群聊事件里调用")
        return openid

    # ------------------------------------------------------------ 发消息

    async def send(self, content: str, *, keyboard: Keyboard | None = None) -> str:
        """发一条主动文本消息(``msg_type=0``), 返回消息 id.

        Args:
            content: 文本内容.
            keyboard: 内嵌键盘(可带按钮), 省略则不带键盘.
        """
        scene, openid = self._target()
        body: dict[str, Any] = {"msg_type": 0, "content": content}
        if keyboard is not None:
            body["keyboard"] = keyboard
        return await _send(scene, openid, body)

    async def send_markdown(
        self,
        content: str,
        *,
        keyboard: Keyboard | None = None,
    ) -> str:
        """发一条 Markdown 消息(``msg_type=2``), 返回消息 id.

        Args:
            content: Markdown 内容.
            keyboard: 内嵌键盘(按钮一般挂在 Markdown 消息上).
        """
        scene, openid = self._target()
        markdown = MessageMarkdown.model_validate({"content": content})
        body: dict[str, Any] = {"msg_type": 2, "markdown": markdown}
        if keyboard is not None:
            body["keyboard"] = keyboard
        return await _send(scene, openid, body)

    async def send_card(
        self,
        *,
        title: str,
        description: str,
        url: str,
        pic_url: str,
    ) -> str:
        """发一条图文卡片消息(``msg_type=8``), 返回消息 id.

        Args:
            title: 卡片标题, 1-50 字符.
            description: 卡片描述, 1-200 字符.
            url: 跳转链接, 必须是 https, 不超过 1024 字符.
            pic_url: 封面图链接, 必须是 https, 不超过 1024 字符.
        """
        scene, openid = self._target()
        card = MessageCard.model_validate(
            {
                "type": "tuwen",
                "content": MessageCardContent.model_validate(
                    {
                        "title": title,
                        "description": description,
                        "url": url,
                        "pic_url": pic_url,
                    }
                ),
            }
        )
        return await _send(scene, openid, {"msg_type": 8, "card": card})

    async def send_media(self, file_info: str, *, content: str = "") -> str:
        """发一条富媒体消息(``msg_type=7``), 返回消息 id.

        Args:
            file_info: 上传接口返回的 ``file_info``.
            content: 附带文本, 留空则只发媒体.
        """
        scene, openid = self._target()
        body: dict[str, Any] = {
            "msg_type": 7,
            "media": MediaInfo.model_validate({"file_info": file_info}),
        }
        if content:
            body["content"] = content
        return await _send(scene, openid, body)

    async def reply(
        self,
        content: str,
        *,
        msg_seq: int | None = None,
        keyboard: Keyboard | None = None,
        seq_key: str | None = None,
    ) -> str | None:
        """被动回复一条文本消息, 直接委托 :meth:`Context.reply`.

        锚点(event_id 优先, 其次 msg_id)与 msg_seq 自增都在 Context / Bot 里,
        这里不重复实现; 不可回复的事件返回 None.

        Args:
            content: 文本内容.
            msg_seq: 显式指定序号; 省略则由 Bot 按锚点自增.
            keyboard: 内嵌键盘, 省略则不带键盘.
            seq_key: 计数用的键, 省略时用锚点本身.
        """
        return await self._ctx.reply(
            content,
            msg_seq=msg_seq,
            keyboard=keyboard,
            seq_key=seq_key,
        )

    async def recall(self, message_id: str) -> None:
        """撤回一条消息: 群聊走群撤回接口, 单聊走单聊撤回接口."""
        scene, openid = self._target()
        if scene == "group":
            await group_messages.recall_group_messages(openid, message_id)
            return
        await user_api.recall_user_messages(openid, message_id)

    # ------------------------------------------------------------ 上传

    async def upload_image(self, path: str | Path) -> str:
        """上传一张图片, 返回可以直接发给 ``send_media`` 的 ``file_info``.

        流程: 读文件 -> 算 ``md5`` / ``sha1`` / ``md5_10m`` (前 10002432 字节的
        md5, 十六进制) -> 预上传拿 ``upload_id`` 与分片预签名 URL -> 逐片 HTTP PUT
        -> 通知服务端该分片完成 -> 合并文件拿 ``file_info``. 文件小于一个分片时
        只传一片.

        Args:
            path: 本地图片路径.

        Raises:
            ValueError: 当前事件不是群聊/单聊事件.
            QQBotError: 预上传响应缺少分片信息, 或合并后没有返回 ``file_info``.
        """
        scene, openid = self._target()
        file_path = Path(path)
        data = file_path.read_bytes()
        prepare = UploadPrepareRequest.model_validate(
            {
                "file_type": IMAGE_FILE_TYPE,
                "file_size": str(len(data)),
                "file_name": file_path.name,
                "md5": hashlib.md5(data).hexdigest(),
                "sha1": hashlib.sha1(data).hexdigest(),
                "md5_10m": hashlib.md5(data[:MD5_10M_BYTES]).hexdigest(),
            }
        )
        if scene == "group":
            prepared = await group_messages.prepare_group_upload(openid, prepare)
        else:
            prepared = await user_api.prepare_user_upload(openid, prepare)
        await self._upload_parts(scene, openid, data, prepared)

        upload_body = {
            "upload_id": prepared.upload_id,
            "file_type": IMAGE_FILE_TYPE,
            "file_name": file_path.name,
        }
        if scene == "group":
            uploaded = await group_messages.upload_group_file(
                openid,
                UploadGroupFileRequest.model_validate(upload_body),
            )
        else:
            uploaded = await user_api.upload_user_file(
                openid,
                UploadUserFileRequest.model_validate(upload_body),
            )
        if not uploaded.file_info:
            raise QQBotError("上传完成但服务端没有返回 file_info")
        return uploaded.file_info

    async def _upload_parts(
        self,
        scene: Scene,
        openid: str,
        data: bytes,
        prepared: UploadPrepareResponse,
    ) -> None:
        """逐个分片上传并通知服务端, 分片顺序以 ``parts`` 里的 index 为准."""
        parts = prepared.parts or []
        if not parts:
            raise QQBotError("预上传响应缺少分片列表, 无法上传")
        ordered = sorted(parts, key=_part_index)
        upload_id = prepared.upload_id or ""
        fallback_block = _int_or_none(prepared.block_size)
        offset = 0
        for position, part in enumerate(ordered):
            block_size = (
                _int_or_none(part.block_size)
                or fallback_block
                or _even_block_size(len(data), len(parts))
            )
            chunk = data[offset : offset + block_size]
            offset += len(chunk)
            presigned_url = part.presigned_url
            if not presigned_url:
                raise QQBotError("预上传响应里有分片缺少 presigned_url")
            async with session.put(presigned_url, data=chunk) as response:
                await response.read()
            finish = UploadPartFinishRequest.model_validate(
                {
                    "upload_id": upload_id,
                    "part_index": part.index if part.index is not None else position,
                    "block_size": str(len(chunk)),
                    "md5": hashlib.md5(chunk).hexdigest(),
                }
            )
            logger.debug(
                f"已上传分片：index={finish.part_index} size={len(chunk)} scene={scene}"
            )
            if scene == "group":
                await group_messages.finish_group_upload_part(openid, finish)
            else:
                await user_api.finish_user_upload_part(openid, finish)

    # ------------------------------------------------------------ 入群申请审批

    async def approve_join_request(
        self,
        member_openid: str | None = None,
        *,
        join_request_id: str | None = None,
    ) -> None:
        """通过一条入群申请.

        Args:
            member_openid: 申请人 openid; 省略时从当前 ``GROUP_JOIN_REQUEST``
                事件体里取.
            join_request_id: 申请 ID; 省略时由事件里携带的 ``join_request_id``
                由服务端按 member 匹配, 建议从事件里取.

        Raises:
            ValueError: 当前不是群聊事件, 或者拿不到申请人 openid.

        Notes:
            ``FRIEND_ADD`` 是好友通知(用户添加后已经是好友), QQ 没有好友申请
            审核接口, 不要在这里找 ``accept_friend``.
        """
        await self._review("approve", member_openid, join_request_id=join_request_id)

    async def decline_join_request(
        self,
        member_openid: str | None = None,
        *,
        reject_reason: str | None = None,
        add_to_blacklist: bool = False,
        join_request_id: str | None = None,
    ) -> None:
        """拒绝一条入群申请.

        Args:
            member_openid: 申请人 openid; 省略时从当前 ``GROUP_JOIN_REQUEST``
                事件体里取.
            reject_reason: 拒绝理由.
            add_to_blacklist: 是否同时把该用户加入群黑名单.
            join_request_id: 申请 ID.

        Raises:
            ValueError: 当前不是群聊事件, 或者拿不到申请人 openid.
        """
        await self._review(
            "decline",
            member_openid,
            join_request_id=join_request_id,
            reject_reason=reject_reason,
            add_to_blacklist=add_to_blacklist,
        )

    async def _review(
        self,
        op: Literal["approve", "decline"],
        member_openid: str | None,
        *,
        join_request_id: str | None = None,
        reject_reason: str | None = None,
        add_to_blacklist: bool = False,
    ) -> None:
        """审批入群申请的公共实现."""
        openid = self._group_openid()
        target_member = member_openid or self._event_member_openid()
        if not target_member:
            raise ValueError("member_openid 未提供, 且当前事件体里取不到 member_openid")
        body: dict[str, Any] = {"op": op}
        if join_request_id is not None:
            body["join_request_id"] = join_request_id
        if reject_reason is not None:
            body["reject_reason"] = reject_reason
        if op == "decline":
            body["add_to_member_blacklist"] = add_to_blacklist
        await join_request_api.review_group_join_request(
            openid,
            target_member,
            ReviewGroupJoinRequest.model_validate(body),
        )

    def _event_member_openid(self) -> str | None:
        """从当前事件体里取申请人 openid."""
        value = getattr(self._ctx.event, "member_openid", None)
        if isinstance(value, str) and value:
            return value
        return _str_field(self._ctx.payload.d, "member_openid")

    # ------------------------------------------------------------ 互动回包

    async def ack_interaction(self, code: int = 0) -> None:
        """回应消息按钮 / 快捷菜单互动, 否则客户端会一直 loading 直到超时.

        Args:
            code: 回调结果. 0=成功, 1=操作失败, 2=操作频繁, 3=重复操作,
                4=没有权限, 5=仅管理员操作; 其它值会被 pydantic 拒绝.

        Raises:
            ValueError: 当前事件不是 ``INTERACTION_CREATE``, 或者事件里没有 id.

        Notes:
            只有 ``type=11``(消息按钮) 与 ``type=12``(快捷菜单) 需要回应, 其它
            互动类型(消息反馈 / 清空会话 / 授权等)不需要也不应该调用本方法.
            ``interaction_id`` 取自事件的 ``d.id``, 并剥掉可能存在的
            ``INTERACTION_CREATE:`` 前缀.
        """
        if self._ctx.event_name != INTERACTION_EVENT:
            raise ValueError(
                f"ack_interaction 只能在 {INTERACTION_EVENT} 事件里调用, "
                f"当前事件是 {self._ctx.event_name}"
            )
        interaction_id = self._interaction_id()
        if not interaction_id:
            raise ValueError("当前互动事件体里没有 id, 无法回应")
        await interaction_api.confirm_interactions(
            interaction_id,
            ConfirmInteractionsRequest.model_validate({"code": code}),
        )

    def _interaction_id(self) -> str | None:
        """互动回包用的 id: 事件体 ``d.id``, 去掉 ``INTERACTION_CREATE:`` 前缀."""
        value = getattr(self._ctx.event, "id", None)
        if not isinstance(value, str) or not value:
            value = _str_field(self._ctx.payload.d, "id")
        if not value:
            return None
        return value.removeprefix(INTERACTION_ID_PREFIX)


__all__ = [
    "IMAGE_FILE_TYPE",
    "INTERACTION_EVENT",
    "INTERACTION_ID_PREFIX",
    "MD5_10M_BYTES",
    "Scene",
    "SceneApi",
]
