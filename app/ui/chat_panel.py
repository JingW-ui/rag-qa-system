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
        self._kb_tags_container.setStyleSheet("background-color: #fafafa; border-bottom: 1px solid #e8e8e8;")
        self._kb_tags_layout = QHBoxLayout(self._kb_tags_container)
        self._kb_tags_layout.setContentsMargins(10, 6, 10, 6)
        self._kb_tags_layout.setSpacing(6)
        self._kb_tags_hint = QLabel('<span style="color:#999;">未关联知识库 — 请在左侧知识库上右键「添加到对话」</span>')
        self._kb_tags_hint.setFont(QFont("Microsoft YaHei", 9))
        self._kb_tags_layout.addWidget(self._kb_tags_hint)
        self._kb_tags_layout.addStretch()
        layout.addWidget(self._kb_tags_container)

        # ---- 消息滚动区 ----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background-color: #f5f5f5; }")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._msg_container = QWidget()
        self._msg_container.setObjectName("msgContainer")
        self._msg_container.setStyleSheet("#msgContainer { background-color: #f5f5f5; }")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(8, 12, 8, 12)
        self._msg_layout.setSpacing(6)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_container)
        layout.addWidget(self._scroll, 1)

        # ---- 输入区 ----
        input_wrapper = QWidget()
        input_wrapper.setStyleSheet("QWidget { background-color: #ffffff; border-top: 1px solid #e0e0e0; }")
        input_layout = QHBoxLayout(input_wrapper)
        input_layout.setContentsMargins(12, 10, 12, 10)

        self._input = QTextEdit()
        self._input.setPlaceholderText("输入问题，Ctrl+Enter 发送...")
        self._input.setMaximumHeight(120)
        self._input.setMinimumHeight(44)
        self._input.setFont(QFont("Microsoft YaHei", 10))
        self._input.setStyleSheet("""
            QTextEdit { border: 1px solid #d0d0d0; border-radius: 8px; padding: 8px 12px; background-color: #fafafa; }
            QTextEdit:focus { border-color: #4a90d9; background-color: #ffffff; }
        """)
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input)

        self._send_btn = QPushButton("发 送")
        self._send_btn.clicked.connect(self._send)
        self._send_btn.setMinimumWidth(72)
        self._send_btn.setMinimumHeight(44)
        self._send_btn.setStyleSheet("""
            QPushButton { background-color: #4a90d9; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; padding: 0px 16px; }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:disabled { background-color: #c0c0c0; }
        """)
        input_layout.addWidget(self._send_btn)

        layout.addWidget(input_wrapper)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._flush_render)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() & Qt.ControlModifier:
                self._send()
                return True
        return super().eventFilter(obj, event)

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
                tag.setFont(QFont("Microsoft YaHei", 9))
                tag.setStyleSheet("""
                    QLabel {
                        background-color: #e8f4fd; color: #2a7ab5;
                        border: 1px solid #b8d8f0; border-radius: 10px;
                        padding: 3px 10px;
                    }
                """)
                self._kb_tags_layout.addWidget(tag)
            self._kb_tags_layout.addStretch()
            self._kb_tags_hint.setVisible(False)
        else:
            self._kb_tags_hint = QLabel('<span style="color:#999;">未关联知识库 — 请在左侧知识库上右键「添加到对话」</span>')
            self._kb_tags_hint.setFont(QFont("Microsoft YaHei", 9))
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
        bubble = MessageBubble(text, is_user)
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
