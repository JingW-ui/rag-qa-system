# -*- coding: utf-8 -*-
"""
Embedding 向量化冒烟测试 — 配置全部从 config.json 读取（无硬编码 key）。

运行: python tests/embedding_test.py
"""
import json
import sys
from pathlib import Path

from openai import OpenAI

# Windows 控制台默认 GBK,强制 UTF-8 输出避免中文乱码
sys.stdout.reconfigure(encoding="utf-8")

# 从 config.json 读取活跃 embedding 供应商与模型
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

provider_id = cfg["active_providers"]["embedding"]
model = cfg["active_models"]["embedding"]
provider_cfg = next(p for p in cfg["model_providers"] if p["id"] == provider_id)

client = OpenAI(api_key=provider_cfg["api_key"], base_url=provider_cfg["base_url"])

texts = [
    "检索增强生成（RAG）通过外部知识库提升大模型回答质量",
    "文本向量化是把文本映射为高维稠密向量的过程",
]

resp = client.embeddings.create(model=model, input=texts)
print(f"[Embedding] model={resp.model} texts={len(texts)}")
for i, d in enumerate(resp.data):
    vec = d.embedding
    print(f"  text[{i}] index={d.index} dims={len(vec)} head={[round(v, 4) for v in vec[:4]]} ...")
