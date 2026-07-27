# -*- coding: utf-8 -*-
"""
聊天气泡组件 — 支持 Markdown 渲染，用户/助手两种样式。
"""

from PySide6.QtWidgets import QLabel, QFrame, QHBoxLayout, QVBoxLayout, QWidget, QScrollArea
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.utils.markdown_renderer import markdown_to_html


class MessageBubble(QFrame):
    """单条聊天气泡，支持 Markdown 渲染 + 流式追加。"""

    def __init__(self, text: str = "", is_user: bool = False, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        self._raw_text = text
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.setObjectName("bubble")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)

        # 气泡内容容器
        self._content = QWidget()
        self._content.setObjectName("bubbleContent")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(0)

        # Markdown 文本标签
        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.RichText)
        self._label.setOpenExternalLinks(True)
        self._label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )
        self._label.setFont(QFont("Microsoft YaHei", 10))
        content_layout.addWidget(self._label)

        # 应用气泡样式
        if self._is_user:
            outer.addStretch()
            outer.addWidget(self._content)
            self._content.setStyleSheet("""
                #bubbleContent {
                    background-color: #d6eaf8;
                    border: 1px solid #aed6f1;
                    border-radius: 14px;
                }
            """)
            # 用户消息：简单 Markdown（通常不需要代码块）
            self._label.setStyleSheet(_LABEL_STYLE)
            self._render(markdown_to_html(self._raw_text, is_user=True))
        else:
            outer.addWidget(self._content)
            outer.addStretch()
            self._content.setStyleSheet("""
                #bubbleContent {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 14px;
                }
            """)
            self._label.setStyleSheet(_LABEL_STYLE)
            self._render(markdown_to_html(self._raw_text, is_user=False))

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

    def sizeHint(self):
        # 根据内容自适应高度
        s = super().sizeHint()
        return s


# QLabel 内联样式（代码块背景色等由全局 CSS 控制）
_LABEL_STYLE = """
    QLabel {
        padding: 0px;
        background: transparent;
        color: #222;
    }
"""
