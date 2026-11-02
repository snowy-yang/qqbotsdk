# API · 频道域

模块前缀：`qqbotsdk.api.guild.*`（可选发行包 `qqbotsdk-guild-py`，`pip install "qqbotsdk-py[guild]"`）。

路径族：`/guilds/{guild_id}/...`、`/channels/{channel_id}/...`、`/users/@me/...`、`/dms/...`。

| 文件 | 域 | 接口数 |
|---|---|---|
| `guild.guild` | 频道信息与 API 权限 | 5 |
| `guild.channel` | 子频道与子频道权限 | 10 |
| `guild.member` | 成员、身份组、禁言 | 13 |
| `guild.messages` | 子频道消息、表情表态、私信 | 9 |
| `guild.content` | 公告、精华、日程、论坛、音频、麦克风 | 17 |

---

## 频道信息 guild.guild

```python
from qqbotsdk.api.guild.guild import (
    get_guild,
    get_me_guilds,
    get_guild_message_setting,
    get_guild_api_permissions,
    create_api_permission_demand,
)
from qqbotsdk.model.guild.guild import (
    GetMeGuildsRequest,
    CreateApiPermissionDemandRequest,
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_guild(guild_id)` | `GET /guilds/{guild_id}` | — → `GetGuildResponse` |
| `get_me_guilds(payload)` | `GET /users/@me/guilds` | `GetMeGuildsRequest` → `GetMeGuildsResponse` |
| `get_guild_message_setting(guild_id)` | `GET /guilds/{guild_id}/message/setting` | — → `GetGuildMessageSettingResponse` |
| `get_guild_api_permissions(guild_id)` | `GET /guilds/{guild_id}/api_permission` | — → `GetGuildApiPermissionsResponse` |
| `create_api_permission_demand(guild_id, payload)` | `POST /guilds/{guild_id}/api_permission/demand` | `CreateApiPermissionDemandRequest` → `CreateApiPermissionDemandResponse` |

- **`GetMeGuildsRequest`**：`before`（读取此 guild_id 之前）、`after`（之后，与 before 同时设置时 after 无效）、`limit`（默认 100，最大 100）。
- **`CreateApiPermissionDemandRequest`**（全必填）：`channel_id`（授权链接发的子频道）、`api_identify`（`ApiPermissionDemandIdentify`）、`desc`（申请后可实现的功能说明）。
- `GetGuildMessageSettingResponse`（= `GuildMessageSetting`）：`disable_create_dm`、`disable_push_msg`、`channel_ids`（主动推送的子频道 ID 列表）、`channel_push_max_num`（每子频道每日最大推送条数）。
- `GetGuildApiPermissionsResponse`：`apis: list[APIPermission]`，`APIPermission` 含 `path`、`method`、`desc`、`auth_status`。

---

## 子频道 guild.channel

```python
from qqbotsdk.api.guild.channel import (
    get_channel,
    get_guild_channels,
    create_channel,
    update_channel,
    delete_channel,
    get_channel_online_nums,
    get_channel_permissions,
    get_channel_role_permissions,
    update_channel_permissions,
    update_channel_role_permissions,
)
from qqbotsdk.model.guild.channel import (
    CreateChannelRequest,
    UpdateChannelRequest,
    UpdateChannelPermissionsRequest,
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_channel(channel_id)` | `GET /channels/{channel_id}` | — → `GetChannelResponse` |
| `get_guild_channels(guild_id)` | `GET /guilds/{guild_id}/channels` | — → `GetGuildChannelsResponse`（`root: list[Channel]`） |
| `create_channel(guild_id, payload)` | `POST /guilds/{guild_id}/channels` | `CreateChannelRequest` → `CreateChannelResponse` |
| `update_channel(channel_id, payload)` | `PATCH /channels/{channel_id}` | `UpdateChannelRequest` → `UpdateChannelResponse` |
| `delete_channel(channel_id)` | `DELETE /channels/{channel_id}` | — → `None` |
| `get_channel_online_nums(channel_id)` | `GET /channels/{channel_id}/online_nums` | — → `GetChannelOnlineNumsResponse`（`online_nums`） |
| `get_channel_permissions(channel_id, user_id)` | `GET /channels/{channel_id}/members/{user_id}/permissions` | — → `GetChannelPermissionsResponse` |
| `get_channel_role_permissions(channel_id, role_id)` | `GET /channels/{channel_id}/roles/{role_id}/permissions` | — → `GetChannelRolePermissionsResponse` |
| `update_channel_permissions(channel_id, user_id, payload)` | `PUT /channels/{channel_id}/members/{user_id}/permissions` | `UpdateChannelPermissionsRequest` → `None` |
| `update_channel_role_permissions(channel_id, role_id, payload)` | `PUT /channels/{channel_id}/roles/{role_id}/permissions` | `UpdateChannelPermissionsRequest` → `None` |

