"""键盘构建辅助的测试."""

import json

import pytest
from pydantic import ValidationError

from qqbotsdk.app import (
    KeyboardBuilder,
    callback,
    command,
    confirm_modal,
    everyone,
    keyboard,
    link,
    only_admin,
    only_roles,
    only_users,
    row,
)
from qqbotsdk.app.keyboard import (
    MAX_BUTTONS_PER_ROW,
    MAX_ROWS,
    STYLE_DANGER,
    STYLE_DEFAULT,
    STYLE_PRIMARY,
    Style,
)
from qqbotsdk.model.sub.messages import Button, Permission


def _flatten(kb: object) -> list[Button]:
    """取出键盘里的按钮 (按行展开)."""
    from qqbotsdk.model.sub.messages import Keyboard

    assert isinstance(kb, Keyboard)
    assert kb.content is not None
    buttons: list[Button] = []
    for current in kb.content.rows or []:
        buttons.extend(current.buttons or [])
    return buttons


def test_callback_button_fields() -> None:
    btn = callback("签到", "/signin", style="primary", visited_label="已签")
    assert btn.id is None
    assert btn.action is not None
    assert btn.action.type == 1
    assert btn.action.data == "/signin"
    assert btn.render_data is not None
    assert btn.render_data.label == "签到"
    assert btn.render_data.visited_label == "已签"
    assert btn.render_data.style == STYLE_PRIMARY


def test_callback_style_aliases() -> None:
    assert callback("a", "/a", style="default").render_data.style == STYLE_DEFAULT  # type: ignore[union-attr]
    assert callback("a", "/a", style="primary").render_data.style == STYLE_PRIMARY  # type: ignore[union-attr]
    assert callback("a", "/a", style="danger").render_data.style == STYLE_DANGER  # type: ignore[union-attr]
    assert callback("a", "/a", style=STYLE_PRIMARY).render_data.style == STYLE_PRIMARY  # type: ignore[union-attr]


def test_unknown_style_raises() -> None:
    bad_style: Style = "rainbow"  # type: ignore[assignment]
    with pytest.raises(ValueError, match="未知按钮样式"):
        callback("a", "/a", style=bad_style)


def test_link_button_requires_https() -> None:
    btn = link("官网", "https://example.com")
    assert btn.action is not None
    assert btn.action.type == 0
    assert btn.action.data == "https://example.com"

    with pytest.raises(ValueError, match="https"):
        link("不安全", "http://example.com")


def test_command_button_defaults() -> None:
    btn = command("帮助", "/help")
    assert btn.action is not None
    assert btn.action.type == 2
    assert btn.action.enter is True
    assert btn.action.reply is True
    assert btn.action.anchor is None


def test_confirm_modal_helper() -> None:
    modal = confirm_modal("确定要签到吗？", confirm_text="确定", cancel_text="取消")
    btn = callback("签到", "/signin", modal=modal)
    assert btn.action is not None
    assert btn.action.modal is not None
    assert btn.action.modal.content == "确定要签到吗？"


def test_button_permission_passthrough() -> None:
    btn = callback("管理", "/admin", permission=Permission(type=1))
    assert btn.action is not None
    assert btn.action.permission is not None
    assert btn.action.permission.type == 1


def test_permission_sugar_everyone_and_admin() -> None:
    assert everyone().model_dump(exclude_none=True) == {"type": 2}
    assert only_admin().model_dump(exclude_none=True) == {"type": 1}


def test_permission_sugar_only_users() -> None:
    perm = only_users("u1", "u2")
    assert perm.type == 0
    assert perm.specify_user_ids == ["u1", "u2"]
    assert perm.specify_role_ids is None


def test_permission_sugar_only_roles() -> None:
    perm = only_roles("r1")
    assert perm.type == 3
    assert perm.specify_role_ids == ["r1"]
    assert perm.specify_user_ids is None


def test_permission_sugar_rejects_empty() -> None:
    with pytest.raises(ValueError, match="至少需要一个用户 ID"):
        only_users()
    with pytest.raises(ValueError, match="至少需要一个身份组 ID"):
        only_roles()


def test_permission_sugar_equals_explicit_form() -> None:
    """每个糖都必须与它文档里写的显式 Permission 写法完全等价."""
    assert everyone() == Permission(type=2)
    assert only_admin() == Permission(type=1)
    assert only_users("u1", "u2") == Permission(type=0, specify_user_ids=["u1", "u2"])
    assert only_roles("r1") == Permission(type=3, specify_role_ids=["r1"])


