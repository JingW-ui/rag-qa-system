# -*- coding: utf-8 -*-
"""
聊天气泡组件 — 支持 Markdown 渲染，用户/助手两种样式。
- AI 气泡：完全透明，Markdown 直接渲染在画布上，无阴影
- 用户气泡：极简胶囊，浅灰背景，无阴影
"""

from PySide6.QtWidgets import QLabel, QFrame, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QApplication
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.utils.markdown_renderer import markdown_to_html, markdown_to_plain
from app.ui.theme import (
    BUBBLE_MAX_WIDTH,
    BUBBLE_PADDING_H, BUBBLE_PADDING_TOP, BUBBLE_PADDING_BOTTOM,
    AI_BUBBLE_PADDING_H, AI_BUBBLE_PADDING_TOP, AI_BUBBLE_PADDING_BOTTOM,
    MSG_MARGIN_H,
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SM,
    bubble_style,
)
from app.ui.widgets.sources_section import SourcesSection
from app.ui.widgets.image_thumb import ImageThumb
from app.ui.widgets.image_preview_dialog import ImagePreviewDialog
from app.ui.widgets.file_card import FileCard
from app.ui.widgets.simple_menu import SimpleMenu


class MessageBubble(QFrame):
    """单条聊天气泡，支持 Markdown 渲染 + 流式追加。"""

    copy_done = Signal(str)  # 复制完成后发出状态提示

    def __init__(
        self, text: str = "", is_user: bool = False, max_width: int = BUBBLE_MAX_WIDTH,
        images: list[bytes] | None = None, file_names: list[str] | None = None, parent=None,
    ):
        super().__init__(parent)
        self._is_user = is_user
        self._raw_text = text
        self._max_width = max_width
        self._sources_section: SourcesSection | None = None
        self._images = images
        self._file_names = file_names
        self._copy_btn: QPushButton | None = None
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.setObjectName("bubble")
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("#bubble { background: transparent; border: none; padding: 0; margin: 0; }")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(MSG_MARGIN_H, 0, MSG_MARGIN_H, 0)

        # 气泡内容容器
        self._content = QWidget()
        self._content.setObjectName("bubbleContent")
        # AI 气泡占满宽度，用户气泡限制最大宽度
        if self._is_user:
            self._content.setMaximumWidth(self._max_width)
        # 无阴影

        # 根据气泡类型选择内边距
        if self._is_user:
            pad_h = BUBBLE_PADDING_H
            pad_top = BUBBLE_PADDING_TOP
            pad_bottom = BUBBLE_PADDING_BOTTOM
        else:
            pad_h = AI_BUBBLE_PADDING_H
            pad_top = AI_BUBBLE_PADDING_TOP
            pad_bottom = AI_BUBBLE_PADDING_BOTTOM

        content_layout = QVBoxLayout(self._content)
        self._content_layout = content_layout
        content_layout.setContentsMargins(pad_h, pad_top, pad_h, pad_bottom)
        content_layout.setSpacing(8)

        # 用户气泡图片缩略图行
        if self._is_user and self._images:
            thumbs_widget = QWidget()
            thumbs_widget.setStyleSheet("background: transparent; border: none;")
            thumbs_layout = QHBoxLayout(thumbs_widget)
            thumbs_layout.setContentsMargins(0, 0, 0, 0)
            thumbs_layout.setSpacing(6)

            available_width = self._max_width - 2 * pad_h
            if len(self._images) == 1:
                max_img_width = available_width
                max_img_height = available_width * 0.75
            else:
                max_img_width = (available_width - (len(self._images) - 1) * 6) // len(self._images)
                max_img_height = max_img_width

            for img_bytes in self._images:
                thumb = ImageThumb(
                    img_bytes,
                    removable=False,
                    max_width=max_img_width,
                    max_height=max_img_height,
                )
                thumb.clicked.connect(self._on_image_clicked)
                thumbs_layout.addWidget(thumb)
            thumbs_layout.addStretch()
            content_layout.addWidget(thumbs_widget)

        # 用户气泡文件附件行
        if self._is_user and self._file_names:
            files_widget = QWidget()
            files_widget.setStyleSheet("background: transparent; border: none;")
            files_layout = QHBoxLayout(files_widget)
            files_layout.setContentsMargins(0, 0, 0, 0)
            files_layout.setSpacing(6)
            for fname in self._file_names:
                card = FileCard(fname, removable=False)
                files_layout.addWidget(card)
            files_layout.addStretch()
            content_layout.addWidget(files_widget)

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

        # AI 气泡：底部操作栏（引用来源 + 复制按钮）
        if not self._is_user:
            self._action_bar = QWidget()
            self._action_bar.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(self._action_bar)
            action_layout.setContentsMargins(0, 4, 0, 0)
            action_layout.setSpacing(8)

            # 左侧：引用来源占位（后续动态添加）
            self._sources_container = QWidget()
            self._sources_container.setStyleSheet("background: transparent;")
            self._sources_layout = QHBoxLayout(self._sources_container)
            self._sources_layout.setContentsMargins(0, 0, 0, 0)
            self._sources_layout.setSpacing(0)
            action_layout.addWidget(self._sources_container)

            # 右侧：复制按钮（初始隐藏）
            self._copy_btn = QPushButton("📋 复制 ▾")
            self._copy_btn.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
            self._copy_btn.setCursor(Qt.PointingHandCursor)
            self._copy_btn.setVisible(False)  # 生成时隐藏
            self._copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #999999;
                    border: none;
                    padding: 2px 4px;
                }
                QPushButton:hover {
                    color: #555555;
                }
            """)
            self._copy_btn.clicked.connect(self._on_copy_clicked)
            action_layout.addWidget(self._copy_btn)

            # 弹性占位，把引用和复制按钮挤到左边紧挨着
            action_layout.addStretch()

            content_layout.addWidget(self._action_bar)

        # 对齐方向
        if self._is_user:
            outer.addStretch()
            outer.addWidget(self._content)
        else:
            # AI 气泡占满宽度，不加 stretch
            outer.addWidget(self._content)

        # 应用气泡样式（根据 is_user）
        self._content.setStyleSheet(bubble_style(self._is_user))
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

    def set_sources(self, contexts: list[dict]) -> None:
        """AI 回答完成后，附加引用来源卡片（仅 AI 气泡）。"""
        if self._is_user or not contexts:
            return
        if not hasattr(self, '_sources_layout'):
            return
        if self._sources_section is None:
            self._sources_section = SourcesSection(contexts, parent=self._sources_container)
            self._sources_layout.addWidget(self._sources_section)
        else:
            self._sources_section.set_contexts(contexts)
        # 显示复制按钮
        if hasattr(self, '_copy_btn') and self._copy_btn:
            self._copy_btn.setVisible(True)

    def show_copy_button(self) -> None:
        """显示复制按钮（用于没有引用来源的情况）。"""
        if not self._is_user and hasattr(self, '_copy_btn') and self._copy_btn:
            self._copy_btn.setVisible(True)

    def _on_image_clicked(self, image_bytes: bytes) -> None:
        """点击图片时弹出大图预览。"""
        dialog = ImagePreviewDialog(image_bytes, self)
        dialog.exec()

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _render(self, html: str) -> None:
        """更新 QLabel 中的 HTML 内容。"""
        self._label.setText(html)

    def _on_copy_clicked(self) -> None:
        """点击复制按钮，弹出下拉菜单。"""
        menu = SimpleMenu(self._copy_btn)
        menu.addAction("📋 复制文本").triggered.connect(self._copy_plain)
        menu.addAction("</> 复制为 Markdown").triggered.connect(self._copy_markdown)
        # 在按钮下方弹出菜单
        pos = self._copy_btn.mapToGlobal(self._copy_btn.rect().bottomLeft())
        menu.exec(pos)

    def _copy_plain(self) -> None:
        """复制纯文本到剪贴板。"""
        text = markdown_to_plain(self._raw_text)
        QApplication.clipboard().setText(text)
        self.copy_done.emit("已复制文本到剪贴板")

    def _copy_markdown(self) -> None:
        """复制 Markdown 原文到剪贴板。"""
        QApplication.clipboard().setText(self._raw_text)
        self.copy_done.emit("已复制 Markdown 到剪贴板")
