# RAG_H

基于 PySide6 + ChromaDB + 阿里云 MaaS 的本地 RAG 知识库问答桌面应用。

## ✨ 功能

- 📚 **知识库管理** — 创建/删除知识库，支持 PDF、DOCX、Markdown 文档
- 💬 **RAG 对话** — 基于知识库内容的流式问答，支持 Markdown 渲染
- 🔗 **多库关联** — 右键将多个知识库关联到对话，跨库检索
- 🔌 **多模型供应商** — 默认阿里云 MaaS，支持扩展 Ollama 本地模型
- ⚙️ **可视化设置** — 增删改模型供应商，热切换对话/Embedding 模型
- 🔑 **安全配置** — API Key 存储在 JSON 配置文件中，不硬编码

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux

### 安装

```bash
git clone https://github.com/JingW-ui/rag-qa-system.git
cd rag-qa-system

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
copy config.json.example config.json
# 编辑 config.json，填入你的阿里云 MaaS API Key
```

### 启动

```bash
python main.py
```

### 使用流程

1. **新建知识库** — 左侧点击 "+ 新建"
2. **上传文档** — 选中知识库，点击 "📤 上传"，选择 PDF/DOCX/MD 文件
3. **关联对话** — 右键知识库 → "💬 添加到对话"
4. **提问** — 右下输入框中输入问题，`Ctrl+Enter` 发送

## 🏗️ 技术栈

| 技术 | 用途 |
|------|------|
| PySide6 | Qt 桌面 UI |
| ChromaDB | 向量数据库 |
| SQLite | 元数据存储 |
| qwen3.7-plus | 默认对话模型 |
| text-embedding-v4 | 默认 Embedding (1024维) |
| PyMuPDF | PDF 解析 |
| python-docx | DOCX 解析 |
| langchain-text-splitters | 文本分块 |

## 📁 项目结构

```
RAG_H/
├── main.py                        # 入口
├── config.json.example            # 配置模板
├── requirements.txt               # 依赖
├── app/
│   ├── core/                      # 后端核心
│   │   ├── config.py              # 配置管理
│   │   ├── database.py            # SQLite 连接
│   │   ├── rag_pipeline.py        # RAG 管线
│   │   ├── vector_store.py        # ChromaDB 封装
│   │   └── ...
│   ├── providers/                 # 模型供应商
│   │   ├── openai_compatible.py   # MaaS / Ollama
│   │   └── ollama.py
│   ├── ui/                        # PySide6 界面
│   │   ├── main_window.py         # 主窗口
│   │   ├── chat_panel.py          # 对话面板
│   │   ├── kb_panel.py            # 知识库面板
│   │   ├── settings_dialog.py     # 设置对话框
│   │   └── workers/               # QThread 后台线程
│   └── utils/                     # 工具
│       ├── chunker.py             # 文本分块
│       └── markdown_renderer.py   # Markdown 渲染
└── tests/
```

## ⚙️ 配置说明

`config.json` 结构：

```json
{
  "model_providers": [
    {
      "id": "maas-default",
      "provider_type": "openai_compatible",
      "base_url": "https://xxx.maas.aliyuncs.com/compatible-mode/v1",
      "api_key": "你的API Key",
      "chat_models": [{"model_name": "qwen3.7-plus", ...}],
      "embedding_models": [{"model_name": "text-embedding-v4", ...}]
    },
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      ...
    }
  ],
  "active_providers": {"chat": "maas-default", "embedding": "maas-default"}
}
```

新增供应商只需在数组中加一条配置，无需改代码。

## 📝 License

MIT