- **`CreateChannelRequest`**（全可选）：`name`、`type`（0文字/2语音/4分组/10005直播/10006应用/10007论坛）、`sub_type`（0闲聊/1公告/2攻略/3开黑）、`position`（分组 type=4 须 ≥2）、`parent_id`、`private_type`（0公开/1群主管理员/2群主管理员+指定成员）、`private_user_ids`、`speak_permission`（0无效/1所有人/2群主管理员+指定成员）、`application_id`。
- **`UpdateChannelRequest`**（全可选）：`name`、`position`、`parent_id`、`private_type`、`speak_permission`。
- **`UpdateChannelPermissionsRequest`**（全可选）：`add` / `remove`（字符串形式的位图）。成员权限与身份组权限**复用同一模型**。

---

## 成员与身份组 guild.member

```python
from qqbotsdk.api.guild.member import (
    get_guild_members,
    get_guild_member,
    remove_guild_member,
    get_guild_roles,
    create_guild_role,
    update_guild_role,
    delete_guild_role,
    get_role_members,
    add_guild_member_role,
    remove_guild_member_role,
    mute_guild,
    mute_guild_members,
    mute_guild_member,
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_guild_members(guild_id, payload)` | `GET /guilds/{guild_id}/members` | `GetGuildMembersRequest` → `GetGuildMembersResponse` |
| `get_guild_member(guild_id, user_id)` | `GET /guilds/{guild_id}/members/{user_id}` | — → `GetGuildMemberResponse` |
| `remove_guild_member(guild_id, user_id, payload)` | `DELETE /guilds/{guild_id}/members/{user_id}` | `RemoveGuildMemberRequest` → `None` |
| `get_guild_roles(guild_id)` | `GET /guilds/{guild_id}/roles` | — → `GetGuildRolesResponse` |
| `create_guild_role(guild_id, payload)` | `POST /guilds/{guild_id}/roles` | `CreateGuildRoleRequest` → `CreateGuildRoleResponse` |
| `update_guild_role(guild_id, role_id, payload)` | `PATCH /guilds/{guild_id}/roles/{role_id}` | `UpdateGuildRoleRequest` → `UpdateGuildRoleResponse` |
| `delete_guild_role(guild_id, role_id)` | `DELETE /guilds/{guild_id}/roles/{role_id}` | — → `None` |
| `get_role_members(guild_id, role_id, payload)` | `GET /guilds/{guild_id}/roles/{role_id}/members` | `GetRoleMembersRequest` → `GetRoleMembersResponse` |
| `add_guild_member_role(guild_id, user_id, role_id, payload)` | `PUT /guilds/{guild_id}/members/{user_id}/roles/{role_id}` | `GuildMemberRoleRequest` → `None` |
| `remove_guild_member_role(guild_id, user_id, role_id, payload)` | `DELETE /guilds/{guild_id}/members/{user_id}/roles/{role_id}` | `GuildMemberRoleRequest` → `None` |
| `mute_guild(guild_id, payload)` | `PATCH /guilds/{guild_id}/mute` | `MuteRequest` → `None`（全员禁言） |
| `mute_guild_members(guild_id, payload)` | `PATCH /guilds/{guild_id}/mute` | `MuteMembersRequest` → `MuteMembersResponse`（批量禁言） |
| `mute_guild_member(guild_id, user_id, payload)` | `PATCH /guilds/{guild_id}/members/{user_id}/mute` | `MuteRequest` → `None`（单人禁言） |

