from qqbotsdk.api.core import session
from qqbotsdk.model.group.join_request import (
    GetGroupJoinRequestsRequest,
    GetGroupJoinRequestsResponse,
    ReviewGroupJoinRequest,
)


async def get_group_join_requests(
    group_openid: str,
    payload: GetGroupJoinRequestsRequest,
) -> GetGroupJoinRequestsResponse:
    async with session.get(
        f"/v2/groups/{group_openid}/join_request_list",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetGroupJoinRequestsResponse.model_validate(result)


async def review_group_join_request(
    group_openid: str,
    member_openid: str,
    payload: ReviewGroupJoinRequest,
) -> None:
    async with session.post(
        f"/v2/groups/{group_openid}/approval_join_request/{member_openid}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()
