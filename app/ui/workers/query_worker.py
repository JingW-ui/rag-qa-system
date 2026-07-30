# -*- coding: utf-8 -*-
"""
查询 Worker — embed → retrieve → generate（后台线程，支持流式）。
"""

from PySide6.QtCore import QThread, Signal

from app.core.rag_pipeline import RAGPipeline


class QueryWorker(QThread):
    """后台执行 RAG 查询（支持多知识库）。"""

    token_generated = Signal(str)          # 每个 token
    response_ready = Signal(str)           # 非流式：完整响应
    context_retrieved = Signal(list)       # 检索到的上下文（用于展示来源）
    finished = Signal(bool, str)           # (success, message)
    error = Signal(str)

    def __init__(
        self,
        collections: list[str],
        question: str,
        rag: RAGPipeline,
        top_k: int = 5,
        stream: bool = True,
        images: list[bytes] | None = None,
        extra_contexts: list[dict] | None = None,
        rerank_enabled: bool = False,
        rerank_candidate_multiplier: int = 3,
        parent=None,
    ):
        super().__init__(parent)
        self._collections = collections
        self._question = question
        self._rag = rag
        self._top_k = top_k
        self._stream = stream
        self._images = images
        self._extra_contexts = extra_contexts
        self._rerank_enabled = rerank_enabled
        self._rerank_candidate_multiplier = rerank_candidate_multiplier

    def run(self) -> None:
        try:
            if self._stream:
                gen, contexts = self._rag.query_multi_with_contexts(
                    self._collections,
                    self._question,
                    top_k=self._top_k,
                    stream=True,
                    images=self._images,
                    extra_contexts=self._extra_contexts,
                    rerank_enabled=self._rerank_enabled,
                    rerank_candidate_multiplier=self._rerank_candidate_multiplier,
                )
                self.context_retrieved.emit(contexts)
                for token in gen:
                    self.token_generated.emit(token)
                self.finished.emit(True, "")
            else:
                answer, contexts = self._rag.query_multi_with_contexts(
                    self._collections,
                    self._question,
                    top_k=self._top_k,
                    stream=False,
                    images=self._images,
                    extra_contexts=self._extra_contexts,
                    rerank_enabled=self._rerank_enabled,
                    rerank_candidate_multiplier=self._rerank_candidate_multiplier,
                )
                self.context_retrieved.emit(contexts)
                self.response_ready.emit(answer)
                self.finished.emit(True, "")

        except Exception as e:
            detail = str(e)
            # 尝试提取 API 返回的详细错误
            if hasattr(e, 'body') and e.body:
                try:
                    import json
                    body = json.loads(e.body) if isinstance(e.body, str) else e.body
                    detail = body.get('message', detail)
                except Exception:
                    pass
            self.error.emit(f"{detail}")
            self.finished.emit(False, str(e))
