"""HTTP 会话: 懒加载 aiohttp 会话并自动注入鉴权请求头.

对外暴露单例 ``session``, 用法与 ``aiohttp.ClientSession`` 一致::

    async with session.get("/users/@me") as resp:
        data = await resp.json()

会话在首次使用时才创建, 因此可以在任意位置 import 本模块, 无需先有事件循环;
发往 OpenAPI 域名的请求会自动附加 ``Authorization: QQBot <access_token>``,
发往其它域名的绝对地址(例如素材上传的 COS 预签名 URL)则不附加该请求头.

响应侧统一交给 :class:`QQBotResponse` 处理, 业务模块无需改动:

- 空响应 (204, 无 content-type, 空 body) 返回 ``{}``, 不再抛 ``ContentTypeError``;
- 非 JSON content-type 返回 ``{}``;
- OpenAPI 域名下 body 含非零 ``err_code`` / ``code`` 时抛 ``QQBotAPIError``;
- 命中 HTTP 429 (限频) 时自动退避重试, 最多 ``MAX_RETRIES`` 次, 见
  :class:`_RetryingRequestContext`; 业务函数仍然只写 ``async with session.get(...)``.
"""

import asyncio
import os
import random
from collections.abc import Awaitable, Callable, Generator, Mapping
from contextlib import contextmanager
from types import TracebackType
from typing import Any, Final, cast
from urllib.parse import urlparse

from aiohttp import ClientResponse, ClientSession, ClientTimeout, TraceConfig
from aiohttp.tracing import TraceRequestStartParams
from aiohttp.typedefs import DEFAULT_JSON_DECODER, JSONDecoder
from loguru import logger

from qqbotsdk.api.auth import get_authorization
from qqbotsdk.errors import QQBotAPIError

# OpenAPI 统一域名
BASE_URL: Final = "https://api.bot.qq.com"

# 默认请求超时(毫秒), 可由环境变量 TIMEOUT 覆盖
DEFAULT_TIMEOUT_MS: Final = 5000

# 429 自动重试: 最多重试次数(不含首次请求)
MAX_RETRIES: Final = 3

# 退避基准秒数: 第 n 次重试等待 RETRY_BASE_SECONDS * 2 ** n, 再叠加抖动
RETRY_BASE_SECONDS: Final = 1.0

# 一次请求的所有重试等待总和上限(秒)
RETRY_TOTAL_WAIT_SECONDS: Final = 30.0

# 抖动比例: 在退避时长上叠加 0~10% 随机量, 避免多客户端同时重试
_RETRY_JITTER_RATIO: Final = 0.1

# 需要自动重试的状态码. 429 表示请求未被处理, 重发不会重复产生副作用
_TOO_MANY_REQUESTS: Final = 429

# 换取凭证的接口本身不需要也不应该带鉴权头
_NO_AUTH_PATHS: Final = frozenset({"/app/getAppAccessToken"})

_API_HOST: Final[str] = urlparse(BASE_URL).hostname or ""

# 统一错误检查生效的域名. 默认只有 OpenAPI 域名, 其它域名(COS 预签名等)保持原样;
# 测试把本地假服务端的 host 加进来即可走同一段检查逻辑.
CHECKED_HOSTS: set[str] = {_API_HOST}

# OpenAPI 在响应头里回传的追踪 ID
_TRACE_ID_HEADER: Final = "X-Tps-trace-ID"

# 业务错误码字段: err_code 为通用字段, code 用于 /app/getAppAccessToken
_ERROR_CODE_KEYS: Final = ("err_code", "code")

# 错误体可能只含这些字段
_ERROR_BODY_KEYS: Final = frozenset({"code", "err_code", "message", "trace_id"})

# 官方说明 201/202 表示异步受理, 正常无响应体; 有错误体时按错误处理
_ASYNC_STATUSES: Final = frozenset({201, 202})


def _timeout_ms() -> int:
    raw = os.getenv("TIMEOUT")
    if not raw:
        return DEFAULT_TIMEOUT_MS
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_MS


def _client_timeout() -> ClientTimeout:
    return ClientTimeout(total=_timeout_ms() / 1000)


def _is_checked_host(host: str | None) -> bool:
    """该域名的响应是否走统一错误检查."""
    return host is not None and host in CHECKED_HOSTS


def _is_json_content_type(content_type: str) -> bool:
    """content-type 是否为 JSON, 含 ``+json`` 后缀."""
    mime = content_type.split(";", 1)[0].strip().lower()
    return mime == "application/json" or mime.endswith("+json")


