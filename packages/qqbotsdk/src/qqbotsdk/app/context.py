"""事件处理上下文: 把网关帧与解析好的事件对象一起交给 handler.

``Context`` 由 :class:`qqbotsdk.app.bot.Bot` 在分发每个 Dispatch 事件时创建,
handler / 中间件都拿它当唯一入参, 并通过它回消息::

    @bot.on_message()
    async def echo(ctx: Context) -> None:
        await ctx.reply(ctx.event.content or "")

回复的锚点规则见 :meth:`Context.reply`.
"""

from typing import TYPE_CHECKING, Any, Final, cast

from qqbotsdk.api import user as user_api
from qqbotsdk.api.group import messages as group_messages
from qqbotsdk.app.api import SceneApi
from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.group.messages import SendGroupMessagesRequest
from qqbotsdk.model.sub.messages import Keyboard
from qqbotsdk.model.user.messages import SendUserMessagesRequest
from qqbotsdk.ws.payload import GatewayPayload

if TYPE_CHECKING:
    from qqbotsdk.app.bot import Bot

# 可以被动回复的群聊消息事件
GROUP_REPLY_EVENTS: Final = frozenset(
    {"GROUP_AT_MESSAGE_CREATE", "GROUP_MESSAGE_CREATE"}
)

# 可以被动回复的单聊消息事件
C2C_REPLY_EVENTS: Final = frozenset({"C2C_MESSAGE_CREATE"})

# 纯文本消息
TEXT_MESSAGE_TYPE: Final = 0


def _str_field(data: Any, key: str) -> str | None:
    """从事件的原始 ``d`` 里取一个非空字符串字段, 取不到时返回 None."""
    if not isinstance(data, dict):
        return None
    mapping = cast("dict[str, Any]", data)
    value = mapping.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _request_body(
    content: str,
    *,
    event_id: str | None,
    msg_id: str | None,
    msg_seq: int | None,
    keyboard: Keyboard | None = None,
) -> dict[str, Any]:
    """拼纯文本消息的请求体.

    ``event_id`` 与 ``msg_id`` 互斥: 有事件 ID 时只填 ``event_id``, 否则才填
    ``msg_id``; 主动消息两者都不填.

    用字典加 ``model_validate`` 而不是直接构造 ``SendXxxMessagesRequest``,
    因为 pyright 识别不到那些 ``Field(None, ...)`` 的默认值, 直接构造会报错.
    """
    body: dict[str, Any] = {"msg_type": TEXT_MESSAGE_TYPE, "content": content}
    if event_id is not None:
        body["event_id"] = event_id
    elif msg_id is not None:
        body["msg_id"] = msg_id
    if msg_seq is not None:
        body["msg_seq"] = msg_seq
    if keyboard is not None:
        body["keyboard"] = keyboard
    return body


