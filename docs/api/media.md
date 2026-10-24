# 素材管理（Markdown 图片）

`from qqbotsdk.api import BotApi`。将 Markdown 消息所需的图片预上传到平台，获得 `qqbot-media://` 引用后写入 Markdown，无需依赖公网图床；图片在有效期内可反复引用，发送时由平台自动转存（官方 2026-10-21 新增）。

限制：单张 ≤10MB，仅 png/jpeg/gif/webp（扩展名须与 Content-Type 一致），单机器人 100 张（删除释放配额），上传任务 4 小时有效，图片自最后一次被消息引用起 90 天滑动过期。

## 方法

| 方法 | 端点 | 说明 |
|---|---|---|
| `upload_media_image(data, file_name, content_type=MEDIA_IMAGE_PNG)` | prepare + 直传 + complete | **一步上传**：`data` 为图片二进制（≤10MB，超限抛 `ValueError`；md5/sha1 自动计算），返回 `{"image_id", "url", "ttl", "preview_url"}`，`url` 直接写入 Markdown |
| `prepare_media_image(file_name, file_size, content_type, md5, sha1)` | POST /v2/media-images/prepare | 返回 `{"upload_id", "presigned_url", "expires_in"}`；随后 PUT 图片二进制到 `presigned_url`（请求头 Content-Type 必须与声明一致，否则 COS 403），完成后调 `complete_media_image` |
| `complete_media_image(upload_id, md5)` | POST /v2/media-images/complete | `md5` 为直传后 COS 响应的 ETag（去引号即文件 MD5）；返回 `{"image_id", "url", "ttl", "preview_url"}` |
| `get_media_images(cursor=None)` | GET /v2/media-images | 有效图片列表（倒序分页）：首页不传 `cursor`，翻页传上一页 `next_cursor`（空串即末页）；返回 `{"images": [...], "next_cursor", "total"}` |
| `delete_media_image(image_id)` | DELETE /v2/media-images/{image_id}/delete | 删除释放配额；引用链接立即失效（已发消息不受影响），不存在的 id 报 40035008 |

常量：`MEDIA_IMAGE_PNG`/`MEDIA_IMAGE_JPEG`/`MEDIA_IMAGE_GIF`/`MEDIA_IMAGE_WEBP`（`from qqbotsdk.api.media import …`）；大小上限 `MEDIA_IMAGE_MAX_BYTES`（10MB）。

## 用法

```python
from pathlib import Path

upload = await api.upload_media_image(
    Path("kline.png").read_bytes(), "kline.png",
)
await api.post_group_message(
    group_openid,
    markdown=f"![分时K线 #800px #400px]({upload['url']})",
    msg_id=msg.id,
)
```

- `preview_url` 为短时效临时链接，仅供发送前自查，不要持久化存储；
- `qqbot-media://` 链接与机器人绑定，其他机器人引用报 40035010；同一 Markdown 中可与普通公网图片 URL 混用；
- 定期用 `get_media_images` 的 `expires_at` 巡检有效期，不用的图 `delete_media_image` 释放配额（超 100 张时 prepare/complete 报 40035007）。
