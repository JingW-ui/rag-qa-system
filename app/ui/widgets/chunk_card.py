# -*- coding: utf-8 -*-
"""
分块卡片组件 — 展示单个检索到的文本分块（文件名、相似度、可展开原文）。
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.theme import (
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_NORMAL,
    SOURCE_SCORE_COLOR, SOURCE_PREVIEW_COLOR, source_card_style,
)


PREVIEW_MAX_CHARS = 100


class ChunkCard(QFrame):
    """单个分块卡片 — 点击切换展开/折叠。"""

    def __init__(self, context: dict, index: int = 0, parent=None):
        super().__init__(parent)
        self._context = context
        self._index = index
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(source_card_style())
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(4)

        # ---- 头部：序号 + 文件名 + 相似度 ----
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        filename = self._context.get("metadata", {}).get("filename", "未知文档")
        # 优先显示重排分数，否则用 L2 距离转换
        rerank_score = self._context.get("rerank_score")
        if rerank_score is not None:
            score = rerank_score * 100  # 0-1 → 0-100
            score_prefix = "🔥"
        else:
            distance = self._context.get("distance", 0.0)
            score = self._distance_to_score(distance)
            score_prefix = ""

        self._header_label = QLabel(f"[{self._index}] 📄 {filename}")
        self._header_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM, QFont.Bold))
        header.addWidget(self._header_label)

        header.addStretch()

        score_label = QLabel(f"{score_prefix}{score:.0f}%")
        score_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
        score_label.setStyleSheet(f"color: {SOURCE_SCORE_COLOR};")
        header.addWidget(score_label)

        layout.addLayout(header)

        # ---- 文本预览 ----
        full_text = self._context.get("text", "")
        self._full_text = full_text
        preview = full_text[:PREVIEW_MAX_CHARS].replace("\n", " ")
        if len(full_text) > PREVIEW_MAX_CHARS:
            preview += "..."

        self._text_label = QLabel(preview)
        self._text_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
        self._text_label.setStyleSheet(f"color: {SOURCE_PREVIEW_COLOR};")
        self._text_label.setWordWrap(True)
        self._text_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )
        layout.addWidget(self._text_label)

    def mousePressEvent(self, event) -> None:
        """点击切换展开/折叠。"""
        if event.button() == Qt.LeftButton:
            self._toggle_expand()
        super().mousePressEvent(event)

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._text_label.setText(self._full_text)
        else:
            preview = self._full_text[:PREVIEW_MAX_CHARS].replace("\n", " ")
            if len(self._full_text) > PREVIEW_MAX_CHARS:
                preview += "..."
            self._text_label.setText(preview)

    @staticmethod
    def _distance_to_score(distance: float) -> float:
        """将 ChromaDB L2 距离转换为近似百分比（0-100）。

        ChromaDB 默认 L2 距离，值越小越相似。
        使用 sigmoid 映射：score = 100 / (1 + distance)
        """
        if distance < 0:
            distance = 0
        return 100.0 / (1.0 + distance)