def _as_int(value: object) -> int | None:
    """把业务码规范成 int, 无法解析时返回 None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _error_code(body: Mapping[str, Any]) -> int | None:
    """返回 body 中的非零业务错误码, 无错误时返回 None."""
    for key in _ERROR_CODE_KEYS:
        raw = body.get(key)
        if raw is None or isinstance(raw, bool):
            continue
        code = _as_int(raw)
        if code is None:
            # 字段存在但不是数字(例如字符串错误标识), 同样视为错误
            if isinstance(raw, str) and raw.strip():
                return 0
            continue
        if code != 0:
            return code
    return None


def _message_of(body: Mapping[str, Any]) -> str:
    """取服务端返回的错误描述."""
    raw = body.get("message")
    if raw is None:
        return ""
    return raw if isinstance(raw, str) else str(raw)


def _trace_id_of(headers: Mapping[str, str], body: Mapping[str, Any]) -> str | None:
    """取追踪 ID: 优先响应头, 回退到 body 的 trace_id."""
    header = headers.get(_TRACE_ID_HEADER)
    if header:
        return header
    raw = body.get("trace_id")
    return raw if isinstance(raw, str) and raw else None


def _looks_like_error_body(body: Mapping[str, Any]) -> bool:
    """判断 201/202 的 body 是否只有错误字段."""
    return "message" in body and set(body) <= _ERROR_BODY_KEYS


def _as_dict(payload: object) -> dict[str, Any] | None:
    """payload 为 dict 时返回带类型注解的视图, 否则返回 None."""
    if isinstance(payload, dict):
        return cast("dict[str, Any]", payload)
    return None


def _check_api_error(
    body: Mapping[str, Any],
    *,
    status: int,
    trace_id: str | None,
) -> None:
    """body 表示业务错误时抛 ``QQBotAPIError``."""
    code = _error_code(body)
    if code is not None:
        raise QQBotAPIError(status, code, _message_of(body), trace_id)
    if status in _ASYNC_STATUSES and _looks_like_error_body(body):
        raise QQBotAPIError(status, 0, _message_of(body), trace_id)


class QQBotResponse(ClientResponse):
    """带统一错误检查的 ``ClientResponse``, 由 ``ClientSession(response_class=...)`` 注入.

    只处理 ``CHECKED_HOSTS`` 里的域名, 其它域名(如 COS 预签名上传)走 aiohttp 原逻辑.
    """

    async def json(
        self,
        *,
        encoding: str | None = None,
        loads: JSONDecoder = DEFAULT_JSON_DECODER,
        content_type: str | None = "application/json",
    ) -> Any:
        """解析响应体, 顺带做统一错误检查.

        Args:
            encoding: 显式指定编码, 缺省按 content-type 推导.
            loads: JSON 解析函数, 默认 ``json.loads``.
            content_type: 期望的 content-type, 传 None 跳过校验.

        Raises:
            QQBotAPIError: body 携带非零业务错误码, 或 201/202 只返回了错误体.
        """
        if not _is_checked_host(self.url.host):
            return await super().json(
                encoding=encoding,
                loads=loads,
                content_type=content_type,
            )

        # 只读取一次 body, 后续都复用 aiohttp 的缓存, 避免二次消费
        raw = await self.read()
        if not raw.strip():
            return {}
        if content_type and not _is_json_content_type(
            self.headers.get("Content-Type", "")
        ):
            return {}

        payload: Any = loads(raw.decode(encoding or self.get_encoding()))
        body = _as_dict(payload)
        if body is not None:
            trace_id = _trace_id_of(self.headers, body)
            _check_api_error(body, status=self.status, trace_id=trace_id)
        return payload

    def raise_for_status(self) -> None:
        """HTTP 4xx/5xx 统一换成 ``QQBotAPIError``.

        OpenAPI 域名下的状态码错误也归入同一异常体系, 调用方只需 ``except QQBotAPIError``;
        其它域名(如 COS 预签名上传)保持 aiohttp 原行为.
        """
        if not _is_checked_host(self.url.host):
            super().raise_for_status()
            return
        if self.status < 400:
            return
        reason = f"HTTP {self.status} {self.reason}".strip()
        raise QQBotAPIError(
            self.status,
            0,
            reason,
            self.headers.get(_TRACE_ID_HEADER),
        )


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """从 ``Retry-After`` 响应头取等待秒数, 缺失或不是合法秒数时返回 None."""
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        seconds = float(raw.strip())
    except ValueError:
        # HTTP-date 形式不解析, 直接退回指数退避
        return None
    return seconds if seconds >= 0 else None


def _retry_delay(attempt: int, headers: Mapping[str, str], *, waited: float) -> float:
    """计算第 ``attempt`` 次(从 0 开始)重试前应等待的秒数.

    优先使用 ``Retry-After``; 否则按 ``RETRY_BASE_SECONDS * 2 ** attempt`` 并叠加
    抖动. 结果还要受 ``RETRY_TOTAL_WAIT_SECONDS`` 约束, 且不小于 0.
    """
    delay = _retry_after_seconds(headers)
    if delay is None:
        delay = RETRY_BASE_SECONDS * (2**attempt)
        delay += delay * _RETRY_JITTER_RATIO * random.random()
    return max(0.0, min(delay, RETRY_TOTAL_WAIT_SECONDS - waited))


class _RetryingRequestContext:
    """``async with session.get(...) as resp`` 的替身, 命中 HTTP 429 时自动重试.

    429 表示服务端因限频**没有处理**该请求, 因此重发不会重复产生副作用, 即便
    ``POST`` 也可以安全重试; 其它状态码(含 4xx/5xx 业务错误)一律不重试, 原样抛出.

    会话级 ``raise_for_status`` 在这里统一关掉: 先自行判定 429, 其余交给
    :meth:`QQBotResponse.raise_for_status` 抛 ``QQBotAPIError``, 调用方感知不到差异.
    """

    __slots__ = ("_label", "_request", "_response")

    def __init__(
        self,
        request: Callable[[], Awaitable[ClientResponse]],
        *,
        label: str = "",
    ) -> None:
        self._request = request
        self._label = label
        self._response: ClientResponse | None = None

    def __await__(self) -> Generator[Any, None, ClientResponse]:
        """保留 ``resp = await session.get(...)`` 的旧写法, 等价于直接进入上下文."""
        return self.__aenter__().__await__()

    async def __aenter__(self) -> ClientResponse:
        waited = 0.0
        for attempt in range(MAX_RETRIES + 1):
            response = await self._request()
            if response.status == _TOO_MANY_REQUESTS and attempt < MAX_RETRIES:
                delay = _retry_delay(attempt, response.headers, waited=waited)
                waited += delay
                logger.warning(
                    f"请求被限频(429)，{delay:.2f} 秒后重试第 {attempt + 1} 次："
                    f"{self._label}"
                )
                response.release()
                await asyncio.sleep(delay)
                continue
            self._raise_for_status(response)
            self._response = response
            return response
        raise RuntimeError("429 重试流程异常")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        response = self._response
        self._response = None
        if response is not None:
            response.release()

    def _raise_for_status(self, response: ClientResponse) -> None:
        """等价于 ``raise_for_status=True``: 非 2xx 抛错, 并释放连接避免泄漏."""
        try:
            response.raise_for_status()
        except BaseException:
            response.release()
            raise


async def _inject_authorization(
    _session: ClientSession,
    _ctx: object,
    params: TraceRequestStartParams,
) -> None:
    """请求发出前注入鉴权头, aiohttp 会 await 协程形式的 trace 回调."""
    if params.url.host != _API_HOST:
        return
    if params.url.path in _NO_AUTH_PATHS:
        return
    params.headers["Authorization"] = await get_authorization()


def _build_trace_config() -> TraceConfig:
    trace_config = TraceConfig()
    trace_config.on_request_start.append(_inject_authorization)
    return trace_config


class QQBotSession:
    """``aiohttp.ClientSession`` 的懒加载包装, 方法签名与 aiohttp 一致."""

    __slots__ = ("_client",)

    def __init__(self) -> None:
        self._client: ClientSession | None = None

    def _ensure(self) -> ClientSession:
        if self._client is None or self._client.closed:
            self._client = ClientSession(
                base_url=BASE_URL,
                raise_for_status=True,
                timeout=_client_timeout(),
                trace_configs=[_build_trace_config()],
                response_class=QQBotResponse,
            )
        return self._client

    def _request_context(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> _RetryingRequestContext:
        """构造可重试的请求上下文, 统一关闭 aiohttp 的会话级 ``raise_for_status``.

        业务函数照旧写 ``async with session.get(...) as resp``, 无需感知重试.
        """

        def send() -> Awaitable[ClientResponse]:
            return self._ensure().request(
                method,
                url,
                raise_for_status=False,
                **kwargs,
            )

        # 日志标签去掉 query, 避免把 COS 预签名 URL 里的签名写进日志
        return _RetryingRequestContext(send, label=f"{method} {url.split('?', 1)[0]}")

    def get(self, url: str, **kwargs: Any) -> _RetryingRequestContext:
        return self._request_context("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> _RetryingRequestContext:
        return self._request_context("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> _RetryingRequestContext:
        return self._request_context("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> _RetryingRequestContext:
        return self._request_context("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> _RetryingRequestContext:
        return self._request_context("DELETE", url, **kwargs)

    @property
    def client(self) -> ClientSession:
        """底层 aiohttp 会话, 供 WebSocket 等需要原生能力的场景使用."""
        return self._ensure()

    async def request(self, method: str, url: str, **kwargs: Any) -> ClientResponse:
        """通用 verb 请求: 与 ``get`` / ``post`` 等完全同构, 同样走 429 重试.

        ``method`` 可以是任意 HTTP verb, 便于按配置分发。行为与
        ``get`` / ``post`` / ``put`` / ``patch`` / ``delete`` 一致:

        - 命中 HTTP 429 时按 ``Retry-After`` / 指数退避自动重试, 最多
          ``MAX_RETRIES`` 次;
        - 非 2xx 抛 :class:`qqbotsdk.errors.QQBotAPIError`(OpenAPI 域名下);
        - 返回的响应**未**读取 body, 调用方自己 ``await resp.json()`` 或
          ``await resp.read()``, 用完由本方法的上下文管理器释放连接::

            async with session.request("GET", "/users/@me") as resp:
                data = await resp.json()

        注意: 直接 ``await session.request(...)`` 拿到的响应不会自动释放,
        与 aiohttp 原生语义一致, 建议一律用 ``async with``.
        """
        return await self._request_context(method, url, **kwargs)

    @property
    def closed(self) -> bool:
        return self._client is None or self._client.closed

    async def close(self) -> None:
        if self._client is not None and not self._client.closed:
            await self._client.close()
        self._client = None

    async def __aenter__(self) -> "QQBotSession":
        self._ensure()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()


# 默认会话: 未注入时所有请求都走它
_DEFAULT_SESSION: Final = QQBotSession()

# 当前注入的会话; None 表示用默认会话
_injected_session: QQBotSession | None = None


class _SessionRouter:
    """``session`` 的转发实现: 每次调用都重新解析当前生效的会话.

    模块级 ``session`` 必须是**稳定的转发层**而不是会话本身: 业务模块的
    ``from ... import session`` 在 import 期就把名字绑死了, 如果 ``session`` 是会话
    实例, 注入就要去改各模块的模块属性(打补丁), 测起来很脆. 这里让名字稳定不变,
    真正的会话由 :func:`set_session` 换, 所有 import 过它的模块自动看到新会话.
    """

    __slots__ = ()

    def __getattr__(self, name: str) -> Any:
        """未显式定义的属性一律转发到当前生效的会话.

        注意这是「转发引用」: ``session.some_attr = x`` 只会写到本代理上, 不会写到
        真正的会话. 需要改内部状态请用 :func:`get_session` 拿真实会话.
        """
        return getattr(resolve_session(), name)

    def _ensure(self) -> ClientSession:
        """确保当前会话的连接池已创建, 返回底层 ``ClientSession``."""
        session = resolve_session()
        return session._ensure()  # pyright: ignore[reportPrivateUsage]

    async def __aenter__(self) -> ClientSession:
        return self._ensure()

    async def __aexit__(self, *_exc: object) -> None:
        return None


def resolve_session() -> QQBotSession:
    """返回当前生效的会话对象: 注入了就用注入的, 否则用模块级默认单例."""
    return _DEFAULT_SESSION if _injected_session is None else _injected_session


def get_session() -> QQBotSession:
    """返回当前生效的会话对象, 供需要改内部状态(例如测试)的场景使用."""
    return resolve_session()


@contextmanager
def use_session(session: QQBotSession) -> Generator[QQBotSession]:
    """在 ``with`` 块内让所有 ``qqbotsdk`` 请求改走指定会话, 退出后还原.

    用于单测: 构造一个指向本地假服务端的会话传进来, 业务模块与 ``ctx.api`` 都会
    自动用它, 不会误连真实域名.

    Args:
        session: 要临时启用的会话对象.

    Yields:
        传入的会话对象本身.
    """
    set_session(session)
    try:
        yield session
    finally:
        reset_session()


def set_session(session: QQBotSession | None) -> None:
    """替换全局会话(传 None 表示恢复默认单例).

    Args:
        session: 新的会话对象, 或 None.

    Notes:
        被替换掉的会话不会被自动关闭, 调用方自己决定何时 ``await it.close()``.
    """
    global _injected_session
    _injected_session = session


def reset_session() -> None:
    """恢复默认单例, 供测试夹具收尾使用(不关闭任何会话)."""
    global _injected_session
    _injected_session = None


session = _SessionRouter()
"""当前生效会话的转发入口, 用法与 ``aiohttp.ClientSession`` 一致.

``from qqbotsdk.api.core import session`` 拿到的就是这个对象; 它本身不持有连接,
真正的会话由 :func:`get_session` / :func:`set_session` 决定, 因此测试里可以整体
换成假服务端上的会话.
"""

__all__ = [
    "BASE_URL",
    "CHECKED_HOSTS",
    "DEFAULT_TIMEOUT_MS",
    "MAX_RETRIES",
    "RETRY_BASE_SECONDS",
    "RETRY_TOTAL_WAIT_SECONDS",
    "QQBotResponse",
    "QQBotSession",
    "get_session",
    "reset_session",
    "session",
    "set_session",
    "use_session",
]
