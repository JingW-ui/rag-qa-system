# -*- coding: utf-8 -*-
"""
模型注册中心 — 从配置加载供应商，提供工厂+路由。
"""

from app.providers.base import (
    BaseProvider,
    ChatProvider,
    EmbeddingProvider,
    RerankProvider,
    ProviderConfig,
)
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.ollama import OllamaProvider


PROVIDER_TYPE_MAP = {
    "openai_compatible": OpenAICompatibleProvider,
    "ollama": OllamaProvider,
}


class ModelRegistry:
    """管理中心：加载供应商、解析活跃模型、提供统一访问。"""

    def __init__(self, config_dict: dict):
        self._providers: dict[str, BaseProvider] = {}
        self._active_chat_provider_id: str = ""
        self._active_embedding_provider_id: str = ""
        self._active_vision_provider_id: str = ""
        self._active_rerank_provider_id: str = ""
        self._active_chat_model: str = ""
        self._active_embedding_model: str = ""
        self._active_vision_model: str = ""
        self._active_rerank_model: str = ""
        self._vision_models: list[tuple[str, str]] = []  # (provider_id, model_name)
        self._load_from_config(config_dict)

    # ------------------------------------------------------------------ #
    #  Initialization
    # ------------------------------------------------------------------ #

    def _load_from_config(self, config_dict: dict) -> None:
        """从 config.json 的完整字典构建注册中心。"""
        # 实例化供应商
        for p_dict in config_dict.get("model_providers", []):
            if not p_dict.get("enabled", True):
                continue
            provider_type = p_dict.get("provider_type", "")
            cls = PROVIDER_TYPE_MAP.get(provider_type)
            if cls is None:
                print(f"[WARN] 未知供应商类型 '{provider_type}'，跳过: {p_dict.get('id')}")
                continue

            provider_config = ProviderConfig(
                id=p_dict["id"],
                name=p_dict.get("name", p_dict["id"]),
                provider_type=provider_type,
                base_url=p_dict.get("base_url", ""),
                api_key=p_dict.get("api_key", ""),
                enabled=p_dict.get("enabled", True),
                chat_models=p_dict.get("chat_models", []),
                embedding_models=p_dict.get("embedding_models", []),
                rerank_models=p_dict.get("rerank_models", []),
                embedding_batch_size=p_dict.get("embedding_batch_size", 10),
            )
            self._providers[provider_config.id] = cls(provider_config)
            # 收集 vision 模型
            for m in provider_config.chat_models:
                if m.get("is_vision"):
                    self._vision_models.append((provider_config.id, m["model_name"]))

        # 设置活跃项
        ap = config_dict.get("active_providers", {})
        am = config_dict.get("active_models", {})
        self._active_chat_provider_id = ap.get("chat", "")
        self._active_embedding_provider_id = ap.get("embedding", "")
        self._active_vision_provider_id = ap.get("vision", "")
        self._active_rerank_provider_id = ap.get("rerank", "")
        self._active_chat_model = am.get("chat", "")
        self._active_embedding_model = am.get("embedding", "")
        self._active_vision_model = am.get("vision", "")
        self._active_rerank_model = am.get("rerank", "")

    def reload_config(self, config_dict: dict) -> None:
        """热重载（设置面板保存后调用）。"""
        self._providers.clear()
        self._vision_models.clear()
        self._load_from_config(config_dict)

    # ------------------------------------------------------------------ #
    #  Provider access
    # ------------------------------------------------------------------ #

    def get_chat_provider(self) -> ChatProvider | None:
        """返回当前活跃的对话供应商。"""
        p = self._providers.get(self._active_chat_provider_id)
        if p is None:
            return None
        if not isinstance(p, ChatProvider):
            return None
        return p

    def get_embedding_provider(self) -> EmbeddingProvider | None:
        """返回当前活跃的 Embedding 供应商。"""
        p = self._providers.get(self._active_embedding_provider_id)
        if p is None:
            return None
        if not isinstance(p, EmbeddingProvider):
            return None
        return p

    def get_rerank_provider(self) -> RerankProvider | None:
        """返回当前活跃的 Rerank 供应商。"""
        p = self._providers.get(self._active_rerank_provider_id)
        if p is None:
            return None
        if not isinstance(p, RerankProvider):
            return None
        return p

    def get_provider(self, provider_id: str) -> BaseProvider | None:
        return self._providers.get(provider_id)

    def list_all_providers(self) -> list[BaseProvider]:
        return list(self._providers.values())

    # ------------------------------------------------------------------ #
    #  Active model info
    # ------------------------------------------------------------------ #

    @property
    def active_chat_model(self) -> str:
        return self._active_chat_model

    @property
    def active_embedding_model(self) -> str:
        return self._active_embedding_model

    @property
    def active_chat_provider_id(self) -> str:
        return self._active_chat_provider_id

    @property
    def active_embedding_provider_id(self) -> str:
        return self._active_embedding_provider_id

    def set_active_chat(self, provider_id: str, model_name: str) -> None:
        self._active_chat_provider_id = provider_id
        self._active_chat_model = model_name

    def set_active_embedding(self, provider_id: str, model_name: str) -> None:
        self._active_embedding_provider_id = provider_id
        self._active_embedding_model = model_name

    def set_active_vision(self, provider_id: str, model_name: str) -> None:
        self._active_vision_provider_id = provider_id
        self._active_vision_model = model_name

    @property
    def active_vision_model(self) -> str:
        return self._active_vision_model

    @property
    def active_vision_provider_id(self) -> str:
        return self._active_vision_provider_id

    @property
    def active_rerank_model(self) -> str:
        return self._active_rerank_model

    @property
    def active_rerank_provider_id(self) -> str:
        return self._active_rerank_provider_id

    def set_active_rerank(self, provider_id: str, model_name: str) -> None:
        self._active_rerank_provider_id = provider_id
        self._active_rerank_model = model_name

    # ------------------------------------------------------------------ #
    #  Vision model support
    # ------------------------------------------------------------------ #

    def get_vision_model(self) -> tuple[ChatProvider | None, str]:
        """返回可用的 vision 模型 (provider, model_name)。

        优先返回用户配置的活跃视觉模型，如果没有则回退到第一个标记 is_vision 的模型。
        用于自动切换：当用户上传图片时，自动使用 vision 模型而非当前 chat 模型。
        """
        # 优先使用配置的活跃视觉模型
        if self._active_vision_provider_id and self._active_vision_model:
            p = self._providers.get(self._active_vision_provider_id)
            if p is not None and isinstance(p, ChatProvider):
                return p, self._active_vision_model

        # 回退：使用第一个标记 is_vision 的模型
        if not self._vision_models:
            return None, ""
        provider_id, model_name = self._vision_models[0]
        p = self._providers.get(provider_id)
        if p is None or not isinstance(p, ChatProvider):
            return None, ""
        return p, model_name

    @property
    def has_vision_model(self) -> bool:
        """是否配置了 vision 模型。"""
        return len(self._vision_models) > 0
