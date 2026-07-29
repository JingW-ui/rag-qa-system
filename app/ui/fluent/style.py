# -*- coding: utf-8 -*-
"""
ThemeManager — 主题管理系统
===========================
职责：深色/浅色主题切换、QSS 文件加载、主题变化通知。
参考 Fluent Design 的设计模式，自研实现。
"""

import os
import enum
from typing import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget, QApplication

# ── 主题枚举 ──────────────────────────────────────────────────────────

class Theme(enum.Enum):
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


# ── 颜色定义（集中管理，方便调色）────────────────────────────────────

class FluentColors:
    """Fluent Design 调色板 — 自研定义，非直接复刻"""
    # 主色
    PRIMARY = "#0078d4"
    PRIMARY_HOVER = "#106ebe"
    PRIMARY_PRESSED = "#005a9e"

    # 文字
    TEXT_PRIMARY = "#1a1a1a"       # 浅色主文字
    TEXT_SECONDARY = "#666666"     # 浅色副文字
    TEXT_DARK_PRIMARY = "#e0e0e0"  # 深色主文字
    TEXT_DARK_SECONDARY = "#999999"

    # 背景
    BG_WINDOW = "#f3f3f3"          # 浅色窗口背景
    BG_CARD = "#ffffff"            # 浅色卡片背景
    BG_NAV = "#fafafa"             # 浅色导航背景
    BG_INPUT = "#ffffff"

    BG_DARK_WINDOW = "#1e1e1e"     # 深色窗口背景
    BG_DARK_CARD = "#2d2d2d"
    BG_DARK_NAV = "#252525"
    BG_DARK_INPUT = "#333333"

    # 边框
    BORDER = "#e0e0e0"
    BORDER_HOVER = "#c0c0c0"
    BORDER_DARK = "#404040"
    BORDER_DARK_HOVER = "#555555"

    # 特殊
    SUCCESS = "#107c10"
    WARNING = "#d68000"
    ERROR = "#d13438"
    INFO = "#0078d4"

    # 高亮
    HIGHLIGHT_BG = "rgba(0, 120, 212, 0.08)"  # 选中项背景


# ── 主题管理器 ────────────────────────────────────────────────────────

class ThemeManager(QObject):
    """全局主题管理器（单例）"""

    themeChanged = Signal(str)  # "light" | "dark"

    _instance = None

    def __init__(self):
        super().__init__()
        self._theme: Theme = Theme.LIGHT
        self._qss_cache: dict[str, str] = {}  # (theme, name) -> qss text
        self._fluent_dir = os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    # ── 主题设置 ──────────────────────────────────────────────────────

    def set_theme(self, theme: Theme) -> None:
        """设置主题并触发更新"""
        if theme == Theme.AUTO:
            theme = self._detect_system_theme()
        if self._theme != theme:
            self._theme = theme
            self._qss_cache.clear()
            self.themeChanged.emit(theme.value)

    def toggle(self) -> None:
        """切换深色/浅色"""
        new = Theme.DARK if self._theme == Theme.LIGHT else Theme.LIGHT
        self.set_theme(new)

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def is_dark(self) -> bool:
        return self._theme == Theme.DARK

    # ── QSS 加载 ──────────────────────────────────────────────────────

    def qss_path(self, name: str) -> str:
        """返回 QSS 文件路径，如 'card' → '.../qss/light/card.qss'"""
        return os.path.join(
            self._fluent_dir, "qss", self._theme.value, f"{name}.qss"
        )

    def load_qss(self, name: str) -> str:
        """加载指定组件的 QSS，带缓存"""
        key = (self._theme.value, name)
        if key in self._qss_cache:
            return self._qss_cache[key]

        fp = self.qss_path(name)
        if not os.path.exists(fp):
            self._qss_cache[key] = ""
            return ""

        with open(fp, encoding="utf-8") as f:
            text = f.read()
        self._qss_cache[key] = text
        return text

    def apply_qss(self, widget: QWidget, name: str) -> None:
        """对 widget 应用指定组件的 QSS"""
        qss = self.load_qss(name)
        if qss:
            widget.setStyleSheet(qss)

    def clear_cache(self) -> None:
        self._qss_cache.clear()

    # ── 系统主题检测 ──────────────────────────────────────────────────

    @staticmethod
    def _detect_system_theme() -> Theme:
        """尝试用 darkdetect 检测系统主题，失败返回 LIGHT"""
        try:
            import darkdetect
            raw = darkdetect.theme()
            return Theme.DARK if raw and raw.lower() == "dark" else Theme.LIGHT
        except Exception:
            return Theme.LIGHT


# ── 全局快捷方式 ─────────────────────────────────────────────────────

theme_manager = ThemeManager.instance()


def set_theme(theme: Theme) -> None:
    theme_manager.set_theme(theme)


def toggle_theme() -> None:
    theme_manager.toggle()


def is_dark_theme() -> bool:
    return theme_manager.is_dark


def apply_qss(widget: QWidget, name: str) -> None:
    theme_manager.apply_qss(widget, name)
