# -*- coding: utf-8 -*-
"""
SmoothScrollArea — 平滑滚动区域（自研实现）
===========================================
参考 Fluent Design 的滚动体验：
- 滚轮触发像素级平滑动画，而非 Qt 默认的行跳跃
- 滚动条窄细圆角，hover 时变宽
"""

from PySide6.QtWidgets import QScrollArea, QScrollBar
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen


class SmoothScrollBar(QScrollBar):
    """Fluent 风格滚动条 — 窄细 + 圆角 + hover 变宽"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground)
        self._hovered = False
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """自绘滚动条"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = 8 if self._hovered else 4
        if self.orientation() == Qt.Vertical:
            rect = self.rect().adjusted(
                (self.width() - width) // 2, 4,
                -(self.width() - width) // 2, -4
            )
        else:
            rect = self.rect().adjusted(
                4, (self.height() - width) // 2,
                -4, -(self.height() - width) // 2
            )

        # 轨道
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 10))
        painter.drawRoundedRect(rect, width // 2, width // 2)

        # 滑块
        if self.maximum() > 0:
            slider_rect = self._slider_rect(rect, width)
            painter.setBrush(QColor(0, 0, 0, 80))
            painter.drawRoundedRect(slider_rect, width // 2, width // 2)

        painter.end()

    def _slider_rect(self, track_rect, width):
        """计算滑块位置"""
        range_ = self.maximum() - self.minimum()
        if range_ <= 0:
            return track_rect

        page = self.pageStep()
        total = range_ + page
        slider_ratio = page / total
        slider_len = max(
            width * 2,
            int(track_rect.height() * slider_ratio)
            if self.orientation() == Qt.Vertical
            else int(track_rect.width() * slider_ratio)
        )

        pos_ratio = self.value() / range_
        if self.orientation() == Qt.Vertical:
            pos = int(pos_ratio * (track_rect.height() - slider_len))
            return track_rect.adjusted(0, pos, 0, pos - (track_rect.height() - slider_len))
        else:
            pos = int(pos_ratio * (track_rect.width() - slider_len))
            return track_rect.adjusted(pos, 0, pos - (track_rect.width() - slider_len), 0)

    def sizeHint(self):
        if self.orientation() == Qt.Vertical:
            from PySide6.QtCore import QSize
            return QSize(8, 100)  # 窄滚动条默认尺寸


class SmoothScrollArea(QScrollArea):
    """平滑滚动区域 — 替换 QScrollArea 的逐行滚轮为平滑动画"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._smooth_timer = QTimer(self)
        self._smooth_timer.timeout.connect(self._tick)
        self._velocity = 0
        self._target = 0
        self._scroll_bar = SmoothScrollBar(self)
        self.setVerticalScrollBar(self._scroll_bar)

    def wheelEvent(self, event):
        """将滚轮事件转为平滑动画"""
        delta = event.angleDelta().y()
        if delta == 0:
            return

        current = self.verticalScrollBar().value()
        step = -delta * 0.5  # 像素映射
        self._target = current + step
        self._target = max(0, min(self._target, self.verticalScrollBar().maximum()))

        if not self._smooth_timer.isActive():
            self._velocity = step
            self._smooth_timer.start(16)  # ~60fps

        event.accept()

    def _tick(self):
        """动画帧 — 向目标逼近"""
        current = self.verticalScrollBar().value()
        diff = self._target - current

        if abs(diff) < 1:
            self.verticalScrollBar().setValue(self._target)
            self._smooth_timer.stop()
            return

        # 缓动逼近
        step = diff * 0.25
        if abs(step) < 1:
            step = 1 if diff > 0 else -1
        self.verticalScrollBar().setValue(current + step)
