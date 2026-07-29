# -*- coding: utf-8 -*-
"""
RAG_H 主题模块 — 集中管理所有 UI 颜色、间距、尺寸，一处改全局生效。
"""

# ============================================================
#  聊天气泡
# ============================================================

# 聊天区背景
CHAT_BG = "#f0f2f5"

# 用户气泡
USER_BUBBLE_BG = "#d6eaf8"

# AI 气泡
AI_BUBBLE_BG = "#ffffff"

# 气泡圆角 (px) — A1: 加大圆角更现代
BUBBLE_RADIUS = 18

# 气泡内边距 — 足够留白才有呼吸感
BUBBLE_PADDING_TOP = 14
BUBBLE_PADDING_BOTTOM = 10
BUBBLE_PADDING_H = 18

# 气泡最大宽度 (px) — B1: 防止气泡占满整行
BUBBLE_MAX_WIDTH = 600

# 消息间距 (px) — 气泡之间的间距
MSG_SPACING = 6

# 消息容器外边距
MSG_MARGIN_H = 10
MSG_MARGIN_V = 6

# shadow 效果参数
SHADOW_RADIUS = 8
SHADOW_OFFSET = (1, 2)


# ============================================================
#  输入区
# ============================================================

INPUT_BG = "#ffffff"
INPUT_BORDER = "#d0d0d0"
INPUT_BORDER_FOCUS = "#4a90d9"
INPUT_RADIUS = 12

SEND_BTN_BG = "#4a90d9"
SEND_BTN_BG_HOVER = "#357abd"
SEND_BTN_BG_DISABLED = "#c0c0c0"
SEND_BTN_COLOR = "#ffffff"
SEND_BTN_SIZE = 32


# ============================================================
#  知识库标签
# ============================================================

TAG_BG = "#e8f4fd"
TAG_COLOR = "#2a7ab5"
TAG_BORDER = "#b8d8f0"
TAG_RADIUS = 10

TAG_BAR_BG = "#fafafa"
TAG_BAR_BORDER = "#e8e8e8"


# ============================================================
#  字体
# ============================================================

FONT_FAMILY = "Microsoft YaHei"
FONT_SIZE_SM = 9
FONT_SIZE_NORMAL = 10
FONT_SIZE_CODE = 12


# ============================================================
#  Markdown 代码块
# ============================================================

CODE_BG = "rgba(0,0,0,0.06)"
CODE_FONT = "'Consolas', 'Courier New', monospace"
PRE_BG = "#1e1e1e"
PRE_COLOR = "#d4d4d4"
PRE_RADIUS = 8


# ============================================================
#  QSS 生成辅助
# ============================================================

def bubble_style(bg: str) -> str:
    """生成聊天气泡 QSS — A1: 去边框、纯色背景、大圆角。"""
    return f"""
        #bubbleContent {{
            background-color: {bg};
            border: none;
            border-radius: {BUBBLE_RADIUS}px;
        }}
    """


def tag_style() -> str:
    """知识库标签 QSS。"""
    return f"""
        QLabel {{
            background-color: {TAG_BG};
            color: {TAG_COLOR};
            border: 1px solid {TAG_BORDER};
            border-radius: {TAG_RADIUS}px;
            padding: 3px 10px;
        }}
    """
