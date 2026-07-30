# -*- coding: utf-8 -*-
"""
文件卡片组件 — 显示在输入区或用户气泡中，支持删除。
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class FileCard(QFrame):
    """单个文件附件卡片，显示文件名和删除按钮。"""

    remove_clicked = Signal(object)  # 点击删除时 emit 自身

    CARD_HEIGHT = 36
    DELETE_BTN_SIZE = 18
    MAX_FILENAME_WIDTH = 150

    def __init__(self, filename: str, removable: bool = True, parent=None):
        super().__init__(parent)
        self._filename = filename
        self._removable = removable
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(self.CARD_HEIGHT)
        self.setMaximumWidth(220)
        self.setStyleSheet("""
            QFrame {
                background-color: #f0f4f8;
                border: 1px solid #d0d7de;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # 文件图标
        icon_label = QLabel("📄")
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 文件名
        self._name_label = QLabel(self._filename)
        self._name_label.setFont(QFont("Microsoft YaHei", 9))
        self._name_label.setStyleSheet("color: #24292f; border: none; background: transparent;")
        self._name_label.setMaximumWidth(self.MAX_FILENAME_WIDTH)
        # 截断过长文件名
        if len(self._filename) > 20:
            display_name = self._filename[:17] + "..."
            self._name_label.setText(display_name)
            self._name_label.setToolTip(self._filename)
        layout.addWidget(self._name_label)

        # 删除按钮（仅输入区可删除）
        if self._removable:
            self._delete_btn = QPushButton("✕")
            self._delete_btn.setFixedSize(self.DELETE_BTN_SIZE, self.DELETE_BTN_SIZE)
            self._delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #656d76;
                    border: none;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #cf222e;
                }
            """)
            self._delete_btn.clicked.connect(self._on_remove)
            layout.addWidget(self._delete_btn)

    def _on_remove(self) -> None:
        self.remove_clicked.emit(self)

    @property
    def filename(self) -> str:
        return self._filename
