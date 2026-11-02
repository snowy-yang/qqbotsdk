# agent.md — qqbotsdk-base/ws（网关 WebSocket）

适用范围：`packages/qqbotsdk-base/src/qqbotsdk/ws/**`（`intents.py`、`payload.py`、`client.py`、`__init__.py`）。

职责：网关长连接的状态机——握手、心跳、重连、Resume、事件分发。**不含任何业务模型**。

## MUST（必须做）

- MUST 按官方顺序驱动状态机：等 `op=10 Hello` → 取 `heartbeat_interval` → 启动心跳 Task → 有 `session_id` 且 `seq` 非空发 `op=6 Resume`，否则发 `op=2 Identify`。
- MUST 在 `Identify` 里固定上报 `"shard": [0, 1]`（本 SDK 不做分片）。
- MUST 让心跳携带**最近一次收到的 `s`**（首次为 `None`），并处理 `op=11` ACK。
- MUST 按关闭码分三类处理：`4009` 保留会话走 Resume；`4001`/`4002`/`4010~4014`/`4914`/`4915` 直接终止不再重连；其余（含 `4006`/`4007`/`4900~4913`/`None`）清空会话重新 Identify。
- MUST 重连使用指数退避（`min(base * 2**(n-1), max)`，指数封顶避免溢出），并在 READY/RESUMED 成功后归零。
- MUST 让 `close()` 幂等：停心跳、关 ws、取消后台任务、投递结束哨兵；`async for` 在停止后以 `StopAsyncIteration` 结束。
- MUST 保持 `__aiter__` 只产出 `op=0` 的 Dispatch 帧（READY / RESUMED 也产出）。

## SHOULD（应当做）

- SHOULD 把无法解析或校验失败的帧记 `warning` 后忽略，而不是让整个连接崩掉。
- SHOULD 让 `wait_ready(timeout=...)` 同时等待「就绪」与「已停止」两个事件，避免无限挂起。
- SHOULD 复用 `qqbotsdk.api.core` 的 `session.client` 与 `qqbotsdk.api.auth.get_access_token()`，不要自建 HTTP 会话。

## MUST NOT（禁止做）

- MUST NOT 打印或记录 `access_token`（包括拼好的 `QQBot <token>`）；调试时只允许打印长度或事件名。
- MUST NOT 实现分片/负载均衡：不接 `shard` 参数、不封装 `GET /gateway/bot`。
- MUST NOT 在 `ws/` 里 import 业务包模型；事件体由业务包自己的 `parse_event` 解析。
- MUST NOT 依赖 aiohttp 的内建心跳（`ws_connect(heartbeat=...)` 必须为 `None`），心跳由本模块自己发。
- MUST NOT 让异常静默死亡：不可重试的终止必须留下 `error` 级日志。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk-base\src\qqbotsdk\ws
.venv\Scripts\pyright.exe
```

回归方式：用 `aiohttp.web` 起本地假网关（Hello → Identify → READY → 心跳/ACK → Dispatch → `close(4009)` → Resume → RESUMED），断言事件顺序、`Identify` 的 `shard == [0, 1]`、Resume 携带的 `session_id`/`seq`。真机联调用 `get_gateway()` 拿地址后连一次，确认能收到 READY 后正常关闭。
