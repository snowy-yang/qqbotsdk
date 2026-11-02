# 错误处理

三级错误全部继承 `QQBotError`，`except QQBotError` 能兜住一切。

| 异常 | 触发场景 | 关键属性 |
|---|---|---|
| `QQBotAPIError` | HTTP 4xx/5xx；HTTP 200 但 body 带非零 `err_code` / `code`；201/202 返回错误体 | `status`、`err_code`、`message`、`trace_id` |
| `QQBotAuthError` | 缺少凭证；换取 access_token 失败 | `message`、`code` |
| `QQBotGatewayError` | 网关致命关闭码（4001/4002/4010~4014/4914/4915）；网关响应缺少 `url` | `code`、`reason` |

```python
from qqbotsdk.errors import QQBotAPIError, QQBotAuthError, QQBotError

try:
    await send_group_messages(group_openid, request)
except QQBotAPIError as exc:
    print(exc.status, exc.err_code, exc.message, exc.trace_id)
except QQBotAuthError as exc:
    print("凭证问题:", exc.message)
except QQBotError:
    ...
```

`QQBotAPIError.__str__` 自带排障信息：

```
QQBotAPIError(status=200, err_code=40034005, message='回复消息msg_id已过期', trace_id=4a8a6156...)
```

## 无响应体接口

删除类接口返回 `204`、异步接口 `201/202`，旧实现会抛 `ContentTypeError`。现在统一返回空结果：

```python
async with session.delete(f"/v2/groups/{group_openid}/messages/{message_id}") as resp:
    data = await resp.json()  # 204 时得到 {}
```

## 429 自动重试

| 参数 | 默认值 | 说明 |
|---|---|---|
| `MAX_RETRIES` | 3 | 最多重试次数 |
| `RETRY_BASE_SECONDS` | 1.0 | 指数退避基数 |
| 等待策略 | — | 有 `Retry-After` 用它，否则 `base * 2**n` + 抖动 |
| 总等待上限 | 30 秒 | 超出即抛出 |

429 表示请求未被处理，因此 POST 也会重试。**非 429 一律不重试**。

```python
import qqbotsdk.api.core as core

core.MAX_RETRIES = 5  # 按需调整
```

## trace_id

优先取响应头 `X-Tps-trace-ID`，其次取 body 的 `trace_id`。提工单时直接贴这个 ID。

## 网关层

致命关闭码会终止客户端，原因通过 `last_error` 暴露：

```python
from qqbotsdk.errors import QQBotGatewayError

if isinstance(ws.last_error, QQBotGatewayError):
    print(ws.last_error.code, ws.last_error.reason)  # 4914 机器人已下架 / 4915 已封禁
```

上层 `Bot` 中，handler 的异常都会进 `on_error`（见 [app.md](app.md)），不会断连。

## 常见业务错误码

| 错误码 | 含义 | 处理 |
|---|---|---|
| `22006` | 消息类型与内容不匹配 | 检查 `msg_type` 与 `content` |
| `304004` | 无 ARK 模板权限 | 先申请模板 |
| `304036` | 无 Markdown 模板权限 | 先申请模板 |
| `304103` | 消息 ID 已过期，不能回复 | 被动回复窗口：群 5 分钟 / 单聊 60 分钟 |
| `40034005` | 回复消息 `msg_id` 已过期 | 同上 |
| `40054005` | 消息被去重 | 递增 `msg_seq`（`ctx.reply()` 已自动处理） |
| `40034100` | 主动消息超频控 | 降低发送频率 |
| `1100301` | 调用方不是群成员 | 先把机器人拉进群 |
| `304019` | @全体成员次数超限 | 每群每天 1 次 |
