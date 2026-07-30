# -*- coding: utf-8 -*-
"""
模型供应商抽象接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class ProviderConfig:
    """供应商配置扁平结构，从 config.json 反序列化。"""
    id: str
    name: str
    provider_type: str
    base_url: str
    api_key: str
    enabled: bool
    chat_models: list[dict] = field(default_factory=list)
    embedding_models: list[dict] = field(default_factory=list)
    rerank_models: list[dict] = field(default_factory=list)
    embedding_batch_size: int = 10


@dataclass
class ChatMessage:
    role: str      # "user" | "assistant" | "system"
    content: str
    images: list[bytes] | None = None  # 多模态：图片字节数据列表（JPEG）


@dataclass
class EmbeddingResult:
    model: str
    embeddings: list[list[float]]
    dimensions: int


class BaseProvider(ABC):
    """任何供应商的最小身份。"""

    def __init__(self, config: ProviderConfig):
        self._config = config

    @property
    def provider_id(self) -> str:
        return self._config.id

    @property
    def provider_name(self) -> str:
        return self._config.name

    @abstractmethod
    def validate_connection(self) -> bool:
        """Ping 端点确认连通性，成功返回 True。"""
        ...


class ChatProvider(ABC):
    """能提供对话补全的供应商。"""

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> str | Iterator[str]:
        """
        - stream=False → 返回完整响应字符串
        - stream=True  → 返回 token 增量迭代器
        """
        ...

    @abstractmethod
    def list_chat_models(self) -> list[str]:
        ...


class EmbeddingProvider(ABC):
    """能提供文本 Embedding 的供应商。"""

    @abstractmethod
    def embed(self, texts: list[str], model: str) -> EmbeddingResult:
        ...

    @abstractmethod
    def list_embedding_models(self) -> list[str]:
        ...


@dataclass
class RerankResult:
    """重排结果：(原始索引, 相关性分数) 列表，按分数降序。"""
    model: str
    results: list[tuple[int, float]]  # [(original_index, relevance_score), ...]


class RerankProvider(ABC):
    """能对 (query, documents) 做精排打分的供应商。"""

    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: list[str],
        model: str,
        top_n: int | None = None,
    ) -> RerankResult:
        """
        Args:
            query: 用户问题。
            documents: 候选文档文本列表。
            model: 重排模型名。
            top_n: 返回前 N 个结果，None 则返回全部。

        Returns:
            RerankResult，results 按 relevance_score 降序排列。
        """
        ...

    @abstractmethod
    def list_rerank_models(self) -> list[str]:
        ...
