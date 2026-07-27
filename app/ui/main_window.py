# -*- coding: utf-8 -*-
"""
主窗口 — 整合侧边栏 + 对话面板。
"""

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QMenuBar, QStatusBar, QMessageBox,
)
from PySide6.QtCore import Qt

from app.core.config import ConfigManager
from app.core.database import DatabaseManager
from app.core.model_registry import ModelRegistry
from app.core.embedding_service import EmbeddingService
from app.core.vector_store import VectorStore
from app.core.kb_manager import KnowledgeBaseManager
from app.core.document_processor import DocumentProcessor
from app.core.rag_pipeline import RAGPipeline
from app.ui.kb_panel import KbPanel
from app.ui.chat_panel import ChatPanel
from app.ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """RAG 问答系统主窗口。"""

    def __init__(
        self,
        config: ConfigManager,
        db: DatabaseManager,
        registry: ModelRegistry,
        emb_svc: EmbeddingService,
        vs: VectorStore,
        kb_mgr: KnowledgeBaseManager,
        proc: DocumentProcessor,
        rag: RAGPipeline,
    ):
        super().__init__()
        self._config = config
        self._db = db
        self._registry = registry
        self._proc = proc
        self._kb_mgr = kb_mgr
        self._vs = vs
        self._emb_svc = emb_svc
        self._rag = rag
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("RAG 问答系统")
        self.resize(1100, 700)

        # ---- 菜单栏 ----
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件(&F)")
        settings_action = file_menu.addAction("设置(&S)...")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("退出(&Q)")
        exit_action.triggered.connect(self.close)

        help_menu = menubar.addMenu("帮助(&H)")
        about_action = help_menu.addAction("关于(&A)")
        about_action.triggered.connect(self._show_about)

        # ---- 状态栏 ----
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪")

        # ---- 中央 Splitter ----
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：知识库面板
        self._kb_panel = KbPanel(
            kb_mgr=self._kb_mgr,
            vs=self._vs,
            emb_svc=self._emb_svc,
            proc=self._proc,
        )
        self._kb_panel.kb_changed.connect(self._on_kb_changed)
        self._kb_panel.chat_kbs_changed.connect(self._on_chat_kbs_changed)
        self._kb_panel.status_message.connect(self._status_bar.showMessage)
        self._kb_panel.setMinimumWidth(260)
        self._kb_panel.setMaximumWidth(400)
        splitter.addWidget(self._kb_panel)

        # 右侧：对话面板
        self._chat_panel = ChatPanel(rag=self._rag, top_k=self._config.app_settings["top_k_retrieval"])
        self._chat_panel.status_message.connect(self._status_bar.showMessage)
        splitter.addWidget(self._chat_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 820])

        self.setCentralWidget(splitter)

    # ------------------------------------------------------------------ #
    #  Slots
    # ------------------------------------------------------------------ #

    def _on_kb_changed(self, kb_id: int, collection_name: str) -> None:
        """左侧选中浏览 KB 变化 — 仅用于文档列表展示，不影响对话。"""
        pass  # 文档列表刷新由 KbPanel 内部处理

    def _on_chat_kbs_changed(self, collections: list, names: list) -> None:
        """对话关联 KB 变化 → 聊天面板多库检索。"""
        self._chat_panel.set_collections(collections, names)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._registry, self)
        if dialog.exec():
            # 用户点确认 — 更新 UI 中的活跃参数
            self._chat_panel.set_collection(self._kb_panel.active_collection)
            self.statusBar().showMessage("设置已保存，新模型已生效")
            # 更新文档处理器参数
            app_s = self._config.app_settings
            self._proc.chunk_size = app_s["chunk_size"]
            self._proc.chunk_overlap = app_s["chunk_overlap"]
            self._proc.chunk_method = app_s["chunk_method"]

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "关于 RAG 问答系统",
            "<h3>RAG 问答系统 v1.0</h3>"
            "<p>基于 PySide6 + ChromaDB + 阿里云 MaaS</p>"
            "<p>支持 PDF / DOCX / Markdown 文档的知识库问答</p>",
        )

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        self._db.close()
        super().closeEvent(event)
