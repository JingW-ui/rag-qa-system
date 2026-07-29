# -*- coding: utf-8 -*-
"""
RAG 管线编排 — 检索 + 生成。
"""

from typing import Iterator, Optional

from app.core.embedding_service import EmbeddingService
from app.core.vector_store import VectorStore
from app.core.model_registry import ModelRegistry
from app.providers.base import ChatMessage


SYSTEM_PROMPT = """你是一个有帮助的AI助手。请根据以下上下文回答用户的问题。
如果上下文没有足够的信息来回答问题，请如实说明，不要编造信息。
回答时尽量引用上下文中的具体内容。"""


class RAGPipeline:
    """编排完整的 RAG 流程：embed → retrieve → build prompt → generate。"""

    def __init__(
        self,
        registry: ModelRegistry,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self._registry = registry
        self._emb_svc = embedding_service
        self._vs = vector_store

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def query(
        self,
        collection_name: str,
        question: str,
        top_k: int = 5,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """单库查询（向后兼容）。"""
        return self.query_multi([collection_name], question, top_k, stream)

    def query_multi(
        self,
        collection_names: list[str],
        question: str,
        top_k: int = 5,
        stream: bool = False,
        images: list[bytes] | None = None,
    ) -> str | Iterator[str]:
        """
        跨多个知识库检索 + 生成。

        Args:
            collection_names: ChromaDB collection 名列表。
            question: 用户问题。
            top_k: 每个库检索片段数（合并后取 top_k）。
            stream: True 时返回 token 迭代器。
            images: 可选，图片字节列表（用于多模态 VLM）。
        """
        result, _contexts = self.query_multi_with_contexts(
            collection_names, question, top_k, stream, images
        )
        return result

    def query_multi_with_contexts(
        self,
        collection_names: list[str],
        question: str,
        top_k: int = 5,
        stream: bool = False,
        images: list[bytes] | None = None,
    ) -> tuple[str | Iterator[str], list[dict]]:
        """
        跨多个知识库检索 + 生成，同时返回检索到的上下文。

        Returns:
            (answer_or_stream, contexts) — contexts 为检索到的分块列表。
        """
        if not collection_names:
            fallback_msg = "没有关联的知识库，请先将知识库添加到对话。"
            if stream:
                return iter([fallback_msg]), []
            return fallback_msg, []

        # 1. 多库检索 + 合并去重 + 按距离排序
        query_vec = self._emb_svc.embed_query(question)
        all_results: list[dict] = []
        seen_ids: set[str] = set()
        for col in collection_names:
            results = self._vs.query(col, query_vec, top_k=top_k)
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

        all_results.sort(key=lambda r: r.get("distance", 999.0))
        all_results = all_results[:top_k]

        if not all_results:
            fallback_msg = "未在关联知识库中找到相关信息。"
            if stream:
                return iter([fallback_msg]), []
            return fallback_msg, []

        # 2. 构建 Prompt
        messages = self._build_messages(question, all_results, images)

        # 3. 生成 — 有图片时自动使用 vision 模型
        if images:
            provider, model = self._registry.get_vision_model()
            if provider is None:
                raise RuntimeError("已附加图片，但未配置视觉理解模型（如 qwen-vl-max）")
        else:
            provider = self._registry.get_chat_provider()
            if provider is None:
                raise RuntimeError("没有可用的对话供应商")
            model = self._registry.active_chat_model

        if stream:
            gen = provider.chat(messages=messages, model=model, stream=True)
            return gen, all_results
        else:
            answer = provider.chat(messages=messages, model=model, stream=False)
            return answer, all_results

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _build_messages(
        self, question: str, contexts: list[dict], images: list[bytes] | None = None
    ) -> list[ChatMessage]:
        """构建 RAG 消息列表。"""
        # 组装上下文
        context_parts: list[str] = []
        for i, ctx in enumerate(contexts, 1):
            filename = ctx.get("metadata", {}).get("filename", "未知文档")
            context_parts.append(f"[来源 {i}: {filename}]\n{ctx['text']}")

        context_text = "\n\n---\n\n".join(context_parts)

        system_content = f"{SYSTEM_PROMPT}\n\n以下是从知识库中检索到的相关上下文：\n\n{context_text}"

        return [
            ChatMessage(role="system", content=system_content),
            ChatMessage(role="user", content=question, images=images),
        ]

    def get_retrieved_contexts(
        self, collection_names: list[str], question: str, top_k: int = 5
    ) -> list[dict]:
        """多库检索（不生成），用于展示来源。"""
        query_vec = self._emb_svc.embed_query(question)
        all_results: list[dict] = []
        seen_ids: set[str] = set()
        for col in collection_names:
            for r in self._vs.query(col, query_vec, top_k=top_k):
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)
        all_results.sort(key=lambda r: r.get("distance", 999.0))
        return all_results[:top_k]
