# 示例

可运行的完整示例，均以仓库根目录为工作目录启动（`.env`、`intents.toml` 放在根目录）。

| 示例 | 内容 |
|---|---|
| `group_bot/main.py` | @消息被动回复、`/img` 富媒体图片、`/btn` Markdown 按钮卡片与点击回调、入群欢迎、单聊回复 |

## 运行前提

1. 根目录 `.env` 配好 `APPID`/`APPSECRET`；
2. `intents.toml` 订阅 `GROUP_AND_C2C_EVENT` 与 `INTERACTION`（仓库默认配置已满足）；
3. 要求机器人已开通群聊能力并拉入测试群。

## 运行

```bash
uv run python examples/group_bot/main.py
```

handler 写法见[事件处理](../docs/guide/handlers.md)。
