"""统一异常体系: 业务层, 凭证层与网关层三级分类.

层次::

    QQBotError                  SDK 所有异常的基类
    +-- QQBotAPIError           OpenAPI 返回的业务/HTTP 错误
    +-- QQBotAuthError          凭证缺失或换取 access_token 失败
    +-- QQBotGatewayError       WebSocket 网关层错误

调用方 ``except QQBotError`` 可以兜住全部错误, 也可以按层分别处理.
"""

__all__ = [
    "QQBotAPIError",
    "QQBotAuthError",
    "QQBotError",
    "QQBotGatewayError",
]


class QQBotError(Exception):
    """SDK 所有异常的基类."""


class QQBotAPIError(QQBotError):
    """OpenAPI 返回的业务错误.

    Attributes:
        status: HTTP 状态码.
        err_code: 业务错误码 (body 中的 ``err_code`` 或 ``code``), 0 表示未知.
        message: 服务端返回的错误描述.
        trace_id: 服务端追踪 ID, 提交工单时需要提供.
    """

    def __init__(
        self,
        status: int,
        err_code: int = 0,
        message: str = "",
        trace_id: str | None = None,
    ) -> None:
        self.status = status
        self.err_code = err_code
        self.message = message
        self.trace_id = trace_id
        super().__init__(status, err_code, message, trace_id)

    def __str__(self) -> str:
        parts = [
            f"status={self.status}",
            f"err_code={self.err_code}",
            f"message={self.message!r}",
        ]
        if self.trace_id:
            parts.append(f"trace_id={self.trace_id}")
        return f"QQBotAPIError({', '.join(parts)})"


class QQBotAuthError(QQBotError):
    """凭证缺失或换取 access_token 失败.

    Attributes:
        message: 失败原因, 换取失败时包含服务端返回的 ``code`` 与 ``message``.
        code: 服务端业务码, 本地凭证缺失时为 None.
    """

    def __init__(self, message: str = "", *, code: int | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    def __str__(self) -> str:
        return f"QQBotAuthError({self.message})"


class QQBotGatewayError(QQBotError):
    """WebSocket 网关层错误.

    Attributes:
        reason: 错误原因描述.
        code: 网关返回的错误码 (op 9 无效会话或 close code), 未知时为 None.
    """

    def __init__(self, reason: str = "", code: int | None = None) -> None:
        self.reason = reason
        self.code = code
        super().__init__(code, reason)

    def __str__(self) -> str:
        if self.code is None:
            return f"QQBotGatewayError({self.reason})"
        return f"QQBotGatewayError(code={self.code}, reason={self.reason})"
