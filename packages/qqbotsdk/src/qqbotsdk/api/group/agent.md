# agent.md — qqbotsdk/api/group（群聊与群管理接口）

适用范围：`packages/qqbotsdk/src/qqbotsdk/api/group/**`（`manage.py`、`messages.py`、`mute.py`、`blacklist.py`、`join_request.py`、`strategy.py`）。

## MUST（必须做）

- MUST 使用群域路径前缀 `/v2/groups/{group_openid}/...`，`group_openid` 一律作为第一个位置参数。
- MUST 严格照文档区分 `group_openid`（群）与 `member_openid`（群内成员）：前者是路径前缀，后者只在需要时作路径参数。
- MUST 遵循顶层 `api/agent.md` 的骨架（`session` + `model_dump(exclude_none=True)` + `model_validate`）。
- MUST 对无响应体的接口（禁言设置、解除禁言、审批入群、删除策略等）返回 `None`，但仍要读取响应。

## SHOULD（应当做）

- SHOULD 按官方分组落文件：群信息/成员/机器人状态 → `manage.py`；群消息与富媒体 → `messages.py`；禁言 → `mute.py`；黑名单 → `blacklist.py`；入群审批 → `join_request.py`；自动审批策略 → `strategy.py`。
- SHOULD 让接口名体现群体语义：`get_group_members`、`remove_group_members`、`review_group_join_request`。

## MUST NOT（禁止做）

- MUST NOT 复用单聊路径 `/v2/users/{user_openid}/...` 的写法（两者 openid 不通用，单聊见 `../agent.md`）。
- MUST NOT 把 `/v2/groups/join_approval_strategy` 这类「不需要群 ID」的接口硬塞 `group_openid` 参数。
- MUST NOT 在群域接口里顺手改单聊或频道逻辑。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk\src\qqbotsdk\api\group
.venv\Scripts\pyright.exe
```
