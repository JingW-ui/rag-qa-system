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
        extra_contexts: list[dict] | None = None,
    ) -> str | Iterator[str]:
        """
        跨多个知识库检索 + 生成。

        Args:
            collection_names: ChromaDB collection 名列表。
            question: 用户问题。
            top_k: 每个库检索片段数（合并后取 top_k）。
            stream: True 时返回 token 迭代器。
            images: 可选，图片字节列表（用于多模态 VLM）。
            extra_contexts: 可选，额外文件上下文列表 [{filename, text}]。
        """
        result, _contexts, _rerank_info = self.query_multi_with_contexts(
            collection_names, question, top_k, stream, images, extra_contexts
        )
        return result

    def query_multi_with_contexts(
        self,
        collection_names: list[str],
        question: str,
        top_k: int = 5,
        stream: bool = False,
        images: list[bytes] | None = None,
        extra_contexts: list[dict] | None = None,
        rerank_enabled: bool = False,
        rerank_candidate_multiplier: int = 3,
    ) -> tuple[str | Iterator[str], list[dict], dict]:
        """
        跨多个知识库检索 + 生成，同时返回检索到的上下文。

        Returns:
            (answer_or_stream, contexts, rerank_info) —
            contexts 为检索到的分块列表；rerank_info 描述本次重排情况。
        """
        if not collection_names:
            fallback_msg = "没有关联的知识库，请先将知识库添加到对话。"
            if stream:
                return iter([fallback_msg]), [], {}
            return fallback_msg, [], {}

        # 1. 多库检索 + 合并去重
        # 如果启用重排，多召回一些候选
        retrieval_k = top_k * rerank_candidate_multiplier if rerank_enabled else top_k
        query_vec = self._emb_svc.embed_query(question)
        all_results: list[dict] = []
        seen_ids: set[str] = set()
        for col in collection_names:
            results = self._vs.query(col, query_vec, top_k=retrieval_k)
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

        all_results.sort(key=lambda r: r.get("distance", 999.0))

        if not all_results:
            fallback_msg = "未在关联知识库中找到相关信息。"
            if stream:
                return iter([fallback_msg]), [], {}
            return fallback_msg, [], {}

        # 2. 重排（如果启用）
        rerank_info: dict = {"enabled": rerank_enabled}
        if rerank_enabled:
            all_results, rerank_info = self._rerank_results(
                question, all_results, top_k
            )

        all_results = all_results[:top_k]

        # 3. 构建 Prompt
        messages = self._build_messages(question, all_results, images, extra_contexts)

        # 4. 生成 — 有图片时自动使用 vision 模型
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
            return gen, all_results, rerank_info
        else:
            answer = provider.chat(messages=messages, model=model, stream=False)
            return answer, all_results, rerank_info

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _rerank_results(
        self, question: str, candidates: list[dict], top_n: int
    ) -> tuple[list[dict], dict]:
        """调用 Rerank 模型对候选结果重排。

        返回 (重排后的列表, rerank_info)。rerank_info 描述本次重排情况，
        供 UI 展示日志。API 失败时静默回退到原始排序。
        """
        info: dict = {
            "enabled": True,
            "ran": False,
            "model": None,
            "candidates": len(candidates),
            "returned": len(candidates),
            "top_n": top_n,
            "fallback": False,
            "error": None,
        }

        rerank_provider = self._registry.get_rerank_provider()
        if rerank_provider is None:
            info["fallback"] = True
            info["error"] = "无可用重排供应商"
            return candidates, info

        rerank_model = self._registry.active_rerank_model
        if not rerank_model:
            info["fallback"] = True
            info["error"] = "未配置重排模型"
            return candidates, info

        info["model"] = rerank_model

        try:
            documents = [c.get("text", "") for c in candidates]
            result = rerank_provider.rerank(
                query=question,
                documents=documents,
                model=rerank_model,
                top_n=top_n,
            )

            # 按重排分数重新排列
            reranked: list[dict] = []
            for idx, score in result.results:
                if 0 <= idx < len(candidates):
                    item = candidates[idx].copy()
                    item["rerank_score"] = score
                    reranked.append(item)

            # 如果重排返回的结果少于 top_n，补充原始结果
            if len(reranked) < top_n:
                used_ids = {r["id"] for r in reranked}
                for c in candidates:
                    if c["id"] not in used_ids:
                        reranked.append(c)
                        if len(reranked) >= top_n:
                            break

            info["ran"] = True
            info["returned"] = len(reranked)
            return reranked, info

        except Exception as e:
            # 静默回退
            print(f"[WARN] Rerank 失败，回退到向量排序: {e}")
            info["fallback"] = True
            info["error"] = str(e)
            return candidates, info

    def _build_messages(
        self,
        question: str,
        contexts: list[dict],
        images: list[bytes] | None = None,
        extra_contexts: list[dict] | None = None,
    ) -> list[ChatMessage]:
        """构建 RAG 消息列表。"""
        # 组装知识库上下文
        context_parts: list[str] = []
        for i, ctx in enumerate(contexts, 1):
            filename = ctx.get("metadata", {}).get("filename", "未知文档")
            context_parts.append(f"[来源 {i}: {filename}]\n{ctx['text']}")

        context_text = "\n\n---\n\n".join(context_parts)
        system_content = f"{SYSTEM_PROMPT}\n\n以下是从知识库中检索到的相关上下文：\n\n{context_text}"

        # 组装用户上传的文件上下文
        if extra_contexts:
            file_parts: list[str] = []
            for fc in extra_contexts:
                filename = fc.get("filename", "未知文件")
                text = fc.get("text", "")
                # 截断过长的文件内容（防止超出 token 限制）
                if len(text) > 8000:
                    text = text[:8000] + "\n...(内容已截断)"
                file_parts.append(f"[文件: {filename}]\n{text}")
            file_text = "\n\n---\n\n".join(file_parts)
            system_content += f"\n\n以下是用户上传的参考文档：\n\n{file_text}"

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
