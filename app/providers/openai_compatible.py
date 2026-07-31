# -*- coding: utf-8 -*-
"""
OpenAI 兼容供应商 — 统一 MaaS、Ollama 等所有 OpenAI-compatible API。
"""

from openai import OpenAI
from typing import Iterator

from .base import (
    BaseProvider,
    ChatProvider,
    EmbeddingProvider,
    RerankProvider,
    ProviderConfig,
    ChatMessage,
    EmbeddingResult,
    RerankResult,
)
from app.utils.image_utils import bytes_to_base64_url


class OpenAICompatibleProvider(BaseProvider, ChatProvider, EmbeddingProvider, RerankProvider):
    """
    使用 openai Python SDK 统一接入所有 OpenAI 兼容接口。
    MaaS (阿里云) 和 Ollama 均可使用该类。
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        # rerank 走 /reranks 端点，base_url 可能与 chat/embedding 不同，懒加载
        self._rerank_client: OpenAI | None = None

    # ------------------------------------------------------------------ #
    #  Chat
    # ------------------------------------------------------------------ #

    def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> str | Iterator[str]:
        # 将 ChatMessage 列表转为 API 格式（支持多模态）
        api_messages = [self._to_api_message(m) for m in messages]
        response = self._client.chat.completions.create(
            model=model,
            messages=api_messages,
            stream=stream,
            **kwargs,
        )
        if stream:
            return self._stream_generator(response)
        content = response.choices[0].message.content
        return content if content else ""

    def list_chat_models(self) -> list[str]:
        return [m.get("model_name", "") for m in self._config.chat_models]

    # ------------------------------------------------------------------ #
    #  Embedding
    # ------------------------------------------------------------------ #

    def embed(self, texts: list[str], model: str) -> EmbeddingResult:
        resp = self._client.embeddings.create(model=model, input=texts)
        embeddings = [d.embedding for d in resp.data]
        return EmbeddingResult(
            model=model,
            embeddings=embeddings,
            dimensions=len(embeddings[0]) if embeddings else 0,
        )

    def list_embedding_models(self) -> list[str]:
        return [m.get("model_name", "") for m in self._config.embedding_models]

    # ------------------------------------------------------------------ #
    #  Rerank
    # ------------------------------------------------------------------ #

    def rerank(
        self,
        query: str,
        documents: list[str],
        model: str,
        top_n: int | None = None,
    ) -> RerankResult:
        """调用阿里云 MaaS rerank 进行精排。

        走 OpenAI 兼容的 /reranks 端点（参考 tests/re-rank_test.py，已验证通过）。
        api_key / base_url 均从 config 读取，无需硬编码。
        """
        client = self._get_rerank_client()

        body: dict = {
            "model": model,
            "query": query,
            "documents": documents,
        }
        if top_n is not None:
            body["top_n"] = top_n

        # cast_to=object → 返回原始 JSON dict
        data = client.post("/reranks", body=body, cast_to=object)

        # 返回格式: {"results": [{"index": int, "relevance_score": float}, ...]}
        raw_results = data.get("results", []) if isinstance(data, dict) else []
        results = [
            (r["index"], r["relevance_score"])
            for r in sorted(
                raw_results,
                key=lambda x: x["relevance_score"],
                reverse=True,
            )
        ]
        return RerankResult(model=model, results=results)

    def _get_rerank_client(self) -> OpenAI:
        """rerank 专用 OpenAI 客户端，api_key/base_url 均取自 config。

        阿里云 MaaS 的 /reranks 端点位于 compatible-api 路径下；config 里
        chat/embedding 用的 base_url 通常是 compatible-mode，这里做替换。
        若 base_url 本身不是 compatible-mode，则原样使用。
        """
        if self._rerank_client is None:
            base = self._config.base_url.replace(
                "/compatible-mode/", "/compatible-api/"
            )
            self._rerank_client = OpenAI(
                api_key=self._config.api_key,
                base_url=base,
            )
        return self._rerank_client

    def list_rerank_models(self) -> list[str]:
        return [m.get("model_name", "") for m in self._config.rerank_models]

    # ------------------------------------------------------------------ #
    #  Connectivity
    # ------------------------------------------------------------------ #

    def validate_connection(self) -> bool:
        try:
            # 用 models.list() 轻量 ping（对 Ollama 也兼容）
            self._client.models.list()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _to_api_message(self, msg: ChatMessage) -> dict:
        """将 ChatMessage 转为 OpenAI API 格式（支持多模态）。"""
        if msg.images:
            # 多模态：content 是 list[dict]
            content_parts = []
            if msg.content:
                content_parts.append({"type": "text", "text": msg.content})
            for img_bytes in msg.images:
                url = bytes_to_base64_url(img_bytes)
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": url},
                })
            return {"role": msg.role, "content": content_parts}
        else:
            # 纯文本
            return {"role": msg.role, "content": msg.content}

    def _stream_generator(self, response) -> Iterator[str]:
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
