# -*- coding: utf-8 -*-
"""
InfoBar — Fluent Design 弹出式通知条（自研实现）
===============================================
参考模式：
- 从窗口顶部滑入的横幅通知
- 四种类型: SUCCESS / WARNING / ERROR / INFO
- 自动消失（可配置时间）
- 支持多条通知队列管理
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QFont


# 类型配色（硬编码，不依赖 QSS — 因为这是动态生成的弹出层）
TYPE_STYLES = {
    "success": {
        "bg": "#dff6dd",
        "border": "#b7e0b3",
        "icon": "✅",
        "color": "#107c10",
    },
    "warning": {
        "bg": "#fff4ce",
        "border": "#ffe48f",
        "icon": "⚠️",
        "color": "#d68000",
    },
    "error": {
        "bg": "#fde7e9",
        "border": "#f5c6cb",
        "icon": "❌",
        "color": "#d13438",
    },
    "info": {
        "bg": "#e5f0fa",
        "border": "#b8d8f0",
        "icon": "ℹ️",
        "color": "#0078d4",
    },
}

TYPE_STYLES_DARK = {
    "success": {
        "bg": "#1e3a1e",
        "border": "#2d5a2d",
        "icon": "✅",
        "color": "#6bb86b",
    },
    "warning": {
        "bg": "#3a2e1e",
        "border": "#5a4a2d",
        "icon": "⚠️",
        "color": "#dba852",
    },
    "error": {
        "bg": "#3a1e1e",
        "border": "#5a2d2d",
        "icon": "❌",
        "color": "#e86868",
    },
    "info": {
        "bg": "#1e2a3a",
        "border": "#2d405a",
        "icon": "ℹ️",
        "color": "#5a9edb",
    },
}


class InfoBar(QWidget):
    """弹出式通知条 — 从窗口顶部滑入"""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"

    def __init__(
        self,
        msg: str,
        type_: str = "info",
        duration: int = 5000,
        parent=None,
    ):
        super().__init__(parent)
        self._type = type_
        self._duration = duration
        self._is_dark = False
        self._setup_ui(msg)

    def _setup_ui(self, msg: str):
        self.setFixedHeight(48)
        self.setMinimumWidth(300)
        self.setMaximumWidth(600)

        # 应用样式
        self._apply_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(8)

        # 图标
        style = self._current_style()
        icon_label = QLabel(style["icon"])
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 消息
        msg_label = QLabel(msg)
        msg_label.setFont(QFont("Microsoft YaHei", 10))
        msg_label.setStyleSheet(f"color: {style['color']}; background: transparent;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 12px;
                font-size: 12px;
                color: inherit;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        close_btn.clicked.connect(self._close_animation)
        layout.addWidget(close_btn)

        # 自动消失定时器
        if self._duration > 0:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._close_animation)
            self._timer.start(self._duration)

    def _current_style(self) -> dict:
        styles = TYPE_STYLES_DARK if self._is_dark else TYPE_STYLES
        return styles.get(self._type, styles["info"])

    def _apply_style(self):
        style = self._current_style()
        self.setStyleSheet(f"""
            InfoBar {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-radius: 6px;
            }}
        """)

    def set_dark_mode(self, dark: bool):
        self._is_dark = dark
        self._apply_style()

    def show(self):
        super().show()
        self._slide_in()

    def _slide_in(self):
        """滑入动画"""
        parent_w = self.parent().width() if self.parent() else 600
        self.setGeometry(parent_w, 0, 0, self.height())
        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(300)
        anim.setStartValue(QRect(parent_w, 0, 0, self.height()))
        target_w = min(parent_w - 40, self.maximumWidth())
        anim.setEndValue(QRect(
            (parent_w - target_w) // 2, 12, target_w, self.height()
        ))
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim

    def _close_animation(self):
        """滑出动画后关闭"""
        if self._timer and self._timer.isActive():
            self._timer.stop()
        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(250)
        anim.setStartValue(self.geometry())
        anim.setEndValue(QRect(self.x(), -self.height(), self.width(), self.height()))
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.deleteLater)
        anim.start()
        self._close_anim = anim

    def mousePressEvent(self, event):
        """点击关闭"""
        self._close_animation()
        super().mousePressEvent(event)


class InfoBarManager:
    """全局 InfoBar 显示管理器（单例）"""

    _instance = None

    def __init__(self):
        self._parent = None
        self._is_dark = False

    @classmethod
    def instance(cls) -> "InfoBarManager":
        if cls._instance is None:
            cls._instance = InfoBarManager()
        return cls._instance

    def set_parent(self, parent: QWidget):
        self._parent = parent

    def set_dark_mode(self, dark: bool):
        self._is_dark = dark

    def show(
        self,
        msg: str,
        type_: str = "info",
        duration: int = 5000,
    ) -> InfoBar:
        """显示一条 InfoBar 通知"""
        if self._parent is None:
            # 尝试从顶级窗口获取
            self._parent = QApplication.activeWindow()

        bar = InfoBar(msg, type_, duration, parent=self._parent)
        bar.set_dark_mode(self._is_dark)
        bar.show()
        return bar


# 全局快捷方式
info_bar_mgr = InfoBarManager.instance()


def show_info(msg: str, duration: int = 5000):
    info_bar_mgr.show(msg, "info", duration)


def show_success(msg: str, duration: int = 4000):
    info_bar_mgr.show(msg, "success", duration)


def show_warning(msg: str, duration: int = 5000):
    info_bar_mgr.show(msg, "warning", duration)


def show_error(msg: str, duration: int = 7000):
    info_bar_mgr.show(msg, "error", duration)
