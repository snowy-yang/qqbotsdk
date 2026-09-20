"""Webhook 接入最小示例：HTTP 回调收群 @消息并回复。

运行前提：
1. 项目根目录 .env 配好 APPID/APPSECRET，并设 CONNECTER=webhook；
2. intents.toml 开启 GROUP_AT_MESSAGE_CREATE；
3. 部署在公网 HTTPS 环境（平台仅支持 80/443/8080/8443 端口，
   本地调试可内网穿透），回调地址填
   https://<你的域名>:<端口><WEBHOOK_PATH>；
4. 开放平台保存回调配置时会先发 op=13 验证请求，SDK 自动完成签名应答。

运行：uv run python examples/webhook_bot/main.py
"""

from qqbotsdk import EventEmitter, main
from qqbotsdk.api import BotApi
from qqbotsdk.payloads import GroupAtMessage

ee = EventEmitter()


@ee.on("GROUP_AT_MESSAGE_CREATE")
async def on_group_message(msg: GroupAtMessage, api: BotApi) -> None:
    if not (msg.group_openid and msg.id):
        return
    await api.post_group_message(
        msg.group_openid, content=f"收到：{msg.content}", msg_id=msg.id,
    )


if __name__ == "__main__":
    main(ee)
