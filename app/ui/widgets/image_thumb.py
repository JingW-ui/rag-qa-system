# -*- coding: utf-8 -*-
"""
图片缩略图组件 — 显示在输入区或用户气泡中，支持删除。
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap


class ImageThumb(QFrame):
    """单个图片缩略图，纯图片显示，无边框。"""

    remove_clicked = Signal(object)  # 点击删除时 emit 自身

    DEFAULT_SIZE = 64
    DELETE_BTN_SIZE = 18

    def __init__(self, image_bytes: bytes, removable: bool = True, size: int = DEFAULT_SIZE, parent=None):
        super().__init__(parent)
        self._image_bytes = image_bytes
        self._removable = removable
        self._thumb_size = size
        self._setup_ui()

    def _setup_ui(self) -> None:
        # 组件样式：透明背景，无边框
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)

        # 图片标签
        self._pixmap_label = QLabel()
        pixmap = QPixmap()
        pixmap.loadFromData(self._image_bytes)
        if not pixmap.isNull():
            w, h = pixmap.width(), pixmap.height()
            if w > self._thumb_size or h > self._thumb_size:
                # 大图：等比例缩小
                pixmap = pixmap.scaled(
                    self._thumb_size, self._thumb_size,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            # 小图：保持原始尺寸，不放大
            self._pixmap_label.setPixmap(pixmap)
        self._pixmap_label.setFixedSize(self._thumb_size, self._thumb_size)
        self._pixmap_label.setAlignment(Qt.AlignCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._pixmap_label)

        # 删除按钮（覆盖在右上角，仅输入区可删除）
        if self._removable:
            self._delete_btn = QPushButton("✕")
            self._delete_btn.setFixedSize(self.DELETE_BTN_SIZE, self.DELETE_BTN_SIZE)
            self._delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 0, 0, 0.6);
                    color: white;
                    border: none;
                    border-radius: 9px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(220, 0, 0, 0.9);
                }
            """)
            self._delete_btn.clicked.connect(self._on_remove)
            self._delete_btn.setParent(self)
            # 定位到右上角
            self._delete_btn.move(
                self._thumb_size - self.DELETE_BTN_SIZE - 2, 2
            )
            self._delete_btn.raise_()  # 确保在最上层

    def _on_remove(self) -> None:
        self.remove_clicked.emit(self)

    @property
    def image_bytes(self) -> bytes:
        return self._image_bytes
