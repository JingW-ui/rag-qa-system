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

from PySide6.QtWidgets import QApplication

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
