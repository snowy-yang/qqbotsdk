from typing import Any, ClassVar, Literal, cast

from pydantic import Field, model_validator

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class Permission(QQBotBaseModel):
    type: Literal[0, 1, 2, 3] | None = Field(
        default=None,
        description="0=指定用户, 1=管理员, 2=所有人, 3=指定身份组（仅频道可用）",
    )
    specify_user_ids: list[str] | None = Field(
        default=None,
        description="有权限的用户 id 的列表",
    )
    specify_role_ids: list[str] | None = Field(
        default=None,
        description="有权限的身份组 id 的列表（仅频道可用）",
    )


class Modal(QQBotBaseModel):
    content: str | None = Field(
        default=None,
        max_length=40,
        description="二次确认的提示文本，不为空则进行二次确认，最多 40 个字符，不能有 URL",
    )
    confirm_text: str | None = Field(
        default=None,
        max_length=4,
        description='二次确认提示确认按钮文字，默认为"确认"，最多 4 个字符',
    )
    cancel_text: str | None = Field(
        default=None,
        max_length=4,
        description='二次确认提示取消按钮文字，默认为"取消"，最多 4 个字符',
    )


class Action(QQBotBaseModel):
    type: Literal[0, 1, 2] | None = Field(
        default=None,
        description="0=跳转按钮，1=回调按钮，2=指令按钮",
    )
    permission: Permission | None = Field(
        default=None,
        description="操作权限",
    )
    data: str | None = Field(
        default=None,
        description="回调数据。type=1/2 时必填",
    )
    unsupport_tips: str | None = Field(
        default=None,
        description="版本过低时提示文案",
    )
    enter: bool | None = Field(
        default=None,
        description="指令按钮可用，点击按钮后直接自动发送 data，仅单聊可用，默认 false",
    )
    reply: bool | None = Field(
        default=None,
        description="指令按钮可用，指令是否带引用回复本消息，默认 false",
    )
    anchor: int | None = Field(
        default=None,
        description="仅指令按钮下有效，设置后忽略 action.enter，设置为 1 时点击按钮自动唤起手Q选图器",
    )
    modal: Modal | None = Field(
        default=None,
        description="用户点击二次确认操作",
    )


class RenderData(QQBotBaseModel):
    label: str | None = Field(
        default=None,
        description=(
            "按钮文字。平台限制为最多 10 字符，超出部分由平台自行裁剪；"
            "SDK 不在此处校验长度，避免用热词/标题等业务数据时被 ValidationError 卡住"
        ),
    )
    visited_label: str | None = Field(
        default=None,
        description="点击后文字，不传则保持不变",
    )
    style: Literal[0, 1, 3, 4] | None = Field(
        default=None,
        description="0=灰色线框，1=蓝色线框，3=白色背景+红色字体，4=蓝色背景+白色字体",
    )


class Button(QQBotBaseModel):
    id: str | None = Field(
        default=None,
        description="按钮 ID。同一键盘内唯一",
    )
    render_data: RenderData | None = Field(
        default=None,
        description="按钮渲染",
    )
    action: Action | None = Field(
        default=None,
        description="按钮点击行为",
    )
    group_id: str | None = Field(
        default=None,
        description="分组ID，同一分组内有一个按钮操作后其它按钮变灰不可点击，仅当 action.type = 1 时有效",
    )


class Row(QQBotBaseModel):
    buttons: list[Button] | None = Field(
        default=None,
        description="行内按钮，从左到右排列",
    )


class KeyboardContent(QQBotBaseModel):
    rows: list[Row] | None = Field(
        default=None,
        description="按钮行列表",
    )


class Keyboard(QQBotBaseModel):
    content: KeyboardContent | None = Field(
        default=None,
        description="自定义键盘布局，用于自定义按钮",
    )


class MessageMarkdown(QQBotBaseModel):
    content: str | None = Field(
        default=None,
        description="Markdown 内容",
    )
    force_verify_image_resource: bool | None = Field(
        default=None,
        description="是否校验图片转存结果，为 true 时图片转存失败会返回错误且消息不发送，默认 false",
    )


