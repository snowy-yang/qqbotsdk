from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel
from qqbotsdk.model.sub.messages import (
    Keyboard,
    MessageReference,
)


class MessageEmbedField(QQBotBaseModel):
    name: str | None = Field(
        None,
        description="字段名",
    )
    value: str | None = Field(
        None,
        description="字段值",
    )


class MessageEmbedThumbnail(QQBotBaseModel):
    url: str | None = Field(
        None,
        description="缩略图 URL",
    )


class MessageEmbed(QQBotBaseModel):
    title: str | None = Field(
        None,
        description="标题",
    )
    description: str | None = Field(
        None,
        description="描述",
    )
    prompt: str | None = Field(
        None,
        description="消息弹窗内容",
    )
    timestamp: str | None = Field(
        None,
        description="消息创建时间，ISO8601 格式",
    )
    thumbnail: MessageEmbedThumbnail | None = Field(
        None,
        description="缩略图，选填",
    )
    fields: list[MessageEmbedField] | None = Field(
        None,
        description="消息体字段列表",
    )


class MessageArkObjKv(QQBotBaseModel):
    key: str | None = Field(
        None,
        description="键",
    )
    value: str | None = Field(
        None,
        description="值",
    )


class MessageArkObj(QQBotBaseModel):
    obj_kv: list[MessageArkObjKv] | None = Field(
        None,
        description="obj 内的 kv 列表",
    )


class MessageArkKv(QQBotBaseModel):
    key: str | None = Field(
        None,
        description="键",
    )
    value: str | None = Field(
        None,
        description="值",
    )
    obj: list[MessageArkObj] | None = Field(
        None,
        description="数组类型变量使用 obj 嵌套结构",
    )


class MessageArk(QQBotBaseModel):
    template_id: int | None = Field(
        None,
        description="ark 模板 ID，需先申请模板权限",
    )
    kv: list[MessageArkKv] | None = Field(
        None,
        description="模板变量列表，如 [{'key': '#DESC#', 'value': '...'}]",
    )


class MessageMarkdownParams(QQBotBaseModel):
    key: str | None = Field(
        None,
        description="Markdown 模板 key",
    )
    values: list[str] | None = Field(
        None,
        description="模板 key 对应的值；长度为 1 表示单值，大于 1 表示列表参数",
    )


class MessageMarkdown(QQBotBaseModel):
    template_id: int | None = Field(
        None,
        description="Markdown 模板 ID，与 content 互斥",
    )
    params: list[MessageMarkdownParams] | None = Field(
        None,
        description="Markdown 模板参数",
    )
    content: str | None = Field(
        None,
        description="原生 Markdown 内容，与 template_id/params 互斥",
    )


class SendChannelMessagesRequest(QQBotBaseModel):
    content: str | None = Field(
        None,
        description="文本内容，支持内嵌格式；content/embed/ark/image/markdown 至少填一个",
    )
    embed: MessageEmbed | None = Field(
        None,
        description="Embed 消息，一种特殊的 ark",
    )
    ark: MessageArk | None = Field(
        None,
        description="ark 消息，需先申请模板权限",
    )
    image: str | None = Field(
        None,
        description="图片 URL，平台会转存后下发图片消息",
    )
    msg_id: str | None = Field(
        None,
        description="被动回复的消息 ID，5 分钟内有效；不填为主动消息",
    )
    event_id: str | None = Field(
        None,
        description="被动回复的事件 ID，与 msg_id 二选一",
    )
    msg_seq: int | None = Field(
        None,
        description="回复消息的序号，与 msg_id 联合使用，避免相同消息重复发送",
    )
    message_reference: MessageReference | None = Field(
        None,
        description="引用回复。填写后以引用形式展示",
    )
    markdown: MessageMarkdown | None = Field(
        None,
        description="Markdown 消息，与 content 互斥",
    )
    keyboard: Keyboard | None = Field(
        None,
        description="内嵌键盘。短形式只传 id，长形式传 content.rows",
    )


class MessageAttachment(QQBotBaseModel):
    url: str | None = Field(
        None,
        description="下载地址",
    )


class MessageAuthor(QQBotBaseModel):
    id: str | None = Field(
        None,
        description="用户 ID",
    )
    username: str | None = Field(
        None,
        description="用户名",
    )
    avatar: str | None = Field(
        None,
        description="头像 URL",
    )
    bot: bool | None = Field(
        None,
        description="是否为机器人",
    )


class SendChannelMessagesResponse(QQBotBaseModel):
    id: str = Field(
        ...,
        description="消息 ID，可用于后续撤回",
    )
    channel_id: str | None = Field(
        None,
        description="子频道 ID",
    )
    guild_id: str | None = Field(
        None,
        description="频道 ID",
    )
    content: str | None = Field(
        None,
        description="消息内容",
    )
    timestamp: str | None = Field(
        None,
        description="消息创建时间，RFC3339 东八区",
    )
    edited_timestamp: str | None = Field(
        None,
        description="消息编辑时间，RFC3339 东八区",
    )
    mention_everyone: bool | None = Field(
        None,
        description="是否 @全员",
    )
    author: MessageAuthor | None = Field(
        None,
        description="消息创建者",
    )
    attachments: list[MessageAttachment] | None = Field(
        None,
        description="附件列表",
    )
    embeds: list[MessageEmbed] | None = Field(
        None,
        description="embed 列表",
    )
    ark: MessageArk | None = Field(
        None,
        description="ark 消息",
    )
    seq_in_channel: str | None = Field(
        None,
        description="子频道消息 seq，用于同一子频道内排序",
    )
    message_reference: MessageReference | None = Field(
        None,
        description="引用消息对象",
    )
    src_guild_id: str | None = Field(
        None,
        description="私信场景下标识来源频道 ID",
    )


class GetChannelMessagesResponse(SendChannelMessagesResponse):
    pass


class ReactionUser(QQBotBaseModel):
    id: str | None = Field(
        None,
        description="用户 ID",
    )
    username: str | None = Field(
        None,
        description="用户名",
    )
    avatar: str | None = Field(
        None,
        description="头像 URL",
    )
    bot: bool | None = Field(
        None,
        description="是否为机器人",
    )


class GetChannelReactionUsersRequest(QQBotBaseModel):
    cookie: str | None = Field(
        None,
        description="上次请求返回的 cookie，首次不填",
    )
    limit: int | None = Field(
        None,
        description="返回的最大用户数 1-100，默认 20",
    )


class GetChannelReactionUsersResponse(QQBotBaseModel):
    users: list[ReactionUser] | None = Field(
        None,
        description="对该消息做出指定表情表态的用户列表",
    )
    cookie: str | None = Field(
        None,
        description="分页标识，下次请求原样回传",
    )
    is_end: bool | None = Field(
        None,
        description="是否已拉取完毕",
    )


class CreateDmsRequest(QQBotBaseModel):
    recipient_id: str = Field(
        ...,
        description="接收者 ID",
    )
    source_guild_id: str = Field(
        ...,
        description="源频道 ID",
    )


class CreateDmsResponse(QQBotBaseModel):
    guild_id: str = Field(
        ...,
        description="私信会话关联的频道 ID",
    )
    channel_id: str = Field(
        ...,
        description="私信会话关联的子频道 ID",
    )
    create_time: str | None = Field(
        None,
        description="创建私信会话时间戳",
    )


class SendDmsMessagesRequest(SendChannelMessagesRequest):
    pass


class SendDmsMessagesResponse(SendChannelMessagesResponse):
    pass
