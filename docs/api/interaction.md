# API · 互动

模块：`qqbotsdk.api.interaction`（核心包）。

用户在消息里点击**按钮**或使用**快捷菜单**后，会在有效时间内收到 `INTERACTION_CREATE` 事件；必须调用本接口回应，否则客户端一直 loading。

```python
from qqbotsdk.api.interaction import confirm_interactions
from qqbotsdk.model.interaction import ConfirmInteractionsRequest

await confirm_interactions(
    interaction_id,
    ConfirmInteractionsRequest(code=0),
)
```

| 接口 | 路由 | 请求 / 响应 |
|---|---|---|
| `confirm_interactions(interaction_id, payload)` | `PUT /interactions/{interaction_id}` | `ConfirmInteractionsRequest` → `None` |

- **`ConfirmInteractionsRequest`**：`code`（可选，`Literal[0,1,2,3,4,5]`）。

## code 取值

| code | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 操作失败 |
| `2` | 操作频繁 |
| `3` | 重复操作 |
| `4` | 没有权限 |
| `5` | 仅管理员操作 |

> 只有 `type=11`（消息按钮）与 `type=12`（快捷菜单）需要回应。更省事的封装见 [app.md](../app.md) 的 `ctx.api.ack_interaction(code)`——它自动从事件取 `interaction_id` 并剥离 `INTERACTION_CREATE:` 前缀。
