# -*- coding: utf-8 -*-
"""
RAG_H 主题模块 — 集中管理所有 UI 颜色、间距、尺寸，一处改全局生效。
"""

# ============================================================
#  全局背景
# ============================================================

# 统一浅灰背景（知识库、文档、聊天面板共用）
PANEL_BG = "#F0F0F0"

# 卡片/输入等元素背景（略白，与浅灰形成层次）
SURFACE_BG = "#FFFFFF"
SURFACE_BORDER = "#E5E5E5"


# ============================================================
#  聊天气泡
# ============================================================

# 聊天区背景 — 与知识库/文档面板统一的浅灰
CHAT_BG = "#F0F0F0"

# 用户气泡 — 比画布深一档的灰色，清晰可辨
USER_BUBBLE_BG = "#E8E8E8"

# AI 气泡 — 完全透明，Markdown 直接渲染
AI_BUBBLE_BG = "transparent"

# 用户气泡圆角 (px) — 小圆角胶囊
BUBBLE_RADIUS = 10

# 用户气泡内边距 — 紧凑
BUBBLE_PADDING_TOP = 6
BUBBLE_PADDING_BOTTOM = 6
BUBBLE_PADDING_H = 12

# AI 气泡内边距 — 无内边距，让 markdown 自由发挥
AI_BUBBLE_PADDING_TOP = 2
AI_BUBBLE_PADDING_BOTTOM = 2
AI_BUBBLE_PADDING_H = 4

# 气泡最大宽度 (px)
BUBBLE_MAX_WIDTH = 600

# 消息间距 (px) — 气泡之间的间距
MSG_SPACING = 10

# 消息容器外边距
MSG_MARGIN_H = 10
MSG_MARGIN_V = 6

# 阴影相关（保留兼容，实际不再使用）
SHADOW_RADIUS = 0
SHADOW_OFFSET = (0, 0)


# ============================================================
#  输入区
# ============================================================

INPUT_BG = "#FFFFFF"
INPUT_BORDER = "transparent"
INPUT_BORDER_FOCUS = "transparent"
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

TAG_BAR_BG = "#F0F0F0"
TAG_BAR_BORDER = "#E5E5E5"


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

