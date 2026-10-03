# 部署与常见问题

## 启动方式

普通脚本一个 `bot.run()` 阻塞运行（Ctrl+C 优雅退出）：

```python
bot = Bot()
# ... @bot.on(...) 注册 handler
bot.run()
```

要嵌入自己的 asyncio 应用（如先起自定义组件再跑 SDK），用异步入口：

```python
async def amain():
    async with ClientSession() as http:      # 你的前置装配
        register_handlers(bot, http)
        await bot.start()                    # 装配 SDK 并常驻，随外层协程退出
```

- **WebSocket**：进程常驻即可；SDK 自动处理鉴权（IDENTIFY，断线自动 RESUME）、心跳与重连。
- **Webhook**：平台回调地址要求公网 HTTPS，本地调试建议用反向代理或内网穿透；开放平台会先发 op=13 验证请求，SDK 自动完成签名应答。

## 常见问题

- **启动后频繁重连 / READY 收不到**：QQ 网关接口有频率限制（code 100017），连续重启需间隔约 1 分钟；SDK 已内置退避，等即可。
- **`ApiError`**：HTTP ≥400 时抛出，`e.status`/`e.code`/`e.message` 可用于排查（如被动回复超时、msg_seq 重复、内容审核不通过）。
- **日志出现 `TokenError: 获取 access_token 失败`**：appid/secret 配置错误或被平台拒绝，`code`/`message` 就是 QQ 返回的真实原因，对照官方错误码排查即可。
- **handler 没被触发**：检查 intents.toml 中该事件所属分组是否为 `true`；群/单聊事件需开通对应能力；频道消息事件区分公私域。
- **想收原始数据**：标注 `Event`，`event.raw` 是完整线上 payload（含 op/t/d），`event.typed` 是事件体解析结果（未收录事件类型为 dict）。
- **日志**：SDK 用 loguru 输出中文日志，连接、重连、API 失败、handler 异常均有记录，可直接用 loguru 配置格式与落盘。
