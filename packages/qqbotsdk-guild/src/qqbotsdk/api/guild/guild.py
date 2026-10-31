from qqbotsdk.api.core import session
from qqbotsdk.model.guild.guild import (
    CreateApiPermissionDemandRequest,
    CreateApiPermissionDemandResponse,
    GetGuildApiPermissionsResponse,
    GetGuildMessageSettingResponse,
    GetGuildResponse,
    GetMeGuildsRequest,
    GetMeGuildsResponse,
)


async def get_guild(
    guild_id: str,
) -> GetGuildResponse:
    async with session.get(
        f"/guilds/{guild_id}",
    ) as resp:
        result = await resp.json()

    return GetGuildResponse.model_validate(result)


async def get_me_guilds(
    payload: GetMeGuildsRequest,
) -> GetMeGuildsResponse:
    async with session.get(
        "/users/@me/guilds",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetMeGuildsResponse.model_validate(result)


async def get_guild_message_setting(
    guild_id: str,
) -> GetGuildMessageSettingResponse:
    async with session.get(
        f"/guilds/{guild_id}/message/setting",
    ) as resp:
        result = await resp.json()

    return GetGuildMessageSettingResponse.model_validate(result)


async def get_guild_api_permissions(
    guild_id: str,
) -> GetGuildApiPermissionsResponse:
    async with session.get(
        f"/guilds/{guild_id}/api_permission",
    ) as resp:
        result = await resp.json()

    return GetGuildApiPermissionsResponse.model_validate(result)


async def create_api_permission_demand(
    guild_id: str,
    payload: CreateApiPermissionDemandRequest,
) -> CreateApiPermissionDemandResponse:
    async with session.post(
        f"/guilds/{guild_id}/api_permission/demand",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreateApiPermissionDemandResponse.model_validate(result)
