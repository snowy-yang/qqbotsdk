# qqbotsdk

QQ 官方机器人 SDK（Python 3.12+）。按域拆成三个可独立安装的发行包，共享同一个 `qqbotsdk` 导入命名空间。

| 发行包 | 内容 | 依赖 |
|---|---|---|
| `qqbotsdk-base-py` | 基座：`QQBotBaseModel`、共享消息模型、鉴权与 `session`、`qqbotsdk.ws` 网关客户端 | aiohttp、loguru、pydantic、python-dotenv |
| `qqbotsdk-py` | 核心业务：群聊消息 / 群管理 / 单聊 / 素材 / 互动 / 菜单 / 面板 | `qqbotsdk-base-py` |
| `qqbotsdk-guild-py` | 频道域：guild / channel / 成员 / 身份组 / 公告 / 精华 / 日程 / 论坛 / 私信 | `qqbotsdk-base-py` |

`loguru`、`python-dotenv`、`aiohttp`、`pydantic` 统一由 base 提供，因此单独安装任一业务包都能直接用日志与 `.env`。

完整文档见 [`docs/`](docs/README.md)，可运行示例见 [`examples/`](examples/README.md)。

## 安装

```bash
pip install qqbotsdk-py                # 核心
pip install qqbotsdk-guild-py          # 只要频道
pip install "qqbotsdk-py[guild]"       # 核心 + 频道（一键）
```

`base` 会被自动带上，无需单独安装。

### 安装不完整怎么办

`qqbotsdk` 是 **PEP 420 隐式命名空间包**（三包共用，没有 `__init__.py`）。这带来一个副作用：**基座包里任意一个 `.py` 文件没落盘，`pip check` 都不会报错**，而你看到的是：

```
ModuleNotFoundError: No module named 'qqbotsdk.api.core'
```

这个信息会误导你去查 `core` 模块，真实原因却是「安装不完整」。排查顺序：`qqbotsdk.api.core` 属于 `qqbotsdk-base-py`，所以该报错的实际含义是「基座包不在或不完整」——先 `pip show -f qqbotsdk-base-py` 确认 `core.py` 在不在文件列表里，再决定是否重装。

2.0.0 版本直接重装即可（`--no-cache-dir` 绕开损坏的本地 wheel 缓存）：

```bash
pip uninstall -y qqbotsdk-py qqbotsdk-guild-py qqbotsdk-base-py
pip install --no-cache-dir qqbotsdk-py
```

注意 `pip check` **无法**发现这类问题：它只校验发行包级别的依赖是否满足，不校验包内文件是否齐全。

## 鉴权

在项目根目录的 `.env`（或环境变量）里配置机器人凭证，SDK 会自动换取并注入 `access_token`：

```ini
APPID=你的AppID
APPSECRET=你的AppSecret
TIMEOUT=5000   # 可选，HTTP 超时（毫秒），默认 5000
```

- 所有走 `qqbotsdk.api.*` 的请求都会自动带上 `Authorization: QQBot <access_token>`，业务代码不用手写请求头。
- 凭证缓存在进程内，有效期 7200 秒；剩余不足 60 秒时自动换取新凭证，并发调用只换一次。
- 需要手动拿凭证：`from qqbotsdk.api.auth import get_access_token`。
- 素材上传等发往其它域名的绝对地址不会带上鉴权头；换取凭证的接口本身也不带。
- 进程退出前建议 `await session.close()`（`from qqbotsdk.api.core import session`），否则 aiohttp 会提示会话未关闭。

## 错误处理

三级错误统一在一个异常体系里（`qqbotsdk.errors`），调用方 `except QQBotError` 就能兜住全部：

| 异常 | 触发场景 | 关键属性 |
|---|---|---|
| `QQBotAPIError` | HTTP 4xx/5xx；HTTP 200 但 body 带非零 `err_code`/`code`；201/202 返回错误体 | `status`、`err_code`、`message`、`trace_id` |
| `QQBotAuthError` | 缺少 `APPID`/`APPSECRET`；换取 access_token 失败 | `message`、`code` |
| `QQBotGatewayError` | 网关返回不可重连的关闭码（4001/4002/4010~4014/4914/4915）；网关响应缺少 `url` | `code`、`reason` |

```python
from qqbotsdk.errors import QQBotAPIError, QQBotError

try:
    await send_group_messages(group_openid, request)
except QQBotAPIError as exc:
    print(exc.err_code, exc.message, exc.trace_id)  # 40034005 回复消息msg_id已过期 abc
except QQBotError:
    ...
```

