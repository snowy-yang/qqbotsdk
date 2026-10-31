import asyncio
import hashlib
from mimetypes import guess_type
from pathlib import Path

from qqbotsdk.api.core import session
from qqbotsdk.model.media import (
    CompleteMediaImageRequest,
    CompleteMediaImageResponse,
    GetMediaImagesRequest,
    GetMediaImagesResponse,
    PrepareMediaImageRequest,
    PrepareMediaImageResponse,
)

# 素材管理支持的图片 MIME 类型
MEDIA_IMAGE_PNG = "image/png"
MEDIA_IMAGE_JPEG = "image/jpeg"
MEDIA_IMAGE_GIF = "image/gif"
MEDIA_IMAGE_WEBP = "image/webp"

MEDIA_IMAGE_TYPES = frozenset(
    {
        MEDIA_IMAGE_PNG,
        MEDIA_IMAGE_JPEG,
        MEDIA_IMAGE_GIF,
        MEDIA_IMAGE_WEBP,
    }
)

# 单张图片大小上限 10MB
MEDIA_IMAGE_MAX_BYTES = 10 * 1024 * 1024


def guess_media_image_type(file: Path) -> str:
    mime = guess_type(file.name)[0]
    if mime not in MEDIA_IMAGE_TYPES:
        raise ValueError(
            f"不支持的图片格式 {file.name!r}: 扩展名需为 png/jpeg/gif/webp 之一"
        )
    return mime


def do_hash(file: Path) -> dict[str, str]:
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    with file.open("rb") as f:
        while chunk := f.read(2048):
            md5.update(chunk)
            sha1.update(chunk)
    payload = {
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
    }
    return payload


async def prepare_media_image(
    file: Path,
) -> PrepareMediaImageResponse:
    # 校验格式与大小, 计算摘要后申请上传; 返回 upload_id 与预签名 URL.
    content_type = guess_media_image_type(file)
    file_size = file.stat().st_size
    if file_size > MEDIA_IMAGE_MAX_BYTES:
        raise ValueError(
            f"图片 {file_size} 字节超过素材管理上限 {MEDIA_IMAGE_MAX_BYTES}（10MB）"
        )

    digest = await asyncio.to_thread(do_hash, file)
    payload = PrepareMediaImageRequest(
        file_name=file.name,
        file_size=file_size,
        content_type=content_type,
        md5=digest["md5"],
        sha1=digest["sha1"],
    )

    async with session.post(
        "/v2/media-images/prepare",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return PrepareMediaImageResponse.model_validate(result)


async def send_media_image(
    presigned_url: str,
    file: Path,
) -> None:
    # PUT 直传图片二进制到预签名 URL, COS 返回空响应体.
    # Content-Type 必须与 prepare 时声明的一致, 否则 COS 返回 403.
    async with session.put(
        presigned_url,
        data=file.read_bytes(),
        headers={"Content-Type": guess_media_image_type(file)},
    ) as resp:
        await resp.read()


async def complete_media_image(
    upload_id: str,
    file: Path,
) -> CompleteMediaImageResponse:
    # 通知服务端上传完成; md5 取自文件内容, 服务端会与 COS 对象 ETag 比对.
    digest = await asyncio.to_thread(do_hash, file)
    payload = CompleteMediaImageRequest(
        upload_id=upload_id,
        md5=digest["md5"],
    )

    async with session.post(
        "/v2/media-images/complete",
        json=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return CompleteMediaImageResponse.model_validate(result)


async def get_media_images(
    payload: GetMediaImagesRequest,
) -> GetMediaImagesResponse:
    async with session.get(
        "/v2/media-images",
        params=payload.model_dump(exclude_none=True),
    ) as resp:
        result = await resp.json()

    return GetMediaImagesResponse.model_validate(result)


async def delete_media_image(
    image_id: str,
) -> None:
    async with session.delete(
        f"/v2/media-images/{image_id}/delete",
    ) as resp:
        await resp.json()
