"""键盘构建辅助.

手拼内嵌键盘要套 `Keyboard -> KeyboardContent -> Row -> Button -> Action -> RenderData`
五层, 这里给一层薄封装::

    from qqbotsdk.app import callback, keyboard, link, row

    kb = keyboard(
        row(callback("签到", "/signin", style="primary"), link("官网", "https://example.com")),
        row(callback("帮助", "/help")),
    )
    await ctx.api.send_markdown("## 今日签到", keyboard=kb)

也支持链式写法::

    kb = (
        KeyboardBuilder()
        .row(callback("签到", "/signin", style="primary"))
        .button(link("官网", "https://example.com"))
        .build()
    )

约束 (官方文档): 最多 5 行, 每行最多 5 个按钮.
"""

from collections.abc import Iterator
from itertools import count
from typing import Any, Final, Literal, Self

from qqbotsdk.model.sub.messages import Button, Keyboard, Modal, Permission, Row

# 官方文档: 键盘最多 5 行, 每行最多 5 个按钮
MAX_ROWS: Final = 5
MAX_BUTTONS_PER_ROW: Final = 5

# 按钮样式: 0 灰色线框, 1 蓝色线框, 3 白底红字, 4 蓝底白字
STYLE_DEFAULT: Final = 0
STYLE_PRIMARY: Final = 1
STYLE_DANGER: Final = 3
STYLE_POSITIVE: Final = 4

Style = int | Literal["default", "primary", "danger", "positive"]

_STYLE_ALIASES: Final[dict[str, int]] = {
    "default": STYLE_DEFAULT,
    "primary": STYLE_PRIMARY,
    "danger": STYLE_DANGER,
    "positive": STYLE_POSITIVE,
}

_ID_PREFIX: Final = "btn"


def _resolve_style(style: Style) -> int:
    """把样式别名解析成文档里的整数值."""
    if isinstance(style, str):
        if style not in _STYLE_ALIASES:
            raise ValueError(f"未知按钮样式 {style!r}, 可选: {sorted(_STYLE_ALIASES)}")
        return _STYLE_ALIASES[style]
    if style not in set(_STYLE_ALIASES.values()):
        raise ValueError(
            f"未知按钮样式 {style!r}, 可选: {sorted(_STYLE_ALIASES.values())}"
        )
    return style


def _render_data(label: str, visited_label: str | None, style: Style) -> dict[str, Any]:
    data: dict[str, Any] = {"label": label, "style": _resolve_style(style)}
    if visited_label is not None:
        data["visited_label"] = visited_label
    return data


def _button(
    *,
    render_data: dict[str, Any],
    action: dict[str, Any],
    button_id: str | None = None,
    group_id: str | None = None,
) -> Button:
    """按需拼装 Button, 避免用部分关键字构造模型."""
    payload: dict[str, Any] = {"render_data": render_data, "action": action}
    if button_id is not None:
        payload["id"] = button_id
    if group_id is not None:
        payload["group_id"] = group_id
    return Button.model_validate(payload)


def callback(
    label: str,
    data: str,
    *,
    style: Style = "default",
    visited_label: str | None = None,
    button_id: str | None = None,
    permission: Permission | None = None,
    unsupported_tips: str | None = None,
    group_id: str | None = None,
    modal: Modal | None = None,
) -> Button:
    """回调按钮: 用户点击后把 ``data`` 回给后台 (收到 INTERACTION_CREATE).

    Args:
        label: 按钮文字, 最多 10 个字符.
        data: 回调数据, 会原样回传.
        style: 样式, 见 ``STYLE_*`` 或 "default"/"primary"/"danger"/"positive".
        visited_label: 点击后显示的文字, 省略则不变.
        button_id: 按钮 ID, 省略时在组装键盘时自动生成.
        permission: 可见/可点权限.
        unsupported_tips: 版本过低时的提示文案.
        group_id: 同组按钮点击后其它按钮置灰, 仅回调按钮有效.
        modal: 二次确认弹窗, 可用 :func:`confirm_modal` 生成.
    """
    action: dict[str, Any] = {"type": 1, "data": data}
    if permission is not None:
        action["permission"] = permission
    if unsupported_tips is not None:
        action["unsupport_tips"] = unsupported_tips
    if modal is not None:
        action["modal"] = modal
    return _button(
        render_data=_render_data(label, visited_label, style),
        action=action,
        button_id=button_id,
        group_id=group_id,
    )


