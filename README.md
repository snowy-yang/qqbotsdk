# qqbotsdk

QQ 官方机器人 SDK（Python 3.12+）。按域拆成三个可独立安装的发行包，共享同一个 `qqbotsdk` 导入命名空间。

| 发行包 | 内容 | 依赖 |
|---|---|---|
| `qqbotsdk-base-py` | 基座：`QQBotBaseModel`、共享消息模型、`session` | aiohttp、loguru、pydantic、python-dotenv |
| `qqbotsdk-py` | 核心业务：群聊消息 / 群管理 / 单聊 / 素材 / 互动 / 菜单 / 面板 | `qqbotsdk-base-py` |
| `qqbotsdk-guild-py` | 频道域：guild / channel / 成员 / 身份组 / 公告 / 精华 / 日程 / 论坛 / 私信 | `qqbotsdk-base-py` |

`loguru`、`python-dotenv`、`aiohttp`、`pydantic` 统一由 base 提供，因此单独安装任一业务包都能直接用日志与 `.env`。

## 安装

```bash
pip install qqbotsdk-py                # 核心
pip install qqbotsdk-guild-py          # 只要频道
pip install "qqbotsdk-py[guild]"       # 核心 + 频道（一键）
```

`base` 会被自动带上，无需单独安装。

## 仓库结构

```
packages/
  qqbotsdk-base/       # qqbotsdk-base-py
  qqbotsdk/            # qqbotsdk-py
  qqbotsdk-guild/      # qqbotsdk-guild-py
```

三个包均为隐式命名空间包（不含 `__init__.py`），可任意组合安装。

## 开发

```bash
uv sync --all-packages
uv run ruff check .
uv run ruff format --check .
uv run pyright
```
