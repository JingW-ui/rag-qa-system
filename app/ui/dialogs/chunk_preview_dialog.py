# -*- coding: utf-8 -*-
"""
分块预览编辑对话框 — 上传文档前预览/调整/编辑分块结果。
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QListWidget, QListWidgetItem, QPlainTextEdit,
    QSpinBox, QComboBox, QPushButton, QLabel, QSplitter,
    QMessageBox, QDialogButtonBox, QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.core.document_processor import DocumentProcessor

CHUNK_METHODS = ["recursive", "fixed"]


class ChunkPreviewDialog(QDialog):
    """分块预览与编辑对话框 — 模态。

    在确认入库前预览分块结果，支持：
      - 调整分块参数并重新分块
      - 编辑单个 chunk 文本
      - 合并相邻 chunk
      - 在光标处拆分 chunk
      - 删除 chunk
    """

    def __init__(
        self,
        file_path: str,
        proc: DocumentProcessor,
        parent=None,
    ):
        super().__init__(parent)
        self._file_path = file_path
        self._proc = proc
        self._full_text: str = ""
        self._chunks: list[str] = []
        self._current_index: int = -1
        self._edited: bool = False  # 是否手动编辑过（避免重新分块时误覆盖）

        self.setWindowTitle(f"分块预览 — {os.path.basename(file_path)}")
        self.resize(900, 600)
        self.setMinimumSize(700, 450)

        self._setup_ui()
        self._parse_and_chunk()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ---- 0. 文件信息 ----
        info = QLabel(f"<b>文件:</b> {os.path.basename(self._file_path)}"
                      f"&nbsp;&nbsp;&nbsp;<span style='color:#888'>{os.path.dirname(self._file_path)}</span>")
        info.setFont(QFont("Microsoft YaHei", 9))
        layout.addWidget(info)

        # ---- 1. 参数面板 ----
        param_group = QGroupBox("分块参数")
        param_form = QFormLayout(param_group)

        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(100, 8000)
        self._chunk_size.setSingleStep(100)
        self._chunk_size.setValue(self._proc.chunk_size)
        param_form.addRow("分块大小 (字符):", self._chunk_size)

        self._chunk_overlap = QSpinBox()
        self._chunk_overlap.setRange(0, 1000)
        self._chunk_overlap.setSingleStep(20)
        self._chunk_overlap.setValue(self._proc.chunk_overlap)
        param_form.addRow("分块重叠 (字符):", self._chunk_overlap)

        method_row = QHBoxLayout()
        self._chunk_method = QComboBox()
        self._chunk_method.addItems(CHUNK_METHODS)
        idx = self._chunk_method.findText(self._proc.chunk_method)
        if idx >= 0:
            self._chunk_method.setCurrentIndex(idx)
        method_row.addWidget(self._chunk_method)
        method_row.addStretch()
        btn_rechunk = QPushButton("🔄 重新分块")
        btn_rechunk.setToolTip("用当前参数重新分块，会覆盖手动编辑")
        btn_rechunk.clicked.connect(self._rechunk)
        method_row.addWidget(btn_rechunk)
        param_form.addRow("分块方法:", method_row)

        layout.addWidget(param_group)

        # ---- 2. 主区域：左列表 + 右编辑 ----
        splitter = QSplitter(Qt.Horizontal)

        # 左侧 — chunk 列表
        left_widget = QGroupBox("分块列表")
        left_layout = QVBoxLayout(left_widget)
        self._chunk_list = QListWidget()
        self._chunk_list.currentRowChanged.connect(self._on_chunk_selected)
        self._chunk_count_label = QLabel("共 0 块")
        self._chunk_count_label.setFont(QFont("Microsoft YaHei", 9))
        self._chunk_count_label.setStyleSheet("color: #888;")
        left_layout.addWidget(self._chunk_list, 1)
        left_layout.addWidget(self._chunk_count_label)
        splitter.addWidget(left_widget)

        # 右侧 — 编辑区域
        right_widget = QGroupBox("编辑块内容")
        right_layout = QVBoxLayout(right_widget)
        self._chunk_editor = QPlainTextEdit()
        self._chunk_editor.setFont(QFont("Microsoft YaHei", 10))
        self._chunk_editor.setPlaceholderText("← 请从左侧选择一个分块进行编辑")
        self._chunk_editor.textChanged.connect(self._on_text_changed)
        right_layout.addWidget(self._chunk_editor, 1)

        # 操作按钮行
        btn_row = QHBoxLayout()
        self._btn_merge = QPushButton("⬆ 合并到上一块")
        self._btn_merge.setToolTip("将当前块内容拼接到上一块末尾，然后删除当前块")
        self._btn_merge.clicked.connect(self._merge_with_prev)
        self._btn_merge.setEnabled(False)
        btn_row.addWidget(self._btn_merge)

        self._btn_split = QPushButton("✂ 在光标处拆分")
        self._btn_split.setToolTip("在编辑区光标位置将当前块一分为二")
        self._btn_split.clicked.connect(self._split_at_cursor)
        self._btn_split.setEnabled(False)
        btn_row.addWidget(self._btn_split)

        self._btn_delete = QPushButton("🗑 删除当前块")
        self._btn_delete.setToolTip("删除当前选中的分块")
        self._btn_delete.clicked.connect(self._delete_current)
        self._btn_delete.setEnabled(False)
        btn_row.addWidget(self._btn_delete)

        self._btn_reset = QPushButton("↩ 恢复原始文本")
        self._btn_reset.setToolTip("恢复当前块为分块时的原始文本")
        self._btn_reset.clicked.connect(self._reset_current)
        self._btn_reset.setEnabled(False)
        btn_row.addWidget(self._btn_reset)

        btn_row.addStretch()
        right_layout.addLayout(btn_row)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # ---- 3. 底部按钮 ----
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(btn_cancel)
        self._btn_accept = QPushButton("✅ 确认入库")
        self._btn_accept.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9; color: white;
                border-radius: 4px; padding: 6px 20px; font-weight: bold;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:disabled { background-color: #c0c0c0; }
        """)
        self._btn_accept.clicked.connect(self._on_accept)
        bottom_row.addWidget(self._btn_accept)
        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------ #
    #  Parse & Chunk
    # ------------------------------------------------------------------ #

    def _parse_and_chunk(self) -> None:
        """解析文件 + 初始分块。"""
        try:
            self._full_text = self._proc.parse(self._file_path)
        except Exception as e:
            QMessageBox.critical(self, "解析错误", f"无法解析文件:\n{e}")
            self.reject()
            return
        self._do_chunk()

    def _do_chunk(self) -> None:
        """用当前参数执行分块并刷新列表。"""
        old_count = len(self._chunks)

        # 用临时参数分块（不修改 proc 的全局设置）
        from app.utils.chunker import chunk_text
        self._chunks = chunk_text(
            self._full_text,
            chunk_size=self._chunk_size.value(),
            chunk_overlap=self._chunk_overlap.value(),
            method=self._chunk_method.currentText(),
        )
        self._edited = False
        self._current_index = -1
        self._refresh_list()

        new_count = len(self._chunks)
        if old_count > 0 and old_count != new_count and self._edited:
            # 理论上不会到这里（_do_chunk 会在 _rechunk 里确认），防御性提示
            pass

    # ------------------------------------------------------------------ #
    #  Chunk list
    # ------------------------------------------------------------------ #

    def _refresh_list(self) -> None:
        """刷新左侧分块列表。"""
        # 先保存当前编辑内容，防止丢失
        if self._current_index >= 0 and self._current_index < len(self._chunks):
            self._chunks[self._current_index] = self._chunk_editor.toPlainText()
        self._current_index = -1  # 防止后续 setCurrentRow 触发错误保存

        self._chunk_list.currentRowChanged.disconnect(self._on_chunk_selected)
        self._chunk_list.clear()

        for i, text in enumerate(self._chunks):
            preview = text.replace("\n", " ")[:80]
            chars = len(text)
            display = f"#{i + 1}  ·  {chars} 字  ·  \"{preview}...\""
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, i)
            self._chunk_list.addItem(item)

        self._chunk_count_label.setText(f"共 {len(self._chunks)} 块  ·  "
                                        f"总 {sum(len(c) for c in self._chunks)} 字")
        self._chunk_list.currentRowChanged.connect(self._on_chunk_selected)

        if self._chunk_list.count() > 0:
            self._chunk_list.setCurrentRow(0)
        else:
            self._chunk_editor.clear()
            self._chunk_editor.setEnabled(False)

    def _on_chunk_selected(self, row: int) -> None:
        """左侧选中某块 → 右侧编辑区显示。"""
        if row < 0 or row >= len(self._chunks):
            self._current_index = -1
            self._chunk_editor.setEnabled(False)
            self._btn_merge.setEnabled(False)
            self._btn_split.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._btn_reset.setEnabled(False)
            return

        # 保存上一块的编辑
        if self._current_index >= 0 and self._current_index < len(self._chunks):
            self._chunks[self._current_index] = self._chunk_editor.toPlainText()

        self._current_index = row
        self._chunk_editor.setEnabled(True)
        self._chunk_editor.blockSignals(True)
        self._chunk_editor.setPlainText(self._chunks[row])
        self._chunk_editor.blockSignals(False)

        # 按钮状态
        self._btn_merge.setEnabled(row > 0)
        self._btn_split.setEnabled(len(self._chunks[row]) > 10)
        self._btn_delete.setEnabled(len(self._chunks) > 1)
        self._btn_reset.setEnabled(True)

    # ---- 编辑操作 ----

    def _on_text_changed(self) -> None:
        """编辑区文本变化 → 同步到当前块。"""
        if self._current_index < 0 or self._current_index >= len(self._chunks):
            return
        self._chunks[self._current_index] = self._chunk_editor.toPlainText()
        self._edited = True
        self._update_list_item(self._current_index)

    def _merge_with_prev(self) -> None:
        """合并当前块到上一块。"""
        if self._current_index <= 0 or self._current_index >= len(self._chunks):
            return
        reply = QMessageBox.question(
            self, "确认合并",
            f"将块 #{self._current_index + 1} 合并到块 #{self._current_index}？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 先保存当前编辑
        self._chunks[self._current_index] = self._chunk_editor.toPlainText()

        # 拼接
        prev = self._chunks[self._current_index - 1]
        curr = self._chunks[self._current_index]
        self._chunks[self._current_index - 1] = prev + curr
        del self._chunks[self._current_index]
        self._edited = True

        target_row = self._current_index - 1  # 在 _refresh_list 前计算
        self._refresh_list()
        if 0 <= target_row < self._chunk_list.count():
            self._chunk_list.setCurrentRow(target_row)

    def _split_at_cursor(self) -> None:
        """在编辑区光标处拆分为两块。"""
        if self._current_index < 0:
            return

        cursor = self._chunk_editor.textCursor()
        pos = cursor.position()
        text = self._chunk_editor.toPlainText()

        if pos <= 0 or pos >= len(text):
            QMessageBox.information(self, "提示", "请在文本中间位置放置光标后再拆分。")
            return

        left = text[:pos]
        right = text[pos:]

        if not left.strip() or not right.strip():
            QMessageBox.information(self, "提示", "拆分后不能有空块，请调整光标位置。")
            return

        # 先保存当前编辑
        self._chunks[self._current_index] = text

        # 拆分：替换当前块为 left，在当前位置+1 插入 right
        self._chunks[self._current_index] = left
        self._chunks.insert(self._current_index + 1, right)
        self._edited = True

        target_row = self._current_index  # 在 _refresh_list 前计算
        self._refresh_list()
        if 0 <= target_row < self._chunk_list.count():
            self._chunk_list.setCurrentRow(target_row)

    def _delete_current(self) -> None:
        """删除当前块。"""
        if self._current_index < 0 or len(self._chunks) <= 1:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除块 #{self._current_index + 1}？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        del self._chunks[self._current_index]
        self._edited = True

        target_row = min(self._current_index, len(self._chunks) - 1)  # 在 _refresh_list 前计算
        self._refresh_list()
        if 0 <= target_row < self._chunk_list.count():
            self._chunk_list.setCurrentRow(target_row)

    def _reset_current(self) -> None:
        """恢复当前块为解析时的原始文本（不可逆，因为已重新分块）。"""
        # 重新分块后原始分块信息已丢失，此按钮仅恢复为当前参数下的 chunk 结果
        # 此处做简单处理：提示用户用"重新分块"
        QMessageBox.information(
            self, "提示",
            "已编辑过的块无法单独恢复。\n如需恢复，请用上方「🔄 重新分块」按钮整体重新分块。",
        )

    def _update_list_item(self, index: int) -> None:
        """更新列表中的单行显示。"""
        if index < 0 or index >= self._chunk_list.count():
            return
        text = self._chunks[index]
        preview = text.replace("\n", " ")[:80]
        chars = len(text)
        display = f"#{index + 1}  ·  {chars} 字  ·  \"{preview}...\""
        self._chunk_list.item(index).setText(display)
        self._chunk_count_label.setText(f"共 {len(self._chunks)} 块  ·  "
                                        f"总 {sum(len(c) for c in self._chunks)} 字")

    # ------------------------------------------------------------------ #
    #  Re-chunk
    # ------------------------------------------------------------------ #

    def _rechunk(self) -> None:
        """用新参数重新分块（会丢失手动编辑）。"""
        if self._edited:
            reply = QMessageBox.question(
                self, "确认重新分块",
                "重新分块会丢失所有手动编辑，确定继续？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self._do_chunk()

    # ------------------------------------------------------------------ #
    #  Accept
    # ------------------------------------------------------------------ #

    def _on_accept(self) -> None:
        """确认入库前校验。"""
        # 先保存当前编辑
        if self._current_index >= 0 and self._current_index < len(self._chunks):
            self._chunks[self._current_index] = self._chunk_editor.toPlainText()

        # 过滤空块
        self._chunks = [c for c in self._chunks if c.strip()]
        if not self._chunks:
            QMessageBox.warning(self, "无内容", "所有分块均为空，无法入库。")
            return
        self.accept()

    # ------------------------------------------------------------------ #
    #  Public
    # ------------------------------------------------------------------ #

    def get_chunks(self) -> list[str]:
        """返回最终编辑后的分块列表。"""
        return list(self._chunks)

    def get_chunk_params(self) -> dict:
        """返回最终使用的分块参数。"""
        return {
            "chunk_size": self._chunk_size.value(),
            "chunk_overlap": self._chunk_overlap.value(),
            "chunk_method": self._chunk_method.currentText(),
        }
