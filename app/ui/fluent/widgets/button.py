# -*- coding: utf-8 -*-
"""
Fluent Design 按钮体系 — 自研实现
==================================
参考模式：
- PrimaryButton: 主色背景 + 白色文字（主要操作）
- ToolButton: 图标按钮，hover 时背景变色
- TransparentButton: 透明背景，hover 时浅灰
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

from ..style import apply_qss


class _FluentButtonMixin:
    """统一应用到所有按钮的属性"""

    def _init_style(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)


class PrimaryButton(QPushButton):
    """Fluent Primary 主按钮 — 蓝色背景 + 白色文字"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self._init_style()

    def _init_style(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def showEvent(self, event):
        super().showEvent(event)
        apply_qss(self, "button")


class ToolButton(QPushButton):
    """Fluent 工具栏按钮 — 仅图标，hover 显示背景"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("ToolButton")
        self._init_style()

    def _init_style(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(32, 32)

    def showEvent(self, event):
        super().showEvent(event)
        apply_qss(self, "button")


class TransparentButton(QPushButton):
    """Fluent 透明按钮 — 无边框，hover 有背景"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("TransparentButton")
        self._init_style()

    def _init_style(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def showEvent(self, event):
        super().showEvent(event)
        apply_qss(self, "button")
