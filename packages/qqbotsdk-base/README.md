# qqbotsdk-base-py

QQ 官方机器人 SDK 基座包。各业务域包共用的最小依赖面与共享代码：

- `qqbotsdk.model.core`：`QQBotBaseModel`（pydantic 基类）
- `qqbotsdk.model.sub.messages`：共享消息模型（键盘、Markdown、引用、富媒体等）
- `qqbotsdk.api.core`：共享 `session`（指向 `https://api.bot.qq.com` 的 `ClientSession`）
- 依赖：`aiohttp`、`pydantic`、`loguru`、`python-dotenv`

## 安装

```bash
pip install qqbotsdk-base-py
```

通常不需要直接安装；装 `qqbotsdk-py` 或 `qqbotsdk-guild-py` 时会自动带上。

## 命名空间

三个发行包共享 `qqbotsdk` 导入命名空间（隐式命名空间包，均不含 `__init__.py`），可任意组合安装。
