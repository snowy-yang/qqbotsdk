from qqbotsdk.api.core import session
from qqbotsdk.model.group.member import (
    GetGroupBotStateResponse,
    GetGroupInfoResponse,
    GetGroupMemberResponse,
    GetGroupMembersRequest,
    GetGroupMembersResponse,
    RemoveGroupMembersRequest,
    RemoveGroupMembersResponse,
)


async def get_group_info(
    group_openid: str,
) -> GetGroupInfoResponse:
    async with session.get(
        f"/v2/groups/{group_openid}/info",
    ) as resp:
        result = await resp.json()

    return GetGroupInfoResponse.model_validate(result)


async def get_group_members(
    group_openid: str,
    payload: GetGroupMembersRequest,
) -> GetGroupMembersResponse:
    async with session.get(
        f"/v2/groups/{group_openid}/members",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetGroupMembersResponse.model_validate(result)


async def get_group_member(
    group_openid: str,
    member_openid: str,
) -> GetGroupMemberResponse:
    async with session.get(
        f"/v2/groups/{group_openid}/members/{member_openid}",
    ) as resp:
        result = await resp.json()

    return GetGroupMemberResponse.model_validate(result)


async def get_group_bot_state(
    group_openid: str,
) -> GetGroupBotStateResponse:
    async with session.get(
        f"/v2/groups/{group_openid}/bot_state",
    ) as resp:
        result = await resp.json()

    return GetGroupBotStateResponse.model_validate(result)


async def remove_group_members(
    group_openid: str,
    payload: RemoveGroupMembersRequest,
) -> RemoveGroupMembersResponse:
    async with session.post(
        f"/v2/groups/{group_openid}/batch_remove_members",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return RemoveGroupMembersResponse.model_validate(result)
