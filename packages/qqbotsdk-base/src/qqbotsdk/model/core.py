from pydantic import BaseModel, ConfigDict


class QQBotBaseModel(BaseModel):
    """响应/事件模型基类: 宽容未知字段, 服务端新增字段不会导致解析失败."""

    model_config = ConfigDict(
        validate_by_name=True,
        serialize_by_alias=True,
        extra="allow",
    )


class QQBotRequestModel(QQBotBaseModel):
    """请求体基类: 禁止未知字段.

    字段名拼错时会立刻抛 ``ValidationError``, 而不是把错误字段静默发给服务端.
    """

    model_config = ConfigDict(
        validate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


__all__ = [
    "QQBotBaseModel",
    "QQBotRequestModel",
]
