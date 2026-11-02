# API · 鉴权与会话

模块：`qqbotsdk.api.auth`、`qqbotsdk.api.core`、`qqbotsdk.api.gateway`（均在 `qqbotsdk-base-py`）。

凭证来自环境变量 `APPID` / `APPSECRET`（支持项目根目录 `.env`）。按官方文档，凭证有效期 7200 秒，剩余不足 60 秒时自动刷新，调用方无需关心过期。

## 鉴权函数

| 函数 | 说明 |
|---|---|
| `await get_access_token(*, force=False)` | 返回可用的 `access_token`，必要时刷新。`force=True` 忽略缓存强制刷新 |
| `await get_authorization() -> str` | 返回请求头值，格式 `QQBot <access_token>` |
| `reset_access_token() -> None` | 清空缓存凭证（测试或主动失效时用） |

```python
from qqbotsdk.api.auth import get_access_token, get_authorization, reset_access_token

token = await get_access_token()  # 命中缓存直接返回
header = await get_authorization()  # "QQBot xxx"
```

并发安全：内部用 `asyncio.Lock`，并发调用只会换取一次凭证。缺少凭证抛 `QQBotAuthError`。

## 会话 `session`

`qqbotsdk.api.core.session` 是懒加载单例（`QQBotSession`），方法签名与 `aiohttp.ClientSession` 一致，但替你做了三件事：

1. **自动注入鉴权头**：发往 OpenAPI 域名（`https://api.bot.qq.com`）的请求附加 `Authorization`；发往其它域名的绝对地址（如素材上传的 COS 预签名 URL）不附加。
2. **统一错误检查**：`QQBotResponse` 把 HTTP 4xx/5xx、以及 HTTP 200 但 body 带非零 `err_code`/`code` 的情况统一抛 `QQBotAPIError`；空响应（204 / 非 JSON content-type）返回 `{}` 而非报错。
3. **429 自动重试**：命中 429 时按 `Retry-After`（否则指数退避 + 抖动）重试，最多 3 次，总等待 ≤ 30 秒。

```python
from qqbotsdk.api.core import session

async with session.get("/users/@me") as resp:
    data = await resp.json()

await session.close()  # 进程退出前关闭
```

| 成员 | 说明 |
|---|---|
| `session.get/post/put/patch/delete(url, **kw)` | 返回可重试的请求上下文，用法同 aiohttp |
| `await session.request(method, url, **kw)` | 直接返回响应（自行处理状态码时用） |
| `session.client` | 底层 `aiohttp.ClientSession`（WebSocket 等原生场景用） |
| `await session.close()` | 关闭会话，可重复调用 |
| `session.closed` | 是否已关闭 |

可调常量（`qqbotsdk.api.core`）：`BASE_URL`（`https://api.bot.qq.com`）、`DEFAULT_TIMEOUT_MS`（5000，可由环境变量 `TIMEOUT` 覆盖）、`MAX_RETRIES`（3）、`RETRY_BASE_SECONDS`（1.0）、`RETRY_TOTAL_WAIT_SECONDS`（30.0）。

## 网关地址

模块：`qqbotsdk.api.gateway`

| 函数 | 说明 |
|---|---|
| `await fetch_gateway_url() -> str` | 调用 `GET /gateway` 返回其中的 `url` 字段（如 `wss://api.sgroup.qq.com/websocket`）；缺少 `url` 抛 `QQBotGatewayError` |

底层网关客户端会自动调用它，一般无需直接用；`qqbotsdk.app.Bot` 的 `url` 省略时也会走这条路。
