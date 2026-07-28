# -*- coding: utf-8 -*-
"""
知识库管理侧边栏 — 扁平 KB 列表 + 对话关联 + 右键菜单。
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QInputDialog, QMessageBox, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QMenu, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from app.core.kb_manager import KnowledgeBaseManager
from app.core.vector_store import VectorStore
from app.core.embedding_service import EmbeddingService
from app.core.document_processor import DocumentProcessor
from app.ui.widgets.file_list_widget import FileListWidget
from app.ui.workers.ingest_worker import IngestWorker
from app.ui.workers.delete_worker import DeleteWorker
from app.ui.dialogs.chunk_preview_dialog import ChunkPreviewDialog


class KbPanel(QWidget):
    """知识库管理面板 — 扁平列表 + 多选对话关联。"""

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)

        # ---- 顶部操作 ----
        header = QHBoxLayout()
        header.addWidget(QLabel("<b>📚 知识库</b>"))
        header.addStretch()
        btn_new = QPushButton("+ 新建")
        btn_new.clicked.connect(self._create_kb)
        header.addWidget(btn_new)
        btn_del = QPushButton("🗑")
        btn_del.setToolTip("删除选中知识库")
        btn_del.clicked.connect(self._delete_current_kb)
        header.addWidget(btn_del)
        layout.addLayout(header)

        # ---- KB 列表 ----
        self._kb_list = QListWidget()
        self._kb_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._kb_list.customContextMenuRequested.connect(self._kb_context_menu)
        self._kb_list.currentRowChanged.connect(self._on_kb_clicked)
        self._kb_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._kb_list.setStyleSheet("""
            QListWidget::item { padding: 4px 6px; border-radius: 2px; }
            QListWidget::item:selected { background-color: #d6eaf8; color: #000; }
        """)
        layout.addWidget(self._kb_list)

        # ---- 分隔 ----
        layout.addWidget(_h_separator())

        # ---- 文档 ----
        doc_header = QHBoxLayout()
        doc_header.addWidget(QLabel("<b>📄 文档</b>"))
        doc_header.addStretch()
        btn_upload = QPushButton("📤 上传")
        btn_upload.clicked.connect(self._upload_document)
        doc_header.addWidget(btn_upload)
        layout.addLayout(doc_header)

        self._file_list = FileListWidget()
        self._file_list.doc_delete_requested.connect(self._delete_document)
        layout.addWidget(self._file_list)

        # ---- 进度 ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

    # ------------------------------------------------------------------ #
    #  KB 列表刷新
    # ------------------------------------------------------------------ #

    def _refresh_kb_list(self, select_kb_id: int | None = None) -> None:
        kbs = self._kb_mgr.list_kbs()
        target_id = select_kb_id if select_kb_id is not None else self._active_kb_id

        self._kb_list.currentRowChanged.disconnect(self._on_kb_clicked)
        self._kb_list.clear()

        for kb in kbs:
            in_chat = kb["id"] in self._chat_kb_ids
            prefix = "💬 " if in_chat else "   "
            text = f"{prefix}{kb['name']}  ({kb.get('doc_count', 0)} 篇)"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, kb["id"])
            item.setToolTip(f"名称: {kb['name']}\n{'已在对话中 — 右键可移除' if in_chat else '右键可添加到对话'}")
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
        menu = QMenu(self)

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
            "文档文件 (*.pdf *.docx *.md *.txt);;所有文件 (*.*)"
        )
        if not file_path:
            return

        # 选择入库方式 — 使用自定义按钮文字
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("入库方式")
        msg_box.setText(f"请选择「{os.path.basename(file_path)}」的入库方式:")
        msg_box.setInformativeText("快速入库 — 使用全局分块参数直接入库\n预览分块 — 预览并编辑分块结果后再入库")
        msg_box.setIcon(QMessageBox.Question)
        btn_quick = msg_box.addButton("⚡ 快速入库", QMessageBox.AcceptRole)
        btn_preview = msg_box.addButton("🔍 预览分块", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_quick)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn_cancel or clicked is None:
            return

        if clicked == btn_quick:
            # 快速入库 — 现有流程
            self._start_ingest(file_path)
        else:
            # 预览分块 — 打开对话框
            dialog = ChunkPreviewDialog(file_path, self._proc, self)
            if dialog.exec():
                chunks = dialog.get_chunks()
                params = dialog.get_chunk_params()
                # 临时覆盖 proc 的分块参数（记录到文档）
                old_size, old_overlap, old_method = (
                    self._proc.chunk_size, self._proc.chunk_overlap, self._proc.chunk_method
                )
                self._proc.chunk_size = params["chunk_size"]
                self._proc.chunk_overlap = params["chunk_overlap"]
                self._proc.chunk_method = params["chunk_method"]
                self._start_ingest(file_path, manual_chunks=chunks)
                self._proc.chunk_size = old_size
                self._proc.chunk_overlap = old_overlap
                self._proc.chunk_method = old_method

    def _start_ingest(self, file_path: str, manual_chunks: list[str] | None = None) -> None:
        """启动入库 worker。"""
        self.status_message.emit(f"开始入库: {os.path.basename(file_path)}")
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._ingest_worker = IngestWorker(
            kb_id=self._active_kb_id, file_path=file_path,
            kb_mgr=self._kb_mgr, vs=self._vs, emb_svc=self._emb_svc, proc=self._proc,
            manual_chunks=manual_chunks,
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


def _h_separator() -> QWidget:
    line = QWidget()
    line.setFixedHeight(1)
    line.setStyleSheet("background-color: #d0d0d0;")
    return line
