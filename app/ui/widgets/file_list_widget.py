# -*- coding: utf-8 -*-
"""
文档列表组件 — 显示知识库内的文档。
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from app.ui.theme import PANEL_BG
from app.ui.widgets.simple_menu import SimpleMenu


STATUS_ICONS = {
    "pending": "⏳",
    "processing": "🔄",
    "completed": "✅",
    "failed": "❌",
}


class FileListWidget(QListWidget):
    """文档列表，显示状态图标。"""

    doc_delete_requested = Signal(int)  # doc_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._docs: list[dict] = []
        # 设置统一背景色
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {PANEL_BG};
                border: none;
            }}
            QListWidget::item {{ padding: 4px 6px; border-radius: 2px; }}
            QListWidget::item:selected {{ background-color: #d6eaf8; color: #000; }}
        """)

    def refresh(self, docs: list[dict]) -> None:
        self._docs = docs
        self.clear()
        for doc in docs:
            icon = STATUS_ICONS.get(doc.get("status", "pending"), "❓")
            filename = doc.get("filename", "?")
            chunks = doc.get("chunk_count", 0)
            status = doc.get("status", "pending")
            text = f"{icon} {filename}  ({chunks} 块)"
            if status == "failed":
                text += f" — {doc.get('error_message', '未知错误')}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, doc["id"])
            item.setToolTip(f"类型: {doc.get('file_type', '?')}\n状态: {status}")
            self.addItem(item)

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if not item:
            return
        doc_id = item.data(Qt.UserRole)
        menu = SimpleMenu(self)
        delete_action = menu.addAction("删除文档")
        action = menu.exec(self.mapToGlobal(pos))
        if action == delete_action:
            self.doc_delete_requested.emit(doc_id)
