# -*- coding: utf-8 -*-
"""
文档删除 Worker — 后台线程删除文档 + 向量。
"""

from PySide6.QtCore import QThread, Signal

from app.core.kb_manager import KnowledgeBaseManager


class DeleteWorker(QThread):
    """删除单个文档（含向量清理）。"""

    finished = Signal(bool, str)        # (success, message)
    doc_deleted = Signal(int)           # doc_id

    def __init__(self, doc_id: int, kb_mgr: KnowledgeBaseManager, parent=None):
        super().__init__(parent)
        self._doc_id = doc_id
        self._kb_mgr = kb_mgr

    def run(self) -> None:
        try:
            self._kb_mgr.delete_document(self._doc_id)
            self.doc_deleted.emit(self._doc_id)
            self.finished.emit(True, "文档已删除")
        except Exception as e:
            self.finished.emit(False, f"删除失败: {e}")
