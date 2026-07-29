# -*- coding: utf-8 -*-
"""
设置对话框 — SettingCard 布局版
================================
Tab 内使用 SettingCardGroup + SettingCard 替代 QFormLayout。
"""

import copy

from PySide6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QGroupBox, QLabel, QMessageBox, QDialogButtonBox,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.core.config import ConfigManager
from app.core.model_registry import ModelRegistry
from app.ui.fluent import PrimaryButton, ToolButton
from app.ui.fluent.widgets.card import SettingCard, SettingCardGroup


PROVIDER_TYPES = ["openai_compatible", "ollama"]
CHUNK_METHODS = ["recursive", "fixed"]


class SettingsDialog(QDialog):
    """模型设置对话框（模态）— Fluent 卡片布局"""

    def __init__(self, config: ConfigManager, registry: ModelRegistry, parent=None):
        super().__init__(parent)
        self._config = config
        self._registry = registry
        self._data = copy.deepcopy(config.data)
        self.setWindowTitle("设置")
        self.resize(780, 560)
        self._setup_ui()
        self._load_data()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        """搭建三 Tab + 确定/取消按钮"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)

        self._tabs = QTabWidget()
        self._setup_providers_tab()
        self._setup_active_models_tab()
        self._setup_general_tab()
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ #
    #  Tab 1: 模型供应商
    # ------------------------------------------------------------------ #

    def _setup_providers_tab(self) -> None:
        """供应商管理：左侧列表 + 右侧表单"""
        tab = QWidget()
        h_layout = QHBoxLayout(tab)
        h_layout.setContentsMargins(8, 8, 8, 8)

        # ---- 左侧：供应商列表 ----
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>供应商</b>"))
        self._prov_list = QListWidget()
        self._prov_list.currentRowChanged.connect(self._on_provider_selected)
        left.addWidget(self._prov_list)

        btn_row = QHBoxLayout()
        btn_add = PrimaryButton("+ 添加")
        btn_add.clicked.connect(self._add_provider)
        btn_row.addWidget(btn_add)
        btn_del = ToolButton("-")
        btn_del.setToolTip("删除供应商")
        btn_del.clicked.connect(self._delete_provider)
        btn_row.addWidget(btn_del)
        left.addLayout(btn_row)
        h_layout.addLayout(left, 1)

        # ---- 右侧：滚动表单区 ----
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        right_container = QWidget()
        right_container.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(4)

        # 名称
        card_name = SettingCard("🏷", "名称", "供应商显示名称")
        self._prov_name = QLineEdit()
        card_name.add_widget(self._prov_name)
        right_layout.addWidget(card_name)

        # 类型
        card_type = SettingCard("🔌", "类型", "API 协议类型")
        self._prov_type = QComboBox()
        self._prov_type.addItems(PROVIDER_TYPES)
        card_type.add_widget(self._prov_type)
        right_layout.addWidget(card_type)

        # Base URL
        card_url = SettingCard("🌐", "Base URL", "API 端点地址")
        self._prov_base_url = QLineEdit()
        card_url.add_widget(self._prov_base_url)
        right_layout.addWidget(card_url)

        # API Key
        card_key = SettingCard("🔑", "API Key", "认证密钥")
        self._prov_api_key = QLineEdit()
        self._prov_api_key.setEchoMode(QLineEdit.Password)
        card_key.add_widget(self._prov_api_key)
        right_layout.addWidget(card_key)

        # 启用
        card_enable = SettingCard("✅", "启用", "启用此供应商")
        self._prov_enabled = QCheckBox("已启用")
        card_enable.add_widget(self._prov_enabled)
        right_layout.addWidget(card_enable)

        # 对话模型表格
        chat_group = QGroupBox("对话模型")
        chat_vbox = QVBoxLayout(chat_group)
        self._chat_model_table = QTableWidget(0, 3)
        self._chat_model_table.setHorizontalHeaderLabels(["模型名", "显示名", "默认"])
        self._chat_model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._chat_model_table.setMaximumHeight(130)
        chat_vbox.addWidget(self._chat_model_table)
        btn_add_chat = PrimaryButton("+ 添加聊天模型")
        btn_add_chat.clicked.connect(lambda: self._add_model_row(self._chat_model_table, is_chat=True))
        chat_vbox.addWidget(btn_add_chat)
        right_layout.addWidget(chat_group)

        # Embedding 模型表格
        emb_group = QGroupBox("Embedding 模型")
        emb_vbox = QVBoxLayout(emb_group)
        self._emb_model_table = QTableWidget(0, 4)
        self._emb_model_table.setHorizontalHeaderLabels(["模型名", "显示名", "维度", "默认"])
        self._emb_model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._emb_model_table.setMaximumHeight(130)
        emb_vbox.addWidget(self._emb_model_table)
        btn_add_emb = PrimaryButton("+ 添加 Embedding 模型")
        btn_add_emb.clicked.connect(lambda: self._add_model_row(self._emb_model_table, is_chat=False))
        emb_vbox.addWidget(btn_add_emb)
        right_layout.addWidget(emb_group)

        right_layout.addStretch()
        right_scroll.setWidget(right_container)
        h_layout.addWidget(right_scroll, 2)

        self._tabs.addTab(tab, "模型供应商")

    # ------------------------------------------------------------------ #
    #  Tab 2: 活跃模型
    # ------------------------------------------------------------------ #

    def _setup_active_models_tab(self) -> None:
        """活跃模型选择 — SettingCard 布局"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 8, 12, 8)

        # 对话模型
        chat_group = SettingCardGroup("默认对话模型")
        prov_card = SettingCard("🏢", "供应商", "选择对话模型供应商")
        self._active_chat_prov = QComboBox()
        self._active_chat_prov.currentIndexChanged.connect(self._refresh_chat_models)
        prov_card.add_widget(self._active_chat_prov)
        chat_group.add_card(prov_card)

        model_card = SettingCard("🤖", "模型", "选择默认对话模型")
        self._active_chat_model = QComboBox()
        model_card.add_widget(self._active_chat_model)
        chat_group.add_card(model_card)
        layout.addWidget(chat_group)

        # Embedding 模型
        emb_group = SettingCardGroup("默认 Embedding 模型")
        prov_card2 = SettingCard("🏢", "供应商", "选择 Embedding 模型供应商")
        self._active_emb_prov = QComboBox()
        self._active_emb_prov.currentIndexChanged.connect(self._refresh_emb_models)
        prov_card2.add_widget(self._active_emb_prov)
        emb_group.add_card(prov_card2)

        model_card2 = SettingCard("🧠", "模型", "选择默认 Embedding 模型")
        self._active_emb_model = QComboBox()
        model_card2.add_widget(self._active_emb_model)
        emb_group.add_card(model_card2)
        layout.addWidget(emb_group)

        # 测试连接
        test_card = SettingCard("🔌", "连接测试", "验证当前供应商配置是否可用")
        btn_test = PrimaryButton("测试连接")
        btn_test.clicked.connect(self._test_connection)
        test_card.add_widget(btn_test)
        layout.addWidget(test_card)

        layout.addStretch()
        self._tabs.addTab(tab, "活跃模型")

    # ------------------------------------------------------------------ #
    #  Tab 3: 通用
    # ------------------------------------------------------------------ #

    def _setup_general_tab(self) -> None:
        """通用设置 — SettingCard 布局"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 8, 12, 8)

        group = SettingCardGroup("分块参数")

        card1 = SettingCard("📏", "分块大小", "每个文档块包含的字符数")
        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(100, 8000)
        self._chunk_size.setSingleStep(100)
        card1.add_widget(self._chunk_size)
        group.add_card(card1)

        card2 = SettingCard("📐", "分块重叠", "相邻块之间的重叠字符数")
        self._chunk_overlap = QSpinBox()
        self._chunk_overlap.setRange(0, 1000)
        self._chunk_overlap.setSingleStep(20)
        card2.add_widget(self._chunk_overlap)
        group.add_card(card2)

        card3 = SettingCard("⚙", "分块方法", "文本分割策略")
        self._chunk_method = QComboBox()
        self._chunk_method.addItems(CHUNK_METHODS)
        card3.add_widget(self._chunk_method)
        group.add_card(card3)

        card4 = SettingCard("🎯", "检索结果数 (Top-K)", "每次检索返回的文档块数量")
        self._top_k = QSpinBox()
        self._top_k.setRange(1, 50)
        card4.add_widget(self._top_k)
        group.add_card(card4)

        layout.addWidget(group)
        layout.addStretch()
        self._tabs.addTab(tab, "通用")

    # ------------------------------------------------------------------ #
    #  Load / Save
    # ------------------------------------------------------------------ #

    def _load_data(self) -> None:
        """回填当前配置到 UI"""
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
            self._active_emb_prov.addItem(prov["name"], prov["id"])

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

        # General
        app = self._data.get("app", {})
        self._chunk_size.setValue(app.get("chunk_size", 800))
        self._chunk_overlap.setValue(app.get("chunk_overlap", 120))
        idx = self._chunk_method.findText(app.get("chunk_method", "recursive"))
        if idx >= 0:
            self._chunk_method.setCurrentIndex(idx)
        self._top_k.setValue(app.get("top_k_retrieval", 5))

        if self._prov_list.count() > 0:
            self._prov_list.setCurrentRow(0)

    def _save_and_accept(self) -> None:
        """从 UI 收集数据并保存"""
        self._save_current_provider()

        self._data["active_providers"]["chat"] = self._active_chat_prov.currentData()
        self._data["active_providers"]["embedding"] = self._active_emb_prov.currentData()
        self._data["active_models"]["chat"] = self._active_chat_model.currentData()
        self._data["active_models"]["embedding"] = self._active_emb_model.currentData()

        self._data["app"]["chunk_size"] = self._chunk_size.value()
        self._data["app"]["chunk_overlap"] = self._chunk_overlap.value()
        self._data["app"]["chunk_method"] = self._chunk_method.currentText()
        self._data["app"]["top_k_retrieval"] = self._top_k.value()

        self._config.save(self._data)
        self._registry.reload_config(self._data)
        self.accept()

    # ------------------------------------------------------------------ #
    #  Provider form
    # ------------------------------------------------------------------ #

    def _on_provider_selected(self, index: int) -> None:
        if index < 0:
            return
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

    def _save_current_provider(self) -> None:
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

        active_p = self._data.get("active_providers", {})
        if prov_id in (active_p.get("chat"), active_p.get("embedding")):
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
                                m.get("dimensions", 1024) if not is_chat else 0)

    def _add_model_row(self, table: QTableWidget, is_chat: bool,
                       name: str = "", display: str = "", default: bool = False,
                       dims: int = 1024) -> None:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(name))
        table.setItem(row, 1, QTableWidgetItem(display))
        if is_chat:
            cb = QTableWidgetItem()
            cb.setCheckState(Qt.Checked if default else Qt.Unchecked)
            table.setItem(row, 2, cb)
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
                m["is_default"] = table.item(row, 2).checkState() == Qt.Checked if table.item(row, 2) else False
            else:
                dims = int(table.item(row, 2).text()) if table.item(row, 2) else 1024
                m["dimensions"] = dims
                m["is_default"] = table.item(row, 3).checkState() == Qt.Checked if table.item(row, 3) else False
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
