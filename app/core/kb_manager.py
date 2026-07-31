# -*- coding: utf-8 -*-
"""
知识库管理器 — KB CRUD + ChromaDB collection 生命周期。
"""

import sqlite3
import uuid
from typing import Optional

from app.core.database import DatabaseManager
from app.core.vector_store import VectorStore


class KnowledgeBaseManager:
    """管理知识库的创建、删除、查询，同步 ChromaDB。"""

    def __init__(self, db: DatabaseManager, vector_store: VectorStore):
        self._db = db
        self._vs = vector_store

    # ------------------------------------------------------------------ #
    #  KB CRUD
    # ------------------------------------------------------------------ #

    def create_kb(self, name: str, description: str = "") -> int:
        """创建知识库，返回 KB ID。"""
        if not name.strip():
            raise ValueError("知识库名称不能为空")

        # 生成唯一 ChromaDB collection 名
        safe_name = name.replace(" ", "_").replace("/", "_")
        chroma_name = f"kb_{safe_name}_{uuid.uuid4().hex[:8]}"

        cur = self._db.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO knowledge_bases (name, description, chroma_collection_name) VALUES (?, ?, ?)",
                (name.strip(), description, chroma_name),
            )
            self._db.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"知识库 '{name}' 已存在")

        kb_id = cur.lastrowid
        # 创建 ChromaDB collection
        self._vs.get_or_create_collection(chroma_name)
        return kb_id

    def delete_kb(self, kb_id: int) -> None:
        """删除知识库及其所有文档和向量。"""
        kb = self.get_kb(kb_id)
        if kb is None:
            raise ValueError(f"知识库不存在: id={kb_id}")

        # 删除 ChromaDB collection（向量一并清除）
        self._vs.delete_collection(kb["chroma_collection_name"])

        # 删除 SQLite 记录（CASCADE 自动删 documents + chunks）
        cur = self._db.conn.cursor()
        cur.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
        self._db.conn.commit()

    def list_kbs(self) -> list[dict]:
        """列出所有知识库。"""
        cur = self._db.conn.cursor()
        cur.execute(
            "SELECT k.*, (SELECT COUNT(*) FROM documents WHERE kb_id = k.id) AS doc_count "
            "FROM knowledge_bases k ORDER BY k.updated_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]

    def get_kb(self, kb_id: int) -> Optional[dict]:
        """获取单个知识库信息。"""
        cur = self._db.conn.cursor()
        cur.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def rename_kb(self, kb_id: int, new_name: str) -> None:
        """重命名知识库。"""
        cur = self._db.conn.cursor()
        cur.execute(
            "UPDATE knowledge_bases SET name = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (new_name.strip(), kb_id),
        )
        self._db.conn.commit()

    # ------------------------------------------------------------------ #
    #  Document management (metadata only)
    # ------------------------------------------------------------------ #

    def add_document(
        self,
        kb_id: int,
        filename: str,
        file_path: str,
        file_type: str,
        file_size: int,
        chunk_size: int,
        chunk_overlap: int,
    ) -> int:
        """添加文档记录，返回 doc_id。"""
        cur = self._db.conn.cursor()
        cur.execute(
            """INSERT INTO documents
               (kb_id, filename, file_path, file_type, file_size, chunk_size, chunk_overlap, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (kb_id, filename, file_path, file_type, file_size, chunk_size, chunk_overlap),
        )
        self._db.conn.commit()
        return cur.lastrowid

    def update_document_status(
        self, doc_id: int, status: str, chunk_count: int = 0, error_message: Optional[str] = None
    ) -> None:
        """更新文档处理状态。"""
        cur = self._db.conn.cursor()
        cur.execute(
            """UPDATE documents
               SET status = ?, chunk_count = ?, error_message = ?,
                   updated_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (status, chunk_count, error_message, doc_id),
        )
        self._db.conn.commit()

    def get_documents(self, kb_id: int) -> list[dict]:
        """获取知识库下所有文档。"""
        cur = self._db.conn.cursor()
        cur.execute(
            "SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC",
            (kb_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def delete_document(self, doc_id: int) -> None:
        """删除文档（SQLite CASCADE + ChromaDB 向量）。"""
        # 先查 chroma_ids 以便清理向量
        cur = self._db.conn.cursor()
        cur.execute("SELECT chroma_id FROM chunks WHERE document_id = ?", (doc_id,))
        chroma_ids = [r["chroma_id"] for r in cur.fetchall()]

        # 查 KB 的 collection 名
        cur.execute(
            """SELECT k.chroma_collection_name FROM knowledge_bases k
               JOIN documents d ON d.kb_id = k.id WHERE d.id = ?""",
            (doc_id,),
        )
        kb_row = cur.fetchone()

        # 删向量
        if kb_row and chroma_ids:
            self._vs.delete_by_ids(kb_row["chroma_collection_name"], chroma_ids)

        # 删 SQLite 记录（CASCADE 自动删 chunks）
        cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._db.conn.commit()

    # ------------------------------------------------------------------ #
    #  Chunk metadata
    # ------------------------------------------------------------------ #

    def add_chunks_batch(self, doc_id: int, chunk_chroma_pairs: list[tuple[int, str, int]]) -> None:
        """批量插入 chunk 元数据。

        Args:
            doc_id: 所属文档 ID。
            chunk_chroma_pairs: [(chunk_index, chroma_id, char_count), ...]
        """
        cur = self._db.conn.cursor()
        cur.executemany(
            "INSERT INTO chunks (document_id, chunk_index, chroma_id, char_count) VALUES (?, ?, ?, ?)",
            [(doc_id, idx, cid, count) for idx, cid, count in chunk_chroma_pairs],
        )
        self._db.conn.commit()

    def get_chunks_for_document(self, doc_id: int) -> list[dict]:
        """取回某文档的所有分块文本（按 chunk_index 排序），供分块预览展示。

        复用 delete_document 中 join 解析 collection 名的模式。
        返回值可直接喂 ChunkCard：每项含 text / metadata.filename / distance=None。
        """
        cur = self._db.conn.cursor()
        cur.execute(
            """SELECT chunk_index, chroma_id FROM chunks
               WHERE document_id = ? ORDER BY chunk_index""",
            (doc_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return []

        # 解析文档所属 KB 的 collection 名 + 文件名
        cur.execute(
            """SELECT k.chroma_collection_name, d.filename
               FROM knowledge_bases k
               JOIN documents d ON d.kb_id = k.id
               WHERE d.id = ?""",
            (doc_id,),
        )
        kb_row = cur.fetchone()
        if not kb_row:
            return []

        collection = kb_row["chroma_collection_name"]
        filename = kb_row["filename"]
        chroma_ids = [r["chroma_id"] for r in rows]
        docs = self._vs.get_by_ids(collection, chroma_ids)

        # 按 chunk_index 顺序对齐（get_by_ids 按传入 ids 顺序返回）
        for i, ctx in enumerate(docs):
            meta = dict(ctx.get("metadata") or {})
            meta.setdefault("filename", filename)
            meta["chunk_index"] = rows[i]["chunk_index"] if i < len(rows) else i
            ctx["metadata"] = meta
        return docs
