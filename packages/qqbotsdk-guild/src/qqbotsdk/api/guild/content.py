from qqbotsdk.api.core import session
from qqbotsdk.model.guild.content import (
    AudioControlRequest,
    CreateChannelScheduleRequest,
    CreateChannelScheduleResponse,
    CreateGuildAnnounceRequest,
    CreateGuildAnnounceResponse,
    DeleteChannelThreadResponse,
    GetChannelPinsResponse,
    GetChannelScheduleResponse,
    GetChannelSchedulesRequest,
    GetChannelSchedulesResponse,
    GetChannelThreadResponse,
    GetChannelThreadsResponse,
    PutChannelThreadRequest,
    PutChannelThreadResponse,
    UpdateChannelScheduleRequest,
    UpdateChannelScheduleResponse,
)


async def create_guild_announce(
    guild_id: str,
    payload: CreateGuildAnnounceRequest,
) -> CreateGuildAnnounceResponse:
    async with session.post(
        f"/guilds/{guild_id}/announces",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreateGuildAnnounceResponse.model_validate(result)


async def delete_guild_announce(
    guild_id: str,
    message_id: str,
) -> None:
    async with session.delete(
        f"/guilds/{guild_id}/announces/{message_id}",
    ) as resp:
        await resp.json()


async def pin_channel_message(
    channel_id: str,
    message_id: str,
) -> GetChannelPinsResponse:
    async with session.put(
        f"/channels/{channel_id}/pins/{message_id}",
    ) as resp:
        result = await resp.json()

    return GetChannelPinsResponse.model_validate(result)


async def unpin_channel_message(
    channel_id: str,
    message_id: str,
) -> None:
    async with session.delete(
        f"/channels/{channel_id}/pins/{message_id}",
    ) as resp:
        await resp.json()


async def get_channel_pins(
    channel_id: str,
) -> GetChannelPinsResponse:
    async with session.get(
        f"/channels/{channel_id}/pins",
    ) as resp:
        result = await resp.json()

    return GetChannelPinsResponse.model_validate(result)


async def get_channel_schedules(
    channel_id: str,
    payload: GetChannelSchedulesRequest,
) -> GetChannelSchedulesResponse:
    async with session.get(
        f"/channels/{channel_id}/schedules",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetChannelSchedulesResponse.model_validate(result)


async def get_channel_schedule(
    channel_id: str,
    schedule_id: str,
) -> GetChannelScheduleResponse:
    async with session.get(
        f"/channels/{channel_id}/schedules/{schedule_id}",
    ) as resp:
        result = await resp.json()

    return GetChannelScheduleResponse.model_validate(result)


async def create_channel_schedule(
    channel_id: str,
    payload: CreateChannelScheduleRequest,
) -> CreateChannelScheduleResponse:
    async with session.post(
        f"/channels/{channel_id}/schedules",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CreateChannelScheduleResponse.model_validate(result)


async def update_channel_schedule(
    channel_id: str,
    schedule_id: str,
    payload: UpdateChannelScheduleRequest,
) -> UpdateChannelScheduleResponse:
    async with session.patch(
        f"/channels/{channel_id}/schedules/{schedule_id}",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UpdateChannelScheduleResponse.model_validate(result)


async def delete_channel_schedule(
    channel_id: str,
    schedule_id: str,
) -> None:
    async with session.delete(
        f"/channels/{channel_id}/schedules/{schedule_id}",
    ) as resp:
        await resp.json()


async def control_channel_audio(
    channel_id: str,
    payload: AudioControlRequest,
) -> None:
    async with session.post(
        f"/channels/{channel_id}/audio",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()


async def put_channel_mic(
    channel_id: str,
) -> None:
    async with session.put(
        f"/channels/{channel_id}/mic",
    ) as resp:
        await resp.json()


async def delete_channel_mic(
    channel_id: str,
) -> None:
    async with session.delete(
        f"/channels/{channel_id}/mic",
    ) as resp:
        await resp.json()


async def get_channel_threads(
    channel_id: str,
) -> GetChannelThreadsResponse:
    async with session.get(
        f"/channels/{channel_id}/threads",
    ) as resp:
        result = await resp.json()

    return GetChannelThreadsResponse.model_validate(result)


async def get_channel_thread(
    channel_id: str,
    thread_id: str,
) -> GetChannelThreadResponse:
    async with session.get(
        f"/channels/{channel_id}/threads/{thread_id}",
    ) as resp:
        result = await resp.json()

    return GetChannelThreadResponse.model_validate(result)


async def put_channel_thread(
    channel_id: str,
    payload: PutChannelThreadRequest,
) -> PutChannelThreadResponse:
    async with session.put(
        f"/channels/{channel_id}/threads",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return PutChannelThreadResponse.model_validate(result)


async def delete_channel_thread(
    channel_id: str,
    thread_id: str,
) -> DeleteChannelThreadResponse:
    async with session.delete(
        f"/channels/{channel_id}/threads/{thread_id}",
    ) as resp:
        result = await resp.json()

    return DeleteChannelThreadResponse.model_validate(result)
