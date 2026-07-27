# -*- coding: utf-8 -*-
"""
文档处理器 — 按文件类型解析 + 分块编排。
"""

import os
from typing import Optional

from app.utils.chunker import chunk_text
from app.utils.text_cleaner import clean_text


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".markdown"}


class DocumentProcessor:
    """解析 PDF/DOCX/MD/TXT，返回纯文本，支持分块。"""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        chunk_method: str = "recursive",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_method = chunk_method

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def parse(self, file_path: str) -> str:
        """
        根据扩展名分发解析。

        Returns:
            清洗后的纯文本。
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}，支持: {SUPPORTED_EXTENSIONS}")

        if ext == ".pdf":
            raw = self._parse_pdf(file_path)
        elif ext in (".docx",):
            raw = self._parse_docx(file_path)
        elif ext in (".md", ".markdown", ".txt"):
            raw = self._parse_text(file_path)
        else:
            raise ValueError(f"未实现的解析器: {ext}")

        return clean_text(raw)

    def parse_and_chunk(self, file_path: str) -> tuple[str, list[str]]:
        """一步完成解析 + 分块。

        Returns:
            (全文, 分块列表)
        """
        full_text = self.parse(file_path)
        chunks = self.chunk(full_text)
        return full_text, chunks

    def chunk(self, text: str) -> list[str]:
        """对文本分块。"""
        return chunk_text(
            text,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            method=self.chunk_method,
        )

    # ------------------------------------------------------------------ #
    #  Internal parsers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        import fitz  # PyMuPDF (lazy import 避免启动加载)

        doc = fitz.open(file_path)
        parts: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text:
                parts.append(text)
        doc.close()
        return "\n\n".join(parts)

    @staticmethod
    def _parse_docx(file_path: str) -> str:
        from docx import Document

        doc = Document(file_path)
        parts: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text.strip())

        # 也提取表格内容
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        return "\n".join(parts)

    @staticmethod
    def _parse_text(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
