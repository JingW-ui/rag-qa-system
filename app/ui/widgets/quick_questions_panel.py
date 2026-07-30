# -*- coding: utf-8 -*-
"""
快捷提问面板 — 空对话时显示预设问题胶囊标签，点击直接发送。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy, QLayout, QPushButton
from PySide6.QtCore import Qt, Signal, QRect, QSize, QPoint
from PySide6.QtGui import QFont, QCursor

from app.ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SM,
    QUICK_CARD_TEXT_COLOR, QUICK_CARD_ICON_COLOR,
    QUICK_CARD_BG, QUICK_CARD_BG_HOVER, QUICK_CARD_BORDER,
    QUICK_CARD_BORDER_HOVER, QUICK_CARD_RADIUS,
)


# 内置快捷问题列表（去图标，纯文字）
DEFAULT_QUICK_QUESTIONS = [
    "总结知识库的核心内容",
    "列出所有主要主题",
    "有哪些常见问题？",
    "快速上手指南",
    "关键概念解释",
    "与其他模块的关系",
]


class FlowLayout(QLayout):
    """流式布局 — 自动换行。"""

    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self._item_list = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing if spacing >= 0 else 6)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            wid = item.sizeHint().width()
            next_x = x + wid + spacing
            if next_x - spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + spacing
                next_x = x + wid + spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + margins.bottom()


class QuickChip(QPushButton):
    """单个快捷提问胶囊 — 一行高度，点击发送问题。"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._text = text
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {QUICK_CARD_BG};
                color: {QUICK_CARD_TEXT_COLOR};
                border: 1px solid {QUICK_CARD_BORDER};
                border-radius: {QUICK_CARD_RADIUS}px;
                padding: 5px 14px;
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZE_SM}pt;
            }}
            QPushButton:hover {{
                background-color: {QUICK_CARD_BG_HOVER};
                border-color: {QUICK_CARD_BORDER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {QUICK_CARD_BORDER_HOVER};
                color: white;
            }}
        """)


class QuickQuestionsPanel(QWidget):
    """快捷提问面板 — 大标题 + 胶囊标签流式布局。"""

    question_selected = Signal(str)  # 用户点击胶囊时 emit 问题文本

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 30, 24, 10)
        layout.setSpacing(16)

        # 大标题
        title = QLabel("👋 你好，我能帮你什么？")
        title.setFont(QFont(FONT_FAMILY, 16, QFont.Bold))
        title.setStyleSheet(f"color: {QUICK_CARD_TEXT_COLOR};")
        layout.addWidget(title)

        # 卡片容器（流式布局）
        cards_container = QWidget()
        cards_container.setStyleSheet("background: transparent; border: none;")
        cards_layout = FlowLayout(cards_container, margin=0, spacing=8)

        for text in DEFAULT_QUICK_QUESTIONS:
            chip = QuickChip(text)
            chip.clicked.connect(lambda checked, t=text: self.question_selected.emit(t))
            cards_layout.addWidget(chip)

        layout.addWidget(cards_container)

        # 底部弹性
        layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

