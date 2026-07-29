# -*- coding: utf-8 -*-
"""
对话面板 — Markdown 消息列表 + 输入区，支持流式输出 + 多知识库关联。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QScrollArea, QLabel, QFrame,
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QFont

from app.core.rag_pipeline import RAGPipeline
from app.ui.widgets.message_bubble import MessageBubble
from app.ui.workers.query_worker import QueryWorker
from app.ui.theme import (
    CHAT_BG, MSG_SPACING, MSG_MARGIN_H, MSG_MARGIN_V,
    INPUT_BG, INPUT_BORDER, INPUT_BORDER_FOCUS, INPUT_RADIUS,
    SEND_BTN_BG, SEND_BTN_BG_HOVER, SEND_BTN_BG_DISABLED, SEND_BTN_COLOR, SEND_BTN_SIZE,
    TAG_BAR_BG, TAG_BAR_BORDER, FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_NORMAL,
    BUBBLE_MAX_WIDTH, tag_style,
)


class ChatPanel(QWidget):
    """对话问答面板 — 支持 Markdown 渲染 + 流式输出 + 多知识库检索。"""

    status_message = Signal(str)

    def __init__(self, rag: RAGPipeline, top_k: int = 5, parent=None):
        super().__init__(parent)
        self._rag = rag
        self._top_k = top_k
        self._query_worker: QueryWorker | None = None
        self._current_ai_bubble: MessageBubble | None = None
        self._active_collections: list[str] = []
        self._stream_buffer: str = ""
        self._render_timer: QTimer | None = None
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 已关联知识库标签栏 ----
        self._kb_tags_container = QWidget()
        self._kb_tags_container.setStyleSheet(
            f"background-color: {TAG_BAR_BG}; border-bottom: 1px solid {TAG_BAR_BORDER};"
        )
        self._kb_tags_layout = QHBoxLayout(self._kb_tags_container)
        self._kb_tags_layout.setContentsMargins(10, 6, 10, 6)
        self._kb_tags_layout.setSpacing(6)
        self._kb_tags_hint = QLabel('<span style="color:#999;">未关联知识库 — 请在左侧知识库上右键「添加到对话」</span>')
        self._kb_tags_hint.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
        self._kb_tags_layout.addWidget(self._kb_tags_hint)
        self._kb_tags_layout.addStretch()
        layout.addWidget(self._kb_tags_container)

        # ---- 消息滚动区 ----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {CHAT_BG}; }}"
        )
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._msg_container = QWidget()
        self._msg_container.setObjectName("msgContainer")
        self._msg_container.setStyleSheet(f"#msgContainer {{ background-color: {CHAT_BG}; }}")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(MSG_MARGIN_H, MSG_MARGIN_V, MSG_MARGIN_H, MSG_MARGIN_V)
        self._msg_layout.setSpacing(MSG_SPACING)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_container)
        layout.addWidget(self._scroll, 1)

        # ---- 输入区（按钮内嵌右下角） ----
        self._input_wrapper = QWidget()
        self._input_wrapper.setObjectName("inputWrapper")
        self._input_wrapper.setStyleSheet(f"""
            #inputWrapper {{
                background-color: {INPUT_BG};
                border: 1px solid {INPUT_BORDER};
                border-radius: {INPUT_RADIUS}px;
            }}
            #inputWrapper:focus-within {{
                border-color: {INPUT_BORDER_FOCUS};
            }}
        """)
        wrapper_layout = QVBoxLayout(self._input_wrapper)
        wrapper_layout.setContentsMargins(4, 4, 4, 4)
        wrapper_layout.setSpacing(0)

        self._input = QTextEdit()
        self._input.setPlaceholderText("输入问题，Enter 发送，Shift+Enter 换行...")
        self._input.setMaximumHeight(120)
        self._input.setMinimumHeight(60)
        self._input.setFont(QFont(FONT_FAMILY, FONT_SIZE_NORMAL))
        self._input.setAcceptRichText(False)  # 纯文本，不支持 Markdown
        self._input.setStyleSheet("""
            QTextEdit {
                border: none;
                background: transparent;
                padding: 4px 40px 4px 8px;
            }
        """)
        self._input.installEventFilter(self)
        wrapper_layout.addWidget(self._input)

        # 发送按钮 — 绝对定位在右下角
        self._send_btn = QPushButton("➤")
        self._send_btn.setFixedSize(SEND_BTN_SIZE, SEND_BTN_SIZE)
        self._send_btn.setToolTip("发送 (Enter)")
        self._send_btn.clicked.connect(self._send)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SEND_BTN_BG};
                color: {SEND_BTN_COLOR};
                border: none;
                border-radius: {SEND_BTN_SIZE // 2}px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {SEND_BTN_BG_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {SEND_BTN_BG_DISABLED};
            }}
        """)
        self._send_btn.setParent(self._input_wrapper)
        self._send_btn.move(0, 0)  # 位置由 resizeEvent 控制

        outer_input_layout = QHBoxLayout()
        outer_input_layout.setContentsMargins(12, 10, 12, 10)
        outer_input_layout.addWidget(self._input_wrapper)
        layout.addLayout(outer_input_layout)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._flush_render)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._input and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()
            # Enter 发送，Shift+Enter 换行
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                if mods & Qt.ShiftModifier:
                    return False  # 允许换行
                else:
                    self._send()
                    return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        """窗口大小变化时重定位发送按钮到输入框右下角。"""
        super().resizeEvent(event)
        self._position_send_btn()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._position_send_btn()

    def _position_send_btn(self) -> None:
        """把发送按钮放在输入框右下角。"""
        if hasattr(self, '_send_btn') and hasattr(self, '_input_wrapper'):
            w = self._input_wrapper.width()
            h = self._input_wrapper.height()
            btn_w = self._send_btn.width()
            btn_h = self._send_btn.height()
            margin = 8
            self._send_btn.move(w - btn_w - margin, h - btn_h - margin)

    # ------------------------------------------------------------------ #
    #  Public — 多 KB 管理
    # ------------------------------------------------------------------ #

    def set_collections(self, collections: list[str], kb_names: list[str]) -> None:
        """设置活跃知识库列表。"""
        self._active_collections = collections
        # 更新标签栏
        _clear_layout(self._kb_tags_layout)
        if kb_names:
            for name in kb_names:
                tag = QLabel(f"📚 {name}")
                tag.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
                tag.setStyleSheet(tag_style())
                self._kb_tags_layout.addWidget(tag)
            self._kb_tags_layout.addStretch()
            self._kb_tags_hint.setVisible(False)
        else:
            self._kb_tags_hint = QLabel('<span style="color:#999;">未关联知识库 — 请在左侧知识库上右键「添加到对话」</span>')
            self._kb_tags_hint.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
            self._kb_tags_layout.addWidget(self._kb_tags_hint)
            self._kb_tags_layout.addStretch()

    def set_collection(self, collection_name: str) -> None:
        """向后兼容单库模式。"""
        self.set_collections([collection_name] if collection_name else [], [""])

    # ------------------------------------------------------------------ #
    #  Send
    # ------------------------------------------------------------------ #

    def _send(self) -> None:
        question = self._input.toPlainText().strip()
        if not question:
            return
        if not self._active_collections:
            self.status_message.emit("请先将知识库添加到对话（右键知识库 → 添加到对话）")
            return

        self._add_bubble(question, is_user=True)
        self._input.clear()

        self._stream_buffer = ""
        self._current_ai_bubble = self._add_bubble("💭 _正在思考..._", is_user=False)
        self._send_btn.setEnabled(False)
        self._input.setEnabled(False)
        self.status_message.emit("查询中...")

        self._query_worker = QueryWorker(
            collections=self._active_collections,
            question=question,
            rag=self._rag,
            top_k=self._top_k,
            stream=True,
        )
        self._query_worker.token_generated.connect(self._on_token)
        self._query_worker.finished.connect(self._on_query_finished)
        self._query_worker.error.connect(self._on_query_error)
        self._query_worker.context_retrieved.connect(self._on_context_retrieved)
        self._query_worker.start()

    # ------------------------------------------------------------------ #
    #  Callbacks
    # ------------------------------------------------------------------ #

    def _on_token(self, token: str) -> None:
        self._stream_buffer += token
        if not self._render_timer.isActive():
            self._render_timer.start(60)

    def _flush_render(self) -> None:
        if self._current_ai_bubble is not None and self._stream_buffer:
            self._current_ai_bubble.set_text(self._stream_buffer)
            self._scroll_to_bottom()

    def _on_context_retrieved(self, contexts: list) -> None:
        if contexts:
            sources = sorted(set(
                ctx.get("metadata", {}).get("filename", "")
                for ctx in contexts if ctx.get("metadata", {}).get("filename")
            ))
            if sources:
                self.status_message.emit(f"检索到 {len(contexts)} 个片段: {', '.join(sources[:4])}")

    def _on_query_finished(self, success: bool, _msg: str) -> None:
        self._flush_render()
        self._send_btn.setEnabled(True)
        self._input.setEnabled(True)
        self._current_ai_bubble = None
        self._stream_buffer = ""
        if success:
            self.status_message.emit("就绪")
        self._input.setFocus()

    def _on_query_error(self, error_msg: str) -> None:
        self._current_ai_bubble = None
        self._stream_buffer = ""
        self._add_bubble(f"❌ {error_msg}", is_user=False)
        self._send_btn.setEnabled(True)
        self._input.setEnabled(True)
        self.status_message.emit(f"错误: {error_msg}")
        self._input.setFocus()

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _add_bubble(self, text: str, is_user: bool) -> MessageBubble:
        bubble = MessageBubble(text, is_user, max_width=BUBBLE_MAX_WIDTH)
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)
        return bubble

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear(self) -> None:
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


def _clear_layout(layout) -> None:
    """清空 layout 中所有子 widget。"""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
