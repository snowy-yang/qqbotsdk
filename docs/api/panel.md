# 指令面板与菜单 API

斜线指令面板即用户在聊天输入框输入 `/` 唤起的指令列表，支持 c2c（单聊）、group（群聊）、channel（文字子频道）、dm（频道私信）四种场景；c2c/group 支持 `target_type="specific"` 按指定对象生效（关联对象每次最多 20 个，详情最多查 1000 个），channel/dm 仅全局生效。一个机器人最多 20 个面板，每面板最多 20 个元素（`name` ≤14 字符、`desc` ≤30 字符）。

常量：`SCOPE_C2C`/`SCOPE_GROUP`/`SCOPE_CHANNEL`/`SCOPE_DM`、`TARGET_ALL`/`TARGET_SPECIFIC`、`ITEM_COMMAND`/`ITEM_LINK`、`TARGET_OP_ADD`/`TARGET_OP_DEL`。

| 方法 | 端点 | 说明 |
|---|---|---|
| `create_panel(scope, panel, *, target_type=None, user_openids=None, group_openids=None, **extra)` | POST /v2/panels | 返回 `{"panel_id": …}`；`panel` 为 `{"items": [{"type": "command"/"link", "name", "desc", "only_admin", "link"}], "remark"}`，command 类型点击后 `name` 填入输入框，link 类型点击跳转 |
| `get_panels(scope, cursor=None, limit=None)` | GET /v2/panels | 分页列表（按设置时间倒序），返回 `records`/`next_cursor`（空串=末页）/`is_end`；`limit` 默认 20、最大 50 |
| `get_panel(panel_id)` | GET /v2/panels/{panel_id} | 面板详情，specific 面板另带关联的 `user_openids`/`group_openids` |
| `update_panel(panel_id, panel)` | PUT /v2/panels/{panel_id} | 整体覆盖元素与备注，不影响已关联对象；返回 `{"version": …}` |
| `delete_panel(panel_id)` | DELETE /v2/panels/{panel_id} | 删除面板，删除后对所有对象失效 |
| `update_panel_targets(panel_id, op, user_openids=None, group_openids=None)` | PUT /v2/panels/{panel_id}/target | `op`：`"add"`/`"del"`；`user_openids` 仅 c2c、`group_openids` 仅 group；channel/dm 与全局面板不支持 |
| `get_menu()` | GET /v2/menu | 查询全局自定义菜单（仅 C2C、对所有用户生效），返回 `{"version", "menu"}`；未设置过时 `menu` 为空 |
| `update_menu(menu=None)` | PUT /v2/menu | 整体覆盖菜单（≤10 项，子菜单 ≤5 且不可再嵌套）；`send_message` 类型点击后把文本（如 `/help`）填入输入框，常与斜线指令配合 |
