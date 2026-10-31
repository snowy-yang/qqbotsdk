from qqbotsdk.api.core import session
from qqbotsdk.model.group.messages import (
    PrepareGroupUploadResponse,
    SendGroupMessagesRequest,
    SendGroupMessagesResponse,
    UploadGroupFileRequest,
    UploadGroupFileResponse,
)
from qqbotsdk.model.sub.upload import (
    UploadPartFinishRequest,
    UploadPrepareRequest,
)


async def send_group_messages(
    group_openid: str,
    payload: SendGroupMessagesRequest,
) -> SendGroupMessagesResponse:
    async with session.post(
        f"/v2/groups/{group_openid}/messages",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return SendGroupMessagesResponse.model_validate(result)


async def recall_group_messages(
    group_openid: str,
    message_id: str,
) -> None:
    async with session.delete(
        f"/v2/groups/{group_openid}/messages/{message_id}",
    ) as resp:
        await resp.json()


async def upload_group_file(
    group_openid: str,
    payload: UploadGroupFileRequest,
) -> UploadGroupFileResponse:
    async with session.post(
        f"/v2/groups/{group_openid}/files",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return UploadGroupFileResponse.model_validate(result)


async def prepare_group_upload(
    group_openid: str,
    payload: UploadPrepareRequest,
) -> PrepareGroupUploadResponse:
    async with session.post(
        f"/v2/groups/{group_openid}/upload_prepare",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return PrepareGroupUploadResponse.model_validate(result)


async def finish_group_upload_part(
    group_openid: str,
    payload: UploadPartFinishRequest,
) -> None:
    async with session.post(
        f"/v2/groups/{group_openid}/upload_part_finish",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        await resp.json()