要点：

- 无响应体的接口（204 删除类、201/202 异步受理）不会再抛 `ContentTypeError`，统一返回空结果。
- **HTTP 429 自动重试**：最多 3 次，优先按 `Retry-After` 等待，否则指数退避 + 抖动，总等待不超过 30 秒；429 表示请求未被处理，因此 POST 也会重试。非 429 一律不重试。可用 `MAX_RETRIES` / `RETRY_BASE_SECONDS` 调整。
- `trace_id` 优先取响应头 `X-Tps-trace-ID`，其次取 body 的 `trace_id`，提工单时直接用它。
- 网关因致命关闭码停止时，可通过 `ws.last_error` 拿到 `QQBotGatewayError`（例如 `4914` 机器人已下架、`4915` 已封禁）。

## 分层约定

**API 层只做两件事**：1:1 薄映射（一个接口一个函数，路径参数外置，`payload.model_dump(exclude_none=True)`）与统一错误体系。调用便利、事件监听、分发、注入、快速调用一律放在上层 `qqbotsdk.app`，不在 API 层做半吊子封装。

## 快速开始（上层 `qqbotsdk.app`）

```python
from qqbotsdk.app import Bot, Context
from qqbotsdk.errors import QQBotAPIError

bot = Bot()  # 网关地址自动获取；intents 默认订阅群/单聊/频道消息/交互


@bot.on_message()  # 等价于注册 GROUP_AT_MESSAGE_CREATE / GROUP_MESSAGE_CREATE / C2C_MESSAGE_CREATE
async def on_message(ctx: Context) -> None:
    await ctx.reply(
        f"收到：{ctx.event.content}"
    )  # event_id / msg_id / msg_seq 自动处理


@bot.on("FRIEND_ADD")
async def on_friend_add(ctx: Context) -> None:
    await ctx.reply("欢迎～")


@bot.middleware  # 洋葱模型：先注册在外层
async def log(ctx: Context, call_next: None) -> None:
    ctx.state["from_middleware"] = True
    await call_next()


@bot.on_error()  # handler / 中间件抛错都进这里
async def on_error(ctx: Context | None, exc: BaseException) -> None:
    if isinstance(exc, QQBotAPIError):
        print(exc.err_code, exc.message, exc.trace_id)
    else:
        raise exc


bot.run()  # 内部 asyncio.run(bot.start())
```

- **监听**：`@bot.on("事件名")` 精确注册，`@bot.on("*")` 通配全部 Dispatch；同事件多 handler 按注册顺序执行，返回 `False` 可阻断后续。
- **分发**：每个事件在独立任务里跑，不阻塞收包与心跳；handler 异常只进 `on_error`，不会断连。
- **注入**：handler 只收一个 `ctx` —— `ctx.event`（已解析的 typed 模型）、`ctx.payload`（原始帧，含 `event_id`/`s`）、`ctx.state`（中间件与 handler 共享）、`ctx.bot`。
- **快速调用**：`ctx.reply(...)` 自动选群/单聊接口并管理 `msg_seq`；`ctx.send(...)` 发主动消息。
- **中间件**：`async def mw(ctx, call_next)`，`await call_next()` 向内，不调用即拦截。
- 生命周期：`bot.run()` 阻塞式；也可 `await bot.start()` / `await bot.stop()` 自行管理。

## 长连接（底层）

`qqbotsdk.ws` 是原始网关客户端，`async for` 与注册回调两种消费方式可以并存：

```python
import asyncio

from qqbotsdk.api.core import session
from qqbotsdk.model.event import parse_event
from qqbotsdk.ws import DEFAULT_INTENTS, WILDCARD_EVENT, GatewayPayload, QQBotWebSocket


async def on_any(payload: GatewayPayload) -> None:
    event = parse_event(payload)  # 未建模事件返回 None
    print(payload.t, event)


async def main() -> None:
    async with QQBotWebSocket(intents=DEFAULT_INTENTS) as ws:  # 网关地址自动获取
        ws.on(WILDCARD_EVENT, on_any)  # 通配：所有 Dispatch
        ws.on("GROUP_AT_MESSAGE_CREATE", on_any)  # 精确事件
        await ws.wait_ready()
        async for payload in ws:  # 也可以继续逐个消费
            print(payload.t)
    await session.close()


asyncio.run(main())
```

- 回调以独立任务派发，不会阻塞收包与心跳；单个回调抛异常只记录日志，不影响连接。
- `ws.off(事件名)` / `ws.off(事件名, handler)` 可取消注册；`close()` 会回收未完成回调任务。

