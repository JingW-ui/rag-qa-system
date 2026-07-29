# -*- coding: utf-8 -*-
"""
FluentWindow — Fluent Design 窗口框架（自研实现）
================================================
参考模式：TitleBar + Navigation + StackedWidget 三明治架构

FluentWindow(QWidget)
├── self.titleBar (FluentTitleBar)   — 自定义标题栏
├── self.hBoxLayout (QHBoxLayout)
│   ├── NavigationInterface          — 左侧可折叠导航
│   └── StackedWidget (QStackedWidget) — 右侧页面容器
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QStackedWidget, QSizePolicy,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPalette
import sys

from .style import apply_qss, theme_manager, Theme, is_dark_theme
from .navigation import NavigationInterface, NAV_EXPANDED, NAV_COLLAPSED


class FluentTitleBar(QWidget):
    """Fluent 自定义标题栏 — 模拟 Fluent Design 风格

    - 48px 高度
    - 左侧：窗口图标 + 标题
    - 右侧：最小化/最大化/关闭按钮
    - 支持鼠标拖拽移动窗口
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(48)

        self._is_dragging = False
        self._drag_pos = QPoint()

        self._setup_ui()

        # 主题变化时更新按钮图标
        theme_manager.themeChanged.connect(self._update_theme_btn)

    def _update_theme_btn(self, _theme_value: str = None):
        """根据当前主题切换按钮图标"""
        if is_dark_theme():
            self._theme_btn.setText("🌙")
            self._theme_btn.setToolTip("切换到浅色主题")
        else:
            self._theme_btn.setText("☀️")
            self._theme_btn.setToolTip("切换到深色主题")

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(8)

        # 窗口图标
        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(18, 18)
        layout.addWidget(self._icon_label)

        # 标题
        self._title_label = QLabel("RAG_H")
        self._title_label.setObjectName("titleLabel")
        self._title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self._title_label)

        layout.addStretch(1)

        # 侧边栏折叠按钮
        self._nav_toggle_btn = QPushButton("☰")
        self._nav_toggle_btn.setFixedSize(36, 36)
        self._nav_toggle_btn.setToolTip("展开/折叠导航")
        self._nav_toggle_btn.setCursor(Qt.PointingHandCursor)
        self._nav_toggle_btn.clicked.connect(self._on_toggle_nav)
        layout.addWidget(self._nav_toggle_btn)

        # 主题切换按钮
        self._theme_btn = QPushButton("☀️")
        self._theme_btn.setFixedSize(36, 36)
        self._theme_btn.setToolTip("切换深色/浅色主题")
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.clicked.connect(self._on_toggle_theme)
        layout.addWidget(self._theme_btn)

        # 窗口控制按钮
        btn_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0;
                font-size: 14px;
                padding: 0 16px;
                color: inherit;
            }
            QPushButton:hover { background-color: rgba(0,0,0,0.06); }
            QPushButton:pressed { background-color: rgba(0,0,0,0.10); }
        """
        btn_style_dark = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0;
                font-size: 14px;
                padding: 0 16px;
                color: #c0c0c0;
            }
            QPushButton:hover { background-color: rgba(255,255,255,0.08); }
            QPushButton:pressed { background-color: rgba(255,255,255,0.12); }
        """

        # 最小化按钮
        self._min_btn = QPushButton("─")
        self._min_btn.setFixedSize(48, 48)
        self._min_btn.setCursor(Qt.PointingHandCursor)
        self._min_btn.clicked.connect(self._on_minimize)
        self._min_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; color: inherit; }
            QPushButton:hover { background-color: rgba(0,0,0,0.06); color: inherit; }
        """)
        layout.addWidget(self._min_btn)

        # 最大化按钮
        self._max_btn = QPushButton("□")
        self._max_btn.setFixedSize(48, 48)
        self._max_btn.setCursor(Qt.PointingHandCursor)
        self._max_btn.clicked.connect(self._on_maximize)
        self._max_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; color: inherit; }
            QPushButton:hover { background-color: rgba(0,0,0,0.06); color: inherit; }
        """)
        layout.addWidget(self._max_btn)

        # 关闭按钮
        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(48, 48)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.clicked.connect(self._on_close)
        self._close_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; color: inherit; }
            QPushButton:hover { background-color: #d13438; color: #ffffff; }
        """)
        layout.addWidget(self._close_btn)

    def set_title(self, title: str):
        self._title_label.setText(title)

    def set_icon(self, pixmap):
        self._icon_label.setPixmap(pixmap)

    # ── 窗口拖拽 ──────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """双击最大化/还原"""
        if event.button() == Qt.LeftButton:
            w = self.window()
            if w.isMaximized():
                w.showNormal()
            else:
                w.showMaximized()

    # ── Slot ──────────────────────────────────────────────────────

    def _on_close(self):
        self.window().close()

    def _on_minimize(self):
        self.window().showMinimized()

    def _on_maximize(self):
        w = self.window()
        if w.isMaximized():
            w.showNormal()
        else:
            w.showMaximized()
        # 更新按钮文字
        self._max_btn.setText("❐" if w.isMaximized() else "□")

    def _on_toggle_nav(self):
        """通知窗口切换导航折叠"""
        parent = self.parent()
        while parent and not hasattr(parent, 'toggle_navigation'):
            parent = parent.parent()
        if parent:
            parent.toggle_navigation()

    def _on_toggle_theme(self):
        theme_manager.toggle()

    def paintEvent(self, event):
        """绘制标题栏背景 + 底部边框线"""
        painter = QPainter(self)
        is_dark = is_dark_theme()
        bg_color = QColor("#2d2d2d" if is_dark else "#ffffff")
        border_color = QColor("#404040" if is_dark else "#e0e0e0")

        painter.fillRect(self.rect(), bg_color)

        # 底部边框
        painter.setPen(QPen(border_color, 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        painter.end()


# 边缘缩放常量
_RESIZE_MARGIN = 4
# 缩放状态
_NONE, _TOP, _BOTTOM, _LEFT, _RIGHT, _TL, _TR, _BL, _BR = range(9)


class FluentWindow(QWidget):
    """Fluent 主窗口 — 无边框 + 自定义标题栏 + 导航 + 页面容器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fluentWindow")

        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 缩放状态
        self._resize_state = _NONE
        self._resize_start_geom = None
        self._resize_start_global = None

        # 主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 标题栏
        self.titleBar = FluentTitleBar(self)
        self._main_layout.addWidget(self.titleBar)

        # 内容区：导航 + 页面
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 导航
        self.navigation = NavigationInterface(self)
        content_layout.addWidget(self.navigation)

        # 页面容器
        self.stackedWidget = QStackedWidget(self)
        content_layout.addWidget(self.stackedWidget, 1)

        self._main_layout.addLayout(content_layout, 1)

        # 监听主题变化
        theme_manager.themeChanged.connect(self._on_theme_changed)

        # 初始主题
        self._on_theme_changed(theme_manager.theme.value)

    # ── 页面管理 ──────────────────────────────────────────────────

    def add_page(self, widget: QWidget, icon_name: str, title: str,
                 is_bottom: bool = False):
        """添加一个页面（自动添加到导航 + StackedWidget）"""
        if not widget.objectName():
            widget.setObjectName(title)
        self.stackedWidget.addWidget(widget)
        item = self.navigation.add_item(icon_name, title, is_bottom=is_bottom)

        # 如果这是第一个页面，自动选中
        if self.stackedWidget.count() == 1:
            self.navigation.set_current_item(item)
            self.stackedWidget.setCurrentWidget(widget)

        return item

    def switch_to(self, widget: QWidget):
        """切换到指定页面"""
        if widget in [self.stackedWidget.widget(i) for i in range(self.stackedWidget.count())]:
            self.stackedWidget.setCurrentWidget(widget)

    def toggle_navigation(self):
        """切换导航展开/折叠"""
        self.navigation.toggle_expand()

    # ── 主题 ──────────────────────────────────────────────────────

    def _on_theme_changed(self, theme_value: str):
        """主题变化时刷新所有样式"""
        is_dark = is_dark_theme()
        bg = QColor("#1e1e1e" if is_dark else "#f3f3f3")
        palette = self.palette()
        palette.setColor(QPalette.Window, bg)
        self.setPalette(palette)

        # 重绘
        self.update()

    # ── 窗口事件 ──────────────────────────────────────────────────

    def paintEvent(self, event):
        """绘制窗口背景"""
        painter = QPainter(self)
        is_dark = is_dark_theme()
        bg_color = QColor("#1e1e1e" if is_dark else "#f3f3f3")
        painter.fillRect(self.rect(), bg_color)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 通知 InfoBarManager 父窗口变化
        from .widgets.info_bar import info_bar_mgr
        info_bar_mgr.set_parent(self)

    def showEvent(self, event):
        super().showEvent(event)
        apply_qss(self, "window")
        from .widgets.info_bar import info_bar_mgr
        info_bar_mgr.set_parent(self)

    # ── 窗口缩放（无边框窗口需要）────────────────────────────────

    def _hit_test(self, pos: QPoint) -> int:
        """检测鼠标位置是否在边缘，返回缩放状态"""
        r = self.rect()
        left = pos.x() <= _RESIZE_MARGIN
        right = pos.x() >= r.width() - _RESIZE_MARGIN
        top = pos.y() <= _RESIZE_MARGIN
        bottom = pos.y() >= r.height() - _RESIZE_MARGIN

        if top and left:
            return _TL
        if top and right:
            return _TR
        if bottom and left:
            return _BL
        if bottom and right:
            return _BR
        if top:
            return _TOP
        if bottom:
            return _BOTTOM
        if left:
            return _LEFT
        if right:
            return _RIGHT
        return _NONE

    def _resize_cursor(self, state: int):
        """设置缩放光标"""
        cursors = {
            _TOP: Qt.SizeVerCursor, _BOTTOM: Qt.SizeVerCursor,
            _LEFT: Qt.SizeHorCursor, _RIGHT: Qt.SizeHorCursor,
            _TL: Qt.SizeFDiagCursor, _BR: Qt.SizeFDiagCursor,
            _TR: Qt.SizeBDiagCursor, _BL: Qt.SizeBDiagCursor,
        }
        self.setCursor(cursors.get(state, Qt.ArrowCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            state = self._hit_test(event.position().toPoint())
            if state != _NONE:
                self._resize_state = state
                self._resize_start_geom = self.geometry()
                self._resize_start_global = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_state != _NONE:
            self._do_resize(event.globalPosition().toPoint())
            event.accept()
            return
        # 悬停时设置光标
        state = self._hit_test(event.position().toPoint())
        self._resize_cursor(state)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_state != _NONE:
            self._resize_state = _NONE
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _do_resize(self, global_pos: QPoint):
        """执行缩放"""
        if self._resize_start_geom is None or self._resize_start_global is None:
            return
        dx = global_pos.x() - self._resize_start_global.x()
        dy = global_pos.y() - self._resize_start_global.y()
        geom = [self._resize_start_geom.x(), self._resize_start_geom.y(),
                self._resize_start_geom.width(), self._resize_start_geom.height()]

        state = self._resize_state
        min_w, min_h = 400, 300

        # 左边缘
        if state in (_LEFT, _TL, _BL):
            geom[0] += dx
            geom[2] -= dx
        # 右边缘
        if state in (_RIGHT, _TR, _BR):
            geom[2] += dx
        # 上边缘
        if state in (_TOP, _TL, _TR):
            geom[1] += dy
            geom[3] -= dy
        # 下边缘
        if state in (_BOTTOM, _BL, _BR):
            geom[3] += dy

        # 最小尺寸限制
        if geom[2] < min_w:
            if state in (_LEFT, _TL, _BL):
                geom[0] -= min_w - geom[2]
            geom[2] = min_w
        if geom[3] < min_h:
            if state in (_TOP, _TL, _TR):
                geom[1] -= min_h - geom[3]
            geom[3] = min_h

        self.setGeometry(*geom)

    # ── 通用方法 ──────────────────────────────────────────────────

    def set_title(self, title: str):
        self.setWindowTitle(title)
        self.titleBar.set_title(title)
