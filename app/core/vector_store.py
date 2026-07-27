# -*- coding: utf-8 -*-
"""
ChromaDB 向量存储封装 — 增删查。
"""

import os
from typing import Optional
import chromadb
from chromadb.config import Settings


class VectorStore:
    """ChromaDB PersistentClient 封装。"""

    def __init__(self, persist_dir: str = "data/chroma"):
        self._persist_dir = os.path.abspath(persist_dir)
        os.makedirs(self._persist_dir, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

    # ------------------------------------------------------------------ #
    #  Collection management
    # ------------------------------------------------------------------ #

    def get_or_create_collection(self, name: str):
        """获取或创建 collection。"""
        return self._client.get_or_create_collection(name=name)

    def delete_collection(self, name: str) -> None:
        """删除整个 collection。"""
        try:
            self._client.delete_collection(name=name)
        except Exception:
            pass  # 不存在则忽略

    def collection_exists(self, name: str) -> bool:
        collections = self._client.list_collections()
        return any(c.name == name for c in collections)

    # ------------------------------------------------------------------ #
    #  Chunk operations
    # ------------------------------------------------------------------ #

    def add_chunks(
        self,
        collection_name: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        """批量添加向量+文本到 collection。"""
        if not chunks:
            return
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """检索最相似的 top_k 个片段。

        Returns:
            [{id, text, metadata, distance}, ...]
        """
        collection = self.get_or_create_collection(collection_name)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
        )

        items: list[dict] = []
        if results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                items.append({
                    "id": results["ids"][0][i],
                    "text": (results.get("documents") or [[""]])[0][i],
                    "metadata": (results.get("metadatas") or [{}])[0][i],
                    "distance": (results.get("distances") or [[0.0]])[0][i],
                })
        return items

    def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        """按 chroma_id 删除向量。"""
        if not ids:
            return
        collection = self.get_or_create_collection(collection_name)
        try:
            collection.delete(ids=ids)
        except Exception:
            pass  # ID 不存在则忽略

    def count(self, collection_name: str) -> int:
        """返回 collection 中的向量数量。"""
        collection = self.get_or_create_collection(collection_name)
        return collection.count()
