# agent.md — qqbotsdk-base-py（基座包）

适用范围：`packages/qqbotsdk-base/**`。上级规定见仓库根 `agent.md`。

本包是**最小依赖面**：只有 `aiohttp`、`pydantic`、`loguru`、`python-dotenv`，且不依赖任何业务包。

## MUST（必须做）

- MUST 保持零业务依赖：只能依赖上面四个第三方库，且不得 import `qqbotsdk-py` / `qqbotsdk-guild-py` 的任何模块。
- MUST 保证 `import qqbotsdk.api.core` 等模块在**没有事件循环**的同步上下文里也能成功（会话必须懒加载）。
- MUST 让 `package` 元数据与内容一致：新增子包要在 `pyproject.toml` 的模块名/命名空间配置下仍能打进 wheel。
- MUST 在改动 `api/`、`ws/`、`model/` 任一子模块后，跑通仓库质量门（见根 `agent.md`）。

## SHOULD（应当做）

- SHOULD 把「跨业务域共享」的东西放这里（模型基类、消息子模型、分片上传模型、HTTP 会话、鉴权、网关客户端）。
- SHOULD 让上游包零成本复用：导出稳定的公开名字并写进 `__all__`。
- SHOULD 用 `loguru` 的 `logger` 输出，日志级别按语义选（连接失败 warning、状态变更 info、逐帧细节 debug）。

## MUST NOT（禁止做）

- MUST NOT 把某个业务域独有的模型放进来（群聊、频道、面板等属于各自业务包）。
- MUST NOT 在模块导入期创建 `aiohttp.ClientSession`、读取网络、或做任何需要事件循环的操作。
- MUST NOT 在日志里输出 `access_token`；`_token_text()` 之类的拼接函数禁止被直接打印。
- MUST NOT 修改 `packages/qqbotsdk-base/README.md` 之外的包级说明文档去描述别的包的行为。

## 子模块

| 子模块 | 职责 | 细则 |
|---|---|---|
| `src/qqbotsdk/api/core.py` | 懒加载 HTTP 会话 + 注入鉴权头 | `src/qqbotsdk/api/agent.md` |
| `src/qqbotsdk/api/auth.py` | access_token 获取/缓存/刷新 | 同上 |
| `src/qqbotsdk/model/` | `QQBotBaseModel` 与共享子模型 | `src/qqbotsdk/model/agent.md` |
| `src/qqbotsdk/ws/` | 网关 WebSocket 客户端 | `src/qqbotsdk/ws/agent.md` |
