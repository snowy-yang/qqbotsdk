# qqbotsdk-guild-py

QQ 官方机器人 SDK 频道域子包：guild / channel / 成员 / 身份组 / 公告 / 精华 / 日程 / 论坛 / 私信。

```bash
pip install qqbotsdk-guild-py
# 或随核心包一起装
pip install "qqbotsdk-py[guild]"
```

```python
from qqbotsdk.api.guild.channel import get_guild_channels
from qqbotsdk.api.guild.messages import send_channel_messages
from qqbotsdk.model.guild.messages import SendChannelMessagesRequest
```
