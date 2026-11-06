"""``qqbotsdk.app`` 内部共享的类型.

单独放一个叶子模块, 是为了让 :mod:`qqbotsdk.app.api` 与 :mod:`qqbotsdk.app.context`
都能引用这些类型而不产生循环导入: ``context`` 要用 ``SceneApi``, ``api`` 的返回值
又要标注 ``PreparedReply``, 两边直接互相 import 会成环.

本模块不导入 ``qqbotsdk.app`` 下的任何模块, 只依赖 ``qqbotsdk.model``。
"""

from typing import Literal, NamedTuple

from qqbotsdk.model.group.messages import SendGroupMessagesRequest
from qqbotsdk.model.user.messages import SendUserMessagesRequest

Scene = Literal["group", "c2c", "other"]
"""场景: 群聊 / 单聊 / 其它(既没有群 OpenID 也没有单聊用户 OpenID)."""


class PreparedReply(NamedTuple):
    """一条已经算好锚点、序号与 ``msg_type`` 的被动回复.

    由 :meth:`qqbotsdk.app.context.Context.build_reply` 产出, 三个字段可以按位置
    解包::

        scene, openid, request = ctx.build_reply(markdown="**hi**")

    Attributes:
        scene: 发送场景, ``"group"`` 或 ``"c2c"``.
        openid: 目标群 / 用户的 openid.
        request: 可以直接交给 ``send_group_messages`` / ``send_user_messages``
            的请求模型.
    """

    scene: Scene
    openid: str
    request: SendGroupMessagesRequest | SendUserMessagesRequest


__all__ = [
    "PreparedReply",
    "Scene",
]
