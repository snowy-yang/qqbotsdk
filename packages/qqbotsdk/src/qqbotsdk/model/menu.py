from typing import Literal

from pydantic import Field

from qqbotsdk.model.core import QQBotBaseModel


class MenuSwitch(QQBotBaseModel):
    switch_id: str | None = Field(
        None,
        description="开关唯一标识；用户切换状态后消息 ext 中会携带该标识",
    )
    default: bool | None = Field(
        None,
        description="开关初始状态：true=默认打开，false=默认关闭",
    )


class SubMenuItem(QQBotBaseModel):
    name: str | None = Field(
        None,
        description="按钮名称，最多 14 个字符",
    )
    type: Literal["send_message", "link"] | None = Field(
        None,
        description="按钮类型：send_message=发送消息，link=链接跳转；二级菜单不支持 menu",
    )
    send_message: str | None = Field(
        None,
        description="发送的内容，仅 type=send_message 时有效",
    )
    link: str | None = Field(
        None,
        description="跳转链接，仅 type=link 时有效，必须以 https:// 开头",
    )


class MenuItem(QQBotBaseModel):
    name: str | None = Field(
        None,
        description="按钮名称，最多 10 个字符",
    )
    type: Literal["switch", "send_message", "link", "menu"] | None = Field(
        None,
        description="按钮类型：switch=开关，send_message=发送消息，link=链接跳转，menu=含子菜单的折叠项",
    )
    sub_menu_items: list[SubMenuItem] | None = Field(
        None,
        description="子菜单列表，仅 type=menu 时有效，最多 5 个且不支持再嵌套",
    )
    send_message: str | None = Field(
        None,
        description="发送的内容，仅 type=send_message 时有效",
    )
    link: str | None = Field(
        None,
        description="跳转链接，仅 type=link 时有效，必须以 https:// 开头",
    )
    switch: MenuSwitch | None = Field(
        None,
        description="开关配置，仅 type=switch 时有效",
    )


class Menu(QQBotBaseModel):
    items: list[MenuItem] | None = Field(
        None,
        description="菜单项列表，最多 10 个，按列表顺序从左到右展示",
    )


class GetMenuResponse(QQBotBaseModel):
    version: int | None = Field(
        None,
        description="当前菜单的版本号",
    )
    menu: Menu | None = Field(
        None,
        description="当前生效的菜单配置；未设置过菜单时为空",
    )


class UpdateMenuRequest(QQBotBaseModel):
    menu: Menu = Field(
        ...,
        description="菜单配置，传入后会覆盖原有的完整菜单配置",
    )


class UpdateMenuResponse(QQBotBaseModel):
    version: int | None = Field(
        None,
        description="本次修改后的菜单版本号",
    )
