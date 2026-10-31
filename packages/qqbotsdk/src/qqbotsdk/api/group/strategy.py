from qqbotsdk.api.core import session
from qqbotsdk.model.group.strategy import (
    CreateJoinApprovalStrategyRequest,
    CreateJoinApprovalStrategyResponse,
    GetJoinApprovalStrategiesRequest,
    GetJoinApprovalStrategiesResponse,
    UpdateJoinApprovalStrategyRequest,
    UpdateJoinApprovalStrategyResponse,
    UpdateWhitelistUsersRequest,
    UpdateWhitelistUsersResponse,
)


async def get_join_approval_strategies(
    payload: GetJoinApprovalStrategiesRequest,
) -> GetJoinApprovalStrategiesResponse:
    async with session.get(
        "/v2/groups/join_approval_strategy",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetJoinApprovalStrategiesResponse.model_validate(result)


async def create_join_approval_strategy(
    payload: CreateJoinApprovalStrategyRequest,
) -> CreateJoinApprovalStrategyResponse:
    async with session.post(
        "/v2/groups/join_approval_strategy",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreateJoinApprovalStrategyResponse.model_validate(result)


async def update_join_approval_strategy(
    strategy_id: str,
    payload: UpdateJoinApprovalStrategyRequest,
) -> UpdateJoinApprovalStrategyResponse:
    async with session.patch(
        f"/v2/groups/join_approval_strategy/{strategy_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdateJoinApprovalStrategyResponse.model_validate(result)


async def delete_join_approval_strategy(
    strategy_id: str,
) -> None:
    async with session.delete(
        f"/v2/groups/join_approval_strategy/{strategy_id}",
    ) as resp:
        await resp.json()


async def execute_join_approval_strategy(
    strategy_id: str,
) -> None:
    async with session.post(
        f"/v2/groups/join_approval_strategy/{strategy_id}/execute",
    ) as resp:
        await resp.json()


async def update_join_approval_strategy_whitelist(
    strategy_id: str,
    payload: UpdateWhitelistUsersRequest,
) -> UpdateWhitelistUsersResponse:
    async with session.post(
        f"/v2/groups/join_approval_strategy/{strategy_id}/whitelist_users",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdateWhitelistUsersResponse.model_validate(result)