def link(
    label: str,
    url: str,
    *,
    style: Style = "default",
    visited_label: str | None = None,
    button_id: str | None = None,
    unsupported_tips: str | None = None,
    group_id: str | None = None,
) -> Button:
    """跳转按钮: 点击打开链接 (必须是 https) 或小程序."""
    if not url.startswith("https://"):
        raise ValueError("跳转按钮的 URL 必须以 https:// 开头")
    action: dict[str, Any] = {"type": 0, "data": url}
    if unsupported_tips is not None:
        action["unsupport_tips"] = unsupported_tips
    return _button(
        render_data=_render_data(label, visited_label, style),
        action=action,
        button_id=button_id,
        group_id=group_id,
    )


def command(
    label: str,
    data: str,
    *,
    enter: bool = True,
    reply: bool = True,
    anchor: int | None = None,
    style: Style = "default",
    visited_label: str | None = None,
    button_id: str | None = None,
    permission: Permission | None = None,
    unsupported_tips: str | None = None,
    group_id: str | None = None,
) -> Button:
    """指令按钮: 点击后把 ``data`` 填进输入框 (单聊可用).

    Args:
        label: 按钮文字, 最多 10 个字符.
        data: 指令内容.
        enter: 是否自动发送 (仅单聊可用).
        reply: 指令是否带引用回复本消息.
        anchor: 设为 1 时点击唤起手Q选图器, 设置后忽略 ``enter``.
    """
    action: dict[str, Any] = {"type": 2, "data": data, "enter": enter, "reply": reply}
    if anchor is not None:
        action["anchor"] = anchor
    if permission is not None:
        action["permission"] = permission
    if unsupported_tips is not None:
        action["unsupport_tips"] = unsupported_tips
    return _button(
        render_data=_render_data(label, visited_label, style),
        action=action,
        button_id=button_id,
        group_id=group_id,
    )


def confirm_modal(
    content: str,
    *,
    confirm_text: str | None = None,
    cancel_text: str | None = None,
) -> Modal:
    """二次确认弹窗, 传给 ``callback(..., modal=...)`` 使用."""
    payload: dict[str, Any] = {"content": content}
    if confirm_text is not None:
        payload["confirm_text"] = confirm_text
    if cancel_text is not None:
        payload["cancel_text"] = cancel_text
    return Modal.model_validate(payload)


def everyone() -> Permission:
    """所有人可点击 (官方 ``permission.type = 2``).

    对应显式写法 ``Permission(type=2)``; 这也是不传 ``permission`` 时的默认行为.
    """
    return Permission.model_validate({"type": 2})


def only_admin() -> Permission:
    """仅管理员可点击 (官方 ``permission.type = 1``).

    对应显式写法 ``Permission(type=1)``. 注意: 约束的是"**可点击**", 不是"可见".
    """
    return Permission.model_validate({"type": 1})


def only_users(*user_ids: str) -> Permission:
    """仅指定用户可点击 (官方 ``permission.type = 0`` + ``specify_user_ids``).

    Args:
        user_ids: 允许点击的用户 ID. 群聊传群成员 ``member_openid``, 单聊/频道传对应的
            ``user_openid`` / ``user_id``; 至少传一个.

    Raises:
        ValueError: 一个都没传.
    """
    if not user_ids:
        raise ValueError("only_users 至少需要一个用户 ID")
    return Permission.model_validate({"type": 0, "specify_user_ids": list(user_ids)})


def only_roles(*role_ids: str) -> Permission:
    """仅指定身份组可点击 (官方 ``permission.type = 3`` + ``specify_role_ids``).

    身份组是**频道域**概念, 群聊/单聊请用 :func:`only_users`.

    Args:
        role_ids: 允许点击的身份组 ID, 至少传一个.

    Raises:
        ValueError: 一个都没传.
    """
    if not role_ids:
        raise ValueError("only_roles 至少需要一个身份组 ID")
    return Permission.model_validate({"type": 3, "specify_role_ids": list(role_ids)})


