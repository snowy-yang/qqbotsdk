# 频道 API

`from qqbotsdk.api import BotApi`。频道（guild）/子频道（channel）场景的旧版接口，按消息、管理、查询三组列出。标"私域"的接口仅频道私域机器人可用。

频道消息的被动回复规则与群聊不同：公域机器人发消息必须带 `msg_id`。

## 频道消息

| 方法 | 端点 | 说明 |
|---|---|---|
| `post_channel_message(channel_id, content="", msg_id=None, msg_seq=1, image=None, **extra)` | POST /channels/{channel_id}/messages | `image` 为图片 URL；embed/ark/markdown 等经 `extra` 透传 |
| `withdraw_channel_message(channel_id, message_id, hide_tip=False)` | DELETE /channels/{channel_id}/messages/{message_id} | **仅私域机器人**；`hide_tip` 对应官方 `hidetip` |
| `put_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | PUT …/reactions/{type}/{emoji_id} | `emoji_type=1` 系统表情，`emoji_id` 为序号字符串 |
| `delete_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | DELETE …/reactions/{type}/{emoji_id} | 删除自己的表态 |
| `create_dms(recipient_id, source_guild_id)` | POST /users/@me/dms | 创建私信会话（需与用户同频道），返回私信的 `guild_id`/`channel_id` |
| `post_dms_message(guild_id, content="", msg_id=None, msg_seq=1, image=None, **extra)` | POST /dms/{guild_id}/messages | 发私信，参数同 `post_channel_message`；主动消息每天单用户 2 条、累计 200 条，被动不限 |
| `withdraw_dms_message(guild_id, message_id, hide_tip=False)` | DELETE /dms/{guild_id}/messages/{message_id} | 撤回自己发的私信，**仅私域** |
| `get_channel_permissions(channel_id, user_id)` / `get_channel_role_permissions(channel_id, role_id)` | GET …/members/{user_id}/permissions · …/roles/{role_id}/permissions | 子频道权限位图（字符串） |
| `update_channel_permissions(channel_id, user_id, *, add=None, remove=None)` / `update_channel_role_permissions(channel_id, role_id, …)` | PUT 同路径 | `add`/`remove` 为字符串权限位图，至少传一个，需管理员权限 |

## 频道管理

| 方法 | 端点 | 说明 |
|---|---|---|
| `create_guild_announce(guild_id, channel_id, message_id, announces_type=0, **extra)` | POST /guilds/{guild_id}/announces | `announces_type`：0 成员公告 / 1 欢迎公告；推荐频道公告经 extra（与消息公告互斥） |
| `create_channel(guild_id, name, **fields)` | POST /guilds/{guild_id}/channels | 创建子频道，**私域**需管理员权限；`fields` 透传 type/sub_type/position/parent_id/private_type/speak_permission 等；触发 CHANNEL_CREATE |
| `update_channel(channel_id, **fields)` | PATCH /channels/{channel_id} | 修改子频道，**私域**；只传变更项；触发 CHANNEL_UPDATE |
| `delete_channel(channel_id)` | DELETE /channels/{channel_id} | 删除子频道，**私域**；不可恢复；触发 CHANNEL_DELETE |
| `delete_guild_announce(guild_id, message_id)` | DELETE /guilds/{guild_id}/announces/{message_id} | 推荐频道公告传 `message_id="all"` |
| `pin_channel_message(channel_id, message_id)` | PUT /channels/{channel_id}/pins/{message_id} | 添加精华消息 |
| `unpin_channel_message(channel_id, message_id)` | DELETE /channels/{channel_id}/pins/{message_id} | 移出精华消息 |
| `get_channel_pins(channel_id)` | GET /channels/{channel_id}/pins | 精华消息列表 |
| `get_channel_schedules(channel_id, since=None)` | GET /channels/{channel_id}/schedules | 默认当天日程；`since` 毫秒时间戳 |
| `get_channel_schedule(channel_id, schedule_id)` | GET /channels/{channel_id}/schedules/{schedule_id} | 单个日程 |
| `create_channel_schedule(channel_id, name, start_timestamp, end_timestamp, jump_channel_id, remind_type="0", description="")` | POST /channels/{channel_id}/schedules | 时间为毫秒时间戳字符串；`remind_type` "0" 不提醒 / "1" 开始时；请求体自动包在 `schedule` 字段；单管理员每天限 10 次 |
| `update_channel_schedule(channel_id, schedule_id, **fields)` | PATCH /channels/{channel_id}/schedules/{schedule_id} | `fields` 为 schedule 内字段透传 |
| `delete_channel_schedule(channel_id, schedule_id)` | DELETE /channels/{channel_id}/schedules/{schedule_id} | 删除日程 |
| `create_guild_role(guild_id, name="", color=None, hoist=None)` | POST /guilds/{guild_id}/roles | 创建身份组，返回 `{"role_id", "role"}`；`color` 为 ARGB 十进制 |
| `update_guild_role(guild_id, role_id, name=None, color=None, hoist=None)` | PATCH /guilds/{guild_id}/roles/{role_id} | 只传变更项；系统默认身份组不可改 |
| `delete_guild_role(guild_id, role_id)` | DELETE /guilds/{guild_id}/roles/{role_id} | 只能删除自建身份组 |
| `add_guild_member_role(guild_id, user_id, role_id)` / `remove_guild_member_role(…)` | PUT / DELETE /guilds/{guild_id}/members/{user_id}/roles/{role_id} | 授予/收回成员身份组 |
| `remove_guild_member(guild_id, user_id, add_blacklist=False, delete_history_msg_days=0)` | DELETE /guilds/{guild_id}/members/{user_id} | 踢人，**私域**需踢人权限；撤回消息仅支持 3/7/15/30 或 -1 全部 |
| `mute_guild(guild_id, mute_end_timestamp=None, mute_seconds=None)` | PATCH /guilds/{guild_id}/mute | 全员禁言，两个时间字段二选一；解除都传 "0" |
| `mute_guild_members(guild_id, user_ids, …)` | PATCH /guilds/{guild_id}/mute | 批量禁言（带 `user_ids`），单次最多 20 人 |
| `create_api_permission_demand(guild_id, channel_id, path, method, desc)` | POST /guilds/{guild_id}/api_permission/demand | 生成接口权限授权链接发到子频道，由频道管理员授权 |
| `mute_guild_member(guild_id, user_id, mute_seconds=0)` | PATCH /guilds/{guild_id}/members/{user_id}/mute | 禁言秒数（上限 28 天），0 解禁 |

## 频道查询

| 方法 | 端点 |
|---|---|
| `get_guild(guild_id)` | GET /guilds/{guild_id} |
| `get_me_guilds(before=None, after=None, limit=None)` | GET /users/@me/guilds |
| `get_guild_channels(guild_id)` | GET /channels/{guild_id}/channels |
| `get_guild_members(guild_id)` | GET /guilds/{guild_id}/members |
| `get_role_members(guild_id, role_id)` | GET /guilds/{guild_id}/roles/{role_id}/members |
| `get_channel_online_nums(channel_id)` | GET /channels/{channel_id}/online_nums |
| `get_guild_message_setting(guild_id)` | GET /guilds/{guild_id}/message/setting |
| `get_guild_api_permissions(guild_id)` | GET /guilds/{guild_id}/api_permission |
| `get_channel(channel_id)` | GET /channels/{channel_id} |
| `get_guild_roles(guild_id)` | GET /guilds/{guild_id}/roles |
| `get_guild_member(guild_id, user_id)` | GET /guilds/{guild_id}/members/{user_id} |
