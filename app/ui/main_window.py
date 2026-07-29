# -*- coding: utf-8 -*-
"""
主窗口 — FluentWindow 框架 + 传统左右分栏布局
=============================================
左侧 KbPanel（知识库列表 + 文档管理）
右侧 ChatPanel（对话 + 消息输入）
两者始终同时可见，保持 RAG 应用的正确工作流。
"""

from PySide6.QtWidgets import QSplitter, QMessageBox
from PySide6.QtCore import Qt
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
from app.ui.kb_panel import KbPanel
from app.ui.chat_panel import ChatPanel
from app.ui.settings_dialog import SettingsDialog

from app.ui.fluent import (
    FluentWindow,
    show_info, show_success, show_warning, show_error,
    info_bar_mgr, theme_manager, is_dark_theme,
)


class MainWindow(FluentWindow):
    """RAG_H 主窗口 — Fluent 标题栏 + 导航, 内容区左右分栏"""

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

        # 窗口标题和图标
        self.set_title("RAG_H")
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "logo.ico"
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            self.titleBar.set_icon(QIcon(icon_path).pixmap(18, 18))

        self.resize(1100, 700)

        # 核心面板（独立于导航页面，直接放内容区）
        self._setup_content()

        # 导航与信号
        self._setup_navigation()
        self._connect_signals()

        # InfoBar
        info_bar_mgr.set_parent(self)
        theme_manager.themeChanged.connect(self._on_theme_change_info_bar)

    def _on_theme_change_info_bar(self, _theme_value: str):
        info_bar_mgr.set_dark_mode(is_dark_theme())

    # ------------------------------------------------------------------ #
    #  内容区主布局：QSplitter 左右分栏
    # ------------------------------------------------------------------ #

    def _setup_content(self):
        """创建左右分栏内容区，替换 stackedWidget 中的默认页面"""
        # 创建 KbPanel + ChatPanel
        self._kb_panel = KbPanel(
            kb_mgr=self._kb_mgr,
            vs=self._vs,
            emb_svc=self._emb_svc,
            proc=self._proc,
        )
        self._kb_panel.status_message.connect(self._on_status_msg)
        self._kb_panel.setMinimumWidth(240)
        self._kb_panel.setMaximumWidth(400)

        self._chat_panel = ChatPanel(
            rag=self._rag,
            top_k=self._config.app_settings["top_k_retrieval"],
        )
        self._chat_panel.status_message.connect(self._on_status_msg)

        # QSplitter 并排放置
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._kb_panel)
        splitter.addWidget(self._chat_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 820])

        # 将 splitter 放入 stackedWidget 的第一个（也是唯一一个）页面
        # 先清掉默认的空页面
        while self.stackedWidget.count() > 0:
            w = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(w)

        self._content_widget = splitter
        self._content_widget.setObjectName("mainContent")
        self.stackedWidget.addWidget(self._content_widget)

    # ------------------------------------------------------------------ #
    #  导航
    # ------------------------------------------------------------------ #

    def _setup_navigation(self):
        """左侧导航：对话（默认选中）+ 设置（底部）"""
        # 导航项 — 点击不做页面切换，但保持高亮反馈
        kb_item = self.navigation.add_item("library", "知识库")
        kb_item.clicked.connect(lambda: self._focus_kb_panel())

        chat_item = self.navigation.add_item("chat", "对话")
        chat_item.clicked.connect(lambda: self._focus_chat_panel())

        # 默认选中对话
        self.navigation.set_current_item(chat_item)

        # 底部
        self.navigation.add_stretch()
        settings_item = self.navigation.add_item("settings", "设置", is_bottom=True)
        settings_item.clicked.connect(self._open_settings)

    def _focus_kb_panel(self):
        """聚焦到知识库区域"""
        self._kb_panel.setFocus()
        show_info("知识库面板", duration=1500)

    def _focus_chat_panel(self):
        """聚焦到对话区域"""
        self._chat_panel.setFocus()
        show_info("对话面板", duration=1500)

    # ------------------------------------------------------------------ #
    #  信号
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        self._kb_panel.kb_changed.connect(self._on_kb_changed)
        self._kb_panel.chat_kbs_changed.connect(self._on_chat_kbs_changed)

    def _on_kb_changed(self, kb_id: int, collection_name: str) -> None:
        pass

    def _on_chat_kbs_changed(self, collections: list, names: list) -> None:
        self._chat_panel.set_collections(collections, names)

    # ------------------------------------------------------------------ #
    #  Status → InfoBar
    # ------------------------------------------------------------------ #

    def _on_status_msg(self, msg: str):
        if not msg:
            return
        if msg.startswith("❌") or msg.startswith("错误"):
            show_error(msg)
        elif msg.startswith("⚠") or msg.startswith("警告"):
            show_warning(msg)
        elif msg.startswith("✅") or msg.startswith("就绪"):
            if "错误" not in msg:
                show_success(msg)
            else:
                show_error(msg)
        else:
            show_info(msg, duration=3000)

    # ------------------------------------------------------------------ #
    #  Dialogs
    # ------------------------------------------------------------------ #

    def _open_settings(self):
        dialog = SettingsDialog(self._config, self._registry, self)
        if dialog.exec():
            app_s = self._config.app_settings
            self._chat_panel.set_collection(self._kb_panel.active_collection)
            show_success("设置已保存")
            self._proc.chunk_size = app_s["chunk_size"]
            self._proc.chunk_overlap = app_s["chunk_overlap"]
            self._proc.chunk_method = app_s["chunk_method"]

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        self._db.close()
        super().closeEvent(event)
