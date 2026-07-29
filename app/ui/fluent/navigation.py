# -*- coding: utf-8 -*-
"""
NavigationInterface — Fluent Design 导航面板（自研实现）
======================================================
参考模式：可折叠侧边导航栏，每项含 icon + text + 选中指示器
- 展开态：显示 icon + 文字（~200px）
- 折叠态：仅显示 icon（~64px）
- 选中项：左侧 3px 蓝色竖条 + 加粗文字
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from .style import apply_qss, is_dark_theme
from .icons import get_icon_for_theme


NAV_EXPANDED = 200
NAV_COLLAPSED = 64


class NavItem(QPushButton):
    """单个导航项 — 自绘，支持 icon + text + 选中态"""

    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._nav_text = text
        self._is_active = False
        self._collapsed = False

        self.setObjectName("navItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(False)
        self.setFixedHeight(44)

    def set_active(self, active: bool):
        self._is_active = active
        self.setProperty("active", active)
        # 强制刷新样式
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def is_active(self) -> bool:
        return self._is_active

    def set_collapsed(self, collapsed: bool):
        self._collapsed = collapsed
        self.update()

    @property
    def nav_text(self) -> str:
        return self._nav_text

    def paintEvent(self, event):
        """自绘导航项"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        is_dark = is_dark_theme()

        # 背景
        if self._is_active:
            bg = QColor(0, 120, 212, 20 if not is_dark else 30)
            painter.fillRect(self.rect(), bg)

        # hover 效果（让 Qt 样式处理，这里只做补充）

        # 选中竖条
        if self._is_active:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#0078d4"))
            painter.drawRoundedRect(0, 8, 3, h - 16, 1.5, 1.5)

        # 图标
        icon_color = "#e0e0e0" if is_dark else "#333333"
        icon = get_icon_for_theme(self._icon_name, is_dark)
        if not icon.isNull():
            icon_size = 20
            ix = 22 if not self._collapsed else (w - icon_size) // 2
            iy = (h - icon_size) // 2
            pixmap = icon.pixmap(icon_size, icon_size)
            painter.drawPixmap(ix, iy, pixmap)

        # 文字（仅展开态显示）
        if not self._collapsed:
            painter.setPen(QColor("#e0e0e0" if is_dark else "#1a1a1a"))
            font = QFont("Microsoft YaHei", 10)
            if self._is_active:
                font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            text_x = 52
            text_y = (h + painter.fontMetrics().ascent()) // 2 - 1
            painter.drawText(text_x, text_y, self._nav_text)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NavigationInterface(QWidget):
    """左侧导航面板 — 可展开/折叠"""

    currentItemChanged = Signal(str)  # 发射 nav_item 的 text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navigationInterface")
        self._items: list[NavItem] = []
        self._active_item: NavItem | None = None
        self._expanded = True
        self._animating = False

        self._setup_ui()
        apply_qss(self, "navigation")

    def _setup_ui(self):
        self.setFixedWidth(NAV_EXPANDED)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # 顶部留白（标题栏高度）
        self._layout.addSpacing(56)

        # 导航项容器
        self._nav_container = QWidget()
        self._nav_layout = QVBoxLayout(self._nav_container)
        self._nav_layout.setContentsMargins(0, 4, 0, 4)
        self._nav_layout.setSpacing(2)
        self._layout.addLayout(self._nav_layout, 1)

        # 底部区域
        self._bottom_layout = QVBoxLayout()
        self._bottom_layout.setContentsMargins(0, 0, 0, 8)
        self._bottom_layout.setSpacing(2)
        self._layout.addLayout(self._bottom_layout)

    # ── 导航项管理 ──────────────────────────────────────────────────

    def add_item(self, icon_name: str, text: str, is_bottom: bool = False) -> NavItem:
        """添加导航项"""
        item = NavItem(icon_name, text, self)
        item.clicked.connect(lambda: self._on_item_clicked(item))

        if is_bottom:
            self._bottom_layout.addWidget(item)
        else:
            self._nav_layout.addWidget(item)

        self._items.append(item)

        # 默认选中第一个
        if len(self._items) == 1 and not is_bottom:
            self.set_current_item(item)

        return item

    def add_stretch(self):
        """添加弹簧，将底部导航项推到底部"""
        self._nav_layout.addStretch(1)

    def set_current_item(self, item: NavItem):
        """设置当前选中的导航项"""
        if self._active_item and self._active_item != item:
            self._active_item.set_active(False)
        item.set_active(True)
        self._active_item = item
        self.currentItemChanged.emit(item.nav_text)

    def set_current_by_text(self, text: str):
        """通过文字设置选中项"""
        for item in self._items:
            if item.nav_text == text:
                self.set_current_item(item)
                return

    # ── 展开/折叠 ──────────────────────────────────────────────────

    def toggle_expand(self):
        """切换展开/折叠"""
        self._expanded = not self._expanded
        target = NAV_EXPANDED if self._expanded else NAV_COLLAPSED

        anim = QPropertyAnimation(self, b"minimumWidth")
        anim.setDuration(200)
        anim.setStartValue(self.width())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(self._on_animation_finished)
        anim.start()

        anim2 = QPropertyAnimation(self, b"maximumWidth")
        anim2.setDuration(200)
        anim2.setStartValue(self.width())
        anim2.setEndValue(target)
        anim2.setEasingCurve(QEasingCurve.OutCubic)
        anim2.start()

        self._expand_anim = anim
        self._expand_anim2 = anim2

        for item in self._items:
            item.set_collapsed(not self._expanded)

    def _on_animation_finished(self):
        self.setFixedWidth(NAV_EXPANDED if self._expanded else NAV_COLLAPSED)

    def is_expanded(self) -> bool:
        return self._expanded

    # ── 内部 ──────────────────────────────────────────────────────

    def _on_item_clicked(self, item: NavItem):
        if item == self._active_item:
            return
        self.set_current_item(item)

    def showEvent(self, event):
        super().showEvent(event)
        apply_qss(self, "navigation")
