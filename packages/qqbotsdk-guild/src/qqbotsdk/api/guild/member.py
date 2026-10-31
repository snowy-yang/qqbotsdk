from qqbotsdk.api.core import session
from qqbotsdk.model.guild.member import (
    CreateGuildRoleRequest,
    CreateGuildRoleResponse,
    GetGuildMemberResponse,
    GetGuildMembersRequest,
    GetGuildMembersResponse,
    GetGuildRolesResponse,
    GetRoleMembersRequest,
    GetRoleMembersResponse,
    GuildMemberRoleRequest,
    MuteMembersRequest,
    MuteMembersResponse,
    MuteRequest,
    RemoveGuildMemberRequest,
    UpdateGuildRoleRequest,
    UpdateGuildRoleResponse,
)


async def get_guild_members(
    guild_id: str,
    payload: GetGuildMembersRequest,
) -> GetGuildMembersResponse:
    async with session.get(
        f"/guilds/{guild_id}/members",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetGuildMembersResponse.model_validate(result)


async def get_guild_member(
    guild_id: str,
    user_id: str,
) -> GetGuildMemberResponse:
    async with session.get(
        f"/guilds/{guild_id}/members/{user_id}",
    ) as resp:
        result = await resp.json()

    return GetGuildMemberResponse.model_validate(result)


async def remove_guild_member(
    guild_id: str,
    user_id: str,
    payload: RemoveGuildMemberRequest,
) -> None:
    async with session.delete(
        f"/guilds/{guild_id}/members/{user_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()


async def get_guild_roles(
    guild_id: str,
) -> GetGuildRolesResponse:
    async with session.get(
        f"/guilds/{guild_id}/roles",
    ) as resp:
        result = await resp.json()

    return GetGuildRolesResponse.model_validate(result)


async def create_guild_role(
    guild_id: str,
    payload: CreateGuildRoleRequest,
) -> CreateGuildRoleResponse:
    async with session.post(
        f"/guilds/{guild_id}/roles",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreateGuildRoleResponse.model_validate(result)


async def update_guild_role(
    guild_id: str,
    role_id: str,
    payload: UpdateGuildRoleRequest,
) -> UpdateGuildRoleResponse:
    async with session.patch(
        f"/guilds/{guild_id}/roles/{role_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdateGuildRoleResponse.model_validate(result)


async def delete_guild_role(
    guild_id: str,
    role_id: str,
) -> None:
    async with session.delete(
        f"/guilds/{guild_id}/roles/{role_id}",
    ) as resp:
        await resp.json()


async def get_role_members(
    guild_id: str,
    role_id: str,
    payload: GetRoleMembersRequest,
) -> GetRoleMembersResponse:
    async with session.get(
        f"/guilds/{guild_id}/roles/{role_id}/members",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetRoleMembersResponse.model_validate(result)


async def add_guild_member_role(
    guild_id: str,
    user_id: str,
    role_id: str,
    payload: GuildMemberRoleRequest,
) -> None:
    async with session.put(
        f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()


async def remove_guild_member_role(
    guild_id: str,
    user_id: str,
    role_id: str,
    payload: GuildMemberRoleRequest,
) -> None:
    async with session.delete(
        f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()


async def mute_guild(
    guild_id: str,
    payload: MuteRequest,
) -> None:
    async with session.patch(
        f"/guilds/{guild_id}/mute",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()


async def mute_guild_members(
    guild_id: str,
    payload: MuteMembersRequest,
) -> MuteMembersResponse:
    async with session.patch(
        f"/guilds/{guild_id}/mute",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return MuteMembersResponse.model_validate(result)


async def mute_guild_member(
    guild_id: str,
    user_id: str,
    payload: MuteRequest,
) -> None:
    async with session.patch(
        f"/guilds/{guild_id}/members/{user_id}/mute",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()
