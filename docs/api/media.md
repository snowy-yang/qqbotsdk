# API · 素材管理

模块：`qqbotsdk.api.media`（核心包）。用于把图片上传为可在 Markdown 里引用的素材（`qqbot-media://<id>`）。

三步走：**prepare（校验+摘要+申请） → 直传 COS（PUT） → complete（通知合并）**。

```python
from pathlib import Path
from qqbotsdk.api.media import (
    prepare_media_image,
    send_media_image,
    complete_media_image,
)

path = Path("a.png")
prepared = await prepare_media_image(path)  # 校验格式/大小 + 计算 MD5/SHA1
await send_media_image(prepared.presigned_url, path)  # PUT 二进制到预签名 URL
done = await complete_media_image(prepared.upload_id, path)
print(done.image_id, done.url)  # 之后在 Markdown 里引用
```

| 接口 | 路由 | 请求 / 响应 | 说明 |
|---|---|---|---|
| `prepare_media_image(file: Path)` | `POST /v2/media-images/prepare` | 本地校验后组 `PrepareMediaImageRequest` → `PrepareMediaImageResponse` | 校验格式/大小、算摘要、申请上传 |
| `send_media_image(presigned_url, file)` | 直传预签名 URL（`PUT`，不带鉴权头） | — → `None` | Content-Type 必须与 prepare 一致，否则 COS 403 |
| `complete_media_image(upload_id, file)` | `POST /v2/media-images/complete` | 组 `CompleteMediaImageRequest` → `CompleteMediaImageResponse` | 服务端比对 ETag |
| `get_media_images(payload)` | `GET /v2/media-images` | `GetMediaImagesRequest` → `GetMediaImagesResponse` | 分页列出素材 |
| `delete_media_image(image_id)` | `DELETE /v2/media-images/{image_id}/delete` | — → `None` | 删除素材 |

> `media.py` 是 API 层的既定例外：它在本地做格式/大小校验、摘要计算与直传 COS，其余接口都是薄映射。

## 辅助函数

| 函数 | 说明 |
|---|---|
| `guess_media_image_type(file: Path) -> str` | 按扩展名推断 MIME；非 png/jpeg/gif/webp 抛 `ValueError` |
| `do_hash(file: Path) -> dict[str, str]` | 同步计算 `{"md5": ..., "sha1": ...}` |

## 限制与字段

- 支持格式：`image/png`、`image/jpeg`、`image/gif`、`image/webp`（常量 `MEDIA_IMAGE_TYPES`）。
- 单张上限：10MB（`MEDIA_IMAGE_MAX_BYTES`），超限抛 `ValueError`。

**`PrepareMediaImageRequest`**（全部必填）：`file_name`（含扩展名）、`file_size`（int，字节）、`content_type`（MIME）、`md5`（32 位 hex）、`sha1`（40 位 hex）。

`PrepareMediaImageResponse`：`upload_id`、`presigned_url`、`expires_in`。

**`CompleteMediaImageRequest`**（全部必填）：`upload_id`、`md5`（服务端与 COS 对象 ETag 比对）。

`CompleteMediaImageResponse`：`image_id`、`url`、`ttl`、`preview_url`。

**`GetMediaImagesRequest`**：`cursor`（可选，翻页用 `next_cursor`）。
`GetMediaImagesResponse`：`images: list[MediaImage]`、`next_cursor`、`total`。

## 常见响应对象字段



**`MediaImage`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `image_id` | `str` | 图片 ID，用于查询与删除 |
| `url` | `str \| None` | Markdown 引用链接，形如 qqbot-media://image/v1/<token> |
| `file_name` | `str \| None` | 上传时的文件名 |
| `preview_url` | `str \| None` | 临时预览链接，短时效，仅供发送前自查，请勿持久化存储 |
| `created_at` | `int \| None` | 上传时间（Unix 秒） |
| `expires_at` | `int \| None` | 过期时间（Unix 秒），每次被消息引用后自动顺延 |

