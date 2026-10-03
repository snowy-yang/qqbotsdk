# 快速开始

从零开始接入 QQ 官方机器人：装包、配置、跑起第一个回声机器人。
事件处理细节见[事件处理](/docs/guide/handlers.md)，收发消息的规则见[收发消息](/docs/guide/messaging.md)。

## 接入准备

1. 到 [QQ 开放平台](https://q.qq.com) 注册开发者账号并创建机器人，拿到 `AppID` 与 `AppSecret`（即 `.env` 里的 `APPID`/`APPSECRET`）。
2. 确认机器人的可用场景，这决定了你能收哪些事件、发哪些消息：
   - **群 / 单聊（v2 接口）**：需要在开放平台开通对应能力，事件与消息接口均用 openid（`group_openid` / `user_openid`），与用户的 QQ 号互不可见。
   - **频道公域机器人**：只能收 `AT_MESSAGE_CREATE`（@机器人才触发），发消息必须带 `msg_id` 被动回复。
   - **频道私域机器人**：可订阅 `GUILD_MESSAGES`（全量消息）与论坛事件，可主动发消息、撤回消息。

## 安装

```bash
pip install qqbotsdk-py        # 或
uv add qqbotsdk-py
```

导入名是 `qqbotsdk`（发行包名带 `-py` 后缀是因为 PyPI 上 `qqbotsdk` 与已有项目撞名）。要求 Python ≥ 3.12。

## 最小可跑示例

项目根目录放两个文件。

`.env`（SDK 启动时自动加载，缺失 `APPID`/`APPSECRET` 启动即报错）：

```ini
APPID=你的AppID
APPSECRET=你的AppSecret
```

`intents.toml`（事件订阅按分组开关，详见[配置与订阅](/docs/guide/config.md)）：

```toml
GROUP_AND_C2C_EVENT = true
```

`main.py`：

```python
from qqbotsdk import Bot
from qqbotsdk.api import BotApi
from qqbotsdk.payloads import GroupAtMessage

bot = Bot()


# handler 形参按标注注入：payload dataclass 与 BotApi 等组件可任意组合
@bot.on("GROUP_AT_MESSAGE_CREATE")
async def on_group_message(msg: GroupAtMessage, api: BotApi):
    # 被动回复带 msg_id（5 分钟内有效，多次回复递增 msg_seq）；失败抛 ApiError
    await api.post_group_message(
        msg.group_openid,
        content=f"你说：{msg.content}",
        msg_id=msg.id,
    )


if __name__ == "__main__":
    bot.run()
```

运行：

```bash
uv run python main.py
```

把机器人拉进测试群，@它说句话，就会收到回声。

## 下一步

- 两种接入方式（WebSocket / Webhook）怎么选：[配置与订阅](/docs/guide/config.md)
- handler 参数注入、后台并发、自定义组件：[事件处理](/docs/guide/handlers.md)
- 富媒体、Markdown 按钮、被动回复时限等消息规则：[收发消息](/docs/guide/messaging.md)
- 完整示例（按钮卡片、入群欢迎、单聊、webhook）：[examples/](https://github.com/snowy-yang/qqbotsdk/tree/main/examples)
