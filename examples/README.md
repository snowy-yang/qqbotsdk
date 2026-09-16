# 示例

可运行的完整示例，均以仓库根目录为工作目录启动（`.env`、`intents.toml` 放在根目录）。

| 示例 | 接入方式 | 内容 |
|---|---|---|
| `group_bot/main.py` | WebSocket | @消息被动回复、`/img` 富媒体图片、`/btn` Markdown 按钮卡片与点击回调、入群欢迎、单聊回复 |
| `webhook_bot/main.py` | Webhook | HTTP 回调收群 @消息并被动回复的最小接入 |

## 运行前提

1. 根目录 `.env` 配好 `APPID`/`APPSECRET`（`webhook_bot` 需另设 `CONNECTER=webhook`）；
2. `intents.toml` 开启对应事件分组（`group_bot` 需 `GROUP_AND_C2C_EVENT` 与 `INTERACTION`，`webhook_bot` 需 `GROUP_AND_C2C_EVENT`）；
3. `group_bot` 要求机器人已开通群聊能力并拉入测试群；`webhook_bot` 要求公网 HTTPS 部署（平台仅支持 80/443/8080/8443 端口，本地调试可用内网穿透）。

## 运行

```bash
uv run python examples/group_bot/main.py
uv run python examples/webhook_bot/main.py
```

Webhook 示例启动后，把 `https://<你的域名>:<端口>/qqbot/webhook` 填到开放平台回调地址；保存时平台先发 op=13 验证请求，SDK 自动完成签名应答。

接入方式切换与 handler 写法详见 [使用指南](docs/GUIDE.md#接入方式选择)。
