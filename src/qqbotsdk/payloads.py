"""事件 payload 的 dataclass 定义与解析。

handler 直接标注具体类型即可拿到解析后的对象（如
`async def on_msg(msg: GroupAtMessage)`）；未收录的事件类型
由 emitter 回退传原始 dict，新增事件只需在这里加 dataclass
并登记到 EVENT_TYPES。
"""

from dataclasses import dataclass, fields
from types import UnionType
from typing import Union, get_args, get_origin


@dataclass(slots=True)
class Author:
    """消息作者。群场景是 member_openid/user_openid，频道场景是 id/username。"""

    id: str | None = None
    user_openid: str | None = None
    member_openid: str | None = None
    username: str | None = None
    bot: bool | None = None


@dataclass(slots=True)
class Ready:
    version: int | None = None
    session_id: str | None = None
    user: dict | None = None
    shard: list[int] | None = None
    intents: int | None = None


@dataclass(slots=True)
class GroupAtMessage:
    """群里 @机器人的消息（GROUP_AT_MESSAGE_CREATE）。"""

    id: str | None = None
    content: str | None = None
    group_openid: str | None = None
    author: Author | None = None
    timestamp: str | None = None

    @property
    def user_openid(self) -> str | None:
        return self.author.member_openid if self.author else None


@dataclass(slots=True)
class C2CMessage:
    """用户单聊消息（C2C_MESSAGE_CREATE）。"""

    id: str | None = None
    content: str | None = None
    author: Author | None = None
    attachments: list[dict] | None = None
    timestamp: str | None = None

    @property
    def user_openid(self) -> str | None:
        return self.author.user_openid if self.author else None


@dataclass(slots=True)
class FriendAdd:
    openid: str | None = None
    event_ts: str | None = None


@dataclass(slots=True)
class FriendDel:
    openid: str | None = None
    event_ts: str | None = None


@dataclass(slots=True)
class GroupAddRobot:
    group_openid: str | None = None
    op_member_openid: str | None = None
    event_ts: str | None = None


@dataclass(slots=True)
class GroupDelRobot:
    group_openid: str | None = None
    op_member_openid: str | None = None
    event_ts: str | None = None


@dataclass(slots=True)
class C2CMsgReject:
    user_openid: str | None = None
    event_ts: str | None = None
    event_status: int | None = None


@dataclass(slots=True)
class C2CMsgReceive:
    user_openid: str | None = None
    event_ts: str | None = None
    event_status: int | None = None


@dataclass(slots=True)
class GroupMsgReject:
    group_openid: str | None = None
    group_manager_openid: str | None = None
    event_ts: str | None = None


@dataclass(slots=True)
class GroupMsgReceive:
    group_openid: str | None = None
    group_manager_openid: str | None = None
    event_ts: str | None = None


@dataclass(slots=True)
class AtMessage:
    """频道 @机器人消息（AT_MESSAGE_CREATE / PUBLIC 与私域共用结构）。"""

    id: str | None = None
    content: str | None = None
    channel_id: str | None = None
    guild_id: str | None = None
    author: Author | None = None
    member: dict | None = None
    timestamp: str | None = None


@dataclass(slots=True)
class DirectMessage:
    """私信消息（DIRECT_MESSAGE_CREATE）。"""

    id: str | None = None
    content: str | None = None
    channel_id: str | None = None
    guild_id: str | None = None
    author: Author | None = None
    member: dict | None = None
    timestamp: str | None = None


@dataclass(slots=True)
class Guild:
    """频道服务器（GUILD_CREATE/UPDATE/DELETE，d 复用同一结构）。"""

    id: str | None = None
    name: str | None = None
    icon: str | None = None
    owner_id: str | None = None
    joined_at: str | None = None


@dataclass(slots=True)
class Channel:
    """子频道（CHANNEL_CREATE/UPDATE/DELETE，d 复用同一结构）。"""

    id: str | None = None
    guild_id: str | None = None
    name: str | None = None
    channel_type: int | None = None
    sub_type: int | None = None
    position: int | None = None
    parent_id: str | None = None
    owner_id: str | None = None
    private_type: int | None = None
    speak_permission: int | None = None


@dataclass(slots=True)
class MessageAudit:
    """消息审核结果（MESSAGE_AUDIT_PASS/REJECT）。"""

    audit_id: str | None = None
    channel_id: str | None = None
    guild_id: str | None = None
    author_id: str | None = None
    message_info: dict | None = None


@dataclass(slots=True)
class MessageReaction:
    """表情表态（MESSAGE_REACTION_ADD/REMOVE）。"""

    guild_id: str | None = None
    channel_id: str | None = None
    user_id: str | None = None
    message_id: str | None = None
    emoji: dict | None = None


@dataclass(slots=True)
class MessageDelete:
    """消息删除（MESSAGE_DELETE / PUBLIC_MESSAGE_DELETE）。"""

    guild_id: str | None = None
    channel_id: str | None = None
    id: str | None = None
    message: dict | None = None
    op_user: dict | None = None


