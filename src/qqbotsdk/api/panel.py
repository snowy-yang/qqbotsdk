"""指令面板（斜线指令）与全局自定义菜单方法集。

指令面板即用户在聊天输入框输入 "/" 唤起的指令列表，支持 c2c（单聊）、
group（群聊）、channel（文字子频道）、dm（频道私信）四种场景；c2c/group
支持 target_type=specific 按指定对象生效（关联对象每次最多 20 个，面板
详情最多查 1000 个），channel/dm 仅全局生效。一个机器人最多 20 个面板，
每个面板最多 20 个元素（name ≤14 字符，desc ≤30 字符）。

全局自定义菜单（/v2/menu）仅 C2C 场景、对所有用户生效；send_message
类型点击后把文本（如 "/help"）填入输入框，常与斜线指令配合引导用户。
"""

from typing import Any

from .core import BaseApi

# scope 取值（生效场景）
SCOPE_C2C = "c2c"
SCOPE_GROUP = "group"
SCOPE_CHANNEL = "channel"
SCOPE_DM = "dm"
# target_type 取值（作用范围）
TARGET_ALL = "all"
TARGET_SPECIFIC = "specific"
# 面板元素 type 取值
ITEM_COMMAND = "command"
ITEM_LINK = "link"
# 关联对象操作 op 取值
TARGET_OP_ADD = "add"
TARGET_OP_DEL = "del"


class PanelApi(BaseApi):
    """指令面板与全局菜单方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

    async def create_panel(
        self,
        scope: str,
        panel: dict,
        *,
        target_type: str | None = None,
        user_openids: list[str] | None = None,
        group_openids: list[str] | None = None,
        **extra: Any,
    ) -> dict:
        """创建指令面板（POST /v2/panels），返回 {"panel_id": ...}。

        panel 为 {"items": [...], "remark": ...} 结构，元素为
        {"type": "command"/"link", "name", "desc", "only_admin", "link"}：
        command 类型点击后 name 填入聊天输入框，link 类型点击跳转 link。
        target_type=specific 时经 user_openids（仅 c2c）或 group_openids
        （仅 group）指定生效对象；channel/dm 仅全局（target_type 只能 all）。
        """
        body: dict[str, Any] = {"scope": scope, "panel": panel}
        if target_type is not None:
            body["target_type"] = target_type
        if user_openids is not None:
            body["user_openids"] = user_openids
        if group_openids is not None:
            body["group_openids"] = group_openids
        body.update(extra)
        return await self.post("/v2/panels", json=body)

    async def get_panels(
        self, scope: str, cursor: str | None = None, limit: int | None = None
    ) -> dict:
        """分页查询指令面板列表（GET /v2/panels），按设置时间倒序。

        返回 {"records": [...], "next_cursor": ..., "is_end": ...}；
        next_cursor 为空串表示已到末页，翻页透传上次响应的 next_cursor。
        limit 为每页条数，默认 20、最大 50。
        """
        params: dict[str, Any] = {"scope": scope}
        if cursor:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        return await self.get("/v2/panels", params=params)

    async def get_panel(self, panel_id: str) -> dict:
        """查询指令面板详情（GET /v2/panels/{panel_id}）。

        返回面板配置与生效场景/范围；specific 面板另带关联的
        user_openids / group_openids 列表（最多 1000 条）。
        """
        return await self.get(f"/v2/panels/{panel_id}")

    async def update_panel(self, panel_id: str, panel: dict) -> dict:
        """修改指令面板（PUT /v2/panels/{panel_id}），返回 {"version": ...}。

        panel 整体覆盖面板元素列表与备注，不影响已关联的用户/群列表。
        """
        return await self.put(f"/v2/panels/{panel_id}", json={"panel": panel})

    async def delete_panel(self, panel_id: str) -> dict:
        """删除指令面板（DELETE /v2/panels/{panel_id}），删除后对所有对象失效。"""
        return await self.delete(f"/v2/panels/{panel_id}")

    async def update_panel_targets(
        self,
        panel_id: str,
        op: str,
        user_openids: list[str] | None = None,
        group_openids: list[str] | None = None,
    ) -> dict:
        """增删面板关联对象（PUT /v2/panels/{panel_id}/target）。

        op："add" 添加 / "del" 移除；user_openids 仅 c2c、group_openids
        仅 group，一次最多 20 个。channel/dm 场景与 target_type=all 的
        全局面板不支持此操作。
        """
        body: dict[str, Any] = {"op": op}
        if user_openids is not None:
            body["user_openids"] = user_openids
        if group_openids is not None:
            body["group_openids"] = group_openids
        return await self.put(f"/v2/panels/{panel_id}/target", json=body)

    # ---------- 全局自定义菜单（仅 C2C） ----------

    async def get_menu(self) -> dict:
        """查询全局自定义菜单（GET /v2/menu），返回 {"version": ..., "menu": ...}。

        menu 为 {"items": [...]}，元素为 {"type": "switch"/"send_message"/
        "link"/"menu", "name", "sub_menu_items", "send_message", "link",
        "switch"}；未设置过菜单时该字段为空。
        """
        return await self.get("/v2/menu")

    async def update_menu(self, menu: dict | None = None) -> dict:
        """修改全局自定义菜单（PUT /v2/menu），返回 {"version": ...}。

        仅 C2C 场景、对所有用户生效；menu 为完整配置，传入后整体覆盖
        （菜单项最多 10 个，子菜单最多 5 个且不支持再嵌套）。
        """
        body: dict[str, Any] = {"menu": menu} if menu is not None else {}
        return await self.put("/v2/menu", json=body)