> **同路径不同载荷**：全员禁言与批量禁言都打 `PATCH /guilds/{guild_id}/mute`，靠请求模型区分（`MuteRequest` 无响应体 / `MuteMembersRequest` 返回 `MuteMembersResponse`）。

- **`GetGuildMembersRequest`**：`after`（上次最后一个 user_id，首次填 `"0"`）、`limit`（1-400，默认 1）。
- **`RemoveGuildMemberRequest`**：`add_blacklist`（可选）、`delete_history_msg_days`（可选，`-1`=全部 / `0`=不撤回 / 3/7/15/30）。
- **`CreateGuildRoleRequest`** / **`UpdateGuildRoleRequest`**：`name`、`color`（ARGB HEX 的十进制值）、`hoist`（0否/1是）。
- **`GetRoleMembersRequest`**：`start_index`（上次回包的 `next`，首次 `"0"`）、`limit`（1-400，默认 1）。
- **`GuildMemberRoleRequest`**：`channel: ChannelReference`（仅 `role_id=5` 子频道管理员时传）。
- **`MuteRequest`**：`mute_end_timestamp`（绝对秒，优先）、`mute_seconds`（解除传 `"0"`）。
- **`MuteMembersRequest`**：`mute_end_timestamp`、`mute_seconds`、`user_ids: list[str]`（必填，≤20）。

---

## 子频道消息 / 表情表态 / 私信 guild.messages

```python
from qqbotsdk.api.guild.messages import (
    send_channel_messages,
    recall_channel_messages,
    get_channel_messages,
    put_channel_reaction,
    delete_channel_reaction,
    get_channel_reaction_users,
    create_dms,
    send_dms_messages,
    recall_dms_messages,
)
from qqbotsdk.model.guild.messages import (
    SendChannelMessagesRequest,
    GetChannelReactionUsersRequest,
    CreateDmsRequest,
    SendDmsMessagesRequest,
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `send_channel_messages(channel_id, payload)` | `POST /channels/{channel_id}/messages` | `SendChannelMessagesRequest` → `SendChannelMessagesResponse` |
| `recall_channel_messages(channel_id, message_id, hide_tip=False)` | `DELETE /channels/{channel_id}/messages/{message_id}` | 查询参数 `hidetip` → `None` |
| `get_channel_messages(channel_id, message_id)` | `GET /channels/{channel_id}/messages/{message_id}` | — → `GetChannelMessagesResponse` |
| `put_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | `PUT /channels/{channel_id}/messages/{message_id}/reactions/{emoji_type}/{emoji_id}` | — → `None` |
| `delete_channel_reaction(channel_id, message_id, emoji_type, emoji_id)` | `DELETE .../reactions/{emoji_type}/{emoji_id}` | — → `None` |
| `get_channel_reaction_users(channel_id, message_id, emoji_type, emoji_id, payload)` | `GET .../reactions/{emoji_type}/{emoji_id}` | `GetChannelReactionUsersRequest` → `GetChannelReactionUsersResponse` |
| `create_dms(payload)` | `POST /users/@me/dms` | `CreateDmsRequest` → `CreateDmsResponse` |
| `send_dms_messages(guild_id, payload)` | `POST /dms/{guild_id}/messages` | `SendDmsMessagesRequest` → `SendDmsMessagesResponse` |
| `recall_dms_messages(guild_id, message_id, hide_tip=False)` | `DELETE /dms/{guild_id}/messages/{message_id}` | 查询参数 `hidetip` → `None` |

- **`SendChannelMessagesRequest`** / **`SendDmsMessagesRequest`**（全可选）：`content`、`embed`（`MessageEmbed`）、`ark`（`MessageArk`，需模板权限）、`image`（图片 URL）、`msg_id`/`event_id`（被动回复二选一）、`msg_seq`、`message_reference`、`markdown`（与 content 互斥）、`keyboard`。content/embed/ark/image/markdown 至少填一个。
- `SendChannelMessagesResponse`（子频道消息回包）字段较多：`id`、`channel_id`、`guild_id`、`content`、`timestamp`、`author`、`attachments`、`embeds`、`ark`、`seq_in_channel`、`message_reference`、`src_guild_id` 等；完整定义见 `qqbotsdk.model.guild.messages`。
- **`MessageArk`** 由 `template_id` 与 `kv: list[MessageArkObj]` 组成（`MessageArkObj` 含 `obj_kv`），需先在开放平台申请 ark 模板权限。
- **`GetChannelReactionUsersRequest`**：`cookie`（上次返回）、`limit`（1-100，默认 20）。
- **`CreateDmsRequest`**（全必填）：`recipient_id`、`source_guild_id`。

