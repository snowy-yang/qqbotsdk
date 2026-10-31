from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class Permission(QQBotBaseModel):
    type: Literal[0, 1, 2] | None = Field(
        None,
        description="0=指定用户, 1=管理员, 2=所有人",
    )
    specify_user_ids: list[str] | None = Field(
        None,
        description="有权限的用户 id 的列表",
    )
    specify_role_ids: list[str] | None = Field(
        None,
        description="有权限的身份组 id 的列表（仅频道可用）",
    )


class Modal(QQBotBaseModel):
    content: str | None = Field(
        None,
        max_length=40,
        description="二次确认的提示文本，最多 40 个字符，不能有 URL",
    )
    confirm_text: str | None = Field(
        None,
        max_length=4,
        description='二次确认提示确认按钮文字，默认为"确认"',
    )
    cancel_text: str | None = Field(
        None,
        max_length=4,
        description='二次确认提示取消按钮文字，默认为"取消"',
    )


class Action(QQBotBaseModel):
    type: Literal[0, 1, 2] | None = Field(
        None,
        description="0=跳转按钮，1=回调按钮，2=指令按钮",
    )
    permission: Permission | None = Field(
        None,
        description="操作权限",
    )
    data: str | None = Field(
        None,
        description="回调数据。type=1/2 时必填",
    )
    unsupport_tips: str | None = Field(
        None,
        description="版本过低时提示文案",
    )
    enter: bool | None = Field(
        None,
        description="指令按钮可用，点击按钮后直接自动发送 data，仅单聊可用",
    )
    reply: bool | None = Field(
        None,
        description="指令按钮可用，指令是否带引用回复本消息",
    )
    anchor: int | None = Field(
        None,
        description="指令按钮下有效，设置为 1 时点击按钮自动唤起手Q选图器",
    )
    modal: Modal | None = Field(
        None,
        description="用户点击二次确认操作",
    )


class RenderData(QQBotBaseModel):
    label: str | None = Field(
        None,
        max_length=10,
        description="按钮文字，最多 10 字符",
    )
    visited_label: str | None = Field(
        None,
        description="点击后文字，不传则保持不变",
    )
    style: Literal[0, 1, 3, 4] | None = Field(
        None,
        description="0=灰色线框，1=蓝色线框，3=白色背景+红色字体，4=蓝色背景+白色字体",
    )


class Button(QQBotBaseModel):
    id: str | None = Field(
        None,
        description="按钮 ID。同一键盘内唯一",
    )
    render_data: RenderData | None = Field(
        None,
        description="按钮渲染",
    )
    action: Action | None = Field(
        None,
        description="按钮点击行为",
    )
    group_id: str | None = Field(
        None,
        description="分组ID。仅当 action.type = 1 时有效",
    )


class Row(QQBotBaseModel):
    buttons: list[Button] | None = Field(
        None,
        description="行内按钮，从左到右排列",
    )


class KeyboardContent(QQBotBaseModel):
    rows: list[Row] | None = Field(
        None,
        description="按钮行列表",
    )


class Keyboard(QQBotBaseModel):
    content: KeyboardContent | None = Field(
        None,
        description="自定义键盘布局",
    )


class MessageMarkdown(QQBotBaseModel):
    content: str | None = Field(
        None,
        description="Markdown 内容",
    )
    force_verify_image_resource: bool | None = Field(
        None,
        description="是否校验图片转存结果，默认为 false",
    )


class MediaInfo(QQBotBaseModel):
    file_info: str | None = Field(
        None,
        description="文件数据。来自文件上传接口返回值",
    )


class MessageReference(QQBotBaseModel):
    message_id: str | None = Field(
        None,
        description="被引用消息 ID，例如 REFIDX_xxxxxx",
    )


class InputNotify(QQBotBaseModel):
    input_type: Literal[1] | None = Field(
        None,
        description="填 1",
    )
    input_second: int | None = Field(
        None,
        le=60,
        description="状态持续时间，最长 60s",
    )


class MessageExtInfo(QQBotBaseModel):
    ref_idx: str | None = Field(
        None,
        description="引用消息索引。对应消息时间 ext 里的 msg_idx 与 ref_msg_idx",
    )


class MessageCardContent(QQBotBaseModel):
    title: str | None = Field(
        None,
        description="卡片标题，1-50 字符",
    )
    description: str | None = Field(
        None,
        description="卡片描述，1-200 字符",
    )
    url: str | None = Field(
        None,
        description="跳转链接，必须为 https，长度 <= 1024 字符",
    )
    pic_url: str | None = Field(
        None,
        description="封面图链接，必须为 https，长度 <= 1024 字符",
    )


class MessageCard(QQBotBaseModel):
    type: Literal["tuwen"] | None = Field(
        None,
        description="卡片类型：tuwen=图文卡片",
    )
    content: MessageCardContent | None = Field(
        None,
        description="卡片元素；type=tuwen 时必须包含 title/description/url/pic_url",
    )
