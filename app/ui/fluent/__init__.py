# -*- coding: utf-8 -*-
"""
Fluent Design 界面组件 — RAG_H 自研实现
========================================
参考 PyQt-Fluent-Widgets 库的设计模式，但所有代码均为原创。

使用方式:
    from app.ui.fluent import (
        FluentWindow, FluentTitleBar,
        NavigationInterface, NavItem,
        PrimaryButton, ToolButton,
        CardWidget, SettingCard, SettingCardGroup,
        InfoBar, show_success, show_error,
        SmoothScrollArea,
        theme_manager, set_theme, Theme,
        get_icon,
    )
"""

# 主题系统
from .style import (
    Theme, ThemeManager, FluentColors,
    theme_manager, set_theme, toggle_theme, is_dark_theme,
)

# 图标系统
from .icons import (
    FluentIcon, IconManager,
    icon_manager, get_icon,
)

# 窗口框架
from .window import FluentWindow, FluentTitleBar

# 导航
from .navigation import NavigationInterface, NavItem

# 控件
from .widgets import (
    PrimaryButton, ToolButton, TransparentButton,
    CardWidget, SettingCard, SettingCardGroup,
    InfoBar, InfoBarManager,
    SmoothScrollArea,
)

# InfoBar 快捷函数
from .widgets.info_bar import (
    show_info, show_success, show_warning, show_error,
    info_bar_mgr,
)

__all__ = [
    # 主题
    "Theme", "ThemeManager", "FluentColors",
    "theme_manager", "set_theme", "toggle_theme", "is_dark_theme",
    # 图标
    "FluentIcon", "IconManager", "icon_manager", "get_icon",
    # 窗口
    "FluentWindow", "FluentTitleBar",
    # 导航
    "NavigationInterface", "NavItem",
    # 控件
    "PrimaryButton", "ToolButton", "TransparentButton",
    "CardWidget", "SettingCard", "SettingCardGroup",
    "InfoBar", "InfoBarManager",
    "SmoothScrollArea",
    # InfoBar 快捷
    "show_info", "show_success", "show_warning", "show_error",
    "info_bar_mgr",
]