---

## 公告 / 精华 / 日程 / 论坛 / 音频 guild.content

```python
from qqbotsdk.api.guild.content import (
    create_guild_announce,
    delete_guild_announce,
    pin_channel_message,
    unpin_channel_message,
    get_channel_pins,
    get_channel_schedules,
    get_channel_schedule,
    create_channel_schedule,
    update_channel_schedule,
    delete_channel_schedule,
    control_channel_audio,
    put_channel_mic,
    delete_channel_mic,
    get_channel_threads,
    get_channel_thread,
    put_channel_thread,
    delete_channel_thread,
)
```

**公告**

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `create_guild_announce(guild_id, payload)` | `POST /guilds/{guild_id}/announces` | `CreateGuildAnnounceRequest` → `CreateGuildAnnounceResponse` |
| `delete_guild_announce(guild_id, message_id)` | `DELETE /guilds/{guild_id}/announces/{message_id}` | — → `None` |

**精华（置顶）**

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `pin_channel_message(channel_id, message_id)` | `PUT /channels/{channel_id}/pins/{message_id}` | — → `GetChannelPinsResponse` |
| `unpin_channel_message(channel_id, message_id)` | `DELETE /channels/{channel_id}/pins/{message_id}` | — → `None` |
| `get_channel_pins(channel_id)` | `GET /channels/{channel_id}/pins` | — → `GetChannelPinsResponse` |

**日程**

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_channel_schedules(channel_id, payload)` | `GET /channels/{channel_id}/schedules` | `GetChannelSchedulesRequest` → `GetChannelSchedulesResponse` |
| `get_channel_schedule(channel_id, schedule_id)` | `GET /channels/{channel_id}/schedules/{schedule_id}` | — → `GetChannelScheduleResponse` |
| `create_channel_schedule(channel_id, payload)` | `POST /channels/{channel_id}/schedules` | `CreateChannelScheduleRequest` → `CreateChannelScheduleResponse` |
| `update_channel_schedule(channel_id, schedule_id, payload)` | `PATCH /channels/{channel_id}/schedules/{schedule_id}` | `UpdateChannelScheduleRequest` → `UpdateChannelScheduleResponse` |
| `delete_channel_schedule(channel_id, schedule_id)` | `DELETE /channels/{channel_id}/schedules/{schedule_id}` | — → `None` |

**论坛（帖子）**

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_channel_threads(channel_id)` | `GET /channels/{channel_id}/threads` | — → `GetChannelThreadsResponse` |
| `get_channel_thread(channel_id, thread_id)` | `GET /channels/{channel_id}/threads/{thread_id}` | — → `GetChannelThreadResponse` |
| `put_channel_thread(channel_id, payload)` | `PUT /channels/{channel_id}/threads` | `PutChannelThreadRequest` → `PutChannelThreadResponse`（`task_id`） |
| `delete_channel_thread(channel_id, thread_id)` | `DELETE /channels/{channel_id}/threads/{thread_id}` | — → `DeleteChannelThreadResponse`（`task_id`） |

**音频 / 麦克风**

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `control_channel_audio(channel_id, payload)` | `POST /channels/{channel_id}/audio` | `AudioControlRequest` → `None` |
| `put_channel_mic(channel_id)` | `PUT /channels/{channel_id}/mic` | — → `None`（上麦） |
| `delete_channel_mic(channel_id)` | `DELETE /channels/{channel_id}/mic` | — → `None`（下麦） |

请求模型要点：

