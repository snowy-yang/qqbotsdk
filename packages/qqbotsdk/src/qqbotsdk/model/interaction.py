from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class ConfirmInteractionsRequest(QQBotBaseModel):
    code: Literal[0, 1, 2, 3, 4, 5] | None = Field(
        None,
        description="回调结果。0=成功, 1=操作失败, 2=操作频繁, 3=重复操作, 4=没有权限, 5=仅管理员操作",
    )
