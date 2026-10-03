# 核心框架 API

`Bot` 门面、分发层（`EventEmitter`）、事件封装（`Event`）与错误体系。
上手流程见[快速开始](/docs/guide/start.md)，分层与装配见[架构设计](/docs/ARCHITECTURE.md)。

## 顶层导出

```python
from qqbotsdk import (
    Bot,                     # 门面：on/run/start/call_api/api/services
    EventEmitter, EventQueue,   # 分发层
    BaseProtocol,            # 协议处理器接口（自定义接入方式时继承）
    Config, Connecter,       # 配置与连接器接口
)
```

| 名称 | 说明 |
|---|---|
| `Bot(config=None)` | 门面类，见下节 |
| `EventEmitter(queue=None)` | 分发主体，`Bot` 内部持有；`queue` 不传自动创建 |
| `EventQueue()` | 业务事件通道（连接层 → 分发层，单向）；需多处共享时手动传入（`bot.queue` 取实例） |
| `Config` | frozen dataclass，环境变量一次性读齐（字段表见[配置与订阅](/docs/guide/config.md#env-配置)） |
| `Connecter` | 连接适配器接口（`typing.Protocol`），按 `CONNECTER` 自动选择实现 |
| `BaseProtocol` | 协议处理器接口（`protocol.py`），自定义接入方式时实现 `on_frame(payload)` |

子包按需导入：

```python
from qqbotsdk.api import BotApi, ApiError
from qqbotsdk.payloads import GroupAtMessage, EVENT_TYPES, parse_event
from qqbotsdk.events import Event
```

## Bot

```python
bot = Bot()                        # 构造即读 .env 校验配置（fail fast）

@bot.on("GROUP_AT_MESSAGE_CREATE") # 注册 handler，语义与 EventEmitter.on 一致
async def handler(msg, api): ...

bot.run()                          # 同步入口：阻塞运行，Ctrl+C 优雅退出
```

| 成员 | 说明 |
|---|---|
| `Bot(config=None)` | 不传 config 时 `Config.load()` 读环境变量；缺 `APPID`/`APPSECRET` 构造即抛 `ValueError` |
| `bot.on(event, fn=None, *, background=False)` | 注册 handler；`event` 为事件 `t` 名或 `Opcode`，装饰器/直传皆可 |
| `bot.run()` | 同步入口：`asyncio.run(start())`，`KeyboardInterrupt` 记日志退出 |
| `await bot.start()` | 异步入口：装配组件并常驻运行，供嵌入外部 asyncio 应用 |
| `bot.call_api(method, path, **kwargs)` | 通用 REST 入口：带鉴权头、429 退避重试、401 刷新 token 重试；kwargs 透传 aiohttp（`json=`/`params=` 等） |
| `bot.api` | 类型化 API 门面（`BotApi`，97 个方法），启动（run/start）后可用，之前抛 `RuntimeError` |
| `bot.services` | `dict[type, Any]` 组件登记表；SDK 启动登记 8 项内置组件，也可登记自定义类型（见[事件处理](/docs/guide/handlers.md#自定义组件注入)） |
| `bot.queue` | 事件队列实例 |
| `bot.config` | `Config` 实例 |

## EventEmitter

`Bot` 内部的分发主体（`bot._emitter`），独立导入用于测试或自定义装配：

```python
ee = EventEmitter()

@ee.on("GROUP_AT_MESSAGE_CREATE")     # 业务事件用 t 名（仅 op=0 会分发到这里）
async def handler(...): ...

@ee.on("GROUP_AT_MESSAGE_CREATE", background=True)   # 后台并发执行，不阻塞事件流
async def slow(...): ...
```

- **只分发业务事件**：`EventEmitter` 只处理 op=0（DISPATCH）事件，按 payload 的 `t` 名路由。协议帧（HELLO/READY/INVALID_SESSION/op=13 等）由各接入方式的协议处理器（`WebsocketProtocol`/`WebhookProtocol`）在连接器内就地处理，不进事件队列、也不会触达你的 handler。
- **注册与顺序**：同一函数对同一事件重复注册只生效一次；handler 按注册顺序串行执行（`background=True` 的除外）。
- **异常隔离**：handler 异常就地记录（loguru），不影响同事件其他 handler 与主循环。
- **后台并发**：`background=True` 的 handler 进后台任务，emit 不等它；同一事件内失去先后保证，仅用于业务 handler。`bot.run()` 退出时统一取消在飞后台任务。
- 业务 handler 的返回值不回流；回复消息请在 handler 里显式调 `BotApi`。

handler 参数注入约定表见[事件处理](/docs/guide/handlers.md)。

## Event

`from qqbotsdk.events import Event`，业务事件推送信封（op/t/d/id）的轻量封装，只封装信封语义、不做字段名映射；事件体字段请标注对应 payload dataclass（见[事件 payload](/docs/api/events.md)）获取解析结果：

| 属性 | 说明 |
|---|---|
| `.raw` | 完整线上 payload（含 op/t/d） |
| `.data` | `d` 的 dict 拷贝 |
| `.typed` | `d` 的 dataclass 解析结果（未知事件类型为 dict） |
| `.type` | 事件 t 名 |
| `.event_id` | 推送信封顶层的事件 id（与 op/t/d 平级，形如 `INTERACTION_CREATE:uuid`）；非消息事件（`INTERACTION_CREATE`/`GROUP_ADD_ROBOT` 等）的被动回复凭据只有这里能拿到，事件体里的裸 UUID 不行（官方点名的常见坑）；消息事件的被动回复凭据是事件体的 `d.id`（payload 的 `.id` 字段，即 msg_id），不用这里 |

## 错误体系

`ApiError(RuntimeError)`，重试后仍失败（HTTP ≥400）时抛出：

| 属性 | 说明 |
|---|---|
| `.status` | HTTP 状态码 |
| `.code` | 官方业务 code（响应体中的 `code`） |
| `.message` | 官方错误描述 |

鉴权阶段（换取 access_token）的失败抛 `TokenError`（`from qqbotsdk.token import TokenError`），与 `ApiError` 同构（`RuntimeError` 子类，同样携带 `.status`/`.code`/`.message`）——appid/secret 配置错误在这里暴露 QQ 返回的真实原因。

`BotApi` 的请求内核（`api/core.py`）：自动附带 `Authorization: QQBot <token>` 鉴权头并刷新 token；429 限流自动重试（最多 3 次，优先 `Retry-After`，退避封顶 30s）；401 强制刷新 token 后重试一次。`bot.call_api` 与全部类型化方法共享该内核。

## 内部模块索引

维护者视角的分层与装配见[架构设计](/docs/ARCHITECTURE.md)：

| 模块 | 职责 |
|---|---|
| `bot.py` | `Bot` 门面：组件装配、`run`/`start` 生命周期 |
| `connecter.py` | `WebsocketConnecter` / `WebhookConnecter`：接入归一为业务事件流入、出站帧流出 |
| `protocol.py` | `BaseProtocol` 协议处理器接口（`on_frame`，由连接适配器逐帧调用） |
| `ws_protocol.py` | IDENTIFY/RESUME 鉴权、会话语义与 `s` 序列号（心跳在 connecter 内） |
| `webhook_protocol.py` | op=13 验证应答 |
| `queue.py` / `session.py` / `token.py` / `crypto.py` | 业务事件通道、ws 会话状态、token 缓存、Ed25519 签名 |
| `model.py` | Opcode、payload 类型、Intent 位掩码 |
