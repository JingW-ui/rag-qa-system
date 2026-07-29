# -*- coding: utf-8 -*-
"""
知识库管理侧边栏 — CardWidget 卡片列表 + 对话框关联。
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QInputDialog, QMessageBox, QFileDialog, QProgressBar,
    QFrame, QMenu, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from app.ui.fluent import PrimaryButton, ToolButton, is_dark_theme, theme_manager
from app.ui.fluent.widgets.card import CardWidget, _apply_card_shadow

from app.core.kb_manager import KnowledgeBaseManager
from app.core.vector_store import VectorStore
from app.core.embedding_service import EmbeddingService
from app.core.document_processor import DocumentProcessor
from app.ui.widgets.file_list_widget import FileListWidget
from app.ui.workers.ingest_worker import IngestWorker
from app.ui.workers.delete_worker import DeleteWorker


# ── KB 卡片组件 ─────────────────────────────────────────────────────

class KbCard(CardWidget):
    """知识库卡片 — 显示名称、文档数、对话关联状态"""

    clicked = Signal(int)        # kb_id
    context_requested = Signal(int, QMenu)  # kb_id, menu

    def __init__(self, kb_id: int, name: str, doc_count: int = 0,
                 in_chat: bool = False, parent=None):
        super().__init__(parent)
        self._kb_id = kb_id
        self._name = name
        self._doc_count = doc_count
        self._in_chat = in_chat
        self._selected = False

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)
        self._setup_content()

    def _setup_content(self):
        self.content_layout.setContentsMargins(12, 10, 12, 10)
        self.content_layout.setSpacing(4)

        # 第一行：名称 + 对话标记
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        name_label = QLabel(self._name)
        name_label.setObjectName("kbCardName")
        name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("color: inherit; background: transparent;")
        row1.addWidget(name_label)

        if self._in_chat:
            chat_badge = QLabel("💬")
            chat_badge.setFixedSize(20, 20)
            chat_badge.setAlignment(Qt.AlignCenter)
            chat_badge.setStyleSheet("""
                QLabel {
                    background-color: #0078d4;
                    color: white;
                    border-radius: 10px;
                    font-size: 10px;
                }
            """)
            chat_badge.setToolTip("已关联到对话")
            row1.addWidget(chat_badge)

        row1.addStretch()
        self.content_layout.addLayout(row1)

        # 第二行：文档数
        doc_text = f"{self._doc_count} 篇文档" if self._doc_count > 0 else "空知识库"
        doc_label = QLabel(doc_text)
        doc_label.setObjectName("kbCardDocCount")
        doc_label.setFont(QFont("Microsoft YaHei", 9))
        doc_label.setStyleSheet("color: #888888; background: transparent;")
        self.content_layout.addWidget(doc_label)

    def set_selected(self, selected: bool):
        self._selected = selected
        dark = is_dark_theme()
        if selected:
            bg = "#1e3a5a" if dark else "#e5f0fa"
            border = "#0078d4"
            self.setStyleSheet(f"""
                #CardWidget {{
                    background-color: {bg};
                    border: 1.5px solid {border};
                    border-radius: 6px;
                }}
            """)
        else:
            bg = "#2d2d2d" if dark else "#ffffff"
            border = "#404040" if dark else "#e8e8e8"
            hover = "#555555" if dark else "#c0c0c0"
            self.setStyleSheet(f"""
                #CardWidget {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 6px;
                }}
                #CardWidget:hover {{
                    border-color: {hover};
                }}
            """)

    @property
    def kb_id(self) -> int:
        return self._kb_id

    # ── 事件 ──────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._kb_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self._in_chat:
            menu.addAction("🔇 从对话移除")
        else:
            menu.addAction("💬 添加到对话")
        self.context_requested.emit(self._kb_id, menu)
        menu.exec(event.globalPos())


# ── 主面板 ─────────────────────────────────────────────────────────

class KbPanel(QWidget):
    """知识库管理面板 — 卡片列表 + 多选对话关联。"""

    kb_changed = Signal(int, str)                # kb_id, collection_name
    chat_kbs_changed = Signal(list, list)         # ([collection_names], [kb_names])
    status_message = Signal(str)

    def __init__(
        self,
        kb_mgr: KnowledgeBaseManager,
        vs: VectorStore,
        emb_svc: EmbeddingService,
        proc: DocumentProcessor,
        parent=None,
    ):
        super().__init__(parent)
        self._kb_mgr = kb_mgr
        self._vs = vs
        self._emb_svc = emb_svc
        self._proc = proc
        self._active_kb_id: int | None = None
        self._chat_kb_ids: set[int] = set()
        self._kb_cards: list[KbCard] = []
        self._ingest_worker: IngestWorker | None = None
        self._delete_worker: DeleteWorker | None = None
        self._setup_ui()
        self._refresh_kb_list()

        # 主题变化时刷新卡片状态
        theme_manager.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, _theme_value: str):
        """主题切换后刷新卡片选中样式"""
        for card in self._kb_cards:
            card.set_selected(card.kb_id == self._active_kb_id)

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)

        # ---- 顶部操作 ----
        header = QHBoxLayout()
        header.addWidget(QLabel("<b>📚 知识库</b>"))
        header.addStretch()
        btn_new = PrimaryButton("+ 新建")
        btn_new.clicked.connect(self._create_kb)
        header.addWidget(btn_new)
        btn_del = ToolButton("🗑")
        btn_del.setToolTip("删除选中知识库")
        btn_del.clicked.connect(self._delete_current_kb)
        header.addWidget(btn_del)
        layout.addLayout(header)

        # ---- KB 卡片列表（放在 ScrollArea 中） ----
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._card_container = QWidget()
        self._card_container.setStyleSheet("background: transparent;")
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(2, 4, 2, 4)
        self._card_layout.setSpacing(6)
        self._card_layout.addStretch()

        self._scroll_area.setWidget(self._card_container)
        layout.addWidget(self._scroll_area, 1)

        # ---- 分隔 ----
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("color: #d0d0d0;")
        layout.addWidget(sep)

        # ---- 文档 ----
        doc_header = QHBoxLayout()
        doc_header.addWidget(QLabel("<b>📄 文档</b>"))
        doc_header.addStretch()
        btn_upload = PrimaryButton("上传")
        btn_upload.setToolTip("上传文档到当前知识库")
        btn_upload.clicked.connect(self._upload_document)
        doc_header.addWidget(btn_upload)
        layout.addLayout(doc_header)

        self._file_list = FileListWidget()
        self._file_list.doc_delete_requested.connect(self._delete_document)
        layout.addWidget(self._file_list, 1)

        # ---- 进度 ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

    # ------------------------------------------------------------------ #
    #  KB 列表刷新（卡片区）
    # ------------------------------------------------------------------ #

    def _refresh_kb_list(self, select_kb_id: int | None = None) -> None:
        kbs = self._kb_mgr.list_kbs()
        target_id = select_kb_id if select_kb_id is not None else self._active_kb_id

        # 清除旧卡片
        self._clear_cards()

        # 创建新卡片
        for kb in kbs:
            in_chat = kb["id"] in self._chat_kb_ids
            card = KbCard(
                kb_id=kb["id"],
                name=kb["name"],
                doc_count=kb.get("doc_count", 0),
                in_chat=in_chat,
            )
            card.clicked.connect(self._on_card_clicked)
            card.context_requested.connect(self._on_card_context)
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)
            self._kb_cards.append(card)

            if target_id is not None and kb["id"] == target_id:
                card.set_selected(True)

        # 默认选中第一个
        if not target_id and self._kb_cards:
            self._kb_cards[0].set_selected(True)
            self._on_card_clicked(self._kb_cards[0].kb_id)

        self._emit_chat_kbs()

    def _clear_cards(self):
        for card in self._kb_cards:
            self._card_layout.removeWidget(card)
            card.deleteLater()
        self._kb_cards.clear()

    def _on_card_clicked(self, kb_id: int) -> None:
        """点击卡片 — 选中高亮 + 刷新文档"""
        for card in self._kb_cards:
            card.set_selected(card.kb_id == kb_id)

        if self._active_kb_id != kb_id:
            self._active_kb_id = kb_id
            kb = self._kb_mgr.get_kb(kb_id)
            if kb:
                self._refresh_docs()
                self.kb_changed.emit(kb_id, kb.get("chroma_collection_name", ""))

    # ------------------------------------------------------------------ #
    #  右键菜单 — 添加/移除对话
    # ------------------------------------------------------------------ #

    def _on_card_context(self, kb_id: int, menu: QMenu) -> None:
        """处理卡片右键菜单 — 添加到对话/从对话移除"""
        kb = self._kb_mgr.get_kb(kb_id)
        if not kb:
            return

        in_chat = kb_id in self._chat_kb_ids
        action = menu.actions()[0]

        if action.text().startswith("💬"):
            # 添加到对话
            self._chat_kb_ids.add(kb_id)
            self.status_message.emit(f"「{kb['name']}」已添加到对话")
        else:
            # 从对话移除
            self._chat_kb_ids.discard(kb_id)
            self.status_message.emit(f"「{kb['name']}」已从对话移除")

        self._refresh_kb_list(select_kb_id=kb_id)
        self._emit_chat_kbs()

    def _emit_chat_kbs(self) -> None:
        collections = []
        names = []
        for kb_id in self._chat_kb_ids:
            kb = self._kb_mgr.get_kb(kb_id)
            if kb:
                collections.append(kb["chroma_collection_name"])
                names.append(kb["name"])
        self.chat_kbs_changed.emit(collections, names)

    # ------------------------------------------------------------------ #
    #  KB CRUD
    # ------------------------------------------------------------------ #

    def _create_kb(self) -> None:
        name, ok = QInputDialog.getText(self, "新建知识库", "名称:")
        if ok and name.strip():
            try:
                kb_id = self._kb_mgr.create_kb(name.strip())
                self._refresh_kb_list(select_kb_id=kb_id)
                self.status_message.emit(f"知识库「{name}」已创建")
            except ValueError as e:
                QMessageBox.warning(self, "错误", str(e))

    def _delete_current_kb(self) -> None:
        if self._active_kb_id is None:
            QMessageBox.information(self, "提示", "请先选择知识库")
            return
        kb = self._kb_mgr.get_kb(self._active_kb_id)
        if kb is None:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除知识库「{kb['name']}」及其所有文档吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._chat_kb_ids.discard(self._active_kb_id)
            self._kb_mgr.delete_kb(self._active_kb_id)
            self._active_kb_id = None
            self._refresh_kb_list()
            self.status_message.emit("知识库已删除")

    # ------------------------------------------------------------------ #
    #  Document
    # ------------------------------------------------------------------ #

    def _refresh_docs(self) -> None:
        if self._active_kb_id is None:
            self._file_list.refresh([])
            return
        docs = self._kb_mgr.get_documents(self._active_kb_id)
        self._file_list.refresh(docs)

    def _upload_document(self) -> None:
        if self._active_kb_id is None:
            QMessageBox.information(self, "提示", "请先选择知识库")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文档", "",
            "文档文件 (*.pdf *.docx *.md *.txt *.json *.jsonl);;所有文件 (*.*)"
        )
        if not file_path:
            return
        self.status_message.emit(f"开始入库: {os.path.basename(file_path)}")
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._ingest_worker = IngestWorker(
            kb_id=self._active_kb_id, file_path=file_path,
            kb_mgr=self._kb_mgr, vs=self._vs, emb_svc=self._emb_svc, proc=self._proc,
        )
        self._ingest_worker.progress.connect(self._on_ingest_progress)
        self._ingest_worker.finished.connect(self._on_ingest_finished)
        self._ingest_worker.start()

    def _delete_document(self, doc_id: int) -> None:
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该文档及其向量数据吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._delete_worker = DeleteWorker(doc_id, self._kb_mgr)
        self._delete_worker.finished.connect(self._on_delete_finished)
        self._delete_worker.start()

    # ------------------------------------------------------------------ #
    #  Worker callbacks
    # ------------------------------------------------------------------ #

    def _on_ingest_progress(self, percent: int, message: str) -> None:
        self._progress.setValue(percent)
        self.status_message.emit(message)

    def _on_ingest_finished(self, success: bool, message: str) -> None:
        self._progress.setVisible(False)
        self.status_message.emit(message)
        self._refresh_docs()
        self._refresh_kb_list()
        if not success:
            QMessageBox.warning(self, "入库失败", message)

    def _on_delete_finished(self, success: bool, message: str) -> None:
        self.status_message.emit(message)
        self._refresh_docs()
        self._refresh_kb_list()
        if not success:
            QMessageBox.warning(self, "删除失败", message)

    # ------------------------------------------------------------------ #
    #  Public
    # ------------------------------------------------------------------ #

    @property
    def active_kb_id(self) -> int | None:
        return self._active_kb_id
