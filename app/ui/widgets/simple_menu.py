# -*- coding: utf-8 -*-
"""
自定义菜单组件 — 去除 Windows 原生边框和阴影，统一样式。
"""

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt

from app.ui.theme import menu_style


class SimpleMenu(QMenu):
    """无系统边框、无阴影、统一样式的右键菜单。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 去除 Windows 系统级边框和阴影
        self.setWindowFlags(
            self.windowFlags()
            | Qt.FramelessWindowHint
            | Qt.NoDropShadowWindowHint
        )
        # 应用统一样式
        self.setStyleSheet(menu_style())
