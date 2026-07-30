# -*- coding: utf-8 -*-
"""
图片预览对话框 — 全屏查看图片，支持缩放和拖拽。
"""

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent


class ImagePreviewDialog(QDialog):
    """全屏图片预览对话框，支持缩放和拖拽查看。"""

    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.2
    MAX_ZOOM = 5.0

    def __init__(self, image_bytes: bytes, parent=None):
        super().__init__(parent)
        self._image_bytes = image_bytes
        self._original_pixmap: QPixmap | None = None
        self._current_scale = 1.0
        self._drag_pos: QPoint | None = None
        self._setup_ui()
        self._load_image()

    def _setup_ui(self) -> None:
        self.setWindowTitle("图片预览")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.9);")

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 关闭按钮（右上角）
        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(40, 40)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self._close_btn.clicked.connect(self.close)
        self._close_btn.setParent(self)

        # 图片标签
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setCursor(Qt.OpenHandCursor)
        layout.addWidget(self._image_label)

    def _load_image(self) -> None:
        """加载图片并初始显示。"""
        pixmap = QPixmap()
        if pixmap.loadFromData(self._image_bytes):
            self._original_pixmap = pixmap
            # 初始缩放：适应屏幕
            self._fit_to_screen()

    def _fit_to_screen(self) -> None:
        """缩放图片以适应屏幕。"""
        if self._original_pixmap is None:
            return

        screen = self.screen()
        if screen is None:
            return

        screen_size = screen.availableSize()
        img_size = self._original_pixmap.size()

        # 计算缩放比例
        scale_w = screen_size.width() / img_size.width()
        scale_h = screen_size.height() / img_size.height()
        self._current_scale = min(scale_w, scale_h) * 0.9  # 留 10% 边距

        self._update_display()

    def _update_display(self) -> None:
        """更新图片显示。"""
        if self._original_pixmap is None:
            return

        new_size = self._original_pixmap.size() * self._current_scale
        scaled = self._original_pixmap.scaled(
            int(new_size.width()),
            int(new_size.height()),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)
        self._image_label.resize(scaled.size())

    def showEvent(self, event) -> None:
        """显示时全屏。"""
        super().showEvent(event)
        self.showFullScreen()
        # 延迟定位关闭按钮
        self._close_btn.move(self.width() - 60, 20)
        self._close_btn.raise_()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """鼠标滚轮缩放。"""
        if self._original_pixmap is None:
            return

        delta = event.angleDelta().y()
        if delta > 0:
            # 放大
            self._current_scale = min(self._current_scale * self.ZOOM_FACTOR, self.MAX_ZOOM)
        else:
            # 缩小
            self._current_scale = max(self._current_scale / self.ZOOM_FACTOR, self.MIN_ZOOM)

        self._update_display()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下开始拖拽。"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.position().toPoint()
            self._image_label.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动拖拽图片。"""
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            delta = event.position().toPoint() - self._drag_pos
            self._image_label.move(self._image_label.pos() + delta)
            self._drag_pos = event.position().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放结束拖拽。"""
        self._drag_pos = None
        self._image_label.setCursor(Qt.OpenHandCursor)

    def keyPressEvent(self, event) -> None:
        """按键事件：ESC 关闭，+/- 缩放。"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self._current_scale = min(self._current_scale * self.ZOOM_FACTOR, self.MAX_ZOOM)
            self._update_display()
        elif event.key() == Qt.Key_Minus:
            self._current_scale = max(self._current_scale / self.ZOOM_FACTOR, self.MIN_ZOOM)
            self._update_display()
        else:
            super().keyPressEvent(event)
