# API · 菜单与面板

模块：`qqbotsdk.api.menu`、`qqbotsdk.api.panel`（核心包）。

## 全局自定义菜单 menu

机器人输入框旁的自定义菜单。全局唯一，读写两个接口。

```python
from qqbotsdk.api.menu import get_menu, update_menu
from qqbotsdk.model.menu import UpdateMenuRequest

current = await get_menu()
print(current.version, current.menu)
await update_menu(UpdateMenuRequest(menu=new_menu))  # 整体覆盖
```

| 接口 | 路由 | 请求 / 响应 | 说明 |
|---|---|---|---|
| `get_menu()` | `GET /v2/menu` | — → `GetMenuResponse` | 取当前菜单 |
| `update_menu(payload)` | `PUT /v2/menu` | `UpdateMenuRequest` → `UpdateMenuResponse` | 整体覆盖 |

- `GetMenuResponse`：`version`、`menu: Menu`。
- **`UpdateMenuRequest`**：`menu: Menu`（可选，传入会覆盖原有完整菜单配置）。

## 指令面板 panel

按场景（单聊 / 群聊 / 子频道 / 频道私信）配置的面板。

```python
from qqbotsdk.api.panel import (
    get_panels,
    create_panel,
    get_panel,
    update_panel,
    delete_panel,
    update_panel_target,
)
from qqbotsdk.model.panel import (
    GetPanelsRequest,
    CreatePanelRequest,
    UpdatePanelRequest,
    UpdatePanelTargetRequest,
)

page = await get_panels(GetPanelsRequest(scope="group", limit=20))
for rec in page.records or []:
    print(rec)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `get_panels(payload)` | `GET /v2/panels` | `GetPanelsRequest` → `GetPanelsResponse` |
| `create_panel(payload)` | `POST /v2/panels` | `CreatePanelRequest` → `CreatePanelResponse` |
| `get_panel(panel_id)` | `GET /v2/panels/{panel_id}` | — → `GetPanelResponse` |
| `update_panel(panel_id, payload)` | `PUT /v2/panels/{panel_id}` | `UpdatePanelRequest` → `UpdatePanelResponse` |
| `delete_panel(panel_id)` | `DELETE /v2/panels/{panel_id}` | — → `None` |
| `update_panel_target(panel_id, payload)` | `PUT /v2/panels/{panel_id}/target` | `UpdatePanelTargetRequest` → `None` |

- `GetPanelsResponse`：`records: list[PanelRecord]`、`next_cursor`、`is_end`。
- **`GetPanelsRequest`**：
  - `scope`（必填，`c2c`单聊 / `group`群聊 / `channel`文字子频道 / `dm`频道私信）
  - `cursor`（可选）、`limit`（可选，默认 20，最大 50）
- **`CreatePanelRequest`**：
  - `scope`（必填；`channel` 和 `dm` 仅支持 `target_type=all`）
  - `target_type`（可选，`all`/`specific`；仅 `c2c`/`group` 支持 `specific`）
  - `user_openids`（可选，仅 c2c+specific，≤20）、`group_openids`（可选，仅 group+specific，≤20）
  - `panel: Panel`（必填，面板配置）
- **`UpdatePanelRequest`**：`panel: Panel`（必填，会覆盖原有元素列表与备注）。
- **`UpdatePanelTargetRequest`**：`op`（必填，`add`/`del`）、`user_openids`（仅 c2c）、`group_openids`（仅 group），各 ≤20。

## 常见响应对象字段



**`Menu`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | `list[menu.MenuItem] \| None` | 菜单项列表，最多 10 个，按列表顺序从左到右展示 |

**`Panel`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | `list[panel.PanelItem] \| None` | 面板元素列表，最多 20 个 |
| `remark` | `str \| None` | 面板备注，最多 255 个字符，不对用户展示 |
| `version` | `int \| None` | 当前版本号 |

**`PanelItem`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | `str \| None` | 元素名称，最多 14 个字符，约 7 个中文汉字；type=command 时点击后填入聊天输入框，type=link 时仅用于展示 |
| `desc` | `str \| None` | 元素描述，最多 30 个字符，约 15 个中文汉字，在面板中展示给用户 |
| `type` | `Literal['command', 'link'] \| None` | 元素类型：command=指令，link=链接跳转 |
| `only_admin` | `bool \| None` | 是否仅管理员可操作 |
| `link` | `str \| None` | 跳转链接，仅 type=link 时有效 |

**`PanelRecord`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `panel_id` | `str \| None` | 面板 ID |
| `scope` | `Literal['c2c', 'group', 'channel', 'dm'] \| None` | 生效场景：c2c=单聊，group=群聊，channel=文字子频道，dm=频道私信 |
| `target_type` | `Literal['all', 'specific'] \| None` | 作用范围：all=全局配置，specific=指定用户/群生效，仅 c2c/group 场景可能为 specific |
| `panel` | `panel.Panel \| None` | 面板配置内容 |
| `created_at` | `str \| None` | 面板创建时间，RFC3339 格式 |
| `updated_at` | `str \| None` | 面板更新时间，RFC3339 格式 |
| `version` | `int \| None` | 面板版本号 |

