# -*- coding: utf-8 -*-
"""
引用来源折叠区 — 展示检索到的分块卡片列表，支持展开/折叠。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.theme import FONT_FAMILY, FONT_SIZE_SM, source_btn_style
from app.ui.widgets.chunk_card import ChunkCard


class SourcesSection(QWidget):
    """引用来源折叠区 — 点击按钮展开/折叠分块卡片列表。"""

    def __init__(self, contexts: list[dict] = None, parent=None):
        super().__init__(parent)
        self._contexts = contexts or []
        self._expanded = False
        self._cards: list[ChunkCard] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        # ---- 折叠按钮 ----
        n = len(self._contexts)
        self._toggle_btn = QPushButton(f"📎 {n} 个引用来源 ▸")
        self._toggle_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet(source_btn_style())
        self._toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self._toggle_btn)

        # ---- 卡片容器 ----
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(6)
        self._cards_container.setVisible(False)
        layout.addWidget(self._cards_container)

        # 预填充卡片
        self._populate_cards()

    def _populate_cards(self) -> None:
        """创建分块卡片。"""
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        for i, ctx in enumerate(self._contexts, 1):
            card = ChunkCard(ctx, index=i, parent=self._cards_container)
            self._cards_layout.addWidget(card)
            self._cards.append(card)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._cards_container.setVisible(self._expanded)
        n = len(self._contexts)
        arrow = "▾" if self._expanded else "▸"
        self._toggle_btn.setText(f"📎 {n} 个引用来源 {arrow}")

    def set_contexts(self, contexts: list[dict]) -> None:
        """更新引用来源数据。"""
        self._contexts = contexts
        n = len(contexts)
        arrow = "▾" if self._expanded else "▸"
        self._toggle_btn.setText(f"📎 {n} 个引用来源 {arrow}")
        self._populate_cards()
