"""论坛(话题子频道)与开放论坛事件模型.

覆盖以下事件的事件体 ``d``:

- ``FORUM_THREAD_CREATE`` / ``FORUM_THREAD_UPDATE`` / ``FORUM_THREAD_DELETE``
- ``FORUM_POST_CREATE`` / ``FORUM_POST_DELETE``
- ``FORUM_REPLY_CREATE`` / ``FORUM_REPLY_DELETE``
- ``FORUM_PUBLISH_AUDIT_RESULT``
- ``OPEN_FORUM_THREAD_CREATE`` / ``_UPDATE`` / ``_DELETE``
- ``OPEN_FORUM_POST_CREATE`` / ``OPEN_FORUM_POST_DELETE``
- ``OPEN_FORUM_REPLY_CREATE`` / ``OPEN_FORUM_REPLY_DELETE``

同时建模文档里的论坛对象(Thread / Post / Reply / AuditResult 以及 RichObject /
RichText 等富文本结构).

注意: 文档的事件示例里 ``title`` / ``content`` 是 RichObject 数组, 而
``qqbotsdk.model.guild.content.ForumThreadInfo`` 把这两个字段声明成了字符串,
无法承载事件示例, 所以这里新增 ``EventThreadInfo`` 并单独定义 ``EventThread``
(不继承 ``content.ForumThread``: 它的 ``thread_info`` 类型不兼容, 且
``guild_id`` / ``channel_id`` / ``author_id`` 在事件示例里会被写成整型).
另外文档示例里这三个 ID 字段偶尔是整型, 统一用 ``ForumID`` 归一化成字符串.

参考:

- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/content/forum/forum.html
- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/content/forum/open_forum.html
- https://bot.q.qq.com/wiki/develop/api-v2/server-inter/channel/content/forum/model.html
"""

from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field

from qqbotsdk.model.core import QQBotBaseModel


