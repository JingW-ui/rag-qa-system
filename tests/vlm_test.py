# -*- coding: utf-8 -*-
"""
VLM 视觉理解冒烟测试 — 配置全部从 config.json 读取（无硬编码 key）。
测试图片: assets/banner.jpg

运行: python tests/vlm_test.py
"""
import base64
import json
import sys
from pathlib import Path

from openai import OpenAI

# Windows 控制台默认 GBK,强制 UTF-8 输出避免中文乱码
sys.stdout.reconfigure(encoding="utf-8")

# 从 config.json 读取活跃 vision 供应商与模型
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

provider_id = cfg["active_providers"]["vision"]
model = cfg["active_models"]["vision"]
provider_cfg = next(p for p in cfg["model_providers"] if p["id"] == provider_id)

# 测试图片
IMG_PATH = Path(__file__).resolve().parent.parent / "assets" / "banner.jpg"
img_b64 = base64.b64encode(IMG_PATH.read_bytes()).decode()
img_url = f"data:image/jpeg;base64,{img_b64}"

client = OpenAI(api_key=provider_cfg["api_key"], base_url=provider_cfg["base_url"])

resp = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请描述这张图片的内容。"},
                {"type": "image_url", "image_url": {"url": img_url}},
            ],
        }
    ],
)
print(f"[VLM] model={resp.model}")
print("reply:", resp.choices[0].message.content)
