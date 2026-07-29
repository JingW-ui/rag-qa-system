# -*- coding: utf-8 -*-
"""
Fluent Design 卡片体系 — 自研实现
==================================
参考模式：
- CardWidget: 圆角卡片容器，带阴影，可放置任意内容
- SettingCard: Icon + 标题 + 副标题 + 右侧控件的设置行
- SettingCardGroup: 分组管理多个 SettingCard
"""

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from ..style import apply_qss, theme_manager, is_dark_theme


# 统一的阴影参数
_SHADOW_BLUR = 12
_SHADOW_OFFSET = (0, 2)
_SHADOW_COLOR_LIGHT = QColor(0, 0, 0, 20)
_SHADOW_COLOR_DARK = QColor(0, 0, 0, 40)


def _apply_card_shadow(widget: QWidget) -> None:
    """给卡片添加统一投影"""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(_SHADOW_BLUR)
    shadow.setOffset(*_SHADOW_OFFSET)
    shadow.setColor(
        _SHADOW_COLOR_DARK if theme_manager.is_dark else _SHADOW_COLOR_LIGHT
    )
    widget.setGraphicsEffect(shadow)


class CardWidget(QFrame):
    """圆角卡片容器 — 白色背景 + 圆角 + 投影"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardWidget")
        self._setup_ui()

    def _setup_ui(self):
        self.setContentsMargins(0, 0, 0, 0)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(8)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def showEvent(self, event):
        super().showEvent(event)
        apply_qss(self, "card")
        _apply_card_shadow(self)


class ElevatedCardWidget(CardWidget):
    """带更明显投影的卡片，用于强调"""

    def __init__(self, parent=None):
        super().__init__(parent)


class SettingCard(QFrame):
    """设置项卡片 — 左侧 icon + 标题 + 副标题，右侧放置交互控件

    使用方式:
        card = SettingCard(icon, "标题", "副标题")
        card.add_widget(QComboBox())
    """

    def __init__(self, icon_text: str, title: str, description: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("SettingCard")
        self._setup_ui(icon_text, title, description)

    def _setup_ui(self, icon_text: str, title: str, description: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 图标
        self._icon_label = QLabel(icon_text)
        self._icon_label.setFixedSize(24, 24)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFont(QFont("Segoe UI Emoji", 14))
        layout.addWidget(self._icon_label)

        # 文字区
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self._title_label = QLabel(title)
        self._title_label.setObjectName("cardTitle")
        text_layout.addWidget(self._title_label)

        if description:
            self._desc_label = QLabel(description)
            self._desc_label.setObjectName("cardDescription")
            text_layout.addWidget(self._desc_label)

        layout.addLayout(text_layout, 1)

        # 右侧控件区
        self._widget_layout = QHBoxLayout()
        self._widget_layout.setSpacing(8)
        layout.addLayout(self._widget_layout)

    def add_widget(self, widget: QWidget) -> None:
        """将交互控件添加到卡片右侧"""
        self._widget_layout.addWidget(widget)

    def showEvent(self, event):
        super().showEvent(event)
        apply_qss(self, "card")
        # 主题变化时刷新
        try:
            theme_manager.themeChanged.disconnect(self._on_theme_changed_card)
        except TypeError:
            pass
        theme_manager.themeChanged.connect(self._on_theme_changed_card)

    def _on_theme_changed_card(self, _v=None):
        """主题变化时重新应用 QSS"""
        apply_qss(self, "card")


class SettingCardGroup(QWidget):
    """设置卡片分组 — 带组标题"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingCardGroup")
        self._title = title
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # 分组标题
        if self._title:
            title_label = QLabel(self._title)
            title_label.setObjectName("groupTitle")
            title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
            title_label.setStyleSheet(
                "color: #4da3e0; padding: 8px 16px 4px 16px; background: transparent;"
                if is_dark_theme()
                else "color: #0078d4; padding: 8px 16px 4px 16px; background: transparent;"
            )
            layout.addWidget(title_label)

        self._card_layout = QVBoxLayout()
        self._card_layout.setContentsMargins(16, 4, 16, 8)
        self._card_layout.setSpacing(1)
        layout.addLayout(self._card_layout)

    def add_card(self, card: SettingCard) -> None:
        """添加设置卡片"""
        self._card_layout.addWidget(card)

    def add_widget(self, widget: QWidget) -> None:
        """直接添加 widget 到分组"""
        self._card_layout.addWidget(widget)
