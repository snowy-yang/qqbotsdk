# 示例

所有示例都在仓库根目录运行（worktree 已通过 `uv sync --all-packages` 把三个包装进 `.venv`）。

```bash
copy .env.example .env      # 或者手动创建 .env，填 APPID / APPSECRET
uv run python examples/hello_bot.py
```

| 示例 | 说明 | 需要 |
|---|---|---|
| [hello_bot.py](hello_bot.py) | 最小回声机器人：`@bot.on_message()` + `ctx.reply()` + `on_error` | 核心包 |
| [middleware.py](middleware.py) | 中间件：计时、限流、关键词过滤、`return False` 阻断 | 核心包 |
| [raw_websocket.py](raw_websocket.py) | 不用上层框架，直接消费原始帧（`async for` 与 `on()` 并存） | 核心包 |
| [api_calls.py](api_calls.py) | 只调 HTTP：取机器人信息、群信息、成员列表、发消息、撤回 | 核心包 |
| [guild_events.py](guild_events.py) | 频道域事件：guild / channel / 成员 / @消息 | `qqbotsdk-guild-py` |
| [interaction_bot.py](interaction_bot.py) | 按钮互动回包（`ack_interaction`）、入群申请审批（`approve_join_request`）、卡片与键盘 | 核心包 |

## 运行前

1. 在开放平台创建机器人，拿到 `APPID` / `APPSECRET`；
2. 仓库根目录创建 `.env`（已被 `.gitignore` 忽略）：

```ini
APPID=你的AppID
APPSECRET=你的AppSecret
TIMEOUT=5000
```

3. 把机器人拉进群 / 频道，并在开放平台配置好事件订阅权限（intents 不匹配会断连，关闭码 4013/4014）。

## 注意事项

- 示例都只打印日志，不会自动回复真实用户之外的内容；`api_calls.py` 会真的发一条消息再撤回，请用测试群。
- 主动消息有频控（群 60 qpm、单聊 20 qpm 等），别用示例刷接口。
- 被动回复窗口：群消息 5 分钟 / 5 次，单聊 60 分钟 / 4 次；过期会返回 `40034005`。
