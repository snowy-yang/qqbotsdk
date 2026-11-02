# 语法糖设计笔记

记录加「语法糖」时的判断标准，避免糖越加越乱。

## 我对这类语法糖的理解

语法糖不是新能力，是**某个常用意图的短名字**。它必须满足三条：

1. **有唯一映射**：每个糖都能写出等价的显式写法，且糖只是那一种写法的别名。
2. **不隐藏协议**：糖不替用户做协议层面的决定（例如不能悄悄把 `type` 改成别的值）。
3. **可退出**：随时能传底层模型（这里是 `Permission`），糖不是唯一入口。

糖的价值只有一个：**把"我每次都这么写"降到一行**，同时让意图在代码里可读。

## 目标

以按钮权限为例，现状是：

```python
callback("签到", "/signin", permission=Permission(type=2))  # 所有人
callback("管理", "/admin", permission=Permission(type=1))  # 仅管理员
callback(
    "私聊", "/dm", permission=Permission(type=0, specify_user_ids=[uid])
)  # 指定用户
callback(
    "内部", "/inner", permission=Permission(type=3, specify_role_ids=[rid])
)  # 指定身份组(频道)
```

`type=2` 是「所有人」还是「仅管理员」？每次都要翻表。目标：

```python
callback("签到", "/signin", permission=everyone())
callback("管理", "/admin", permission=only_admin())
callback("私聊", "/dm", permission=only_users(uid))
callback("内部", "/inner", permission=only_roles(rid))
```

读代码时不用查表；写代码时不用记数字。

## 会「突兀」的情形（加糖前逐条过）

| 突兀类型 | 表现 | 这条这里的处理 |
|---|---|---|
| **词汇突兀** | 自造词和官方术语对不上（`admin_only`、`visible_to`） | 官方字段是 `permission.type` + `specify_user_ids` / `specify_role_ids`；糖名用 `only_*` / `everyone`，动词与"谁能操作"一致，不另造概念 |
| **语义偏移** | `admin_only=True` 听起来像"仅管理员可见"，实际是"仅管理员**可点**" | 命名直接锁定"可操作"，docstring 首句写明"仅管理员可点击" |
| **默认值被悄悄改变** | 糖一加，默认从"所有人"变成"管理员" | 糖只返回 `Permission`，不改变任何默认值：不传 `permission=` 仍然是所有人 |
| **组合冲突** | `admin_only=True` 和 `visible_to([...])` 同时传，谁生效 | 不做成按钮参数，而是**返回 `Permission`** 的工厂函数，天然互斥：传一个对象，不存在两个开关打架 |
| **返回类型突兀** | `visible_to()` 返回 `Button` 就无法和别的糖组合 | 所有权限糖统一返回 `Permission`，可直接塞 `permission=`，也可自己再 `model_copy(update=...)` |
| **跨场景含糊** | 群里是 `member_openid`，单聊是 `user_openid`，频道是 `user_id`/`role_id` | 参数名保持中性 `user_ids` / `role_ids`，docstring 说明"群内需传群成员 openid、频道传 user_id"；**身份组仅频道可用**这一点必须写出来 |
| **空集合静默失效** | `only_users()` 不传人 → 谁都点不了，还很难查 | 空参数直接 `ValueError` |
| **糖与显式参数并存** | 又加 `permission=` 又加糖参数 | 不新增按钮参数，只加 `Permission` 的工厂函数，入口仍然唯一 |

## 设计决定

- 命名：`everyone()` / `only_admin()` / `only_users(*user_ids)` / `only_roles(*role_ids)`，全部返回 `Permission`。
- 位置：与键盘助手同模块（`qqbotsdk.app.keyboard`），因为它们服务于同一个场景。
- 保留 `permission=Permission(...)` 作为逃生通道，糖只是便利入口。
- 校验：`only_users()` / `only_roles()` 空参数抛 `ValueError`；`type` 由工厂固定，不让用户传。
- 不做的事：不做 `visible_to()`（语义与官方字段不一致）、不做布尔开关（会和现有参数组合打架）、不替用户判断场景（群/频道的 id 语义不同，交给调用方）。

## 加新糖前的 6 个问题

1. 它有唯一的显式等价写法吗？能写进文档吗？
2. 名字用的是官方术语，还是我发明的？
3. 它会不会改变某个默认行为？
4. 它和已有参数能不能同时传？冲突时谁赢？
5. 返回类型能不能与其它糖组合？
6. 参数为空 / 跨场景 / 非法值时，是报错还是静默？

六个问题有一个答不上来，就先不加。
