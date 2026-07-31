# -*- coding: utf-8 -*-
"""
Rerank 冒烟测试 — 配置全部从 config.json 读取（无硬编码 key）。

运行: python tests/re-rank_test.py
"""
import json
from pathlib import Path

from openai import OpenAI

# 从 config.json 读取活跃 rerank 供应商与模型
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

active_rerank_provider_id = cfg["active_providers"]["rerank"]
rerank_model = cfg["active_models"]["rerank"]

provider_cfg = next(
    p for p in cfg["model_providers"] if p["id"] == active_rerank_provider_id
)

# 阿里云 MaaS 的 /reranks 端点位于 compatible-api 路径下
base_url = provider_cfg["base_url"].replace("/compatible-mode/", "/compatible-api/")
api_key = provider_cfg["api_key"]

client = OpenAI(api_key=api_key, base_url=base_url)

resp = client.post(
    "/reranks",
    body={
        "model": rerank_model,
        "query": "什么是文本排序模型",
        "documents": [
            "文本排序模型广泛用于搜索引擎和推荐系统中，它们根据文本相关性对候选文本进行排序",
            "量子计算是计算科学的一个前沿领域",
            "预训练语言模型的发展给文本排序模型带来了新的进展",
        ],
        "top_n": 2,
    },
    cast_to=object,
)
print(resp)