class Context:
    """一次事件处理的可变上下文.

    Attributes:
        bot: 触发本次处理的 Bot 实例, 可用它取全局状态或停止机器人.
        payload: 原始网关数据包, 里面的 ``id`` 是被动回复用的事件 ID.
        event: 按 ``payload.t`` 解析出来的事件模型, 未建模或解析失败时为 None.
        state: 本次处理内可自由读写的字典, 中间件可以用它往上挂数据传给 handler,
            不需要就当作不存在.
    """

    __slots__ = ("_api", "bot", "event", "payload", "state")

    def __init__(
        self,
        bot: "Bot",
        payload: GatewayPayload,
        event: QQBotBaseModel | None = None,
    ) -> None:
        self.bot = bot
        self.payload = payload
        self.event = event
        self.state: dict[str, Any] = {}
        self._api: SceneApi | None = None

    def __repr__(self) -> str:
        return (
            f"Context(event_name={self.event_name!r}, "
            f"event={type(self.event).__name__})"
        )

    @property
    def event_name(self) -> str | None:
        """事件名, 即网关帧里的 ``t``."""
        return self.payload.t

    @property
    def api(self) -> SceneApi:
        """场景门面, 首次访问时才构造.

        用它一行完成发消息 / 撤回 / 上传 / 审批 / 互动回包::

            await ctx.api.send("文本")
            await ctx.api.reply("收到")
            await ctx.api.ack_interaction(0)
        """
        if self._api is None:
            self._api = SceneApi(self)
        return self._api

    @property
    def group_openid(self) -> str | None:
        """群 OpenID: 仅有群聊场景的事件才有值."""
        value = getattr(self.event, "group_openid", None)
        if isinstance(value, str) and value:
            return value
        return _str_field(self.payload.d, "group_openid")

    @property
    def user_openid(self) -> str | None:
        """用户 OpenID: 单聊取 ``author.user_openid``, 其它事件依次尝试常见字段."""
        author = getattr(self.event, "author", None)
        value = getattr(author, "user_openid", None)
        if isinstance(value, str) and value:
            return value
        for key in ("user_openid", "openid"):
            candidate = getattr(self.event, key, None)
            if not isinstance(candidate, str) or not candidate:
                candidate = _str_field(self.payload.d, key)
            if isinstance(candidate, str) and candidate:
                return candidate
        return None

    def _anchor_ids(self) -> tuple[str | None, str | None]:
        """返回 ``(event_id, msg_id)``, 前者取信封 ``payload.id``, 后者取 ``d.id``."""
        event_id = self.payload.id or None
        message_id = getattr(self.event, "id", None)
        if not isinstance(message_id, str) or not message_id:
            message_id = _str_field(self.payload.d, "id")
        return event_id, message_id

    def _reply_target(self) -> tuple[str, str] | None:
        """被动回复的目标: 返回 ``(场景, openid)``, 不可回复时返回 None."""
        event_name = self.payload.t or ""
        if event_name in GROUP_REPLY_EVENTS:
            group_openid = self.group_openid
            if group_openid:
                return "group", group_openid
            return None
        if event_name in C2C_REPLY_EVENTS:
            user_openid = self.user_openid
            if user_openid:
                return "user", user_openid
            return None
        return None

    async def reply(
        self,
        content: str,
        *,
        msg_seq: int | None = None,
        keyboard: Keyboard | None = None,
        seq_key: str | None = None,
    ) -> str | None:
        """被动回复一条文本消息, 返回新消息 id.

        只支持消息类事件: ``GROUP_AT_MESSAGE_CREATE`` / ``GROUP_MESSAGE_CREATE``
        走群聊接口(目标取 ``d.group_openid``), ``C2C_MESSAGE_CREATE`` 走单聊接口
        (目标取 ``d.author.user_openid``); 其它事件返回 None.

        锚点规则是**事件 ID 优先**:

        1. 信封 ``payload.id`` 有值: 只填 ``event_id``, 不填 ``msg_id``;
        2. 信封没有 id: 回退到事件体 ``payload.d.id``, 只填 ``msg_id``;
        3. 两个都取不到: 返回 None, 不会悄悄退化成消耗主动推送频次的主动消息.

        ``msg_seq`` 用于同一锚点上的多条回复去重(平台对同一个 msg_id + msg_seq
        重复发送会返回 40054005): 不传时由 Bot 按锚点自增(首次 1, 第二次 2),
        传了则以传入值为准, 并把该锚点的计数推进到该值. 平台上限是群聊 5 次、
        单聊 4 次, 超出会被拒发.

        ``keyboard`` 是内嵌键盘(可带按钮), 省略则不带键盘. 群聊与单聊共用同一种
        键盘结构, 因此这里直接透传; 用它就能在被动回复里带上按钮而不用绕开框架
        直连 ``send_group_messages``::

            await ctx.reply("来答题", keyboard=keyboard)

        ``seq_key`` 只影响计数用哪个键, 省略时用锚点本身. 如果你自己拼请求直连
        ``send_group_messages`` 发过一条被动回复, 先 ``bot.next_msg_seq(锚点)``
        登记, 或把那次也算成同一个 ``seq_key``, 就不会撞上 40054005.
        """
        target = self._reply_target()
        if target is None:
            return None
        event_id, message_id = self._anchor_ids()
        anchor = event_id or message_id
        if anchor is None:
            return None
        seq = self.bot.next_msg_seq(anchor, msg_seq, seq_key=seq_key)
        body = _request_body(
            content,
            event_id=event_id,
            msg_id=None if event_id is not None else message_id,
            msg_seq=seq,
            keyboard=keyboard,
        )
        return await _send_to(*target, body)

    async def send(self, content: str) -> str | None:
        """发一条主动消息(不带 ``event_id`` / ``msg_id``), 返回新消息 id.

        目标优先取群 OpenID, 其次取用户 OpenID; 都取不到时返回 None.
        主动消息受平台推送频次限制, 能用 :meth:`reply` 就不要用这个.
        """
        openid: str | None = None
        scene = "group"
        group_openid = self.group_openid
        if group_openid:
            openid = group_openid
        else:
            scene = "user"
            openid = self.user_openid
        if not openid:
            return None
        body = _request_body(content, event_id=None, msg_id=None, msg_seq=None)
        return await _send_to(scene, openid, body)


async def _send_to(scene: str, openid: str, body: dict[str, Any]) -> str:
    """按场景调用群聊或单聊发送接口, 返回新消息 id."""
    if scene == "group":
        response = await group_messages.send_group_messages(
            openid,
            SendGroupMessagesRequest.model_validate(body),
        )
        return response.id
    user_response = await user_api.send_user_messages(
        openid,
        SendUserMessagesRequest.model_validate(body),
    )
    return user_response.id


__all__ = [
    "C2C_REPLY_EVENTS",
    "GROUP_REPLY_EVENTS",
    "Context",
]