class MediaInfo(QQBotBaseModel):
    file_info: str | None = Field(
        default=None,
        description="文件数据。来自文件上传接口返回值",
    )


class MessageReference(QQBotBaseModel):
    message_id: str | None = Field(
        default=None,
        description="被引用消息 ID，例如 REFIDX_xxxxxx",
    )


class InputNotify(QQBotBaseModel):
    input_type: Literal[1] | None = Field(
        default=None,
        description="填 1",
    )
    input_second: int | None = Field(
        default=None,
        le=60,
        description="状态持续时间，最长 60s",
    )


class MessageExtInfo(QQBotBaseModel):
    ref_idx: str | None = Field(
        default=None,
        description="引用消息索引。对应消息时间 ext 里的 msg_idx 与 ref_msg_idx",
    )


class MessageCardContent(QQBotBaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="卡片标题，1-50 字符",
    )
    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="卡片描述，1-200 字符",
    )
    url: str | None = Field(
        default=None,
        max_length=1024,
        description="跳转链接，必须为 https，长度 <= 1024 字符",
    )
    pic_url: str | None = Field(
        default=None,
        max_length=1024,
        description="封面图链接，必须为 https，长度 <= 1024 字符",
    )


class MessageCard(QQBotBaseModel):
    type: Literal["tuwen"] | None = Field(
        default=None,
        description="卡片类型：tuwen=图文卡片",
    )
    content: MessageCardContent | None = Field(
        default=None,
        description="卡片元素；type=tuwen 时必须包含 title/description/url/pic_url",
    )


class MessageSendRequestBase(QQBotRequestModel):
    """发送消息请求的公共校验: 按内容字段推导 ``msg_type``, 并校验内容互斥.

    平台的 ``msg_type`` 与内容字段是一一对应的(``content``→0、``markdown``→2、
    ``input_notify``→6、``media``→7、``card``→8), 但两个字段都是可选的: 只填
    ``markdown`` 而不填 ``msg_type`` 时, 请求体会缺 ``msg_type`` 而只剩内容字段,
    语义全靠平台默认推断. 这里在**校验前**按填入的字段补齐 ``msg_type``, 让
    ``SendXxxMessagesRequest(markdown=...)`` 直接就是一个合法的请求.

    同时把原来只写在 docstring 里的互斥关系变成真校验:

    - ``markdown`` / ``media`` / ``card`` / ``input_notify`` 四者至多填一个;
    - ``content`` 与 ``markdown`` 互斥(官方: 传了 markdown 后 content 必须为空);
    - ``content`` 可以与 ``media`` 共存, 作为富媒体的附带文本.

    显式传了 ``msg_type`` 但与内容字段对不上时直接报错, 而不是把矛盾发给服务端.
    """

    # 内容字段 -> 该字段对应的 msg_type
    _MSG_TYPE_BY_FIELD: ClassVar[dict[str, int]] = {
        "markdown": 2,
        "media": 7,
        "card": 8,
        "input_notify": 6,
    }

    @model_validator(mode="before")
    @classmethod
    def _infer_msg_type(cls, data: Any) -> Any:
        """补齐 ``msg_type`` 并校验内容字段互斥."""
        if not isinstance(data, dict):
            return data
        raw = cast("dict[str, Any]", data)
        filled = [name for name in cls._MSG_TYPE_BY_FIELD if raw.get(name) is not None]
        if len(filled) > 1:
            raise ValueError(f"消息内容字段互斥，不能同时传 {filled}")
        has_content = raw.get("content") is not None
        if has_content and "markdown" in filled:
            raise ValueError(
                "content 与 markdown 互斥：传了 markdown 时 content 必须为空"
            )

        if filled:
            inferred = cls._MSG_TYPE_BY_FIELD[filled[0]]
        elif has_content:
            inferred = 0
        else:
            # 没有任何内容字段(例如只带键盘), 保持原样交给平台判断
            return raw

        declared = raw.get("msg_type")
        if declared is None:
            return {**raw, "msg_type": inferred}
        if declared != inferred:
            source = filled[0] if filled else "content"
            raise ValueError(
                f"msg_type={declared!r} 与内容字段 {source!r} 不匹配，"
                f"按 {source!r} 应为 {inferred}"
            )
        return raw