def _coerce_int_id(value: Any) -> Any:
    """把文档示例里偶发的整型 ID 归一化成字符串."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return value


ForumID = Annotated[str, BeforeValidator(_coerce_int_id)]


class ForumTextInfo(QQBotBaseModel):
    """富文本 - 普通文本."""

    text: str | None = Field(
        default=None,
        description="普通文本内容",
    )


class ForumAtUserInfo(QQBotBaseModel):
    """富文本 - @用户信息."""

    id: ForumID | None = Field(
        default=None,
        description="被 @ 的用户 ID",
    )
    nick: str | None = Field(
        default=None,
        description="用户昵称",
    )


class ForumAtRoleInfo(QQBotBaseModel):
    """富文本 - @身份组信息."""

    role_id: ForumID | None = Field(
        default=None,
        description="身份组 ID, 文档类型为 uint64",
    )
    name: str | None = Field(
        default=None,
        description="身份组名称",
    )
    color: int | None = Field(
        default=None,
        description="身份组颜色值",
    )


class ForumAtGuildInfo(QQBotBaseModel):
    """富文本 - @频道信息."""

    guild_id: ForumID | None = Field(
        default=None,
        description="频道 ID",
    )
    guild_name: str | None = Field(
        default=None,
        description="频道名称",
    )


class ForumAtInfo(QQBotBaseModel):
    """富文本 - @内容."""

    type: Literal[1, 2, 3] | None = Field(
        default=None,
        description="@ 的类型: 1=at 特定人, 2=at 角色组所有人, 3=at 频道所有人",
    )
    user_info: ForumAtUserInfo | None = Field(
        default=None,
        description="被 @ 的用户",
    )
    role_info: ForumAtRoleInfo | None = Field(
        default=None,
        description="被 @ 的身份组",
    )
    guild_info: ForumAtGuildInfo | None = Field(
        default=None,
        description="被 @ 的频道",
    )


class ForumURLInfo(QQBotBaseModel):
    """富文本 - 链接信息."""

    url: str | None = Field(
        default=None,
        description="链接地址",
    )
    display_text: str | None = Field(
        default=None,
        description="链接显示文本",
    )


class ForumEmojiInfo(QQBotBaseModel):
    """富文本 - emoji 信息."""

    id: ForumID | None = Field(
        default=None,
        description="表情 ID, 文档类型为 string",
    )
    type: ForumID | None = Field(
        default=None,
        description="表情类型, 文档类型为 string",
    )
    name: str | None = Field(
        default=None,
        description="名称",
    )
    url: str | None = Field(
        default=None,
        description="链接",
    )


class ForumChannelInfo(QQBotBaseModel):
    """富文本 - 提到的子频道信息."""

    channel_id: ForumID | None = Field(
        default=None,
        description="子频道 ID, 文档类型为 uint64",
    )
    channel_name: str | None = Field(
        default=None,
        description="子频道名称",
    )


class ForumRichObject(QQBotBaseModel):
    """富文本内容, 对应文档的 RichObject 对象."""

    type: Literal[1, 2, 3, 4, 5, 10, 11] | None = Field(
        default=None,
        description="富文本类型: 1=普通文本, 2=at, 3=url, 4=表情, 5=#子频道, 10=视频, 11=图片",
    )
    text_info: ForumTextInfo | None = Field(
        default=None,
        description="文本",
    )
    at_info: ForumAtInfo | None = Field(
        default=None,
        description="@ 内容",
    )
    url_info: ForumURLInfo | None = Field(
        default=None,
        description="链接",
    )
    emoji_info: ForumEmojiInfo | None = Field(
        default=None,
        description="表情",
    )
    channel_info: ForumChannelInfo | None = Field(
        default=None,
        description="提到的子频道",
    )


class ForumTextProps(QQBotBaseModel):
    """富文本 - 文本属性."""

    font_bold: bool | None = Field(
        default=None,
        description="是否加粗",
    )
    italic: bool | None = Field(
        default=None,
        description="是否斜体",
    )
    underline: bool | None = Field(
        default=None,
        description="是否有下划线",
    )


class ForumTextElem(QQBotBaseModel):
    """富文本 - 文本元素."""

    text: str | None = Field(
        default=None,
        description="正文",
    )
    props: ForumTextProps | None = Field(
        default=None,
        description="文本属性",
    )


class ForumPlatImage(QQBotBaseModel):
    """富文本 - 平台图片属性."""

    url: str | None = Field(
        default=None,
        description="架平图片链接",
    )
    width: int | None = Field(
        default=None,
        description="图片宽度",
    )
    height: int | None = Field(
        default=None,
        description="图片高度",
    )
    image_id: str | None = Field(
        default=None,
        description="图片 ID",
    )


class ForumPlatVideo(QQBotBaseModel):
    """富文本 - 平台视频属性."""

    url: str | None = Field(
        default=None,
        description="架平视频链接",
    )
    width: int | None = Field(
        default=None,
        description="视频宽度",
    )
    height: int | None = Field(
        default=None,
        description="视频高度",
    )
    video_id: str | None = Field(
        default=None,
        description="视频 ID",
    )
    duration: int | None = Field(
        default=None,
        description="视频时长",
    )
    cover: ForumPlatImage | None = Field(
        default=None,
        description="视频封面图",
    )


class ForumImageElem(QQBotBaseModel):
    """富文本 - 图片元素."""

    third_url: str | None = Field(
        default=None,
        description="第三方图片链接",
    )
    width_percent: float | None = Field(
        default=None,
        description="宽度比例, 即缩放后在屏幕上显示的比例",
    )


class ForumVideoElem(QQBotBaseModel):
    """富文本 - 视频元素."""

    third_url: str | None = Field(
        default=None,
        description="第三方视频文件链接",
    )


class ForumURLElem(QQBotBaseModel):
    """富文本 - URL 元素."""

    url: str | None = Field(
        default=None,
        description="URL 链接",
    )
    desc: str | None = Field(
        default=None,
        description="URL 描述",
    )


class ForumElem(QQBotBaseModel):
    """富文本 - 元素结构."""

    type: Literal[1, 2, 3, 4] | None = Field(
        default=None,
        description="元素类型: 1=文本, 2=图片, 3=视频, 4=URL",
    )
    text: ForumTextElem | None = Field(
        default=None,
        description="文本元素",
    )
    image: ForumImageElem | None = Field(
        default=None,
        description="图片元素",
    )
    video: ForumVideoElem | None = Field(
        default=None,
        description="视频元素",
    )
    url: ForumURLElem | None = Field(
        default=None,
        description="URL 元素",
    )


class ForumParagraphProps(QQBotBaseModel):
    """富文本 - 段落属性."""

    alignment: Literal[0, 1, 2] | None = Field(
        default=None,
        description="段落对齐方向: 0=左对齐, 1=居中, 2=右对齐",
    )


class ForumParagraph(QQBotBaseModel):
    """富文本 - 段落结构."""

    elems: list[ForumElem] | None = Field(
        default=None,
        description="元素列表",
    )
    props: ForumParagraphProps | None = Field(
        default=None,
        description="段落属性",
    )


class ForumRichText(QQBotBaseModel):
    """富文本内容, 对应文档的 RichText 对象."""

    paragraphs: list[ForumParagraph] | None = Field(
        default=None,
        description="段落列表, 一段一行, 段落内无元素的为空行",
    )


class EventThreadInfo(QQBotBaseModel):
    """帖子事件里的主帖内容, 对应文档的 ThreadInfo 对象."""

    thread_id: ForumID | None = Field(
        default=None,
        description="主帖 ID",
    )
    title: list[ForumRichObject] | None = Field(
        default=None,
        description="帖子标题, 富文本对象数组",
    )
    content: list[ForumRichObject] | None = Field(
        default=None,
        description="帖子内容, 富文本对象数组",
    )
    date_time: str | None = Field(
        default=None,
        description="发表时间, ISO8601 格式",
    )


class EventThread(QQBotBaseModel):
    """主题事件体, 对应文档的 Thread 对象.

    与 ``content.ForumThread`` 字段一致, 但 ``thread_info`` 换成富文本版本,
    且 ``guild_id`` / ``channel_id`` / ``author_id`` 允许整型输入.
    """

    guild_id: ForumID | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: ForumID | None = Field(
        default=None,
        description="子频道 ID",
    )
    author_id: ForumID | None = Field(
        default=None,
        description="作者 ID",
    )
    thread_info: EventThreadInfo | None = Field(
        default=None,
        description="主帖内容",
    )


class EventPostInfo(QQBotBaseModel):
    """帖子事件里的评论内容, 对应文档的 PostInfo 对象."""

    thread_id: ForumID | None = Field(
        default=None,
        description="主题 ID",
    )
    post_id: ForumID | None = Field(
        default=None,
        description="帖子 ID",
    )
    content: list[ForumRichObject] | None = Field(
        default=None,
        description="帖子内容, 富文本对象数组",
    )
    date_time: str | None = Field(
        default=None,
        description="评论时间, ISO8601 格式",
    )


class EventPost(QQBotBaseModel):
    """评论事件体, 对应文档的 Post 对象."""

    guild_id: ForumID | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: ForumID | None = Field(
        default=None,
        description="子频道 ID",
    )
    author_id: ForumID | None = Field(
        default=None,
        description="作者 ID",
    )
    post_info: EventPostInfo | None = Field(
        default=None,
        description="帖子内容",
    )


class EventReplyInfo(QQBotBaseModel):
    """回复事件里的回复内容, 对应文档的 ReplyInfo 对象."""

    thread_id: ForumID | None = Field(
        default=None,
        description="主题 ID",
    )
    post_id: ForumID | None = Field(
        default=None,
        description="帖子 ID",
    )
    reply_id: ForumID | None = Field(
        default=None,
        description="回复 ID",
    )
    content: list[ForumRichObject] | None = Field(
        default=None,
        description="回复内容, 富文本对象数组",
    )
    date_time: str | None = Field(
        default=None,
        description="回复时间, ISO8601 格式",
    )


class EventReply(QQBotBaseModel):
    """回复事件体, 对应文档的 Reply 对象."""

    guild_id: ForumID | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: ForumID | None = Field(
        default=None,
        description="子频道 ID",
    )
    author_id: ForumID | None = Field(
        default=None,
        description="作者 ID",
    )
    reply_info: EventReplyInfo | None = Field(
        default=None,
        description="回复内容",
    )


class EventAuditResult(QQBotBaseModel):
    """论坛帖子审核结果事件体, 对应文档的 AuditResult 对象."""

    guild_id: ForumID | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: ForumID | None = Field(
        default=None,
        description="子频道 ID",
    )
    author_id: ForumID | None = Field(
        default=None,
        description="作者 ID",
    )
    thread_id: ForumID | None = Field(
        default=None,
        description="主题 ID",
    )
    post_id: ForumID | None = Field(
        default=None,
        description="帖子 ID",
    )
    reply_id: ForumID | None = Field(
        default=None,
        description="回复 ID",
    )
    type: Literal[1, 2, 3] | None = Field(
        default=None,
        description="审核类型: 1=帖子, 2=评论, 3=回复",
    )
    result: Literal[0, 1] | None = Field(
        default=None,
        description="审核结果: 0=成功, 1=失败",
    )
    err_msg: str | None = Field(
        default=None,
        description="result 不为 0 时的错误信息",
    )


class EventOpenForum(QQBotBaseModel):
    """开放论坛(OPEN_FORUM_*)事件体.

    文档的开放论坛示例只给出 ``guild_id`` / ``channel_id`` / ``author_id`` 三个
    字段, 没有 thread/post/reply 详情, 因此单独建模.
    """

    guild_id: ForumID | None = Field(
        default=None,
        description="频道 ID",
    )
    channel_id: ForumID | None = Field(
        default=None,
        description="子频道 ID",
    )
    author_id: ForumID | None = Field(
        default=None,
        description="作者 ID",
    )


class ForumThreadCreateEvent(EventThread):
    """FORUM_THREAD_CREATE: 话题子频道内新建主题时触发, intents=FORUMS_EVENT."""


class ForumThreadUpdateEvent(EventThread):
    """FORUM_THREAD_UPDATE: 主题被更新时触发, intents=FORUMS_EVENT."""


class ForumThreadDeleteEvent(EventThread):
    """FORUM_THREAD_DELETE: 主题被删除时触发, intents=FORUMS_EVENT."""


class ForumPostCreateEvent(EventPost):
    """FORUM_POST_CREATE: 主题下新建评论时触发, intents=FORUMS_EVENT."""


class ForumPostDeleteEvent(EventPost):
    """FORUM_POST_DELETE: 评论被删除时触发, intents=FORUMS_EVENT."""


class ForumReplyCreateEvent(EventReply):
    """FORUM_REPLY_CREATE: 评论下新增回复时触发, intents=FORUMS_EVENT."""


class ForumReplyDeleteEvent(EventReply):
    """FORUM_REPLY_DELETE: 回复被删除时触发, intents=FORUMS_EVENT."""


class ForumPublishAuditResultEvent(EventAuditResult):
    """FORUM_PUBLISH_AUDIT_RESULT: 论坛内容审核结果下发时触发, intents=FORUMS_EVENT."""


class OpenForumThreadCreateEvent(EventOpenForum):
    """OPEN_FORUM_THREAD_CREATE: 开放论坛新建主题时触发."""


class OpenForumThreadUpdateEvent(EventOpenForum):
    """OPEN_FORUM_THREAD_UPDATE: 开放论坛主题被更新时触发."""


class OpenForumThreadDeleteEvent(EventOpenForum):
    """OPEN_FORUM_THREAD_DELETE: 开放论坛主题被删除时触发."""


class OpenForumPostCreateEvent(EventOpenForum):
    """OPEN_FORUM_POST_CREATE: 开放论坛新增评论时触发."""


class OpenForumPostDeleteEvent(EventOpenForum):
    """OPEN_FORUM_POST_DELETE: 开放论坛评论被删除时触发."""


class OpenForumReplyCreateEvent(EventOpenForum):
    """OPEN_FORUM_REPLY_CREATE: 开放论坛新增回复时触发."""


class OpenForumReplyDeleteEvent(EventOpenForum):
    """OPEN_FORUM_REPLY_DELETE: 开放论坛回复被删除时触发."""


__all__ = [
    "EventAuditResult",
    "EventOpenForum",
    "EventPost",
    "EventPostInfo",
    "EventReply",
    "EventReplyInfo",
    "EventThread",
    "EventThreadInfo",
    "ForumAtGuildInfo",
    "ForumAtInfo",
    "ForumAtRoleInfo",
    "ForumAtUserInfo",
    "ForumChannelInfo",
    "ForumElem",
    "ForumEmojiInfo",
    "ForumID",
    "ForumImageElem",
    "ForumParagraph",
    "ForumParagraphProps",
    "ForumPlatImage",
    "ForumPlatVideo",
    "ForumPostCreateEvent",
    "ForumPostDeleteEvent",
    "ForumPublishAuditResultEvent",
    "ForumReplyCreateEvent",
    "ForumReplyDeleteEvent",
    "ForumRichObject",
    "ForumRichText",
    "ForumTextElem",
    "ForumTextInfo",
    "ForumTextProps",
    "ForumThreadCreateEvent",
    "ForumThreadDeleteEvent",
    "ForumThreadUpdateEvent",
    "ForumURLElem",
    "ForumURLInfo",
    "ForumVideoElem",
    "OpenForumPostCreateEvent",
    "OpenForumPostDeleteEvent",
    "OpenForumReplyCreateEvent",
    "OpenForumReplyDeleteEvent",
    "OpenForumThreadCreateEvent",
    "OpenForumThreadDeleteEvent",
    "OpenForumThreadUpdateEvent",
]
