# -*- coding: utf-8 -*-
"""
知识库列表组件。
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal

from app.ui.widgets.simple_menu import SimpleMenu


class KbListWidget(QListWidget):
    """知识库列表，支持右键菜单。"""

    kb_selected = Signal(int)          # kb_id
    kb_delete_requested = Signal(int)  # kb_id
    kb_rename_requested = Signal(int, str)  # kb_id, current_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.currentRowChanged.connect(self._on_selection_changed)
        self._kb_data: list[dict] = []

    def refresh(self, kb_list: list[dict]) -> None:
        self._kb_data = kb_list
        self.clear()
        for kb in kb_list:
            name = kb.get("name", "?")
            doc_count = kb.get("doc_count", 0)
            item = QListWidgetItem(f"{name}  ({doc_count} 篇文档)")
            item.setData(Qt.UserRole, kb["id"])
            self.addItem(item)

    def _on_selection_changed(self, row: int) -> None:
        if 0 <= row < len(self._kb_data):
            self.kb_selected.emit(self._kb_data[row]["id"])

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if not item:
            return
        kb_id = item.data(Qt.UserRole)
        kb_name = item.text().split("  (")[0]

        menu = SimpleMenu(self)
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")

        action = menu.exec(self.mapToGlobal(pos))
        if action == rename_action:
            self.kb_rename_requested.emit(kb_id, kb_name)
        elif action == delete_action:
            self.kb_delete_requested.emit(kb_id)
