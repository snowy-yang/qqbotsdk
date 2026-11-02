# 底层网关客户端 `qqbotsdk.ws`

上层 `qqbotsdk.app` 已经封装好了；只有需要自己控制分发时才直接用这一层。

```python
import asyncio

from qqbotsdk.api.core import session
from qqbotsdk.model.event import parse_event
from qqbotsdk.ws import DEFAULT_INTENTS, QQBotWebSocket


async def main() -> None:
    async with QQBotWebSocket(intents=DEFAULT_INTENTS) as ws:
        await ws.wait_ready()
        async for payload in ws:
            print(payload.t, parse_event(payload))
    await session.close()


asyncio.run(main())
```

## 构造参数

```python
QQBotWebSocket(
    *,
    intents: Intents = DEFAULT_INTENTS,
    url: str | None = None,          # 省略则每次建连前 GET /gateway 自动获取
    auto_reconnect: bool = True,
    max_reconnect_attempts: int | None = None,   # None = 不限
    backoff_base: float = 1.0,
    backoff_max: float = 60.0,
)
```

## 两种消费方式（可并存）

```python
# 1) 逐个消费
async for payload in ws:
    ...

# 2) 注册回调（独立任务派发，不阻塞收包）
ws.on("GROUP_AT_MESSAGE_CREATE", handler)  # 精确事件
ws.on("*", handler)  # 通配，等价 WILDCARD_EVENT
ws.off("GROUP_AT_MESSAGE_CREATE")  # 清空该事件
ws.off("GROUP_AT_MESSAGE_CREATE", handler)  # 摘掉单个
```

回调签名 `async def handler(payload: GatewayPayload) -> None`；抛异常只记日志，不影响连接。

## 属性与方法

| 成员 | 说明 |
|---|---|
| `await ws.wait_ready(timeout=None)` | 等到 READY 或 RESUMED |
| `await ws.close()` | 关闭连接、取消心跳与回调任务（幂等） |
| `ws.session_id` / `ws.seq` | 会话 ID / 最近序号 |
| `ws.last_error` | 因致命关闭码停止时的 `QQBotGatewayError` |
| `async with ws:` | 进入启动、退出关闭 |

## 协议行为（都已内置）

- **握手**：`op=10 Hello` 取 `heartbeat_interval` → 起独立心跳任务 → 有 `session_id`+`seq` 发 `op=6 Resume`，否则发 `op=2 Identify`（`shard` 固定 `[0, 1]`）。
- **心跳**：定时发 `op=1`，携带最近一次 `s`；收到 `op=11` ACK 复位。
- **重连**：指数退避（`min(base * 2**(n-1), max)`），`op=7` 保留会话、`op=9` 清会话重新 Identify。
- **关闭码**：

| 关闭码 | 行为 |
|---|---|
| `4009` | 保留会话，重连后 Resume |
| `4001` `4002` `4010~4014` `4914` `4915` | 终止，不再重连（原因见 `last_error`） |
| 其它（含 `4006` `4007` `4900~4913`） | 清空会话，重新 Identify |

## 不做分片

固定单连接，`Identify` 恒上报 `shard=[0, 1]`，也不封装 `GET /gateway/bot`。规模不大时单连接足够；确有负载均衡需求请自行拆包并发起多条连接。

## 与上层的选择

| 场景 | 用哪个 |
|---|---|
| 写机器人业务 | `qqbotsdk.app`（`Bot` + `Context`） |
| 自己实现分发/中间件体系 | `qqbotsdk.ws` |
| 只调 HTTP 接口、不要长连接 | `qqbotsdk.api` |