心跳、断线重连、Resume 补发与关闭码策略都由客户端处理，详见 `packages/qqbotsdk-base/README.md`。

**不做分片（负载均衡）**：本 SDK 的网关客户端固定单连接，`Identify` 一律上报 `shard=[0, 1]`，因此不提供 `shard` 参数，也不再封装 `GET /gateway/bot`（该接口只用来取推荐分片数）。机器人规模不大时单连接即可接收全部事件；确有分片需求请自行拆包并发起多条连接。

## 事件模型

收到的事件体（`d`）都有对应的 pydantic 模型，按域分两个注册表：

| 注册表 | 覆盖事件 |
|---|---|
| `qqbotsdk.model.event`（`qqbotsdk-py`） | 群聊 / 单聊 / 好友 / 订阅消息 / 互动，共 16 个事件 |
| `qqbotsdk.model.guild.event`（`qqbotsdk-guild-py`） | 频道 / 子频道 / 消息 / 成员 / 表情表态 / 消息审核 / 论坛 / 音频，共 40 个事件 |

```python
from qqbotsdk.model.event import EVENT_MODELS, parse_event  # 群聊/单聊/互动
from qqbotsdk.model.guild.event import (
    parse_event as parse_guild_event,
)  # 频道（需装 guild 包）

event = parse_event(payload) or parse_guild_event(payload)
print(EVENT_MODELS)  # 事件名 -> 模型类
```

事件模型只描述事件体，信封（`id` / `op` / `s` / `t`）由 `qqbotsdk.ws.payload.GatewayPayload` 承载；`READY` 的事件体是 `qqbotsdk.ws.payload.ReadyContent`。

## 仓库结构

```
packages/
  qqbotsdk-base/       # qqbotsdk-base-py
  qqbotsdk/            # qqbotsdk-py
  qqbotsdk-guild/      # qqbotsdk-guild-py
```

三个包的 `qqbotsdk/` 顶层目录均为隐式命名空间包（不含 `__init__.py`），可任意组合安装；子包（如 `qqbotsdk/ws/`）仍带自己的 `__init__.py` 用于汇总导出。

## 开发约定

每个模块目录都有一份 `agent.md`，用 MUST / SHOULD / MUST NOT 写清「必须做、应当做、禁止做」。改代码前先读目标目录及上级目录的 `agent.md`，冲突时就近优先。

| 位置 | 覆盖内容 |
|---|---|
| `agent.md` | 仓库总则：依赖方向、质量门、废弃字段政策、不做分片、凭证安全 |
| `packages/qqbotsdk-base/agent.md` | 基座包总则 |
| `packages/qqbotsdk-base/src/qqbotsdk/api/agent.md` | HTTP 会话与鉴权（注入请求头、token 刷新） |
| `packages/qqbotsdk-base/src/qqbotsdk/model/agent.md` | 模型写法与共享子模型 |
| `packages/qqbotsdk-base/src/qqbotsdk/ws/agent.md` | 网关状态机、心跳、重连、关闭码策略 |
| `packages/qqbotsdk/agent.md` | 核心业务包总则 |
| `packages/qqbotsdk/src/qqbotsdk/api/agent.md` | 顶层接口映射规范 |
| `packages/qqbotsdk/src/qqbotsdk/api/group/agent.md` | 群聊接口规范 |
| `packages/qqbotsdk/src/qqbotsdk/model/agent.md` | 顶层请求/响应模型 |
| `packages/qqbotsdk/src/qqbotsdk/model/group/agent.md` | 群聊/群管理模型 |
| `packages/qqbotsdk/src/qqbotsdk/model/user/agent.md` | 单聊模型 |
| `packages/qqbotsdk/src/qqbotsdk/model/event/agent.md` | 事件模型与注册表 |
| `packages/qqbotsdk/src/qqbotsdk/app/agent.md` | 上层框架（监听/分发/注入/中间件/快捷调用） |
| `packages/qqbotsdk-guild/agent.md` | 频道域包总则 |
| `packages/qqbotsdk-guild/src/qqbotsdk/api/guild/agent.md` | 频道域接口规范 |
| `packages/qqbotsdk-guild/src/qqbotsdk/model/guild/agent.md` | 频道域模型与事件规范 |

## 开发

```bash
uv sync --all-packages
uv run ruff check .
uv run ruff format --check .
uv run pyright              # 已通过 venvPath/venv 指向 .venv
```
