# qqbotsdk-py

QQ 官方机器人 SDK 核心包：群聊 / 单聊 / 素材 / 互动 / 菜单 / 面板，以及上层框架 `qqbotsdk.app`。

```bash
pip install qqbotsdk-py
pip install "qqbotsdk-py[guild]"   # 额外安装频道域子包
```

## 上层框架（推荐入口）

```python
from qqbotsdk.app import Bot, Context

bot = Bot()


@bot.on_message()
async def on_message(ctx: Context) -> None:
    await ctx.reply(f"收到：{ctx.event.content}")


bot.run()
```

事件监听、分发、中间件、注入与快捷回复都在这一层，详见仓库根 `README.md`。

## API 层（薄映射）

`api/` 与 `model/` 是一对一的协议映射，一个接口一个函数，路径参数外置：

```python
from qqbotsdk.api.group.messages import send_group_messages
from qqbotsdk.model.group.messages import SendGroupMessagesRequest

await send_group_messages(
    group_openid,
    SendGroupMessagesRequest(msg_type=0, content="hi"),
)
```

错误统一为 `qqbotsdk.errors` 里的三级异常；429 自动重试；删除类接口返回空结果不抛异常。
