# -*- coding: utf-8 -*-
"""
知识库页 — 左栏 KB 列表 + 文档列表,右栏分块预览,对话关联 + 右键菜单。

左导航 + 右内容的 master-detail 结构:左栏自上而下放 KB 列表(限高)与文档列表,
中间水平 QSplitter 可拖拽列宽,右栏整列给分块预览。
保留全部 KB/文档 CRUD、IngestWorker/DeleteWorker、对话关联、右键菜单逻辑。
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QInputDialog, QMessageBox, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QAbstractItemView,
    QScrollArea, QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.core.kb_manager import KnowledgeBaseManager
from app.core.vector_store import VectorStore
from app.core.embedding_service import EmbeddingService
from app.core.document_processor import DocumentProcessor
from app.ui.widgets.file_list_widget import FileListWidget
from app.ui.widgets.chunk_card import ChunkCard
from app.ui.widgets.section_header import SectionHeader, h_separator, clear_layout
from app.ui.workers.ingest_worker import IngestWorker
from app.ui.workers.delete_worker import DeleteWorker
from app.ui.theme import PANEL_BG, FONT_FAMILY, FONT_SIZE_SM, list_style
from app.ui.widgets.simple_menu import SimpleMenu


class KbPage(QWidget):
    """知识库页 — 左栏 KB+文档 / 右栏分块预览,水平 QSplitter 可拖拽列宽。"""

    kb_changed = Signal(int, str)                # kb_id, collection_name (选中浏览)
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
        self._active_kb_id: int | None = None    # 当前选中浏览的 KB
        self._chat_kb_ids: set[int] = set()       # 对话关联的 KB id 集合
        self._ingest_worker: IngestWorker | None = None
        self._delete_worker: DeleteWorker | None = None
        self._setup_ui()
        self._refresh_kb_list()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"KbPage {{ background-color: {PANEL_BG}; }}")

        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # ==================== 左栏:KB 列表 + 文档列表 ====================
        left = QWidget()
        left.setMinimumWidth(260)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(SectionHeader(
            "📚 知识库",
            [("+ 新建", "新建知识库", self._create_kb),
             ("🗑", "删除选中知识库", self._delete_current_kb)],
        ))

        self._kb_list = QListWidget()
        self._kb_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._kb_list.customContextMenuRequested.connect(self._kb_context_menu)
        self._kb_list.currentRowChanged.connect(self._on_kb_clicked)
        self._kb_list.itemDoubleClicked.connect(self._on_kb_double_clicked)
        self._kb_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._kb_list.setMaximumHeight(220)
        self._kb_list.setStyleSheet(list_style())
        left_layout.addWidget(self._kb_list, 0)

        left_layout.addWidget(h_separator())

        left_layout.addWidget(SectionHeader(
            "📄 文档",
            [("📤 上传", "上传文档到当前知识库", self._upload_document)],
        ))

        self._file_list = FileListWidget()
        self._file_list.doc_delete_requested.connect(self._delete_document)
        self._file_list.currentRowChanged.connect(self._on_doc_selected)
        left_layout.addWidget(self._file_list, 1)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        left_layout.addWidget(self._progress)

        splitter.addWidget(left)

        # ==================== 右栏:分块预览 ====================
        right = QWidget()
        right.setMinimumWidth(360)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(SectionHeader("🧩 分块预览"))

        self._chunk_scroll = QScrollArea()
        self._chunk_scroll.setWidgetResizable(True)
        self._chunk_scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {PANEL_BG}; }}"
        )
        self._chunk_container = QWidget()
        self._chunk_layout = QVBoxLayout(self._chunk_container)
        self._chunk_layout.setContentsMargins(0, 0, 0, 0)
        self._chunk_layout.setSpacing(0)
        self._chunk_layout.addStretch()
        self._chunk_scroll.setWidget(self._chunk_container)
        right_layout.addWidget(self._chunk_scroll, 1)

        splitter.addWidget(right)

        splitter.setSizes([340, 820])
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter)

        # 分块预览占位提示
        self._show_chunk_placeholder("选择左侧文档以预览分块")

    # ------------------------------------------------------------------ #
    #  KB 列表刷新
    # ------------------------------------------------------------------ #

    def _refresh_kb_list(self, select_kb_id: int | None = None) -> None:
        kbs = self._kb_mgr.list_kbs()
        target_id = select_kb_id if select_kb_id is not None else self._active_kb_id

        try:
            self._kb_list.currentRowChanged.disconnect(self._on_kb_clicked)
        except (TypeError, RuntimeError):
            pass  # 信号未连接或已断开,忽略(修复旧 bug:裸 disconnect 会抛 TypeError)
        self._kb_list.clear()

        for kb in kbs:
            in_chat = kb["id"] in self._chat_kb_ids
            prefix = "💬 " if in_chat else "   "
            text = f"{prefix}{kb['name']}  ({kb.get('doc_count', 0)} 篇)"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, kb["id"])
            item.setToolTip(f"名称: {kb['name']}\n双击{'移除' if in_chat else '添加'}到对话")
            self._kb_list.addItem(item)

        # 恢复/设置选中
        restored = False
        if target_id is not None:
            for i in range(self._kb_list.count()):
                if self._kb_list.item(i).data(Qt.UserRole) == target_id:
                    self._kb_list.setCurrentRow(i)
                    restored = True
                    break
        self._kb_list.currentRowChanged.connect(self._on_kb_clicked)

        if self._kb_list.count() > 0 and not restored:
            self._kb_list.setCurrentRow(0)

        if self._kb_list.currentRow() >= 0:
            self._on_kb_clicked(self._kb_list.currentRow())
        else:
            self._active_kb_id = None
            self._file_list.refresh([])

        self._emit_chat_kbs()

    def _on_kb_clicked(self, row: int) -> None:
        if row < 0:
            return
        item = self._kb_list.item(row)
        if item is None:
            return
        self._active_kb_id = item.data(Qt.UserRole)
        kb = self._kb_mgr.get_kb(self._active_kb_id)
        if kb:
            self._refresh_docs()

    def _on_kb_double_clicked(self, item: QListWidgetItem) -> None:
        """双击知识库项时快速添加到对话或从对话移除"""
        if item is None:
            return
        kb_id = item.data(Qt.UserRole)
        kb = self._kb_mgr.get_kb(kb_id)
        if kb is None:
            return

        in_chat = kb_id in self._chat_kb_ids
        if in_chat:
            self._chat_kb_ids.discard(kb_id)
            self.status_message.emit(f"「{kb['name']}」已从对话移除")
        else:
            self._chat_kb_ids.add(kb_id)
            self.status_message.emit(f"「{kb['name']}」已添加到对话")

        self._refresh_kb_list()
        self._emit_chat_kbs()

    # ------------------------------------------------------------------ #
    #  右键菜单 — 添加/移除对话
    # ------------------------------------------------------------------ #

    def _kb_context_menu(self, pos) -> None:
        item = self._kb_list.itemAt(pos)
        if item is None:
            return
        kb_id = item.data(Qt.UserRole)
        kb = self._kb_mgr.get_kb(kb_id)
        if kb is None:
            return

        in_chat = kb_id in self._chat_kb_ids
        menu = SimpleMenu(self)

        if in_chat:
            action = menu.addAction("🔇 从对话移除")
        else:
            action = menu.addAction("💬 添加到对话")

        chosen = menu.exec(self._kb_list.mapToGlobal(pos))
        if chosen == action:
            if in_chat:
                self._chat_kb_ids.discard(kb_id)
                self.status_message.emit(f"「{kb['name']}」已从对话移除")
            else:
                self._chat_kb_ids.add(kb_id)
                self.status_message.emit(f"「{kb['name']}」已添加到对话")
            self._refresh_kb_list()
            self._emit_chat_kbs()

    def _emit_chat_kbs(self) -> None:
        """通知聊天面板当前关联的 KB。"""
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
            self._show_chunk_placeholder("选择左侧文档以预览分块")
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
    #  分块预览
    # ------------------------------------------------------------------ #

    def _on_doc_selected(self, row: int) -> None:
        """文档选中 → 取回其分块并渲染 ChunkCard 列表。"""
        if row < 0:
            return
        item = self._file_list.item(row)
        if item is None:
            return
        doc_id = item.data(Qt.UserRole)
        try:
            chunks = self._kb_mgr.get_chunks_for_document(doc_id)
        except Exception as e:
            self._show_chunk_placeholder(f"读取分块失败: {e}")
            return

        clear_layout(self._chunk_layout)
        if not chunks:
            self._show_chunk_placeholder("该文档暂无分块数据")
            return
        for i, ctx in enumerate(chunks, 1):
            self._chunk_layout.addWidget(ChunkCard(ctx, index=i))
        self._chunk_layout.addStretch()

    def _show_chunk_placeholder(self, text: str) -> None:
        """在分块预览区显示占位提示。"""
        clear_layout(self._chunk_layout)
        hint = QLabel(text)
        hint.setFont(QFont(FONT_FAMILY, FONT_SIZE_SM))
        hint.setStyleSheet("color: #999;")
        hint.setAlignment(Qt.AlignCenter)
        self._chunk_layout.addWidget(hint)
        self._chunk_layout.addStretch()

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
        self._show_chunk_placeholder("选择左侧文档以预览分块")
        if not success:
            QMessageBox.warning(self, "删除失败", message)

    # ------------------------------------------------------------------ #
    #  Public
    # ------------------------------------------------------------------ #

    @property
    def active_kb_id(self) -> int | None:
        return self._active_kb_id