- **`CreateGuildAnnounceRequest`**：`channel_id`（message_id 有值时必填）、`message_id`（有值时创建消息类型公告）、`announces_type`（0成员公告/1欢迎公告）、`recommend_channels: list[RecommendChannel]`（推荐子频道，整体替换，与消息类型公告互斥）。
- **`GetChannelSchedulesRequest`**：`since`（起始毫秒时间戳，不传返回当天）。
- **`CreateChannelScheduleRequest`** / **`UpdateChannelScheduleRequest`**：`schedule: ScheduleInfo`（必填，不带 id）。
- **`PutChannelThreadRequest`**（全必填）：`title`、`content`（`format=4` 时按 RichText 结构）、`format`（1纯文本/2HTML/3Markdown/4RichText JSON）。
- **`AudioControlRequest`**：`status`（必填，0开始/1暂停/2继续/3停止）、`audio_url`（status=0 时传）、`text`（status=0 时传）。

## 常见响应对象字段



**`Channel`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 子频道 ID |
| `guild_id` | `str \| None` | 所属频道 ID |
| `name` | `str \| None` | 子频道名 |
| `type` | `int \| None` | 子频道类型：0=文字，2=语音，4=分组，10005=直播，10006=应用，10007=论坛 |
| `sub_type` | `int \| None` | 子频道子类型：0=闲聊，1=公告，2=攻略，3=开黑 |
| `position` | `int \| None` | 排序值，从 1 开始 |
| `parent_id` | `str \| None` | 所属分组 ID，仅对子频道有效，对子频道分组（type=4）无效 |
| `owner_id` | `str \| None` | 创建人 ID |
| `private_type` | `int \| None` | 私密类型：0=公开，1=群主管理员可见，2=群主管理员+指定成员 |
| `speak_permission` | `int \| None` | 发言权限：0=无效，1=所有人，2=群主管理员+指定成员 |
| `application_id` | `str \| None` | 应用子频道标识 |
| `permissions` | `str \| None` | 用户拥有的子频道权限位图 |

**`Guild`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 频道 ID |
| `name` | `str \| None` | 频道名称 |
| `icon` | `str \| None` | 频道头像 URL |
| `owner_id` | `str \| None` | 创建者用户 ID |
| `owner` | `bool \| None` | 当前机器人是否为创建者 |
| `member_count` | `int \| None` | 成员数 |
| `max_members` | `int \| None` | 最大成员数 |
| `description` | `str \| None` | 频道描述 |
| `joined_at` | `str \| None` | 加入时间，ISO8601 格式 |

**`Member`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `user` | `guild.member.User \| None` | 用户对象 |
| `nick` | `str \| None` | 频道昵称 |
| `roles` | `list[str] \| None` | 身份组 ID 列表 |
| `joined_at` | `str \| None` | 加入时间，ISO8601 格式 |
| `deaf` | `bool \| None` | 是否被禁听 |
| `mute` | `bool \| None` | 是否被禁言 |
| `pending` | `bool \| None` | 是否待审核入频道 |

**`User`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 用户 ID |
| `username` | `str \| None` | 用户名 |
| `avatar` | `str \| None` | 用户头像地址 |
| `bot` | `bool \| None` | 是否为机器人 |
| `union_openid` | `str \| None` | 跨应用统一用户 OpenID，需特殊申请；仅单独拉取成员信息时返回 |
| `union_user_account` | `str \| None` | 机器人关联的互联应用的用户信息，需特殊申请 |

**`Role`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 身份组 ID |
| `name` | `str \| None` | 身份组名称 |
| `color` | `int \| None` | ARGB 的 HEX 十六进制颜色值转换后的十进制数值 |
| `hoist` | `int \| None` | 在成员列表中单独展示：0=否，1=是 |
| `number` | `int \| None` | 身份组成员数量 |
| `member_limit` | `int \| None` | 身份组成员上限 |

**`ScheduleInfo`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | `str \| None` | 日程名称 |
| `description` | `str \| None` | 日程描述 |
| `start_timestamp` | `str \| None` | 开始时间，毫秒级时间戳字符串 |
| `end_timestamp` | `str \| None` | 结束时间，毫秒级时间戳字符串 |
| `jump_channel_id` | `str \| None` | 跳转子频道 ID |
| `remind_type` | `str \| None` | 提醒类型：0=不提醒，1=开始时提醒，2=开始前 5 分钟提醒，3=开始前 15 分钟提醒，4=开始前 30 分钟提醒，5=开始前 60 分钟提醒 |

**`RecommendChannel`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `channel_id` | `str \| None` | 推荐子频道 ID |
| `introduce` | `str \| None` | 推荐语 |

