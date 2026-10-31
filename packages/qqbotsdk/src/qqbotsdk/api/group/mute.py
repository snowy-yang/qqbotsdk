from qqbotsdk.api.core import session
from qqbotsdk.model.group.mute import (
    GetGroupMuteStateResponse,
    SetGroupMuteStateRequest,
)


async def get_group_mute_state(
    group_openid: str,
) -> GetGroupMuteStateResponse:
    async with session.get(
        f"/v2/groups/{group_openid}/restrict_chat_setting",
    ) as resp:
        result = await resp.json()

    return GetGroupMuteStateResponse.model_validate(result)


async def set_group_mute_state(
    group_openid: str,
    payload: SetGroupMuteStateRequest,
) -> None:
    async with session.post(
        f"/v2/groups/{group_openid}/restrict_chat_setting",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()
