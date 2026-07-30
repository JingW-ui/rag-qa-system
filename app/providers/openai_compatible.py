# -*- coding: utf-8 -*-
"""
OpenAI 兼容供应商 — 统一 MaaS、Ollama 等所有 OpenAI-compatible API。
"""

import requests
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
        """调用阿里云 gte-rerank API 进行精排。

        阿里云 rerank 使用独立 endpoint，不走 OpenAI SDK。
        """
        # 从 base_url 推断 rerank endpoint
        # base_url 通常是 https://xxx/compatible-mode/v1
        base = self._config.base_url.rstrip("/")
        if base.endswith("/v1"):
            rerank_url = base[:-3] + "/services/rerank/text-rerank/text-rerank"
        elif base.endswith("/compatible-mode"):
            rerank_url = base + "/v1/services/rerank/text-rerank/text-rerank"
        else:
            rerank_url = base + "/services/rerank/text-rerank/text-rerank"

        payload = {
            "model": model,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "return_documents": False,
            },
        }
        if top_n is not None:
            payload["parameters"]["top_n"] = top_n

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(rerank_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # 解析结果：阿里云返回 {"output": {"results": [{"index": int, "relevance_score": float}, ...]}}
        output = data.get("output", {})
        raw_results = output.get("results", [])

        results = [
            (r["index"], r["relevance_score"])
            for r in sorted(raw_results, key=lambda x: x["relevance_score"], reverse=True)
        ]

        return RerankResult(model=model, results=results)

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
