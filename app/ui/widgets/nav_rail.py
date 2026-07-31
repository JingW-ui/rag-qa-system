# -*- coding: utf-8 -*-
"""
左侧导航栏 — 纯文字按钮切换主内容区页面。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.theme import PANEL_BG, SURFACE_BORDER, FONT_FAMILY, FONT_SIZE_NORMAL


class NavRail(QWidget):
    """最左侧纯文字导航栏，点击切换 QStackedWidget 页面。

    用 QButtonGroup 互斥可选中；`page_changed` 用 `idClicked`
    仅在用户点击时触发，避免程序设置选中态时回环。
    """

    page_changed = Signal(int)  # QStackedWidget 页面索引

    PAGES: list[tuple[str, str]] = [
        ("对话", "对话问答"),
        ("知识库", "知识库与文档"),
        ("设置", "设置"),
        ("帮助", "帮助 / 关于"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(96)
        self.setStyleSheet(
            f"NavRail {{ background-color: {PANEL_BG};"
            f" border-right: 1px solid {SURFACE_BORDER}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(4)

        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, (label, tip) in enumerate(self.PAGES):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(QFont(FONT_FAMILY, FONT_SIZE_NORMAL))
            b.setStyleSheet(self._button_qss())
            self._group.addButton(b, i)
            layout.addWidget(b)
            self._buttons.append(b)

        layout.addStretch()

        # idClicked 仅在用户点击时触发；程序切换页面用 set_current
        self._group.idClicked.connect(self.page_changed)
        self._buttons[0].setChecked(True)  # 默认:对话

    @staticmethod
    def _button_qss() -> str:
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #555555;
                padding: 10px 8px;
                text-align: left;
            }
            QPushButton:hover { background-color: #E5E5E5; }
            QPushButton:checked {
                background-color: #d6eaf8;
                color: #2a7ab5;
                font-weight: 600;
            }
        """

    def set_current(self, index: int) -> None:
        """程序化切换选中项（不触发 page_changed）。"""
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
