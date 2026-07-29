# -*- coding: utf-8 -*-
"""
Embedding 服务 — 封装模型注册中心的 embedding 调用，提供自动分批。
"""

from app.core.model_registry import ModelRegistry


class EmbeddingService:
    """
    调用当前活跃 Embedding 供应商生成向量。
    自动分批处理，batch size 从供应商配置读取（默认 20）。
    """

    def __init__(self, registry: ModelRegistry):
        self._registry = registry

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def embed_query(self, query: str) -> list[float]:
        """对单个查询文本生成向量。"""
        provider = self._registry.get_embedding_provider()
        if provider is None:
            raise RuntimeError("没有可用的 Embedding 供应商")
        model = self._registry.active_embedding_model
        result = provider.embed([query], model=model)
        return result.embeddings[0]

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """批量生成向量，自动按供应商配置的 batch_size 分批。"""
        if not chunks:
            return []

        provider = self._registry.get_embedding_provider()
        if provider is None:
            raise RuntimeError("没有可用的 Embedding 供应商")
        model = self._registry.active_embedding_model
        batch_size = provider._config.embedding_batch_size

        all_embeddings: list[list[float]] = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            result = provider.embed(batch, model=model)
            all_embeddings.extend(result.embeddings)

        return all_embeddings

    @property
    def dimensions(self) -> int:
        """获取当前 embedding 模型维度（从配置读取）。"""
        provider = self._registry.get_embedding_provider()
        if provider is None:
            return 0
        config = provider._config
        for m in config.embedding_models:
            if m.get("model_name") == self._registry.active_embedding_model:
                return m.get("dimensions", 0)
        return 0