def row(*buttons: Button) -> Row:
    """把若干按钮组成一行."""
    if not buttons:
        raise ValueError("一行至少要有一个按钮")
    if len(buttons) > MAX_BUTTONS_PER_ROW:
        raise ValueError(
            f"一行最多 {MAX_BUTTONS_PER_ROW} 个按钮, 当前 {len(buttons)} 个"
        )
    return Row.model_validate({"buttons": list(buttons)})


def _assign_ids(rows: list[Row]) -> list[Row]:
    """给没有 id 的按钮按顺序补上 ``btn-1``, ``btn-2`` ..."""
    counter: Iterator[int] = count(1)
    assigned: list[Row] = []
    for current in rows:
        buttons: list[Button] = []
        for button in current.buttons or []:
            if button.id:
                buttons.append(button)
            else:
                buttons.append(
                    button.model_copy(update={"id": f"{_ID_PREFIX}-{next(counter)}"})
                )
        assigned.append(Row.model_validate({"buttons": buttons}))
    return assigned


def _build_keyboard(rows: list[Row]) -> Keyboard:
    if not rows:
        raise ValueError("键盘至少要有一个按钮")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"键盘最多 {MAX_ROWS} 行, 当前 {len(rows)} 行")
    return Keyboard.model_validate(
        {"content": {"rows": _assign_ids(rows)}},
    )


def keyboard(
    *items: Row | Button,
    max_per_row: int = MAX_BUTTONS_PER_ROW,
) -> Keyboard:
    """组装键盘.

    可以传若干 ``Row``, 也可以直接传 ``Button`` (按 ``max_per_row`` 自动切行)::

        keyboard(row(callback("A", "/a"), callback("B", "/b")))
        keyboard(callback("A", "/a"), callback("B", "/b"), max_per_row=1)

    Raises:
        ValueError: 行数或每行按钮数超限, 或者没有按钮.
    """
    if max_per_row < 1 or max_per_row > MAX_BUTTONS_PER_ROW:
        raise ValueError(f"max_per_row 需在 1..{MAX_BUTTONS_PER_ROW} 之间")

    rows: list[Row] = []
    pending: list[Button] = []
    for item in items:
        if isinstance(item, Button):
            pending.append(item)
            if len(pending) >= max_per_row:
                rows.append(row(*pending))
                pending = []
        else:
            if pending:
                rows.append(row(*pending))
                pending = []
            rows.append(item)
    if pending:
        rows.append(row(*pending))

    return _build_keyboard(rows)


class KeyboardBuilder:
    """链式键盘构建器, 适合按条件动态拼装."""

    def __init__(self) -> None:
        self._rows: list[Row] = []
        self._pending: list[Button] = []

    def button(self, *buttons: Button) -> Self:
        """往当前行追加按钮 (超过 5 个自动换行)."""
        for button in buttons:
            self._pending.append(button)
            if len(self._pending) >= MAX_BUTTONS_PER_ROW:
                self._flush()
        return self

    def row(self, *buttons: Button) -> Self:
        """结束当前行, 另起一行."""
        self._flush()
        if buttons:
            self._rows.append(row(*buttons))
        return self

    def _flush(self) -> None:
        if self._pending:
            self._rows.append(row(*self._pending))
            self._pending = []

    def build(self) -> Keyboard:
        """产出 ``Keyboard``; 行数超限或没有任何按钮时抛 ``ValueError``."""
        self._flush()
        return _build_keyboard(self._rows)


__all__ = [
    "MAX_BUTTONS_PER_ROW",
    "MAX_ROWS",
    "STYLE_DANGER",
    "STYLE_DEFAULT",
    "STYLE_POSITIVE",
    "STYLE_PRIMARY",
    "KeyboardBuilder",
    "Style",
    "callback",
    "command",
    "confirm_modal",
    "everyone",
    "keyboard",
    "link",
    "only_admin",
    "only_roles",
    "only_users",
    "row",
]
