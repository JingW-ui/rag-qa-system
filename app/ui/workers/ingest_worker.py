# -*- coding: utf-8 -*-
"""
文档入库 Worker — 解析 → 分块 → embedding → 存储（后台线程）。
"""

import os
import uuid

from PySide6.QtCore import QThread, Signal

from app.core.document_processor import DocumentProcessor
from app.core.embedding_service import EmbeddingService
from app.core.vector_store import VectorStore
from app.core.kb_manager import KnowledgeBaseManager


class IngestWorker(QThread):
    """后台线程执行文档入库全流程。"""

    progress = Signal(int, str)       # (percent, message)
    finished = Signal(bool, str)      # (success, message)
    doc_ingested = Signal(int)        # doc_id — 通知 UI 刷新

    def __init__(
        self,
        kb_id: int,
        file_path: str,
        kb_mgr: KnowledgeBaseManager,
        vs: VectorStore,
        emb_svc: EmbeddingService,
        proc: DocumentProcessor,
        parent=None,
    ):
        super().__init__(parent)
        self._kb_id = kb_id
        self._file_path = file_path
        self._kb_mgr = kb_mgr
        self._vs = vs
        self._emb_svc = emb_svc
        self._proc = proc

    def run(self) -> None:
        try:
            filename = os.path.basename(self._file_path)
            ext = os.path.splitext(filename)[1].lower().lstrip(".")
            file_size = os.path.getsize(self._file_path)

            # 1. 创建文档记录
            self.progress.emit(5, "创建文档记录...")
            valid_types = ("pdf", "docx", "md", "txt", "json", "jsonl")
            doc_id = self._kb_mgr.add_document(
                kb_id=self._kb_id,
                filename=filename,
                file_path=self._file_path,
                file_type=ext if ext in valid_types else "md",
                file_size=file_size,
                chunk_size=self._proc.chunk_size,
                chunk_overlap=self._proc.chunk_overlap,
            )

            # 2. 更新为 processing
            self._kb_mgr.update_document_status(doc_id, "processing")
            self.progress.emit(10, "解析文档...")

            # 3. 解析
            full_text = self._proc.parse(self._file_path)
            self.progress.emit(30, f"解析完成 ({len(full_text)} 字符)")

            # 4. 分块
            self.progress.emit(35, "文本分块...")
            chunks = self._proc.chunk(full_text)

            if not chunks:
                self._kb_mgr.update_document_status(doc_id, "failed", 0, "文档内容为空或无法提取文本")
                self.finished.emit(False, "文档内容为空，无法入库")
                return

            self.progress.emit(40, f"分块完成 ({len(chunks)} 块)，生成向量...")

            # 5. Embedding
            embeddings = self._emb_svc.embed_chunks(chunks)
            self.progress.emit(70, f"向量生成完成 ({len(embeddings)} 个)")

            # 6. 存储到 ChromaDB
            self.progress.emit(75, "写入向量库...")
            kb = self._kb_mgr.get_kb(self._kb_id)

            chroma_ids = [f"doc{doc_id}_{i}" for i in range(len(chunks))]
            metadatas = [
                {"filename": filename, "chunk_index": i, "doc_id": str(doc_id)}
                for i in range(len(chunks))
            ]
            self._vs.add_chunks(
                kb["chroma_collection_name"], chunks, embeddings, metadatas, chroma_ids
            )
            self.progress.emit(90, "保存元数据...")

            # 7. 写入 chunk 元数据
            pairs = [(i, cid, len(chunks[i])) for i, cid in enumerate(chroma_ids)]
            self._kb_mgr.add_chunks_batch(doc_id, pairs)

            # 8. 更新为 completed
            self._kb_mgr.update_document_status(doc_id, "completed", len(chunks))

            self.progress.emit(100, f"入库完成！{len(chunks)} 个片段已写入知识库")
            self.doc_ingested.emit(doc_id)
            self.finished.emit(True, f"「{filename}」入库成功（{len(chunks)} 个片段）")

        except Exception as e:
            if 'doc_id' in locals():
                self._kb_mgr.update_document_status(doc_id, "failed", 0, str(e))
            self.finished.emit(False, f"入库失败: {e}")
