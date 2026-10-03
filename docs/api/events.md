# 事件 payload

`qqbotsdk.payloads` 定义事件 `d` 的 dataclass。handler 标注类型即得解析对象；未知事件类型回退原始 dict。所有字段均可为 None（线上缺省即 None），嵌套 `author` 自动解析为 `Author`。事件对照表只在本文。

## 事件名 → dataclass 对照

下表左列是 intents.toml 的订阅分组（订阅粒度即分组，组内事件无法单独开关，见[配置与订阅](/docs/guide/config.md#事件订阅intentstoml)），中列是同时属于该分组、会被一起推送的事件 `t` 名：

| intents 分组 | 事件 t 名 | dataclass |
|---|---|---|
| GROUP_AND_C2C_EVENT | `C2C_MESSAGE_CREATE` | `C2CMessage` |
| | `GROUP_AT_MESSAGE_CREATE` / `GROUP_MESSAGE_CREATE` | `GroupAtMessage` |
| | `FRIEND_ADD` / `FRIEND_DEL` | `FriendAdd` / `FriendDel` |
| | `GROUP_ADD_ROBOT` / `GROUP_DEL_ROBOT` | `GroupAddRobot` / `GroupDelRobot` |
| | `C2C_MSG_REJECT` / `C2C_MSG_RECEIVE` | `C2CMsgReject` / `C2CMsgReceive` |
| | `GROUP_MSG_REJECT` / `GROUP_MSG_RECEIVE` | `GroupMsgReject` / `GroupMsgReceive` |
| | `SUBSCRIBE_MESSAGE_STATUS` | `SubscribeMessageStatus` |
| GROUP_MEMBER_EVENT | `GROUP_MEMBER_ADD` / `GROUP_MEMBER_REMOVE` | `GroupMemberChange` |
| | `GROUP_JOIN_REQUEST`（仅机器人是群管理员时推送） | `GroupJoinRequest` |
| PUBLIC_GUILD_MESSAGES | `AT_MESSAGE_CREATE` | `AtMessage` |
| | `PUBLIC_MESSAGE_DELETE` | `MessageDelete` |
| GUILD_MESSAGES（私域） | `MESSAGE_DELETE` | `MessageDelete` |
| DIRECT_MESSAGE | `DIRECT_MESSAGE_CREATE` | `DirectMessage` |
| GUILDS | `GUILD_CREATE` / `GUILD_UPDATE` / `GUILD_DELETE` | `Guild` |
| | `CHANNEL_CREATE` / `CHANNEL_UPDATE` / `CHANNEL_DELETE` | `Channel` |
| GUILD_MESSAGE_REACTIONS | `MESSAGE_REACTION_ADD` / `…_REMOVE` | `MessageReaction` |
| MESSAGE_AUDIT | `MESSAGE_AUDIT_PASS` / `…_REJECT` | `MessageAudit` |
| INTERACTION | `INTERACTION_CREATE` | `Interaction` |
| FORUMS_EVENT（私域） | `FORUM_THREAD_CREATE` / `…_UPDATE` / `…_DELETE` | `ForumThread` |
| | `FORUM_POST_CREATE` / `…_DELETE` | `ForumPost` |
| | `FORUM_REPLY_CREATE` / `…_DELETE` | `ForumReply` |
| AUDIO_ACTION | `AUDIO_START` / `AUDIO_FINISH` / `AUDIO_ON_MIC` / `AUDIO_OFF_MIC` | `AudioAction` |
| —（DISPATCH 协议事件） | `READY` | `Ready` |

未收录的事件（如私域 `MESSAGE_CREATE`、`DIRECT_MESSAGE_DELETE`、`GUILD_MEMBER_*`）没有对应 dataclass 可标注，请标注 `Event` 经 `.typed`（未知事件类型为 dict）或 `.raw` 访问；新增事件在 `payloads.py` 加 dataclass 并登记 `EVENT_TYPES` 即可。

`GROUP_MESSAGE_CREATE` 是群消息**全量模式**：需在开放平台开通"接收所有消息"权限，群里每条消息（不限 @机器人）都推送此事件，与 `GROUP_AT_MESSAGE_CREATE` 共用 `GroupAtMessage`。官方提示同一 msg_id 可能重复推送，业务侧需按 `id` 去重。

## 常用 dataclass 字段

```python
Author            # id, user_openid, member_openid, username, bot
GroupAtMessage    # id, content, group_openid, author, timestamp,
                  # message_type, message_scene, attachments, mentions, ark_data, msg_elements
C2CMessage        # id, content, author, attachments, timestamp
AtMessage         # id, content, channel_id, guild_id, author, member, timestamp
DirectMessage     # 同 AtMessage
GroupJoinRequest  # group_openid, join_request_id, member_openid, username, risk_tips,
                  # apply_at, apply_source, invited_by, verify_info, auto_approved, …
GroupMemberChange # timestamp, group_openid, member_openid, user_openid
```

- `GroupAtMessage.user_openid` / `C2CMessage.user_openid`：便利属性，从 `author.member_openid`/`author.user_openid` 取发言人标识。
- 群/单聊场景拿不到用户真实 QQ 号，只有 openid；频道场景 `Author.id`/`username` 有效。
- 其余事件 dataclass 为 2~5 个平铺字段的同构结构（openid/时间戳/信息 dict），字段名即官方文档字段。

`parse_event(t, d)`：把事件 `d` 解析为对应 dataclass（`Event.typed` 的内部实现），`EVENT_TYPES` 为事件名 → 类的完整登记表。
