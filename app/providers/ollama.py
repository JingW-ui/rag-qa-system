# -*- coding: utf-8 -*-
"""
Ollama 本地模型供应商 — OpenAI 兼容接口，直接继承。
"""

from .openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """
    Ollama 完全兼容 OpenAI API 格式，无需重写。
    保留此类便于后续扩展 Ollama 特有功能（如 pull model、list local models 等）。
    """
    pass
