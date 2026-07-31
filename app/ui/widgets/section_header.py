# -*- coding: utf-8 -*-
"""
共享 UI 工具 — 区块标题栏、水平分隔线、清空 layout。

供 KbPage / SettingsPage / HelpPage 等复用，避免重复的内联实现。
"""

from typing import Callable, Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from app.ui.theme import FONT_FAMILY, FONT_SIZE_NORMAL, separator_style


class SectionHeader(QWidget):
    """区块标题栏：`<b>标题</b>` + stretch + 右侧小按钮组。

    抽取自 kb_panel.py / settings_dialog.py 中重复出现的标题行模式。

    Args:
        title: 标题文本（不含粗体标记，内部自动加 <b>）。
        buttons: 右侧按钮配置列表，每项为 (text, tooltip, on_clicked)；
                 None 占位项表示在其前插入 addStretch()（用于左对齐按钮组）。
                 默认在所有按钮前插入一个 stretch，使标题左对齐、按钮右对齐。
        stretch_first: 若为 False 则不在按钮前插 stretch（按钮左对齐紧贴标题）。
    """

    def __init__(
        self,
        title: str,
        buttons: Optional[list[Optional[tuple[str, str, Callable]]]] = None,
        stretch_first: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"<b>{title}</b>")
        label.setFont(QFont(FONT_FAMILY, FONT_SIZE_NORMAL))
        layout.addWidget(label)

        if stretch_first:
            layout.addStretch()

        self._buttons: list[QPushButton] = []
        for entry in (buttons or []):
            if entry is None:
                layout.addStretch()
                continue
            text, tip, on_clicked = entry
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(on_clicked)
            layout.addWidget(btn)
            self._buttons.append(btn)

    @property
    def buttons(self) -> list[QPushButton]:
        return self._buttons


def h_separator() -> QWidget:
    """1px 水平灰线（迁自 kb_panel._h_separator）。"""
    line = QWidget()
    line.setFixedHeight(1)
    line.setStyleSheet(separator_style())
    return line


def clear_layout(layout) -> None:
    """清空 layout 中所有子 widget（迁自 chat_panel._clear_layout）。"""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
