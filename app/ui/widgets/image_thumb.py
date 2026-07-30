# -*- coding: utf-8 -*-
"""
图片缩略图组件 — 显示在输入区或用户气泡中，支持删除和大图预览。
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap


class ImageThumb(QFrame):
    """单个图片缩略图，纯图片显示，无边框，支持灵活尺寸。"""

    remove_clicked = Signal(object)  # 点击删除时 emit 自身
    clicked = Signal(bytes)  # 点击图片时 emit 图片字节数据

    DELETE_BTN_SIZE = 20

    def __init__(
        self,
        image_bytes: bytes,
        removable: bool = True,
        max_width: int = 64,
        max_height: int = 64,
        parent=None,
    ):
        super().__init__(parent)
        self._image_bytes = image_bytes
        self._removable = removable
        self._max_width = max_width
        self._max_height = max_height
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
        self._pixmap_label.setCursor(Qt.PointingHandCursor)
        pixmap = QPixmap()
        pixmap.loadFromData(self._image_bytes)

        if not pixmap.isNull():
            # 等比例缩放到 max_width × max_height 范围内
            scaled = pixmap.scaled(
                self._max_width,
                self._max_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._pixmap_label.setPixmap(scaled)
            self._pixmap_label.setFixedSize(scaled.size())
        else:
            self._pixmap_label.setFixedSize(self._max_width, self._max_height)

        self._pixmap_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
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
                    border-radius: 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(220, 0, 0, 0.9);
                }
            """)
            self._delete_btn.clicked.connect(self._on_remove)
            self._delete_btn.setParent(self)
            # 定位到右上角（延迟到 showEvent 获取实际尺寸）
            self._delete_btn.raise_()

    def showEvent(self, event) -> None:
        """显示时重新定位删除按钮到实际图片右上角。"""
        super().showEvent(event)
        if self._removable and hasattr(self, '_delete_btn'):
            img_w = self._pixmap_label.width()
            self._delete_btn.move(img_w - self.DELETE_BTN_SIZE - 2, 2)

    def mousePressEvent(self, event) -> None:
        """点击图片触发预览。"""
        if event.button() == Qt.LeftButton and not self._removable:
            # 只在非可删除模式（气泡中）触发预览
            self.clicked.emit(self._image_bytes)
        super().mousePressEvent(event)

    def _on_remove(self) -> None:
        self.remove_clicked.emit(self)

    @property
    def image_bytes(self) -> bytes:
        return self._image_bytes
