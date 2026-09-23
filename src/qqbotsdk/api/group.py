"""群管理方法集（群 openid 接入面）：群信息、成员、机器人群内状态、
入群申请审批、群黑名单、禁言查询与入群自动审批策略。

多数接口要求机器人拥有群管理员身份；成员/黑名单/批量移除等能力
（官方标注"内邀接入中"）与群信息等接口仅白名单机器人可用，未开通时
服务端返回 11253（ApiError.code）。入群自动审批策略是机器人维度的
全局配置（路径不含群 openid），关联群时 group_openids 与 group_ids
二选一（后者为 QQ 群号），最多 100 个，一个机器人最多 20 个策略。
"""

from typing import Any

from .core import BaseApi

# 审批/黑名单/白名单的操作取值
OP_ADD = "add"
OP_DEL = "del"
APPROVE = "approve"
DECLINE = "decline"


class GroupApi(BaseApi):
    """群管理方法集；请求内核（鉴权/重试/错误）由 BaseApi 提供。"""

    # ---------- 群信息与成员 ----------

    async def get_group_info(self, group_openid: str) -> dict:
        """获取群基本信息（GET /v2/groups/{group_openid}/info）。

        返回群名称/简介/分类/标签/成员数等；仅白名单机器人可用。
        """
        return await self.get(f"/v2/groups/{group_openid}/info")

    async def get_group_members(self, group_openid: str, cursor: str | None = None) -> dict:
        """获取群成员列表（GET /v2/groups/{group_openid}/members）。

        每次最多返回 30 条，翻页透传上次响应的 next_cursor（空串=末页）。
        """
        params = {"cursor": cursor} if cursor else None
        return await self.get(f"/v2/groups/{group_openid}/members", params=params)

    async def get_group_member(self, group_openid: str, member_openid: str) -> dict:
        """获取指定群成员信息（GET .../members/{member_openid}）。

        返回昵称、角色（member/owner/admin）、入群时间等。
        """
        return await self.get(
            f"/v2/groups/{group_openid}/members/{member_openid}"
        )

    async def get_group_bot_state(self, group_openid: str) -> dict:
        """获取机器人在指定群内的状态（GET .../bot_state）。

        返回机器人入群时间、是否允许主动推送（allow_proactive_msg）、
        群内消息接收设置（recv_msg_setting）与自身角色。
        """
        return await self.get(f"/v2/groups/{group_openid}/bot_state")

    async def remove_group_members(
        self,
        group_openid: str,
        member_openids: list[str],
        add_to_member_blacklist: bool = False,
    ) -> dict:
        """批量移除群成员（POST .../batch_remove_members），单次最多 20 个。

        add_to_member_blacklist=True 同时加入群黑名单；返回含拉黑失败
        的 openid 列表。
        """
        body: dict[str, Any] = {"member_openids": member_openids}
        if add_to_member_blacklist:
            body["add_to_member_blacklist"] = True
        return await self.post(
            f"/v2/groups/{group_openid}/batch_remove_members", json=body
        )

    # ---------- 入群申请 ----------

    async def get_group_join_requests(
        self, group_openid: str, cursor: str | None = None, limit: int | None = None
    ) -> dict:
        """拉取入群申请列表（GET .../join_request_list），需群管理员身份。

        返回 {"list": [...], "next_cursor": ...}；申请含 join_request_id
        （审批时回传）、验证方式与问答内容。limit 默认 20、最大 50。
        """
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        return await self.get(
            f"/v2/groups/{group_openid}/join_request_list",
            params=params or None,
        )

    async def review_group_join_request(
        self,
        group_openid: str,
        member_openid: str,
        op: str,
        join_request_id: str | None = None,
        reject_reason: str | None = None,
        add_to_member_blacklist: bool | None = None,
    ) -> dict:
        """审批入群申请（POST .../approval_join_request/{member_openid}）。

        op 为 APPROVE（通过）或 DECLINE（拒绝），需群管理员身份；
        拒绝时可附 reject_reason 并以 add_to_member_blacklist=True
        同时加入群黑名单。
        """
        body: dict[str, Any] = {"op": op}
        if join_request_id:
            body["join_request_id"] = join_request_id
        if reject_reason:
            body["reject_reason"] = reject_reason
        if add_to_member_blacklist is not None:
            body["add_to_member_blacklist"] = add_to_member_blacklist
        return await self.post(
            f"/v2/groups/{group_openid}/approval_join_request/{member_openid}",
            json=body,
        )

    # ---------- 群黑名单与禁言查询 ----------

    async def get_group_blacklist(
        self, group_openid: str, cursor: str | None = None, limit: int | None = None
    ) -> dict:
        """查询群黑名单列表（GET .../member_blacklist），支持分页。

        limit 默认 20、最大 100；返回 {"users": [...], "next_cursor": ...}。
        """
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        return await self.get(
            f"/v2/groups/{group_openid}/member_blacklist", params=params or None
        )

    async def update_group_blacklist(
        self, group_openid: str, op: str, member_openids: list[str]
    ) -> dict:
        """群黑名单增删（POST .../member_blacklist），单次最多 20 个。

        op 为 OP_ADD（加入）或 OP_DEL（移出）；目标成员在群中时无法
        加入黑名单（先移除再加）。返回失败的 openid 列表。
        """
        return await self.post(
            f"/v2/groups/{group_openid}/member_blacklist",
            json={"op": op, "member_openids": member_openids},
        )

    async def get_group_mute_state(self, group_openid: str) -> dict:
        """查询群禁言状态（GET .../restrict_chat_setting），需群管理员身份。

        返回全员禁言规则（global_rule：定时/周期禁言）与当前被禁言的
        成员列表（members，不含已过期）。
        """
        return await self.get(f"/v2/groups/{group_openid}/restrict_chat_setting")

    # ---------- 入群自动审批策略（机器人维度全局配置） ----------

    async def get_join_approval_strategies(
        self, cursor: str | None = None, limit: int | None = None
    ) -> dict:
        """查询入群自动审批策略列表（GET /v2/groups/join_approval_strategy）。

        按创建时间倒序，返回 {"strategies": [...], "next_cursor": ...}；
        limit 默认 20、最大 50。
        """
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        return await self.get(
            "/v2/groups/join_approval_strategy", params=params or None
        )

    async def create_join_approval_strategy(
        self,
        *,
        group_openids: list[str] | None = None,
        group_ids: list[str] | None = None,
        is_enable: str | None = None,
        expire_at: str | None = None,
        remark: str | None = None,
        **extra: Any,
    ) -> dict:
        """创建入群自动审批策略（POST /v2/groups/join_approval_strategy）。

        group_openids 与 group_ids（QQ 群号，字符串避免 JS 精度问题）
        二选一必填，互斥，最多 100 个；is_enable "on"/"off"（默认 on）；
        expire_at 为 RFC3339 过期时间（默认一年）；策略仅当机器人拥有
        群管理员身份时生效。返回服务端生成的 strategy_id。
        """
        body: dict[str, Any] = {}
        if group_openids is not None:
            body["group_openids"] = group_openids
        if group_ids is not None:
            body["group_ids"] = group_ids
        if is_enable is not None:
            body["is_enable"] = is_enable
        if expire_at is not None:
            body["expire_at"] = expire_at
        if remark is not None:
            body["remark"] = remark
        body.update(extra)
        return await self.post("/v2/groups/join_approval_strategy", json=body)

    async def update_join_approval_strategy(
        self,
        strategy_id: str,
        *,
        is_enable: str | None = None,
        expire_at: str | None = None,
        group_action: dict | None = None,
        remark: str | None = None,
    ) -> dict:
        """修改入群自动审批策略（PATCH /v2/groups/join_approval_strategy/{id}）。

        只传变更项；group_action 为 {"op": "add"/"del", "group_openids":
        [...]} 或带 "group_ids"，群标识形式须与创建时一致。
        """
        body: dict[str, Any] = {}
        if is_enable is not None:
            body["is_enable"] = is_enable
        if expire_at is not None:
            body["expire_at"] = expire_at
        if group_action is not None:
            body["group_action"] = group_action
        if remark is not None:
            body["remark"] = remark
        return await self.patch(
            f"/v2/groups/join_approval_strategy/{strategy_id}", json=body
        )

    async def delete_join_approval_strategy(self, strategy_id: str) -> dict:
        """删除入群自动审批策略（DELETE /v2/groups/join_approval_strategy/{id}）。"""
        return await self.delete(f"/v2/groups/join_approval_strategy/{strategy_id}")

    async def execute_join_approval_strategy(self, strategy_id: str) -> dict:
        """执行入群自动审批策略（POST .../{strategy_id}/execute）。

        对策略关联的全部群发起全量扫描，命中白名单号码的入群申请自动
        审批通过；异步执行，约 10 分钟完成。
        """
        return await self.post(f"/v2/groups/join_approval_strategy/{strategy_id}/execute")

    async def update_join_approval_strategy_whitelist(
        self, strategy_id: str, op: str, whitelist_users: list[str]
    ) -> dict:
        """增删策略白名单 QQ 号码（POST .../{strategy_id}/whitelist_users）。

        op 为 OP_ADD/OP_DEL；whitelist_users 为 QQ 号码字符串列表
        （避免 JS 精度问题），单次最多 10000 个，号码上限 10 万。
        """
        return await self.post(
            f"/v2/groups/join_approval_strategy/{strategy_id}/whitelist_users",
            json={"op": op, "whitelist_users": whitelist_users},
        )
