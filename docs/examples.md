# 代码示例

示例可运行，源码在仓库 `examples/` 目录，每个文件顶部都写了运行方式。

```bash
uv sync --all-packages
cp .env.example .env        # 填入 APPID / APPSECRET
uv run python examples/hello_bot.py
```

## 清单

| 示例 | 学到什么 | 依赖 |
|---|---|---|
| [`examples/hello_bot.py`](../examples/hello_bot.py) | `Bot` + `@bot.on_message()` + `ctx.reply()` + `on_error`，最小可用机器人 | 核心包 |
| [`examples/middleware.py`](../examples/middleware.py) | 洋葱中间件：计时、限流、过滤、`return False` 阻断后续 handler | 核心包 |
| [`examples/raw_websocket.py`](../examples/raw_websocket.py) | 底层 `QQBotWebSocket`：`async for` 与 `on()` 并存、`last_error` | 核心包 |
| [`examples/api_calls.py`](../examples/api_calls.py) | 纯 HTTP 用法：`get_me` / 群信息 / 成员列表 / 发消息 / 撤回 | 核心包 |
| [`examples/guild_events.py`](../examples/guild_events.py) | 频道域事件与 `Intents` 收窄 | `qqbotsdk-guild-py` |
| [`examples/interaction_bot.py`](../examples/interaction_bot.py) | 按钮互动回包、入群申请审批、带键盘的 Markdown | 核心包 |

## 三个最小片段

### 回声机器人

```python
from qqbotsdk.app import Bot, Context

bot = Bot()


@bot.on_message()
async def on_message(ctx: Context) -> None:
    await ctx.reply(f"收到：{ctx.event.content}")


bot.run()
```

### 中间件

```python
@bot.middleware
async def timing(ctx: Context, call_next) -> None:
    await call_next()  # 不调用即拦截该事件
    print("done", ctx.event_name)
```

### 只调接口

```python
from qqbotsdk.api.bot import get_me

me = await get_me()
print(me.username)
```

更多细节见 [app.md](app.md)、[api.md](api.md)、[events.md](events.md)、[ws.md](ws.md)。
