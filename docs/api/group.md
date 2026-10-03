# 群管理 API

`from qqbotsdk.api import BotApi`。多数接口要求机器人拥有群管理员身份；成员/黑名单/批量移除等能力官方标注"内邀接入中"，未开通时服务端返回业务码 11253。

入群申请的审批结果也会以事件推送（`GROUP_JOIN_REQUEST` / `GROUP_MEMBER_ADD` 等，见[事件 payload](/docs/api/events.md)）。

常量：`APPROVE`/`DECLINE`（审批动作）、`OP_ADD`/`OP_DEL`（黑名单/白名单操作）。

| 方法 | 端点 | 说明 |
|---|---|---|
| `get_group_info(group_openid)` | GET /v2/groups/{group_openid}/info | 群名称/简介/分类/标签/成员数 |
| `get_group_members(group_openid, cursor=None)` | GET …/members | 成员列表，每页最多 30 条，`next_cursor` 翻页（空串=末页） |
| `get_group_member(group_openid, member_openid)` | GET …/members/{member_openid} | 成员昵称/角色（member/owner/admin）/入群时间 |
| `get_group_bot_state(group_openid)` | GET …/bot_state | 机器人自身状态：入群时间、是否允许主动推送、群内消息接收设置、角色 |
| `remove_group_members(group_openid, member_openids, add_to_member_blacklist=False)` | POST …/batch_remove_members | 批量移除，单次最多 20 个，可选拉黑 |
| `get_group_join_requests(group_openid, cursor=None, limit=None)` | GET …/join_request_list | 入群申请列表（含验证问答），需群管理员；limit 默认 20 最大 50 |
| `review_group_join_request(group_openid, member_openid, op, join_request_id=None, reject_reason=None, add_to_member_blacklist=None)` | POST …/approval_join_request/{member_openid} | `op`：`APPROVE`/`DECLINE`；拒绝时可附理由并拉黑 |
| `get_group_mute_state(group_openid)` | GET …/restrict_chat_setting | 禁言状态：全员禁言规则（定时/周期）与被禁言成员列表 |
| `get_group_blacklist(group_openid, cursor=None, limit=None)` | GET …/member_blacklist | 黑名单列表，limit 默认 20 最大 100 |
| `update_group_blacklist(group_openid, op, member_openids)` | POST …/member_blacklist | `op`：`OP_ADD`/`OP_DEL`，单次最多 20 个；成员在群中时无法拉黑 |
| `get_join_approval_strategies(cursor=None, limit=None)` | GET /v2/groups/join_approval_strategy | 自动审批策略列表（机器人维度全局配置），按创建时间倒序 |
| `create_join_approval_strategy(*, group_openids=None, group_ids=None, is_enable=None, expire_at=None, remark=None)` | POST /v2/groups/join_approval_strategy | 关联群两种标识二选一（互斥，最多 100 个）；`is_enable` "on"/"off"；默认一年过期；仅机器人有群管理员身份时生效；返回 `strategy_id` |
| `update_join_approval_strategy(strategy_id, *, is_enable=None, expire_at=None, group_action=None, remark=None)` | PATCH …/{strategy_id} | 只传变更项；`group_action` 为 `{"op": "add"/"del", "group_openids": […]}`，群标识形式须与创建时一致 |
| `delete_join_approval_strategy(strategy_id)` | DELETE …/{strategy_id} | 删除策略 |
| `execute_join_approval_strategy(strategy_id)` | POST …/{strategy_id}/execute | 全量扫描关联群并自动通过白名单申请；异步约 10 分钟 |
| `update_join_approval_strategy_whitelist(strategy_id, op, whitelist_users)` | POST …/{strategy_id}/whitelist_users | QQ 号码字符串列表，单次最多 10000、上限 10 万 |
