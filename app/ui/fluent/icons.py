# -*- coding: utf-8 -*-
"""
IconManager — SVG 图标系统
==========================
参考 Fluent Design 的图标分层架构，自研实现。
- SVG 文件目录：app/ui/fluent/svg/
- 图标 fill 使用 "currentColor" 关键字，在加载时替换为目标色
- 支持从 Fluent UI System Icons (MIT) 获取矢量图标
"""

import os
import xml.etree.ElementTree as ET

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtSvg import QSvgRenderer


class FluentIcon:
    """Fluent 图标枚举 — 定义 RAG_H 所需的图标名称"""

    # 导航
    KB = "library"           # 知识库
    CHAT = "chat"            # 对话
    SETTINGS = "settings"    # 设置

    # 操作
    ADD = "add"              # 添加
    DELETE = "delete"        # 删除
    UPLOAD = "upload"        # 上传
    SEND = "send"            # 发送
    SEARCH = "search"        # 搜索
    CLOSE = "close"          # 关闭

    # 状态
    CHECK = "check"          # 成功
    WARNING = "warning"      # 警告
    ERROR = "error"          # 错误
    INFO = "info"            # 信息

    # 通用
    FOLDER = "folder"        # 文件夹
    FILE = "file"            # 文件
    DARK_MODE = "dark_mode"  # 深色模式
    LIGHT_MODE = "light_mode"  # 浅色模式


class IconManager:
    """SVG 图标管理器（单例）"""

    _instance = None

    def __init__(self):
        self._svg_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "svg"
        )
        self._svg_cache: dict[str, str] = {}  # name -> raw svg text

    @classmethod
    def instance(cls) -> "IconManager":
        if cls._instance is None:
            cls._instance = IconManager()
        return cls._instance

    # ── SVG 加载 ──────────────────────────────────────────────────────

    def load_svg(self, name: str) -> str | None:
        """加载 SVG 原始文本"""
        if name in self._svg_cache:
            return self._svg_cache[name]

        fp = os.path.join(self._svg_dir, f"{name}.svg")
        if not os.path.exists(fp):
            # 尝试返回空图标
            return None

        with open(fp, encoding="utf-8") as f:
            text = f.read()
        self._svg_cache[name] = text
        return text

    # ── 获取 QIcon ────────────────────────────────────────────────────

    def get_icon(self, name: str, color: str | None = None) -> QIcon:
        """获取指定颜色的图标

        Parameters
        ----------
        name: str
            图标名称（对应 svg/{name}.svg）
        color: str | None
            颜色值，如 "#0078d4"。None 表示使用 currentColor
        """
        svg_text = self.load_svg(name)
        if svg_text is None:
            return QIcon()

        # 替换颜色
        if color:
            svg_text = svg_text.replace("currentColor", color)

        # 从 SVG 文本生成 QIcon
        pixmap = QPixmap()
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        pixmap = QPixmap(24, 24)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    def get_icon_for_theme(self, name: str, is_dark: bool = False) -> QIcon:
        """根据主题获取合适的图标颜色"""
        color = "#e0e0e0" if is_dark else "#333333"
        return self.get_icon(name, color)

    # ── 快捷方式 ──────────────────────────────────────────────────────

    def available_icons(self) -> list[str]:
        """列出所有可用的图标名称"""
        if not os.path.isdir(self._svg_dir):
            return []
        return sorted(
            f.replace(".svg", "")
            for f in os.listdir(self._svg_dir)
            if f.endswith(".svg")
        )


# ── 全局快捷方式 ─────────────────────────────────────────────────────

icon_manager = IconManager.instance()


def get_icon(name: str, color: str | None = None) -> QIcon:
    return icon_manager.get_icon(name, color)


def get_icon_for_theme(name: str, is_dark: bool = False) -> QIcon:
    return icon_manager.get_icon_for_theme(name, is_dark)
