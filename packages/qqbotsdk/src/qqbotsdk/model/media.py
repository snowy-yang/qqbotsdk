from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel, QQBotRequestModel


class MediaImage(QQBotBaseModel):
    image_id: str = Field(
        ...,
        description="图片 ID，用于查询与删除",
    )
    url: str | None = Field(
        default=None,
        description="Markdown 引用链接，形如 qqbot-media://image/v1/<token>",
    )
    file_name: str | None = Field(
        default=None,
        description="上传时的文件名",
    )
    preview_url: str | None = Field(
        default=None,
        description="临时预览链接，短时效，仅供发送前自查，请勿持久化存储",
    )
    created_at: int | None = Field(
        default=None,
        description="上传时间（Unix 秒）",
    )
    expires_at: int | None = Field(
        default=None,
        description="过期时间（Unix 秒），每次被消息引用后自动顺延",
    )


class PrepareMediaImageRequest(QQBotRequestModel):
    file_name: str = Field(
        ...,
        description="文件名（含扩展名，如 kline.png）",
    )
    file_size: int = Field(
        ...,
        ge=0,
        description="文件大小（字节），单张上限 10MB",
    )
    content_type: str = Field(
        ...,
        description="图片 MIME 类型：image/png、image/jpeg、image/gif、image/webp",
    )
    md5: str = Field(
        ...,
        description="文件内容 MD5（32 位十六进制）",
    )
    sha1: str = Field(
        ...,
        description="文件内容 SHA1（40 位十六进制）",
    )


class PrepareMediaImageResponse(QQBotBaseModel):
    upload_id: str = Field(
        ...,
        description="上传任务 ID，4 小时内有效",
    )
    presigned_url: str = Field(
        ...,
        description="预签名上传 URL，用 HTTP PUT 直传图片二进制",
    )
    expires_in: int | None = Field(
        default=None,
        ge=0,
        description="预签名 URL 有效期（秒），过期后需重新申请",
    )


class CompleteMediaImageRequest(QQBotRequestModel):
    upload_id: str = Field(
        ...,
        description="prepare 返回的上传任务 ID",
    )
    md5: str = Field(
        ...,
        description="上传返回的 ETag（文件 MD5，32 位十六进制），服务端会与 COS 对象实际 ETag 比对",
    )


class CompleteMediaImageResponse(QQBotBaseModel):
    image_id: str = Field(
        ...,
        description="图片 ID，用于查询与删除",
    )
    url: str | None = Field(
        default=None,
        description="Markdown 引用链接，形如 qqbot-media://image/v1/<token>",
    )
    ttl: int | None = Field(
        default=None,
        ge=0,
        description="滑动有效期窗口（秒），每次引用后自动顺延，90 天内未被引用则失效",
    )
    preview_url: str | None = Field(
        default=None,
        description="临时预览链接，短时效，仅供发送前自查，请勿持久化存储",
    )


class GetMediaImagesRequest(QQBotRequestModel):
    cursor: str | None = Field(
        default=None,
        description="分页游标，首页不传，翻页使用上一页返回的 next_cursor",
    )


class GetMediaImagesResponse(QQBotBaseModel):
    images: list[MediaImage] | None = Field(
        default=None,
        description="图片列表，按上传时间倒序",
    )
    next_cursor: str | None = Field(
        default=None,
        description="下一页游标，为空表示已到末页",
    )
    total: int | None = Field(
        default=None,
        ge=0,
        description="当前有效图片总数（与数量上限同一口径）",
    )
