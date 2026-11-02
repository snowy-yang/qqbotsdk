# qqbotsdk-base-py

QQ 官方机器人 SDK 基座包。各业务域包共用的最小依赖面与共享代码：

- `qqbotsdk.model.core`：`QQBotBaseModel`（pydantic 基类）
- `qqbotsdk.model.sub.messages`：共享消息模型（键盘、Markdown、引用、富媒体等）
- `qqbotsdk.api.core`：懒加载的共享 `session`（指向 `https://api.bot.qq.com`，自动注入鉴权头）
- `qqbotsdk.api.auth`：`access_token` 的获取、缓存与自动刷新
- `qqbotsdk.ws`：网关 WebSocket 客户端
- 依赖：`aiohttp`、`pydantic`、`loguru`、`python-dotenv`

## 安装

```bash
pip install qqbotsdk-base-py
```

通常不需要直接安装；装 `qqbotsdk-py` 或 `qqbotsdk-guild-py` 时会自动带上。

## 鉴权

在 `.env` 或环境变量里配置 `APPID` / `APPSECRET`（可选 `TIMEOUT`，单位毫秒）：

```python
from qqbotsdk.api.auth import get_access_token
from qqbotsdk.api.bot import get_me  # 请求会自动带上 Authorization: QQBot <token>
from qqbotsdk.api.core import session

me = await get_me()  # 不用手写请求头
token = await get_access_token()  # 需要自己持有时
await session.close()  # 进程退出前收尾
```

- 凭证进程内缓存，有效期 7200 秒，剩余不足 60 秒时自动换取；并发调用只换一次。
- 换取凭证的接口本身不带鉴权头；发往其它域名的绝对地址（如 COS 预签名上传）也不带。
- `session` 在首次使用时才创建，因此可以在任意位置 import，不需要先有事件循环。

## 命名空间

三个发行包共享 `qqbotsdk` 导入命名空间（各包的 `qqbotsdk/` 顶层目录不含 `__init__.py`，子包如 `qqbotsdk/ws/` 仍带自己的 `__init__.py` 以汇总导出），可任意组合安装。

## WebSocket 网关

`qqbotsdk.ws` 提供网关客户端（只依赖 aiohttp 与 pydantic，不含业务模型）：

```python
import asyncio

from qqbotsdk.ws import DEFAULT_INTENTS, QQBotWebSocket


async def main() -> None:
    async with QQBotWebSocket(intents=DEFAULT_INTENTS) as ws:  # 网关地址自动获取
        await ws.wait_ready()
        async for payload in ws:
            print(payload.t, payload.d)


asyncio.run(main())
```

要点：

- `Intents`（`IntFlag`）声明订阅的事件位；`DEFAULT_INTENTS` = 群与单聊消息 + 公域频道消息 + 频道成员 + 交互事件。
- `async for` 只产出 `op=0` 的 Dispatch 事件（`payload.t` / `payload.d` / `payload.s` / `payload.id`），READY 与 RESUMED 也会产出；READY 的事件体可用 `ReadyContent` 解析。
- **不做分片**：固定单连接，`Identify` 一律上报 `shard=[0, 1]`，没有 `shard` 参数，也不封装 `GET /gateway/bot`；需要多连接负载均衡请自行拆分。
- 心跳按 Hello 下发的 `heartbeat_interval` 由独立 `asyncio.Task` 定时发送，收到 op=11 ACK 后复位，退出时自动取消。
- 断线自动重连（指数退避）：仍持有 `session_id` 与 `seq` 时走 Resume，否则重新 Identify；不可重试的关闭码（4001、4002、4010~4014、4914、4915）会直接终止。
- `url` 省略时**每次建连前自动调用 `GET /gateway` 获取**（地址可能随调度变化，不硬编码域名）；也可显式传 `url=` 覆盖。
- 因致命关闭码停止时，`ws.last_error` 是 `QQBotGatewayError`（带 `code`，例如 `4914` 已下架、`4915` 已封禁）。
- `await ws.wait_ready()` 等到 READY 或 RESUMED；`await ws.close()` 或退出 `async with` 时关闭连接并取消后台任务；日志不会打印 access_token。
- 可注册回调：`ws.on("GROUP_AT_MESSAGE_CREATE", handler)` / `ws.on(WILDCARD_EVENT, handler)`，回调以独立任务派发、不阻塞收包，异常只记日志；`ws.off(...)` 取消，注册回调后 `async for` 仍可用。
- HTTP 429 自动重试（最多 3 次、`Retry-After` 优先、指数退避 + 抖动、总等待 ≤ 30 秒），可用 `MAX_RETRIES` / `RETRY_BASE_SECONDS` 调整。

## 错误体系

`qqbotsdk.errors` 定义三级错误，全部继承 `QQBotError`：

- `QQBotAPIError`：HTTP 4xx/5xx、body 带非零 `err_code`/`code`、201/202 错误体（`status`/`err_code`/`message`/`trace_id`）。
- `QQBotAuthError`：凭证缺失或换取 access_token 失败。
- `QQBotGatewayError`：网关致命关闭码、网关响应缺少 `url`。

`api/core.py` 通过自定义 `response_class` 统一做这套检查，因此业务 api 函数里看不到任何错误处理代码。
