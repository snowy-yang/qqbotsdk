# agent.md — qqbotsdk-guild-py（频道域包）

适用范围：`packages/qqbotsdk-guild/**`。上级规定见仓库根 `agent.md`。

覆盖：guild / channel / 成员 / 身份组 / 权限 / 接口授权 / 发言管理 / 内容（公告、精华、日程、音频、论坛）/ 频道私信 / 频道事件。

## MUST（必须做）

- MUST 只依赖 `qqbotsdk-base-py`，不得 import `qqbotsdk-py`（依赖单向：base ← 核心 ← guild）。
- MUST 使用频道域的 `guild_id` / `channel_id` / `user_id` / `role_id` 作为路径参数，不写成 openid。
- MUST 保持「接口 ↔ 模型」一一对应，api 骨架与顶层规范一致（`session` + `model_dump(exclude_none=True)` + `model_validate`）。
- MUST 在改动后跑通仓库质量门（ruff check / ruff format --check / pyright）。

## SHOULD（应当做）

- SHOULD 按官方分组组织：`api/guild/{channel,guild,member,messages,content}.py`。
- SHOULD 优先复用本包已有对象模型（`Guild`、`Channel`、`Member`、`User`、`Role`、`MessageEmbed`、`MessageArk`），避免重复造。

## MUST NOT（禁止做）

- MUST NOT 加回**子频道公告**接口（`post_channel_announces` / `delete_channel_announces`）：官方 2022-03-15 标注废弃，已从本包移除。
- MUST NOT 把频道域模型挪进 `qqbotsdk-py`，也不要在 `qqbotsdk-py` 里 import 本包。
- MUST NOT 重命名已公开的事件/模型类（破坏性）。

## 子模块

| 子模块 | 职责 | 细则 |
|---|---|---|
| `src/qqbotsdk/api/guild/` | 频道域接口映射 | `src/qqbotsdk/api/guild/agent.md` |
| `src/qqbotsdk/model/guild/` | 频道域模型与事件模型 | `src/qqbotsdk/model/guild/agent.md` |
