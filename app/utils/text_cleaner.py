# -*- coding: utf-8 -*-
"""
文本清洗工具 — Unicode 规范化、空白清理。
"""

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    清洗文本：
    - Unicode 规范化 (NFKC)
    - 合并连续空白
    - 去除首尾空白
    - 去除零宽字符
    """
    if not text:
        return ""

    # Unicode 规范化
    text = unicodedata.normalize("NFKC", text)

    # 去除零宽字符
    text = re.sub(r"[​‌‍‎‏﻿]", "", text)

    # 将各种空白符统一为普通空格
    text = re.sub(r"[\t\r\n\v\f]+", "\n", text)

    # 合并连续的空行（最多保留一个空行）
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 每行内部合并多余空白
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[^\S\n]+", " ", line).strip()
        lines.append(line)

    return "\n".join(lines).strip()
