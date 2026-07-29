# -*- coding: utf-8 -*-
"""
聊天气泡组件 — 支持 Markdown 渲染，用户/助手两种样式。
"""

from PySide6.QtWidgets import QLabel, QFrame, QHBoxLayout, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.utils.markdown_renderer import markdown_to_html
from app.ui.theme import (
    USER_BUBBLE_BG, AI_BUBBLE_BG,
    BUBBLE_MAX_WIDTH, BUBBLE_PADDING_H, BUBBLE_PADDING_TOP, BUBBLE_PADDING_BOTTOM,
    MSG_MARGIN_H,
    FONT_FAMILY, FONT_SIZE_NORMAL,
    SHADOW_RADIUS, SHADOW_OFFSET,
    bubble_style,
)


def _make_shadow(parent: QWidget) -> QGraphicsDropShadowEffect:
    """创建统一的阴影效果。"""
    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(SHADOW_RADIUS)
    shadow.setOffset(*SHADOW_OFFSET)
    shadow.setColor(QColor(0, 0, 0, 30))
    return shadow


class MessageBubble(QFrame):
    """单条聊天气泡，支持 Markdown 渲染 + 流式追加。"""

    def __init__(self, text: str = "", is_user: bool = False, max_width: int = BUBBLE_MAX_WIDTH, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        self._raw_text = text
        self._max_width = max_width
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.setObjectName("bubble")
        # 消除 QFrame 默认 frame 间距
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("#bubble { background: transparent; border: none; padding: 0; margin: 0; }")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(MSG_MARGIN_H, 0, MSG_MARGIN_H, 0)

        # 气泡内容容器
        self._content = QWidget()
        self._content.setObjectName("bubbleContent")
        self._content.setMaximumWidth(self._max_width)
        self._content.setGraphicsEffect(_make_shadow(self._content))

        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(
            BUBBLE_PADDING_H, BUBBLE_PADDING_TOP,
            BUBBLE_PADDING_H, BUBBLE_PADDING_BOTTOM
        )
        content_layout.setSpacing(0)

        # Markdown 文本标签
        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.RichText)
        self._label.setOpenExternalLinks(True)
        self._label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )
        self._label.setFont(QFont(FONT_FAMILY, FONT_SIZE_NORMAL))
        self._label.setStyleSheet("""
            QLabel {
                padding: 0px;
                background: transparent;
                color: #222;
            }
        """)
        content_layout.addWidget(self._label)

        # 对齐方向 + 气泡样式
        bg_color = USER_BUBBLE_BG if self._is_user else AI_BUBBLE_BG
        if self._is_user:
            outer.addStretch()
            outer.addWidget(self._content)
        else:
            outer.addWidget(self._content)
            outer.addStretch()

        self._content.setStyleSheet(bubble_style(bg_color))
        self._render(markdown_to_html(self._raw_text, is_user=self._is_user))

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def set_text(self, text: str) -> None:
        """设置完整文本（非流式）。"""
        self._raw_text = text
        self._render(markdown_to_html(text, is_user=self._is_user))

    def append_text(self, delta: str) -> None:
        """流式追加 token，重新渲染 Markdown。"""
        self._raw_text += delta
        self._render(markdown_to_html(self._raw_text, is_user=self._is_user))

    @property
    def raw_text(self) -> str:
        return self._raw_text

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _render(self, html: str) -> None:
        """更新 QLabel 中的 HTML 内容。"""
        self._label.setText(html)
