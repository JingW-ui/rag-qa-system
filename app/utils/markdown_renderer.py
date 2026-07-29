# -*- coding: utf-8 -*-
"""
Markdown → HTML 渲染器，用于聊天气泡显示。
"""

import re
import markdown
from markdown.extensions import fenced_code, tables, codehilite

from app.ui.theme import CODE_BG, CODE_FONT, PRE_BG, PRE_COLOR, PRE_RADIUS, FONT_SIZE_CODE


# 聊天气泡内使用的 CSS（内联在 <style> 中）
BUBBLE_CSS = f"""
<style>
body {{ margin: 0; padding: 0; font-size: 14px; line-height: 1.6; }}
code {{
    background-color: {CODE_BG};
    padding: 2px 5px;
    border-radius: 3px;
    font-family: {CODE_FONT};
    font-size: {FONT_SIZE_CODE}px;
}}
pre {{
    background-color: {PRE_BG};
    color: {PRE_COLOR};
    padding: 12px 16px;
    border-radius: {PRE_RADIUS}px;
    overflow-x: auto;
    font-family: {CODE_FONT};
    font-size: {FONT_SIZE_CODE}px;
    line-height: 1.5;
    margin: 8px 0;
}}
pre code {{
    background: none;
    padding: 0;
    color: inherit;
    font-size: inherit;
}}
table {{
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 13px;
}}
th, td {{
    border: 1px solid #d0d0d0;
    padding: 6px 12px;
    text-align: left;
}}
th {{
    background-color: #f5f5f5;
    font-weight: bold;
}}
blockquote {{
    border-left: 3px solid #4a90d9;
    padding-left: 12px;
    margin: 8px 0;
    color: #555;
}}
ul, ol {{ margin: 4px 0; padding-left: 24px; }}
li {{ margin: 2px 0; }}
h1, h2, h3, h4 {{ margin: 8px 0 4px; }}
h1 {{ font-size: 18px; }}
h2 {{ font-size: 16px; border-bottom: 1px solid #e0e0e0; }}
h3 {{ font-size: 15px; }}
h4 {{ font-size: 14px; }}
a {{ color: #4a90d9; }}
hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 12px 0; }}
p {{ margin: 2px 0 0 0; }}
strong {{ font-weight: bold; }}
em {{ font-style: italic; }}
</style>
"""


# Markdown 转换器（重用，避免重复创建）
_md_converter = markdown.Markdown(
    extensions=[
        "fenced_code",    # ``` 围栏代码块
        "tables",         # GFM 表格
        "codehilite",     # 代码高亮（需要 Pygments）
    ],
    extension_configs={
        "codehilite": {
            "css_class": "",
            "guess_lang": True,
        },
    },
)


def markdown_to_html(text: str, is_user: bool = False) -> str:
    """
    将 Markdown 文本转换为带内联 CSS 的 HTML。

    Args:
        text: Markdown 文本。
        is_user: 用户消息时简化样式。

    Returns:
        可直接用于 QLabel RichText 的 HTML 字符串。
    """
    if not text.strip():
        return ""

    # 预处理：修复没有空行分隔的列表
    text = _preprocess_markdown(text)

    # 重置转换器
    _md_converter.reset()

    # 转换 Markdown → HTML
    body = _md_converter.convert(text)

    # 用户消息用简单样式
    if is_user:
        css = BUBBLE_CSS
    else:
        css = BUBBLE_CSS

    return f"<html><head>{css}</head><body>{body}</body></html>"


def _preprocess_markdown(text: str) -> str:
    """预处理 Markdown，修复常见的格式问题。"""
    # 确保列表前有空行
    text = re.sub(r'([^\n])\n( *[-*+])', r'\1\n\n\2', text)
    text = re.sub(r'([^\n])\n( *\d+[.)])', r'\1\n\n\2', text)
    return text
