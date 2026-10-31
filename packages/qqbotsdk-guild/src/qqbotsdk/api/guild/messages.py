from qqbotsdk.api.core import session
from qqbotsdk.model.guild.messages import (
    CreateDmsRequest,
    CreateDmsResponse,
    GetChannelMessagesResponse,
    GetChannelReactionUsersRequest,
    GetChannelReactionUsersResponse,
    SendChannelMessagesRequest,
    SendChannelMessagesResponse,
    SendDmsMessagesRequest,
    SendDmsMessagesResponse,
)


async def send_channel_messages(
    channel_id: str,
    payload: SendChannelMessagesRequest,
) -> SendChannelMessagesResponse:
    async with session.post(
        f"/channels/{channel_id}/messages",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return SendChannelMessagesResponse.model_validate(result)


async def recall_channel_messages(
    channel_id: str,
    message_id: str,
    hide_tip: bool = False,
) -> None:
    async with session.delete(
        f"/channels/{channel_id}/messages/{message_id}",
        params={"hidetip": str(hide_tip).lower()},
    ) as resp:
        await resp.json()


async def get_channel_messages(
    channel_id: str,
    message_id: str,
) -> GetChannelMessagesResponse:
    async with session.get(
        f"/channels/{channel_id}/messages/{message_id}",
    ) as resp:
        result = await resp.json()

    return GetChannelMessagesResponse.model_validate(result)


async def put_channel_reaction(
    channel_id: str,
    message_id: str,
    emoji_type: int,
    emoji_id: str,
) -> None:
    async with session.put(
        f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji_type}/{emoji_id}",
    ) as resp:
        await resp.json()


async def delete_channel_reaction(
    channel_id: str,
    message_id: str,
    emoji_type: int,
    emoji_id: str,
) -> None:
    async with session.delete(
        f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji_type}/{emoji_id}",
    ) as resp:
        await resp.json()


async def get_channel_reaction_users(
    channel_id: str,
    message_id: str,
    emoji_type: int,
    emoji_id: str,
    payload: GetChannelReactionUsersRequest,
) -> GetChannelReactionUsersResponse:
    async with session.get(
        f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji_type}/{emoji_id}",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetChannelReactionUsersResponse.model_validate(result)


async def create_dms(
    payload: CreateDmsRequest,
) -> CreateDmsResponse:
    async with session.post(
        "/users/@me/dms",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreateDmsResponse.model_validate(result)


async def send_dms_messages(
    guild_id: str,
    payload: SendDmsMessagesRequest,
) -> SendDmsMessagesResponse:
    async with session.post(
        f"/dms/{guild_id}/messages",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return SendDmsMessagesResponse.model_validate(result)


async def recall_dms_messages(
    guild_id: str,
    message_id: str,
    hide_tip: bool = False,
) -> None:
    async with session.delete(
        f"/dms/{guild_id}/messages/{message_id}",
        params={"hidetip": str(hide_tip).lower()},
    ) as resp:
        await resp.json()
