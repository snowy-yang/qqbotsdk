# API · 机器人基础

模块：`qqbotsdk.api.bot`（核心包）。HTTP 方法、路径、请求/响应模型如下。

## get_gateway

```python
from qqbotsdk.api.bot import get_gateway

resp = await get_gateway()
print(resp.url)
```

- `GET /gateway` → `GetGatewayResponse`
- 返回 `GetGatewayResponse(url: str)`：WebSocket 网关地址。
- 与 `qqbotsdk.api.gateway.fetch_gateway_url()` 同一接口；后者只取 `url` 字符串，前者返回完整响应模型。**不做分片**（本 SDK 固定单连接，不封装 `GET /gateway/bot`）。

## get_me

```python
from qqbotsdk.api.bot import get_me

me = await get_me()
print(me.id, me.username)
```

- `GET /users/@me` → `GetMeResponse`
- 响应字段（均可选）：`id`、`username`、`avatar`、`bot`、`union_openid`、`union_user_account`、`share_url`、`welcome_msg`。

## generate_url_link

```python
from qqbotsdk.api.bot import generate_url_link
from qqbotsdk.model.bot import GenerateUrlLinkRequest

resp = await generate_url_link(GenerateUrlLinkRequest(callback_data="group_1"))
print(resp.data)
```

- `POST /v2/generate_url_link` → `GenerateUrlLinkResponse`
- 请求 `GenerateUrlLinkRequest`：

  | 字段 | 类型 | 必填 | 说明 |
  |---|---|---|---|
  | `callback_data` | `str` | 否 | 回传给机器人后台的数据，最长 32 字符 |

- 响应 `GenerateUrlLinkResponse(data: GenerateUrlLinkData | None)`。
