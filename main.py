# -*- coding: utf-8 -*-
"""
RAG_H — 入口
"""

import sys
import os

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ctypes

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# Windows 任务栏：设置唯一的 appUserModelId，避免与 python.exe 混在一起
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("rag-h.rag-qa-system.1.0")
    except Exception:
        pass

from app.core.config import ConfigManager
from app.core.database import DatabaseManager
from app.core.model_registry import ModelRegistry
from app.core.embedding_service import EmbeddingService
from app.core.vector_store import VectorStore
from app.core.kb_manager import KnowledgeBaseManager
from app.core.document_processor import DocumentProcessor
from app.core.rag_pipeline import RAGPipeline
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局 QMenu 样式 — 覆盖 Fusion 风格默认装饰
    app.setStyleSheet("""
        QMenu {
            background-color: #FFFFFF;
            border: 1px solid #E5E5E5;
            border-radius: 6px;
            padding: 4px 0px;
        }
        QMenu::item {
            padding: 6px 16px;
            color: #333333;
            border-radius: 0px;
        }
        QMenu::item:selected {
            background-color: #F0F0F0;
        }
        QMenu::separator {
            height: 1px;
            background-color: #E5E5E5;
            margin: 4px 0px;
        }
        QToolTip {
            background-color: #FFFFFF;
            border: none;
            padding: 2px 6px;
            color: #333333;
            font-size: 9pt;
        }
    """)
    # 设置应用图标（任务栏 + 窗口标题栏）
    logo_path = os.path.join(PROJECT_ROOT, "assets", "logo.ico")
    if os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))

    # 1. 加载配置
    config = ConfigManager(
        config_path=os.path.join(PROJECT_ROOT, "config.json"),
        default_path=os.path.join(PROJECT_ROOT, "config.default.json"),
    )
    print(f"[OK] 配置加载完成，供应商数: {len(config.providers)}")
    print(f"    活跃对话: {config.get_active_chat_model()}")
    print(f"    活跃 Embedding: {config.get_active_embedding_model()}")

    # 2. 初始化数据库
    db = DatabaseManager(db_path=os.path.join(PROJECT_ROOT, "data", "database.db"))
    print(f"[OK] 数据库初始化完成")

    # 3. 模型注册中心
    registry = ModelRegistry(config.data)
    print(f"[OK] 模型注册中心就绪，供应商: {[p.provider_id for p in registry.list_all_providers()]}")

    # 4. 核心服务
    vs = VectorStore(persist_dir=os.path.join(PROJECT_ROOT, "data", "chroma"))
    emb_svc = EmbeddingService(registry)
    kb_mgr = KnowledgeBaseManager(db, vs)
    proc = DocumentProcessor(
        chunk_size=config.app_settings["chunk_size"],
        chunk_overlap=config.app_settings["chunk_overlap"],
        chunk_method=config.app_settings["chunk_method"],
    )
    rag = RAGPipeline(registry, emb_svc, vs)
    print(f"[OK] 核心服务就绪")

    # 5. 启动窗口
    window = MainWindow(config, db, registry, emb_svc, vs, kb_mgr, proc, rag)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
