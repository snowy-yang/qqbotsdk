from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel
from qqbotsdk.model.sub.messages import (
    Keyboard,
    MediaInfo,
    MessageCard,
    MessageExtInfo,
    MessageMarkdown,
    MessageReference,
    MessageSendRequestBase,
)
from qqbotsdk.model.sub.upload import UploadPrepareResponse


class SendGroupMessagesRequest(MessageSendRequestBase):
    """发送群聊消息请求.

    ``msg_type`` 可省略: 会按填入的内容字段自动推导(``content``→0、
    ``markdown``→2、``media``→7、``card``→8), 并校验内容字段互斥.
    """

    msg_type: Literal[0, 2, 7, 8] | None = Field(
        default=None,
        description="消息类型：0=纯文本(content)，2=Markdown(markdown)，7=富媒体(media)，8=图文卡片(card)",
    )
    content: str | None = Field(
        default=None,
        description="文本内容。msg_type=0 时为全文；传了 markdown 后此字段必须为空",
    )
    markdown: MessageMarkdown | None = Field(
        default=None,
        description="Markdown 消息。msg_type=2 时必填；填写后 content 必须为空",
    )
    keyboard: Keyboard | None = Field(
        default=None,
        description="内嵌键盘。短形式只传 id，长形式传 content.rows",
    )
    msg_id: str | None = Field(
        default=None,
        description="被动回复的消息 ID，从 GROUP_AT_MESSAGE_CREATE 等事件的 d.id 获取，5 分钟内有效",
    )
    event_id: str | None = Field(
        default=None,
        description="被动回复的事件 ID，从事件最外层的 id 获取，与 msg_id 二选一",
    )
    msg_seq: int | None = Field(
        default=None,
        description="回复消息的序号，与 msg_id 联合使用，避免相同消息 id 重复发送，不填默认是 1",
    )
    media: MediaInfo | None = Field(
        default=None,
        description="富媒体消息。msg_type=7 时填写，file_info 来自群聊富媒体上传接口",
    )
    message_reference: MessageReference | None = Field(
        default=None,
        description="引用回复。填写后以引用形式展示，关联上下文",
    )
    card: MessageCard | None = Field(
        default=None,
        description="图文卡片消息。msg_type=8 时必须填写",
    )


class SendGroupMessagesResponse(QQBotBaseModel):
    id: str = Field(
        ...,
        description="消息 ID，可用于后续撤回",
    )
    timestamp: str = Field(
        ...,
        description="发送时间，RFC3339 东八区",
    )
    ext_info: MessageExtInfo | None = Field(
        default=None,
        description="扩展信息",
    )


class UploadGroupFileRequest(QQBotRequestModel):
    file_type: Literal[1, 2, 3, 4] | None = Field(
        default=None,
        description="媒体类型：1=图片(png/jpg)，2=视频(mp4)，3=语音(silk/mp3/wav)，4=文件",
    )
    url: str | None = Field(
        default=None,
        description="媒体资源 URL，需以 http 开头，平台会下载并转存；分片上传合并时可为空",
    )
    srv_send_msg: bool | None = Field(
        default=None,
        description="true=直接发送消息并占用主动消息频次；false=仅返回 file_info",
    )
    upload_id: str | None = Field(
        default=None,
        description="分片上传任务 ID，来自预上传响应的 upload_id；传入后走分片上传合并路径，url 可为空",
    )
    file_name: str | None = Field(
        default=None,
        description="文件名，分片上传或二进制上传时必填",
    )
    file_data: str | None = Field(
        default=None,
        description="直接上传的二进制数据，大小需要在 5M 以内",
    )


class UploadGroupFileResponse(QQBotBaseModel):
    file_uuid: str | None = Field(
        default=None,
        description="文件唯一 ID",
    )
    file_info: str | None = Field(
        default=None,
        description="文件信息，用于发送消息接口的 media.file_info 字段，直接透传即可",
    )
    ttl: int | None = Field(
        default=None,
        description="file_info 有效期（秒），到期后需重新上传；0 表示可长期使用",
    )
    id: str | None = Field(
        default=None,
        description="发送消息的唯一 ID，仅 srv_send_msg=true 时返回",
    )
    raw_url: str | None = Field(
        default=None,
        description="文件下载链接，有效期与 ttl 一致；仅分片上传合并且 file_type 为图片/视频/语音时返回",
    )


class PrepareGroupUploadResponse(UploadPrepareResponse):
    pass
