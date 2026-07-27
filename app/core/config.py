# -*- coding: utf-8 -*-
"""
RAG 问答系统 — 配置管理器
从 config.json 加载配置，支持保存和校验。
"""

import json
import os
import copy
from typing import Any, Optional


class ConfigManager:
    """加载、校验、保存 JSON 配置。"""

    REQUIRED_TOP_KEYS = {"version", "app", "model_providers", "active_providers", "active_models"}
    REQUIRED_APP_KEYS = {"chunk_size", "chunk_overlap", "chunk_method", "top_k_retrieval", "data_dir", "log_level"}
    REQUIRED_PROVIDER_KEYS = {"id", "name", "provider_type", "base_url", "api_key", "chat_models", "embedding_models", "enabled"}

    def __init__(self, config_path: str = "config.json", default_path: Optional[str] = None):
        self._config_path = os.path.abspath(config_path)
        self._default_path = os.path.abspath(default_path) if default_path else None
        self._data: dict = {}
        self.load()

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def load(self) -> dict:
        """加载配置。如果 config.json 不存在，从 config.default.json 复制。"""
        if not os.path.exists(self._config_path):
            if self._default_path and os.path.exists(self._default_path):
                self._copy_default()
            else:
                raise FileNotFoundError(
                    f"配置文件不存在: {self._config_path}，且未找到默认模板。"
                )

        with open(self._config_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        self._resolve_env_vars(self._data)
        self._validate()
        return self._data

    def save(self, data: Optional[dict] = None) -> None:
        """保存配置到文件。"""
        if data is not None:
            self._data = data
        self._validate()
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def reload(self) -> dict:
        """重新加载配置（如设置面板修改后）。"""
        return self.load()

    # ------------------------------------------------------------------ #
    #  Access helpers
    # ------------------------------------------------------------------ #

    @property
    def data(self) -> dict:
        return copy.deepcopy(self._data)

    @property
    def app_settings(self) -> dict:
        return copy.deepcopy(self._data.get("app", {}))

    @property
    def providers(self) -> list[dict]:
        return copy.deepcopy(self._data.get("model_providers", []))

    @property
    def active_providers(self) -> dict:
        return copy.deepcopy(self._data.get("active_providers", {}))

    @property
    def active_models(self) -> dict:
        return copy.deepcopy(self._data.get("active_models", {}))

    def get_provider(self, provider_id: str) -> Optional[dict]:
        """按 ID 取某个供应商配置。"""
        for p in self._data.get("model_providers", []):
            if p.get("id") == provider_id:
                return copy.deepcopy(p)
        return None

    def get_active_chat_provider(self) -> Optional[dict]:
        return self.get_provider(self._data.get("active_providers", {}).get("chat", ""))

    def get_active_embedding_provider(self) -> Optional[dict]:
        return self.get_provider(self._data.get("active_providers", {}).get("embedding", ""))

    def get_active_chat_model(self) -> str:
        return self._data.get("active_models", {}).get("chat", "")

    def get_active_embedding_model(self) -> str:
        return self._data.get("active_models", {}).get("embedding", "")

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _copy_default(self) -> None:
        """从默认模板复制配置。"""
        os.makedirs(os.path.dirname(self._config_path) or ".", exist_ok=True)
        with open(self._default_path, "r", encoding="utf-8") as src:
            with open(self._config_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())

    def _resolve_env_vars(self, obj: Any) -> None:
        """递归解析 ${ENV_VAR} 占位符（原地修改）。"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    env_var = v[2:-1]
                    obj[k] = os.environ.get(env_var, "")
                else:
                    self._resolve_env_vars(v)
        elif isinstance(obj, list):
            for item in obj:
                self._resolve_env_vars(item)

    def _validate(self) -> None:
        """基本校验，缺失关键字段时抛出 ValueError。"""
        missing = self.REQUIRED_TOP_KEYS - set(self._data.keys())
        if missing:
            raise ValueError(f"config.json 缺少顶层字段: {missing}")

        app = self._data.get("app", {})
        missing_app = self.REQUIRED_APP_KEYS - set(app.keys())
        if missing_app:
            raise ValueError(f"config.json [app] 缺少字段: {missing_app}")

        providers = self._data.get("model_providers", [])
        if not providers:
            raise ValueError("config.json model_providers 不能为空")

        for idx, p in enumerate(providers):
            missing_p = self.REQUIRED_PROVIDER_KEYS - set(p.keys())
            if missing_p:
                raise ValueError(f"config.json model_providers[{idx}] ({p.get('id', '?')}) 缺少字段: {missing_p}")
