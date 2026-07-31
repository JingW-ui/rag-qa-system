# -*- coding: utf-8 -*-
"""
帮助 / 关于页 — 内嵌于主窗体,不再弹窗。
内容种子取自原 main_window._show_about 的 HTML。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.theme import PANEL_BG, FONT_FAMILY, FONT_SIZE_NORMAL


class HelpPage(QWidget):
    """帮助 / 关于页(静态内容)。"""

    ABOUT_HTML = """
    <h2 style="color:#2a7ab5;">RAG_H v1.0</h2>
    <p>基于 <b>PySide6</b> + <b>ChromaDB</b> + <b>阿里云 MaaS</b> 的 RAG 知识库问答系统。</p>
    <p>支持 PDF / DOCX / Markdown / 纯文本 / JSON 等文档的知识库问答与多模态视觉理解。</p>

    <h3>快速入门</h3>
    <ol>
      <li><b>知识库</b>页:点击「+ 新建」创建知识库;选中后「📤 上传」导入文档,
          右侧自动展示分块预览。双击知识库(或右键)将其「添加到对话」。</li>
      <li><b>对话</b>页:在输入框提问,系统从已关联知识库检索并生成回答。
          可拖入或点「📎」附加图片(自动切换视觉模型)/文件作为额外上下文。</li>
      <li><b>设置</b>页:管理模型供应商、活跃模型(对话/视觉/Embedding/重排)与通用参数
          (分块、Top-K、重排)。改完点「💾 保存」即时生效,「↺ 重置」回退。</li>
      <li>回答下方可展开「引用来源」查看命中的分块与相关度。</li>
    </ol>

    <h3>技术栈</h3>
    <ul>
      <li>UI:PySide6(Qt6)</li>
      <li>向量库:ChromaDB(本地持久化)</li>
      <li>模型:阿里云 MaaS(OpenAI 兼容)/ Ollama(本地)</li>
      <li>重排:qwen3-rerank(OpenAI 兼容 /reranks 端点)</li>
    </ul>

    <p style="color:#999;">本地运行 · 数据安全 · 开源</p>
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"HelpPage {{ background-color: {PANEL_BG}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {PANEL_BG}; }}"
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(8)

        body = QLabel(self.ABOUT_HTML)
        body.setTextFormat(Qt.RichText)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        body.setWordWrap(True)
        body.setFont(QFont(FONT_FAMILY, FONT_SIZE_NORMAL))
        body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(body)
        layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)
