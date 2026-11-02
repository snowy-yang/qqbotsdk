# agent.md — qqbotsdk/api/guild（频道域接口）

适用范围：`packages/qqbotsdk-guild/src/qqbotsdk/api/guild/**`（`channel.py`、`guild.py`、`member.py`、`messages.py`、`content.py`）。

## MUST（必须做）

- MUST 使用频道域路径：`/guilds/{guild_id}/...`、`/channels/{channel_id}/...`、`/users/@me/...`、`/dms/...`。
- MUST 对**同路径不同载荷**的接口保持区分，不要合并成一个函数：
  - 全员禁言 `PATCH /guilds/{guild_id}/mute`（`MuteRequest`，无响应体）；
  - 批量禁言同路径（`MuteMembersRequest` → `MuteMembersResponse`）；
  - 单人禁言 `PATCH /guilds/{guild_id}/members/{user_id}/mute`（`MuteRequest`，无响应体）。
- MUST 让无响应体的接口（权限修改、禁言、撤回、上麦/下麦、表情表态、公告删除等）返回 `None`，但仍读取响应。
- MUST 遵循顶层 `api/agent.md` 的请求骨架与命名约定。

## SHOULD（应当做）

- SHOULD 对权限接口复用同一个请求模型（`UpdateChannelPermissionsRequest` 同时服务成员权限与身份组权限）。
- SHOULD 把 MIME/文件相关处理留在调用方，api 层只做薄映射。

## MUST NOT（禁止做）

- MUST NOT 在本目录实现子频道公告（官方已废弃，见包级 `agent.md`）。
- MUST NOT 把 `guild_id`/`channel_id` 塞进请求模型。
- MUST NOT 手写鉴权头或自建会话；一律用 `qqbotsdk.api.core.session`。
- MUST NOT 在接口里吞异常或做重试。

## 自检

```powershell
cd D:\QQBotSDK
.venv\Scripts\ruff.exe check packages\qqbotsdk-guild\src\qqbotsdk\api
.venv\Scripts\pyright.exe
```
