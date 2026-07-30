# -*- coding: utf-8 -*-
"""
设置对话框 — 模型供应商管理 + 活跃模型选择 + 通用设置。
"""

import copy

from PySide6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QGroupBox, QLabel, QMessageBox, QDialogButtonBox,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt

from app.core.config import ConfigManager
from app.core.model_registry import ModelRegistry


PROVIDER_TYPES = ["openai_compatible", "ollama"]
CHUNK_METHODS = ["recursive", "fixed"]


class SettingsDialog(QDialog):
    """模型设置对话框（模态）。"""

    def __init__(
        self,
        config: ConfigManager,
        registry: ModelRegistry,
        parent=None,
    ):
        super().__init__(parent)
        self._config = config
        self._registry = registry
        # 深拷贝以避免直接修改原始数据
        self._data = copy.deepcopy(config.data)
        self.setWindowTitle("设置")
        self.resize(700, 520)
        self._setup_ui()
        self._load_data()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._setup_providers_tab()
        self._setup_active_models_tab()
        self._setup_general_tab()
        layout.addWidget(self._tabs)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ #
    #  Tab 1: Model Providers
    # ------------------------------------------------------------------ #

    def _setup_providers_tab(self) -> None:
        tab = QWidget()
        h_layout = QHBoxLayout(tab)

        # 左侧列表
        left = QVBoxLayout()
        self._prov_list = QListWidget()
        self._prov_list.currentRowChanged.connect(self._on_provider_selected)
        left.addWidget(QLabel("<b>供应商</b>"))
        left.addWidget(self._prov_list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ 添加")
        btn_add.clicked.connect(self._add_provider)
        btn_row.addWidget(btn_add)
        btn_del = QPushButton("- 删除")
        btn_del.clicked.connect(self._delete_provider)
        btn_row.addWidget(btn_del)
        left.addLayout(btn_row)
        h_layout.addLayout(left, 1)

        # 右侧表单
        right = QFormLayout()

        self._prov_name = QLineEdit()
        right.addRow("名称:", self._prov_name)

        self._prov_type = QComboBox()
        self._prov_type.addItems(PROVIDER_TYPES)
        right.addRow("类型:", self._prov_type)

        self._prov_base_url = QLineEdit()
        right.addRow("Base URL:", self._prov_base_url)

        self._prov_api_key = QLineEdit()
        self._prov_api_key.setEchoMode(QLineEdit.Password)
        right.addRow("API Key:", self._prov_api_key)

        self._prov_enabled = QCheckBox("启用")
        right.addRow("", self._prov_enabled)

        # Chat Models 表格
        chat_group = QGroupBox("对话模型")
        chat_layout = QVBoxLayout(chat_group)
        self._chat_model_table = QTableWidget(0, 4)
        self._chat_model_table.setHorizontalHeaderLabels(["模型名", "显示名", "视觉", "默认"])
        self._chat_model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        chat_layout.addWidget(self._chat_model_table)
        btn_add_chat = QPushButton("+ 添加聊天模型")
        btn_add_chat.clicked.connect(lambda: self._add_model_row(self._chat_model_table, is_chat=True))
        chat_layout.addWidget(btn_add_chat)
        right.addRow(chat_group)

        # Embedding Models 表格
        emb_group = QGroupBox("Embedding 模型")
        emb_layout = QVBoxLayout(emb_group)
        self._emb_model_table = QTableWidget(0, 4)
        self._emb_model_table.setHorizontalHeaderLabels(["模型名", "显示名", "维度", "默认"])
        self._emb_model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        emb_layout.addWidget(self._emb_model_table)
        btn_add_emb = QPushButton("+ 添加 Embedding 模型")
        btn_add_emb.clicked.connect(lambda: self._add_model_row(self._emb_model_table, is_chat=False))
        emb_layout.addWidget(btn_add_emb)
        right.addRow(emb_group)

        # Rerank Models 表格
        rerank_group = QGroupBox("重排模型 (Rerank)")
        rerank_layout = QVBoxLayout(rerank_group)
        self._rerank_model_table = QTableWidget(0, 3)
        self._rerank_model_table.setHorizontalHeaderLabels(["模型名", "显示名", "默认"])
        self._rerank_model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rerank_layout.addWidget(self._rerank_model_table)
        btn_add_rerank = QPushButton("+ 添加 Rerank 模型")
        btn_add_rerank.clicked.connect(lambda: self._add_rerank_model_row(self._rerank_model_table))
        rerank_layout.addWidget(btn_add_rerank)
        right.addRow(rerank_group)

        h_layout.addLayout(right, 2)
        self._tabs.addTab(tab, "模型供应商")

    # ------------------------------------------------------------------ #
    #  Tab 2: Active Models
    # ------------------------------------------------------------------ #

    def _setup_active_models_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

        # 对话模型
        chat_group = QGroupBox("默认对话模型")
        chat_form = QFormLayout(chat_group)
        self._active_chat_prov = QComboBox()
        self._active_chat_prov.currentIndexChanged.connect(self._refresh_chat_models)
        chat_form.addRow("供应商:", self._active_chat_prov)
        self._active_chat_model = QComboBox()
        chat_form.addRow("模型:", self._active_chat_model)
        layout.addRow(chat_group)

        # 视觉模型
        vision_group = QGroupBox("默认视觉模型 (VLM)")
        vision_form = QFormLayout(vision_group)
        self._active_vision_prov = QComboBox()
        self._active_vision_prov.currentIndexChanged.connect(self._refresh_vision_models)
        vision_form.addRow("供应商:", self._active_vision_prov)
        self._active_vision_model = QComboBox()
        vision_form.addRow("模型:", self._active_vision_model)
        layout.addRow(vision_group)

        # Embedding 模型
        emb_group = QGroupBox("默认 Embedding 模型")
        emb_form = QFormLayout(emb_group)
        self._active_emb_prov = QComboBox()
        self._active_emb_prov.currentIndexChanged.connect(self._refresh_emb_models)
        emb_form.addRow("供应商:", self._active_emb_prov)
        self._active_emb_model = QComboBox()
        emb_form.addRow("模型:", self._active_emb_model)
        layout.addRow(emb_group)

        # Rerank 模型
        rerank_group = QGroupBox("默认重排模型 (Rerank)")
        rerank_form = QFormLayout(rerank_group)
        self._active_rerank_prov = QComboBox()
        self._active_rerank_prov.currentIndexChanged.connect(self._refresh_rerank_models)
        rerank_form.addRow("供应商:", self._active_rerank_prov)
        self._active_rerank_model = QComboBox()
        rerank_form.addRow("模型:", self._active_rerank_model)
        layout.addRow(rerank_group)

        # Test Connection
        btn_test = QPushButton("🔌 测试当前连接")
        btn_test.clicked.connect(self._test_connection)
        layout.addRow(btn_test)

        self._tabs.addTab(tab, "活跃模型")

    # ------------------------------------------------------------------ #
    #  Tab 3: General
    # ------------------------------------------------------------------ #

    def _setup_general_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(100, 8000)
        self._chunk_size.setSingleStep(100)
        layout.addRow("分块大小 (字符):", self._chunk_size)

        self._chunk_overlap = QSpinBox()
        self._chunk_overlap.setRange(0, 1000)
        self._chunk_overlap.setSingleStep(20)
        layout.addRow("分块重叠 (字符):", self._chunk_overlap)

        self._chunk_method = QComboBox()
        self._chunk_method.addItems(CHUNK_METHODS)
        layout.addRow("分块方法:", self._chunk_method)

        self._top_k = QSpinBox()
        self._top_k.setRange(1, 50)
        layout.addRow("检索结果数 (Top-K):", self._top_k)

        # Rerank 设置
        rerank_group = QGroupBox("重排设置")
        rerank_layout = QFormLayout(rerank_group)

        self._rerank_enabled = QCheckBox("启用")
        rerank_layout.addRow("重排:", self._rerank_enabled)

        self._rerank_multiplier = QSpinBox()
        self._rerank_multiplier.setRange(2, 10)
        self._rerank_multiplier.setSingleStep(1)
        rerank_layout.addRow("候选倍数 (Top-K × N):", self._rerank_multiplier)

        layout.addRow(rerank_group)

        self._tabs.addTab(tab, "通用")

    # ------------------------------------------------------------------ #
    #  Load / Save
    # ------------------------------------------------------------------ #

    def _load_data(self) -> None:
        """回填当前配置到 UI。"""
        # Providers list
        self._prov_list.clear()
        for p in self._data.get("model_providers", []):
            item = QListWidgetItem(f"{p.get('name', p['id'])}  [{p.get('provider_type', '?')}]")
            item.setData(Qt.UserRole, p["id"])
            self._prov_list.addItem(item)

        # Active models
        active_p = self._data.get("active_providers", {})
        active_m = self._data.get("active_models", {})

        for prov in self._data.get("model_providers", []):
            self._active_chat_prov.addItem(prov["name"], prov["id"])
            self._active_vision_prov.addItem(prov["name"], prov["id"])
            self._active_emb_prov.addItem(prov["name"], prov["id"])
            self._active_rerank_prov.addItem(prov["name"], prov["id"])

        # 设置当前活跃
        chat_pid = active_p.get("chat", "")
        for i in range(self._active_chat_prov.count()):
            if self._active_chat_prov.itemData(i) == chat_pid:
                self._active_chat_prov.setCurrentIndex(i)
                break
        self._refresh_chat_models()
        for i in range(self._active_chat_model.count()):
            if self._active_chat_model.itemData(i) == active_m.get("chat", ""):
                self._active_chat_model.setCurrentIndex(i)
                break

        vision_pid = active_p.get("vision", "")
        for i in range(self._active_vision_prov.count()):
            if self._active_vision_prov.itemData(i) == vision_pid:
                self._active_vision_prov.setCurrentIndex(i)
                break
        self._refresh_vision_models()
        for i in range(self._active_vision_model.count()):
            if self._active_vision_model.itemData(i) == active_m.get("vision", ""):
                self._active_vision_model.setCurrentIndex(i)
                break

        emb_pid = active_p.get("embedding", "")
        for i in range(self._active_emb_prov.count()):
            if self._active_emb_prov.itemData(i) == emb_pid:
                self._active_emb_prov.setCurrentIndex(i)
                break
        self._refresh_emb_models()
        for i in range(self._active_emb_model.count()):
            if self._active_emb_model.itemData(i) == active_m.get("embedding", ""):
                self._active_emb_model.setCurrentIndex(i)
                break

        # Rerank
        rerank_pid = active_p.get("rerank", "")
        for i in range(self._active_rerank_prov.count()):
            if self._active_rerank_prov.itemData(i) == rerank_pid:
                self._active_rerank_prov.setCurrentIndex(i)
                break
        self._refresh_rerank_models()
        for i in range(self._active_rerank_model.count()):
            if self._active_rerank_model.itemData(i) == active_m.get("rerank", ""):
                self._active_rerank_model.setCurrentIndex(i)
                break

        # General
        app = self._data.get("app", {})
        self._chunk_size.setValue(app.get("chunk_size", 800))
        self._chunk_overlap.setValue(app.get("chunk_overlap", 120))
        idx = self._chunk_method.findText(app.get("chunk_method", "recursive"))
        if idx >= 0:
            self._chunk_method.setCurrentIndex(idx)
        self._top_k.setValue(app.get("top_k_retrieval", 5))
        self._rerank_enabled.setChecked(app.get("rerank_enabled", True))
        self._rerank_multiplier.setValue(app.get("rerank_candidate_multiplier", 3))

        # 选第一个供应商
        if self._prov_list.count() > 0:
            self._prov_list.setCurrentRow(0)

    def _save_and_accept(self) -> None:
        """从 UI 收集数据并保存。"""
        self._save_current_provider()  # 先保存当前正在编辑的供应商

        self._data["active_providers"]["chat"] = self._active_chat_prov.currentData()
        self._data["active_providers"]["embedding"] = self._active_emb_prov.currentData()
        self._data["active_providers"]["vision"] = self._active_vision_prov.currentData()
        self._data["active_providers"]["rerank"] = self._active_rerank_prov.currentData()
        self._data["active_models"]["chat"] = self._active_chat_model.currentData()
        self._data["active_models"]["embedding"] = self._active_emb_model.currentData()
        self._data["active_models"]["vision"] = self._active_vision_model.currentData()
        self._data["active_models"]["rerank"] = self._active_rerank_model.currentData()

        self._data["app"]["chunk_size"] = self._chunk_size.value()
        self._data["app"]["chunk_overlap"] = self._chunk_overlap.value()
        self._data["app"]["chunk_method"] = self._chunk_method.currentText()
        self._data["app"]["top_k_retrieval"] = self._top_k.value()
        self._data["app"]["rerank_enabled"] = self._rerank_enabled.isChecked()
        self._data["app"]["rerank_candidate_multiplier"] = self._rerank_multiplier.value()

        self._config.save(self._data)
        self._registry.reload_config(self._data)
        self.accept()

    # ------------------------------------------------------------------ #
    #  Provider form
    # ------------------------------------------------------------------ #

    def _on_provider_selected(self, index: int) -> None:
        if index < 0:
            return
        # 先保存当前
        self._save_current_provider()

        prov_id = self._prov_list.currentItem().data(Qt.UserRole)
        prov = self._find_provider(prov_id)
        if prov is None:
            return

        self._prov_name.setText(prov.get("name", ""))
        idx = self._prov_type.findText(prov.get("provider_type", ""))
        self._prov_type.setCurrentIndex(idx if idx >= 0 else 0)
        self._prov_base_url.setText(prov.get("base_url", ""))
        self._prov_api_key.setText(prov.get("api_key", ""))
        self._prov_enabled.setChecked(prov.get("enabled", True))

        self._populate_model_table(self._chat_model_table, prov.get("chat_models", []), is_chat=True)
        self._populate_model_table(self._emb_model_table, prov.get("embedding_models", []), is_chat=False)
        self._populate_rerank_model_table(self._rerank_model_table, prov.get("rerank_models", []))

    def _save_current_provider(self) -> None:
        """将表单内容写回当前选中供应商。"""
        item = self._prov_list.currentItem()
        if item is None:
            return
        prov_id = item.data(Qt.UserRole)
        prov = self._find_provider(prov_id)
        if prov is None:
            return

        prov["name"] = self._prov_name.text()
        prov["provider_type"] = self._prov_type.currentText()
        prov["base_url"] = self._prov_base_url.text()
        prov["api_key"] = self._prov_api_key.text()
        prov["enabled"] = self._prov_enabled.isChecked()
        prov["chat_models"] = self._read_model_table(self._chat_model_table, is_chat=True)
        prov["embedding_models"] = self._read_model_table(self._emb_model_table, is_chat=False)
        prov["rerank_models"] = self._read_rerank_model_table(self._rerank_model_table)

        # 更新列表显示
        item.setText(f"{prov['name']}  [{prov['provider_type']}]")

    def _add_provider(self) -> None:
        prov = {
            "id": f"provider_{len(self._data['model_providers'])}",
            "name": "新供应商",
            "provider_type": "openai_compatible",
            "base_url": "https://api.example.com/v1",
            "api_key": "",
            "chat_models": [{"model_name": "gpt-3.5-turbo", "display_name": "GPT-3.5", "is_default": True}],
            "embedding_models": [{"model_name": "text-embedding-ada-002", "display_name": "ADA", "is_default": True, "dimensions": 1536}],
            "enabled": True,
        }
        self._data["model_providers"].append(prov)
        item = QListWidgetItem(f"{prov['name']}  [{prov['provider_type']}]")
        item.setData(Qt.UserRole, prov["id"])
        self._prov_list.addItem(item)
        self._prov_list.setCurrentItem(item)

    def _delete_provider(self) -> None:
        item = self._prov_list.currentItem()
        if item is None:
            return
        prov_id = item.data(Qt.UserRole)

        # 不允许删除活跃供应商
        active_p = self._data.get("active_providers", {})
        if prov_id in (active_p.get("chat"), active_p.get("embedding"), active_p.get("vision"), active_p.get("rerank")):
            QMessageBox.warning(self, "无法删除", "该供应商正在被活跃使用，请先切换到其他供应商。")
            return

        self._data["model_providers"] = [
            p for p in self._data["model_providers"] if p["id"] != prov_id
        ]
        self._prov_list.takeItem(self._prov_list.row(item))

    # ------------------------------------------------------------------ #
    #  Model tables
    # ------------------------------------------------------------------ #

    def _populate_model_table(self, table: QTableWidget, models: list[dict], is_chat: bool) -> None:
        table.setRowCount(0)
        for m in models:
            self._add_model_row(table, is_chat,
                                m.get("model_name", ""),
                                m.get("display_name", ""),
                                m.get("is_default", False),
                                m.get("dimensions", 1024) if not is_chat else 0,
                                m.get("is_vision", False) if is_chat else False)

    def _add_model_row(self, table: QTableWidget, is_chat: bool,
                       name: str = "", display: str = "", default: bool = False,
                       dims: int = 1024, is_vision: bool = False) -> None:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(name))
        table.setItem(row, 1, QTableWidgetItem(display))

        if is_chat:
            # Column 2: Vision (视觉)
            vision_cb = QTableWidgetItem()
            vision_cb.setCheckState(Qt.Checked if is_vision else Qt.Unchecked)
            table.setItem(row, 2, vision_cb)
            # Column 3: Default (默认)
            default_cb = QTableWidgetItem()
            default_cb.setCheckState(Qt.Checked if default else Qt.Unchecked)
            table.setItem(row, 3, default_cb)
        else:
            table.setItem(row, 2, QTableWidgetItem(str(dims)))
            cb = QTableWidgetItem()
            cb.setCheckState(Qt.Checked if default else Qt.Unchecked)
            table.setItem(row, 3, cb)

    def _read_model_table(self, table: QTableWidget, is_chat: bool) -> list[dict]:
        models = []
        for row in range(table.rowCount()):
            name = table.item(row, 0).text() if table.item(row, 0) else ""
            display = table.item(row, 1).text() if table.item(row, 1) else ""
            if not name:
                continue
            m = {"model_name": name, "display_name": display or name}
            if is_chat:
                m["is_vision"] = table.item(row, 2).checkState() == Qt.Checked if table.item(row, 2) else False
                m["is_default"] = table.item(row, 3).checkState() == Qt.Checked if table.item(row, 3) else False
            else:
                dims = int(table.item(row, 2).text()) if table.item(row, 2) else 1024
                m["dimensions"] = dims
                m["is_default"] = table.item(row, 3).checkState() == Qt.Checked if table.item(row, 3) else False
            models.append(m)
        return models

    def _populate_rerank_model_table(self, table: QTableWidget, models: list[dict]) -> None:
        table.setRowCount(0)
        for m in models:
            self._add_rerank_model_row(
                table,
                m.get("model_name", ""),
                m.get("display_name", ""),
                m.get("is_default", False),
            )

    def _add_rerank_model_row(
        self, table: QTableWidget,
        name: str = "", display: str = "", default: bool = False,
    ) -> None:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(name))
        table.setItem(row, 1, QTableWidgetItem(display))
        cb = QTableWidgetItem()
        cb.setCheckState(Qt.Checked if default else Qt.Unchecked)
        table.setItem(row, 2, cb)

    def _read_rerank_model_table(self, table: QTableWidget) -> list[dict]:
        models = []
        for row in range(table.rowCount()):
            name = table.item(row, 0).text() if table.item(row, 0) else ""
            display = table.item(row, 1).text() if table.item(row, 1) else ""
            if not name:
                continue
            m = {
                "model_name": name,
                "display_name": display or name,
                "is_default": table.item(row, 2).checkState() == Qt.Checked if table.item(row, 2) else False,
            }
            models.append(m)
        return models

    # ------------------------------------------------------------------ #
    #  Active model refresh
    # ------------------------------------------------------------------ #

    def _refresh_chat_models(self) -> None:
        self._active_chat_model.clear()
        prov_id = self._active_chat_prov.currentData()
        prov = self._find_provider(prov_id)
        if prov:
            for m in prov.get("chat_models", []):
                self._active_chat_model.addItem(m.get("display_name", m["model_name"]), m["model_name"])

    def _refresh_emb_models(self) -> None:
        self._active_emb_model.clear()
        prov_id = self._active_emb_prov.currentData()
        prov = self._find_provider(prov_id)
        if prov:
            for m in prov.get("embedding_models", []):
                self._active_emb_model.addItem(m.get("display_name", m["model_name"]), m["model_name"])

    def _refresh_vision_models(self) -> None:
        self._active_vision_model.clear()
        prov_id = self._active_vision_prov.currentData()
        prov = self._find_provider(prov_id)
        if prov:
            for m in prov.get("chat_models", []):
                if m.get("is_vision"):
                    self._active_vision_model.addItem(m.get("display_name", m["model_name"]), m["model_name"])

    def _refresh_rerank_models(self) -> None:
        self._active_rerank_model.clear()
        prov_id = self._active_rerank_prov.currentData()
        prov = self._find_provider(prov_id)
        if prov:
            for m in prov.get("rerank_models", []):
                self._active_rerank_model.addItem(m.get("display_name", m["model_name"]), m["model_name"])

    # ------------------------------------------------------------------ #
    #  Test connection
    # ------------------------------------------------------------------ #

    def _test_connection(self) -> None:
        self._save_current_provider()
        prov_id = self._active_chat_prov.currentData()
        provider = self._registry.get_provider(prov_id)
        if provider is None:
            QMessageBox.warning(self, "测试失败", "未找到活跃供应商实例，请保存后重试。")
            return
        ok = provider.validate_connection()
        if ok:
            QMessageBox.information(self, "连接测试", "✅ 连接成功！")
        else:
            QMessageBox.warning(self, "连接测试", "❌ 连接失败，请检查 API Key 和 Base URL。")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _find_provider(self, prov_id: str) -> dict | None:
        for p in self._data.get("model_providers", []):
            if p["id"] == prov_id:
                return p
        return None