def test_permission_sugar_fits_button_and_composes() -> None:
    btn = callback("私聊", "/dm", permission=only_users("u1"))
    assert btn.action is not None
    assert btn.action.permission is not None
    assert btn.action.permission.type == 0
    assert btn.action.permission.specify_user_ids == ["u1"]

    # 糖返回 Permission, 仍可再 model_copy 微调 (可退出 / 可组合)
    tweaked = only_admin().model_copy(update={"type": 2})
    assert tweaked.type == 2


def test_keyboard_assigns_ids_and_dumps() -> None:
    kb = keyboard(
        row(callback("签到", "/signin"), link("官网", "https://example.com")),
        row(callback("帮助", "/help")),
    )
    buttons = _flatten(kb)
    assert [b.id for b in buttons] == ["btn-1", "btn-2", "btn-3"]

    dumped = kb.model_dump(exclude_none=True)
    assert json.dumps(dumped)  # 能被 json.dumps 序列化
    assert dumped["content"]["rows"][0]["buttons"][0]["action"]["type"] == 1


def test_keyboard_keeps_explicit_ids() -> None:
    kb = keyboard(row(callback("签到", "/signin", button_id="signin")))
    assert _flatten(kb)[0].id == "signin"


def test_keyboard_auto_chunks_flat_buttons() -> None:
    kb = keyboard(*[callback(f"b{i}", f"/b{i}") for i in range(5)], max_per_row=2)
    assert kb.content is not None
    rows = kb.content.rows or []
    assert [len(r.buttons or []) for r in rows] == [2, 2, 1]


def test_keyboard_rejects_empty_and_oversized() -> None:
    with pytest.raises(ValueError, match="至少要有一个按钮"):
        keyboard()

    with pytest.raises(ValueError, match="最多"):
        row(*[callback(f"b{i}", f"/b{i}") for i in range(MAX_BUTTONS_PER_ROW + 1)])

    too_many_rows = [row(callback(f"b{i}", f"/b{i}")) for i in range(MAX_ROWS + 1)]
    with pytest.raises(ValueError, match="最多"):
        keyboard(*too_many_rows)


def test_builder_chain() -> None:
    kb = (
        KeyboardBuilder()
        .row(callback("签到", "/signin", style="primary"))
        .button(link("官网", "https://example.com"))
        .button(callback("帮助", "/help"))
        .build()
    )
    buttons = _flatten(kb)
    assert len(buttons) == 3
    assert [b.id for b in buttons] == ["btn-1", "btn-2", "btn-3"]


def test_builder_auto_wrap() -> None:
    builder = KeyboardBuilder().button(*[callback(f"b{i}", f"/b{i}") for i in range(6)])
    kb = builder.build()
    assert kb.content is not None
    assert [len(r.buttons or []) for r in kb.content.rows or []] == [5, 1]


def test_builder_requires_button() -> None:
    with pytest.raises(ValueError, match="至少要有一个按钮"):
        KeyboardBuilder().build()


def test_builder_row_limit() -> None:
    builder = KeyboardBuilder()
    for i in range(MAX_ROWS + 1):
        builder.row(callback(f"b{i}", f"/b{i}"))
    with pytest.raises(ValueError, match="最多"):
        builder.build()


def test_keyboard_can_be_used_in_send_request() -> None:
    """拼出来的键盘要能直接塞进发送请求模型."""
    from qqbotsdk.model.group.messages import SendGroupMessagesRequest

    kb = keyboard(row(callback("签到", "/signin")))
    request = SendGroupMessagesRequest.model_validate(
        {"msg_type": 2, "markdown": {"content": "## hi"}, "keyboard": kb.model_dump()}
    )
    assert request.keyboard is not None
    assert request.keyboard.content is not None
    assert request.keyboard.content.rows is not None
    assert request.keyboard.content.rows[0].buttons is not None
    assert request.keyboard.content.rows[0].buttons[0].action is not None
    assert request.keyboard.content.rows[0].buttons[0].action.data == "/signin"


def test_validation_error_on_too_long_label() -> None:
    with pytest.raises(ValidationError):
        callback("这是一个超过十个字符的按钮文案", "/x")