@dataclass(slots=True)
class Interaction:
    """互动（INTERACTION_CREATE）。

    按钮点击（type=11）时 data.resolved.button_data 携带按钮的
    action.data；id 用于 PUT /interactions/{id} 回应（见
    BotApi.respond_interaction）。注意被动回复的 event_id 不取这里的
    id（它是裸 UUID），要取网关帧最外层的 id（Event.event_id，形如
    INTERACTION_CREATE:uuid）——官方文档点名的常见坑。
    """

    id: str | None = None
    type: int | None = None
    scene: str | None = None  # c2c / group / guild
    chat_type: int | None = None  # 0 频道 / 1 群聊 / 2 单聊
    guild_id: str | None = None
    channel_id: str | None = None
    group_openid: str | None = None
    user_openid: str | None = None
    group_member_openid: str | None = None
    data: dict | None = None
    version: int | None = None
    application_id: str | None = None
    timestamp: str | None = None

    @property
    def button_data(self) -> str:
        """被点击按钮的 action.data（即 data.resolved.button_data）。"""
        resolved = (self.data or {}).get("resolved")
        value = resolved.get("button_data") if isinstance(resolved, dict) else None
        return value if isinstance(value, str) else ""


@dataclass(slots=True)
class ForumThread:
    """论坛主题（FORUM_THREAD_CREATE/UPDATE/DELETE）。"""

    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None
    thread_info: dict | None = None


@dataclass(slots=True)
class ForumPost:
    """论坛帖子（FORUM_POST_CREATE/DELETE）。"""

    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None
    post_info: dict | None = None


@dataclass(slots=True)
class ForumReply:
    """论坛评论（FORUM_REPLY_CREATE/DELETE）。"""

    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None
    reply_info: dict | None = None


@dataclass(slots=True)
class AudioAction:
    """音频动作（AUDIO_START/FINISH/ON_MIC/OFF_MIC）。"""

    guild_id: str | None = None
    channel_id: str | None = None
    audio_info: dict | None = None


# 事件名（t）→ payload 类型
EVENT_TYPES: dict[str, type] = {
    "READY": Ready,
    "GROUP_AT_MESSAGE_CREATE": GroupAtMessage,
    "C2C_MESSAGE_CREATE": C2CMessage,
    "FRIEND_ADD": FriendAdd,
    "FRIEND_DEL": FriendDel,
    "GROUP_ADD_ROBOT": GroupAddRobot,
    "GROUP_DEL_ROBOT": GroupDelRobot,
    "C2C_MSG_REJECT": C2CMsgReject,
    "C2C_MSG_RECEIVE": C2CMsgReceive,
    "GROUP_MSG_REJECT": GroupMsgReject,
    "GROUP_MSG_RECEIVE": GroupMsgReceive,
    "AT_MESSAGE_CREATE": AtMessage,
    "DIRECT_MESSAGE_CREATE": DirectMessage,
    "GUILD_CREATE": Guild,
    "GUILD_UPDATE": Guild,
    "GUILD_DELETE": Guild,
    "CHANNEL_CREATE": Channel,
    "CHANNEL_UPDATE": Channel,
    "CHANNEL_DELETE": Channel,
    "MESSAGE_AUDIT_PASS": MessageAudit,
    "MESSAGE_AUDIT_REJECT": MessageAudit,
    "MESSAGE_REACTION_ADD": MessageReaction,
    "MESSAGE_REACTION_REMOVE": MessageReaction,
    "MESSAGE_DELETE": MessageDelete,
    "PUBLIC_MESSAGE_DELETE": MessageDelete,
    "INTERACTION_CREATE": Interaction,
    "FORUM_THREAD_CREATE": ForumThread,
    "FORUM_THREAD_UPDATE": ForumThread,
    "FORUM_THREAD_DELETE": ForumThread,
    "FORUM_POST_CREATE": ForumPost,
    "FORUM_POST_DELETE": ForumPost,
    "FORUM_REPLY_CREATE": ForumReply,
    "FORUM_REPLY_DELETE": ForumReply,
    "AUDIO_START": AudioAction,
    "AUDIO_FINISH": AudioAction,
    "AUDIO_ON_MIC": AudioAction,
    "AUDIO_OFF_MIC": AudioAction,
}

# 全部已知 payload 类型，供 emitter 按参数标注识别
PAYLOAD_TYPES: frozenset[type] = frozenset(EVENT_TYPES.values())


def _is_author_type(annotation: object) -> bool:
    if annotation is Author:
        return True
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        return Author in get_args(annotation)
    return False


def _build(cls: type, d: dict) -> object:
    kwargs = {}
    for f in fields(cls):
        if f.name not in d:
            continue
        value = d[f.name]
        if isinstance(value, dict) and _is_author_type(f.type):
            value = _build(Author, value)
        kwargs[f.name] = value
    return cls(**kwargs)


def parse_event(t: str | None, d: dict) -> object:
    """把事件 d 解析为对应 dataclass；未收录的事件类型原样返回 dict。"""
    if t and (cls := EVENT_TYPES.get(t)) and isinstance(d, dict):
        return _build(cls, d)
    return d
