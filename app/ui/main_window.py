# -*- coding: utf-8 -*-
"""
主窗口 — 左侧活动栏 + 右侧 QStackedWidget(对话/知识库/设置/帮助)。
"""

from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QWidget, QHBoxLayout, QStackedWidget,
)
from PySide6.QtGui import QIcon
import os

from app.core.config import ConfigManager
from app.core.database import DatabaseManager
from app.core.model_registry import ModelRegistry
from app.core.embedding_service import EmbeddingService
from app.core.vector_store import VectorStore
from app.core.kb_manager import KnowledgeBaseManager
from app.core.document_processor import DocumentProcessor
from app.core.rag_pipeline import RAGPipeline
from app.ui.kb_page import KbPage
from app.ui.chat_panel import ChatPanel
from app.ui.settings_page import SettingsPage
from app.ui.help_page import HelpPage
from app.ui.widgets.nav_rail import NavRail
from app.ui.theme import PANEL_BG, menu_style


# QStackedWidget 页面索引(与 NavRail.PAGES 顺序一致)
PAGE_CHAT = 0
PAGE_KB = 1
PAGE_SETTINGS = 2
PAGE_HELP = 3


class MainWindow(QMainWindow):
    """RAG_H 主窗口 — 单一窗体,活动栏切换页面。"""

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
        self.setWindowTitle("RAG_H")
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1100, 700)

        # 设置主窗口背景
        self.setStyleSheet(f"QMainWindow {{ background-color: {PANEL_BG}; }}")

        # ---- 菜单栏:仅保留 退出 ----
        menubar = self.menuBar()
        menubar.setStyleSheet(menu_style())
        file_menu = menubar.addMenu("文件(&F)")
        exit_action = file_menu.addAction("退出(&Q)")
        exit_action.triggered.connect(self.close)

        # ---- 状态栏 ----
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪 — RAG_H")

        # ---- 中央:NavRail + QStackedWidget ----
        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self._nav = NavRail()
        self._stack = QStackedWidget()

        # 页面 0:对话
        self._chat_panel = ChatPanel(
            rag=self._rag,
            top_k=self._config.app_settings["top_k_retrieval"],
            rerank_enabled=self._config.app_settings.get("rerank_enabled", True),
            rerank_candidate_multiplier=self._config.app_settings.get("rerank_candidate_multiplier", 3),
        )
        self._chat_panel.status_message.connect(self._status_bar.showMessage)

        # 页面 1:知识库
        self._kb_page = KbPage(
            kb_mgr=self._kb_mgr,
            vs=self._vs,
            emb_svc=self._emb_svc,
            proc=self._proc,
        )
        self._kb_page.kb_changed.connect(self._on_kb_changed)
        self._kb_page.chat_kbs_changed.connect(self._on_chat_kbs_changed)
        self._kb_page.status_message.connect(self._status_bar.showMessage)

        # 页面 2:设置
        self._settings_page = SettingsPage(config=self._config, registry=self._registry)
        self._settings_page.saved.connect(self._on_settings_saved)
        self._settings_page.status_message.connect(self._status_bar.showMessage)

        # 页面 3:帮助
        self._help_page = HelpPage()

        for w in (self._chat_panel, self._kb_page, self._settings_page, self._help_page):
            self._stack.addWidget(w)

        h.addWidget(self._nav)
        h.addWidget(self._stack, 1)

        self.setCentralWidget(central)

        # 活动栏切换 → 切页面
        self._nav.page_changed.connect(self._stack.setCurrentIndex)

    # ------------------------------------------------------------------ #
    #  Slots
    # ------------------------------------------------------------------ #

    def _on_kb_changed(self, kb_id: int, collection_name: str) -> None:
        """选中浏览 KB 变化 — 仅用于文档列表展示,不影响对话。"""
        pass  # 文档列表刷新由 KbPage 内部处理

    def _on_chat_kbs_changed(self, collections: list, names: list) -> None:
        """对话关联 KB 变化 → 聊天面板多库检索。"""
        self._chat_panel.set_collections(collections, names)

    def _on_settings_saved(self) -> None:
        """设置页保存后刷新运行时参数(替代原 _open_settings 的保存后处理)。

        修复旧 bug:rerank/top_k 此前仅在 ChatPanel 构造时传入一次,改设置后不刷新。
        """
        app_s = self._config.app_settings
        self._proc.chunk_size = app_s["chunk_size"]
        self._proc.chunk_overlap = app_s["chunk_overlap"]
        self._proc.chunk_method = app_s["chunk_method"]
        self._chat_panel.set_retrieval_params(
            top_k=app_s["top_k_retrieval"],
            rerank_enabled=app_s.get("rerank_enabled", True),
            rerank_candidate_multiplier=app_s.get("rerank_candidate_multiplier", 3),
        )
        self._status_bar.showMessage("设置已保存,新模型与参数已生效")

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        self._db.close()
        super().closeEvent(event)
