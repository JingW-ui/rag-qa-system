# -*- coding: utf-8 -*-
"""
Embedding 服务 — 封装模型注册中心的 embedding 调用，提供自动分批。
"""

from app.core.model_registry import ModelRegistry


DEFAULT_BATCH_SIZE = 32


class EmbeddingService:
    """
    调用当前活跃 Embedding 供应商生成向量。
    自动分批处理，防止单次请求过大。
    """

    def __init__(self, registry: ModelRegistry, batch_size: int = DEFAULT_BATCH_SIZE):
        self._registry = registry
        self._batch_size = batch_size

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
        """批量生成向量，自动分批。"""
        if not chunks:
            return []

        provider = self._registry.get_embedding_provider()
        if provider is None:
            raise RuntimeError("没有可用的 Embedding 供应商")
        model = self._registry.active_embedding_model

        all_embeddings: list[list[float]] = []
        for i in range(0, len(chunks), self._batch_size):
            batch = chunks[i : i + self._batch_size]
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
