# -*- coding: utf-8 -*-
"""
文本分块策略。
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    method: str = "recursive",
) -> list[str]:
    """
    将长文本切分为片段。

    Args:
        text: 原始文本。
        chunk_size: 每个 chunk 的目标字符数。
        chunk_overlap: chunk 之间的重叠字符数。
        method: 分块方法。
            - "recursive": 递归字符分块（推荐）
            - "fixed": 按固定长度滑动窗口

    Returns:
        文本片段列表。
    """
    if not text or not text.strip():
        return []

    if method in ("recursive", "sentence"):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
            length_function=len,
            is_separator_regex=False,
        )
        return splitter.split_text(text)

    elif method == "fixed":
        # 简单滑动窗口
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end].strip())
            start += chunk_size - chunk_overlap
        return [c for c in chunks if c]

    else:
        raise ValueError(f"不支持的分块方法: {method}")
