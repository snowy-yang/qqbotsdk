from qqbotsdk.api.core import session
from qqbotsdk.model.group.blacklist import (
    GetGroupBlacklistRequest,
    GetGroupBlacklistResponse,
    UpdateGroupBlacklistRequest,
    UpdateGroupBlacklistResponse,
)


async def get_group_blacklist(
    group_openid: str,
    payload: GetGroupBlacklistRequest,
) -> GetGroupBlacklistResponse:
    async with session.get(
        f"/v2/groups/{group_openid}/member_blacklist",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetGroupBlacklistResponse.model_validate(result)


async def update_group_blacklist(
    group_openid: str,
    payload: UpdateGroupBlacklistRequest,
) -> UpdateGroupBlacklistResponse:
    async with session.post(
        f"/v2/groups/{group_openid}/member_blacklist",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdateGroupBlacklistResponse.model_validate(result)