def bubble_style(is_user: bool = False) -> str:
    """生成聊天气泡 QSS。

    - 用户气泡：浅灰背景 + 小圆角胶囊，无阴影
    - AI 气泡：完全透明，直接渲染在画布上
    """
    if is_user:
        return f"""
            #bubbleContent {{
                background-color: {USER_BUBBLE_BG};
                border: none;
                border-radius: {BUBBLE_RADIUS}px;
            }}
        """
    else:
        return """
            #bubbleContent {
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
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


# ============================================================
#  列表 / 分隔线
# ============================================================

# QListWidget 选中色（知识库/文档列表共用）
LIST_ITEM_SELECTED_BG = "#d6eaf8"
SEPARATOR_COLOR = "#d0d0d0"


def list_style() -> str:
    """统一 QListWidget QSS（知识库列表、文档列表共用）。

    取代 kb_panel / file_list_widget 中复制粘贴的内联样式。
    """
    return f"""
        QListWidget {{
            background-color: {PANEL_BG};
            border: none;
        }}
        QListWidget::item {{ padding: 4px 6px; border-radius: 2px; }}
        QListWidget::item:selected {{ background-color: {LIST_ITEM_SELECTED_BG}; color: #000; }}
    """


def separator_style() -> str:
    """水平分隔线 QSS（1px 灰线）。"""
    return f"background-color: {SEPARATOR_COLOR};"


# ============================================================
#  按钮
# ============================================================

BTN_COLOR = "#666666"
BTN_COLOR_HOVER = "#333333"
BTN_HOVER_BG = "rgba(0,0,0,0.06)"
BTN_PRESSED_BG = "rgba(0,0,0,0.10)"
BTN_DISABLED_COLOR = "#AAAAAA"
BTN_RADIUS = 6
BTN_PADDING_V = 5
BTN_PADDING_H = 10


def button_style() -> str:
    """统一文字按钮 QSS — 透明底、无边框、hover 浅灰,扁平低存在感。

    用于 SectionHeader 动作按钮与设置页等裸 QPushButton,取代原生 Windows 方按钮。
    聊天发送/附件按钮有内联样式,不受影响。
    """
    return f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            border-radius: {BTN_RADIUS}px;
            padding: {BTN_PADDING_V}px {BTN_PADDING_H}px;
            color: {BTN_COLOR};
        }}
        QPushButton:hover {{
            background-color: {BTN_HOVER_BG};
            color: {BTN_COLOR_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {BTN_PRESSED_BG};
        }}
        QPushButton:disabled {{
            color: {BTN_DISABLED_COLOR};
        }}
    """


# ============================================================
#  Tab / 表格 / 分组框
# ============================================================

TAB_COLOR = "#888888"
TAB_COLOR_HOVER = "#555555"
TAB_COLOR_SELECTED = "#2a7ab5"
TAB_INDICATOR = "#4a90d9"
TAB_HOVER_UNDERLINE = "#D0D0D0"

TABLE_BG = "#FFFFFF"
TABLE_RADIUS = 6
TABLE_ITEM_PADDING_V = 6
TABLE_ITEM_PADDING_H = 8
TABLE_HEADER_BG = "#F7F7F7"
TABLE_HEADER_COLOR = "#555555"

GROUPBOX_RADIUS = 6
GROUPBOX_TITLE_COLOR = "#666666"


def tab_style() -> str:
    """QTabWidget 扁平下划线指示器样式 — 取代原生大块灰 Tab。"""
    return f"""
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        QTabBar::tab {{
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 16px;
            margin: 0;
            color: {TAB_COLOR};
        }}
        QTabBar::tab:selected {{
            color: {TAB_COLOR_SELECTED};
            border-bottom: 2px solid {TAB_INDICATOR};
        }}
        QTabBar::tab:hover:!selected {{
            color: {TAB_COLOR_HOVER};
            border-bottom: 2px solid {TAB_HOVER_UNDERLINE};
        }}
    """


def table_style() -> str:
    """QTableWidget 扁平无网格样式 — 发丝边框、浅灰表头、选中浅蓝。

    配合 table.setShowGrid(False) + verticalHeader().setVisible(False) 使用。
    """
    return f"""
        QTableWidget {{
            background-color: {TABLE_BG};
            border: 1px solid {SURFACE_BORDER};
            border-radius: {TABLE_RADIUS}px;
            gridline-color: transparent;
            outline: none;
        }}
        QTableWidget::item {{
            padding: {TABLE_ITEM_PADDING_V}px {TABLE_ITEM_PADDING_H}px;
            border: none;
        }}
        QTableWidget::item:selected {{
            background-color: {LIST_ITEM_SELECTED_BG};
            color: #000;
        }}
        QHeaderView::section {{
            background-color: {TABLE_HEADER_BG};
            color: {TABLE_HEADER_COLOR};
            border: none;
            border-bottom: 1px solid {SURFACE_BORDER};
            padding: {TABLE_ITEM_PADDING_V}px {TABLE_ITEM_PADDING_H}px;
            font-weight: normal;
        }}
        QTableCornerButton::section {{
            background-color: {TABLE_HEADER_BG};
            border: none;
        }}
    """


def groupbox_style() -> str:
    """QGroupBox 柔化样式 — 发丝圆角边框 + 顶部标题,取代原生粗框。

    标题背景填 PANEL_BG 以"打断"顶部边框线,与页面浅灰底融合。
    """
    return f"""
        QGroupBox {{
            background: transparent;
            border: 1px solid {SURFACE_BORDER};
            border-radius: {GROUPBOX_RADIUS}px;
            margin-top: 12px;
            padding-top: 10px;
            font-weight: normal;
            color: {GROUPBOX_TITLE_COLOR};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 4px;
            background-color: {PANEL_BG};
            color: {GROUPBOX_TITLE_COLOR};
        }}
    """


# ============================================================
#  引用来源卡片
# ============================================================

SOURCE_CARD_BG = "transparent"
SOURCE_CARD_BORDER = "#E5E5E5"
SOURCE_CARD_RADIUS = 0
SOURCE_BTN_COLOR = "#888888"
SOURCE_SCORE_COLOR = "#7c8db5"
SOURCE_PREVIEW_COLOR = "#555555"
SOURCE_SEPARATOR_COLOR = "#E5E5E5"


def source_card_style() -> str:
    """分块卡片 QSS — 仅顶部细线分隔。"""
    return f"""
        QFrame {{
            background-color: transparent;
            border: none;
            border-top: 1px solid {SOURCE_CARD_BORDER};
            padding: 8px 0px;
        }}
    """


def source_btn_style() -> str:
    """引用来源按钮 QSS — 极简文字链接。"""
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {SOURCE_BTN_COLOR};
            border: none;
            padding: 4px 0px;
            text-align: left;
        }}
        QPushButton:hover {{
            color: #333333;
        }}
    """


# ============================================================
#  快捷提问卡片
# ============================================================

QUICK_CARD_BG = "#ffffff"
QUICK_CARD_BG_HOVER = "#f0f4f8"
QUICK_CARD_BORDER = "#e8e8e8"
QUICK_CARD_BORDER_HOVER = "#4a90d9"
QUICK_CARD_RADIUS = 12
QUICK_CARD_TEXT_COLOR = "#2c3e50"
QUICK_CARD_ICON_COLOR = "#4a90d9"


def quick_card_style() -> str:
    """快捷提问卡片 QSS。"""
    return f"""
        QFrame {{
            background-color: {QUICK_CARD_BG};
            border: 1px solid {QUICK_CARD_BORDER};
            border-radius: {QUICK_CARD_RADIUS}px;
            padding: 12px 16px;
        }}
        QFrame:hover {{
            background-color: {QUICK_CARD_BG_HOVER};
            border-color: {QUICK_CARD_BORDER_HOVER};
        }}
    """


# ============================================================
#  右键菜单
# ============================================================

MENU_BG = "#FFFFFF"
MENU_BORDER = "#E5E5E5"
MENU_RADIUS = 6
MENU_ITEM_HOVER = "#F0F0F0"
MENU_ITEM_PADDING = "6px 16px"
MENU_TEXT_COLOR = "#333333"


def menu_style() -> str:
    """统一右键菜单 QSS — 无阴影、灰色 hover、圆角。"""
    return f"""
        QMenu {{
            background-color: {MENU_BG};
            border: 1px solid {MENU_BORDER};
            border-radius: {MENU_RADIUS}px;
            padding: 4px 0px;
        }}
        QMenu::item {{
            padding: {MENU_ITEM_PADDING};
            color: {MENU_TEXT_COLOR};
            border-radius: 0px;
        }}
        QMenu::item:selected {{
            background-color: {MENU_ITEM_HOVER};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {MENU_BORDER};
            margin: 4px 0px;
        }}
    """
