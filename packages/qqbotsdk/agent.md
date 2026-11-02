# agent.md — qqbotsdk-py（核心业务包）

适用范围：`packages/qqbotsdk/**`。上级规定见仓库根 `agent.md`，基座细则见 `packages/qqbotsdk-base/agent.md`。

覆盖业务域：群聊消息、群管理、单聊、素材、互动、菜单、面板、机器人基础、事件模型。

## MUST（必须做）

- MUST 只依赖 `qqbotsdk-base-py`；**不得** import `qqbotsdk-guild-py`（guild 是 optional extra，反向依赖会让裸装 `ImportError`）。
- MUST 让 api 层保持薄映射，模型层只描述数据结构；不要在 api 层塞业务流程（唯一例外是 `api/media.py` 的本地校验/摘要计算，改动前先看 `api/agent.md`）。
- MUST 新增接口时同时给三样东西：`XxxRequest`（如需请求体）、`XxxResponse`（如需响应体）、`async def` 映射函数。
- MUST 在改动后跑通仓库质量门（ruff check / ruff format --check / pyright）。

## SHOULD（应当做）

- SHOULD 按域组织文件：`api/` 与 `model/` 保持同名对应（例如 `api/group/mute.py` ↔ `model/group/mute.py`）。
- SHOULD 新增响应模型时让可选字段默认为 `None`，避免服务端字段缺失导致解析失败。
- SHOULD 用 `qqbotsdk-base` 已有的共享子模型，而不是在本包重复定义消息/键盘/Markdown 结构。

## MUST NOT（禁止做）

- MUST NOT 在一个接口里做多步业务编排（例如「先上传再发送」），这类组合留给调用方或未来的高层模块。
- MUST NOT 修改 `qqbotsdk-base` 的文件来适配本包需求；需要改基座时先确认影响面（三个包共用）。
- MUST NOT 建模官方标注【已废弃】的字段或接口。
- MUST NOT 重命名已公开的类/函数（跨包引用，破坏性）。

## 子模块

| 子模块 | 职责 | 细则 |
|---|---|---|
| `src/qqbotsdk/api/` | 顶层接口：app/bot/interaction/media/menu/panel/user | `src/qqbotsdk/api/agent.md` |
| `src/qqbotsdk/api/group/` | 群聊接口 | `src/qqbotsdk/api/group/agent.md` |
| `src/qqbotsdk/model/`（顶层 `.py`） | 顶层请求/响应模型 | `src/qqbotsdk/model/agent.md` |
| `src/qqbotsdk/model/group/` | 群聊/群管理模型 | `src/qqbotsdk/model/group/agent.md` |
| `src/qqbotsdk/model/user/` | 单聊模型 | `src/qqbotsdk/model/user/agent.md` |
| `src/qqbotsdk/model/event/` | 群聊/单聊/好友/互动**事件**模型 | `src/qqbotsdk/model/event/agent.md` |
