# -*- coding: utf-8 -*-
"""
LLM 对话冒烟测试 — 配置全部从 config.json 读取（无硬编码 key）。

运行: python tests/llm_test.py
"""
import json
import sys
from pathlib import Path

from openai import OpenAI

# Windows 控制台默认 GBK,强制 UTF-8 输出避免中文乱码
sys.stdout.reconfigure(encoding="utf-8")

# 从 config.json 读取活跃 chat 供应商与模型
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

provider_id = cfg["active_providers"]["chat"]
model = cfg["active_models"]["chat"]
provider_cfg = next(p for p in cfg["model_providers"] if p["id"] == provider_id)

client = OpenAI(api_key=provider_cfg["api_key"], base_url=provider_cfg["base_url"])

resp = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "你是一个有帮助的AI助手。"},
        {"role": "user", "content": "用一句话介绍什么是 RAG（检索增强生成）。"},
    ],
)
print(f"[LLM] model={resp.model}")
print("reply:", resp.choices[0].message.content)
