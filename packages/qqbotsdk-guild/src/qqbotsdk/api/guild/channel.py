from qqbotsdk.api.core import session
from qqbotsdk.model.guild.channel import (
    CreateChannelRequest,
    CreateChannelResponse,
    GetChannelOnlineNumsResponse,
    GetChannelPermissionsResponse,
    GetChannelResponse,
    GetChannelRolePermissionsResponse,
    GetGuildChannelsResponse,
    UpdateChannelPermissionsRequest,
    UpdateChannelRequest,
    UpdateChannelResponse,
)


async def get_channel(
    channel_id: str,
) -> GetChannelResponse:
    async with session.get(
        f"/channels/{channel_id}",
    ) as resp:
        result = await resp.json()

    return GetChannelResponse.model_validate(result)


async def get_guild_channels(
    guild_id: str,
) -> GetGuildChannelsResponse:
    async with session.get(
        f"/guilds/{guild_id}/channels",
    ) as resp:
        result = await resp.json()

    return GetGuildChannelsResponse.model_validate(result)


async def create_channel(
    guild_id: str,
    payload: CreateChannelRequest,
) -> CreateChannelResponse:
    async with session.post(
        f"/guilds/{guild_id}/channels",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreateChannelResponse.model_validate(result)


async def update_channel(
    channel_id: str,
    payload: UpdateChannelRequest,
) -> UpdateChannelResponse:
    async with session.patch(
        f"/channels/{channel_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdateChannelResponse.model_validate(result)


async def delete_channel(
    channel_id: str,
) -> None:
    async with session.delete(
        f"/channels/{channel_id}",
    ) as resp:
        await resp.json()


async def get_channel_online_nums(
    channel_id: str,
) -> GetChannelOnlineNumsResponse:
    async with session.get(
        f"/channels/{channel_id}/online_nums",
    ) as resp:
        result = await resp.json()

    return GetChannelOnlineNumsResponse.model_validate(result)


async def get_channel_permissions(
    channel_id: str,
    user_id: str,
) -> GetChannelPermissionsResponse:
    async with session.get(
        f"/channels/{channel_id}/members/{user_id}/permissions",
    ) as resp:
        result = await resp.json()

    return GetChannelPermissionsResponse.model_validate(result)


async def get_channel_role_permissions(
    channel_id: str,
    role_id: str,
) -> GetChannelRolePermissionsResponse:
    async with session.get(
        f"/channels/{channel_id}/roles/{role_id}/permissions",
    ) as resp:
        result = await resp.json()

    return GetChannelRolePermissionsResponse.model_validate(result)


async def update_channel_permissions(
    channel_id: str,
    user_id: str,
    payload: UpdateChannelPermissionsRequest,
) -> None:
    async with session.put(
        f"/channels/{channel_id}/members/{user_id}/permissions",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()


async def update_channel_role_permissions(
    channel_id: str,
    role_id: str,
    payload: UpdateChannelPermissionsRequest,
) -> None:
    async with session.put(
        f"/channels/{channel_id}/roles/{role_id}/permissions",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()
