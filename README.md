![banner](assets/banner.jpg)

基于 PySide6 + ChromaDB + 阿里云 MaaS 的本地 RAG 知识库问答桌面应用。本地运行，数据不出本机，支持多模型供应商、重排检索与多模态视觉理解。

## 功能

- **知识库管理** — 创建/删除知识库，支持 PDF、DOCX、Markdown、纯文本、JSON、JSONL 文档
- **RAG 对话** — 基于知识库的流式问答，Markdown 实时渲染，回答附引用来源与相关度
- **重排检索** — 可选 qwen3-rerank（OpenAI 兼容 `/reranks` 端点）对召回结果二次排序，提升命中精度
- **多模态视觉** — 拖入或点按附加图片，自动切换视觉模型作为额外上下文
- **多库关联** — 右键将多个知识库关联到对话，跨库检索
- **多模型供应商** — 默认阿里云 MaaS，可扩展 Ollama 本地模型，热切换对话/视觉/Embedding/重排模型
- **可视化设置** — 增删改模型供应商与活跃模型，调整分块/Top-K/重排参数，保存即时生效
- **安全配置** — API Key 存于本地 JSON 配置，不硬编码

## 快速开始

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

左侧导航栏在「对话 / 知识库 / 设置 / 帮助」四页间切换。

1. **新建知识库** — 知识库页点击「+ 新建」
2. **上传文档** — 选中知识库，在文档区点「上传」，选择 PDF/DOCX/MD/TXT/JSON 文件，右侧自动展示分块预览
3. **关联对话** — 右键知识库 →「添加到对话」（或双击），可关联多个库跨库检索
4. **提问** — 对话页输入框输入问题，`Ctrl+Enter` 发送；回答下方可展开「引用来源」查看命中分块与相关度
5. **调参** — 设置页调整分块/Top-K/重排等参数，点「保存」即时生效

## 打包为独立应用

使用 PyInstaller 打包为 Windows 可执行文件，无需安装 Python 环境即可运行。

### 打包（Windows）

```bash
# 确保虚拟环境已激活
venv\Scripts\activate

# 安装 PyInstaller
pip install pyinstaller

# 一键打包
python do_build.py
```

打包产物位于 `dist/RAG_H/RAG_H.exe`。

### 打包参数说明

| 参数 | 说明 |
|------|------|
| `--windowed` | 无控制台窗口（纯 GUI） |
| `--onedir` | 目录模式（启动更快，便于调试） |
| `--icon=assets/logo.ico` | 程序图标 |
| `--collect-all chromadb` | 完整打包 ChromaDB 及其原生依赖 |

> 如需制作安装包，可使用 [Inno Setup](https://jrsoftware.org/isinfo.php) 或 [NSIS](https://nsis.sourceforge.io/) 将 `dist/RAG_H/` 目录打包为安装程序。

## 技术栈

| 技术 | 用途 |
|------|------|
| PySide6 (Qt6) | 桌面 UI |
| ChromaDB | 向量数据库（本地持久化） |
| SQLite | 元数据存储 |
| qwen3.7-plus | 默认对话模型 |
| text-embedding-v4 | 默认 Embedding（1024 维） |
| qwen3-rerank | 重排模型（`/reranks` 端点） |
| PyMuPDF | PDF 解析 |
| python-docx | DOCX 解析 |
| langchain-text-splitters | 文本分块 |
| markdown | Markdown 渲染 |

## 项目结构

```
RAG_H/
├── main.py                        # 入口
├── config.json.example            # 配置模板
├── requirements.txt               # 依赖
├── do_build.py                    # PyInstaller 打包脚本
├── app/
│   ├── core/                      # 后端核心
│   │   ├── config.py              # 配置管理
│   │   ├── database.py            # SQLite 连接
│   │   ├── document_processor.py  # 文档解析与分块
│   │   ├── embedding_service.py   # Embedding 服务
│   │   ├── kb_manager.py          # 知识库管理
│   │   ├── model_registry.py      # 模型注册与活跃模型
│   │   ├── rag_pipeline.py        # RAG 管线（检索 + 重排 + 生成）
│   │   └── vector_store.py        # ChromaDB 封装
│   ├── providers/                 # 模型供应商
│   │   ├── base.py
│   │   ├── openai_compatible.py   # MaaS（OpenAI 兼容）
│   │   └── ollama.py              # Ollama 本地
│   ├── ui/                        # PySide6 界面
│   │   ├── main_window.py         # 主窗口（导航栏 + 页面栈）
│   │   ├── chat_panel.py          # 对话面板
│   │   ├── kb_page.py             # 知识库页
│   │   ├── settings_page.py       # 设置页
│   │   ├── help_page.py           # 帮助页
│   │   ├── theme.py               # 集中样式
│   │   ├── widgets/               # 复用组件（卡片/导航栏/菜单等）
│   │   └── workers/               # QThread 后台线程（入库/删除/查询）
│   └── utils/                     # 工具
│       ├── chunker.py             # 文本分块
│       ├── image_utils.py         # 图片处理
│       ├── markdown_renderer.py   # Markdown 渲染
│       └── text_cleaner.py        # 文本清洗
└── tests/
```

## 配置说明

`config.json` 结构（节选）：

```json
{
  "app": {
    "chunk_size": 800,
    "chunk_overlap": 120,
    "chunk_method": "recursive",
    "top_k_retrieval": 5,
    "rerank_enabled": true,
    "rerank_candidate_multiplier": 3
  },
  "model_providers": [
    {
      "id": "maas-default",
      "provider_type": "openai_compatible",
      "base_url": "https://xxx.maas.aliyuncs.com/compatible-mode/v1",
      "api_key": "你的API Key",
      "chat_models": [{"model_name": "qwen3.7-plus", "is_default": true}],
      "embedding_models": [{"model_name": "text-embedding-v4", "dimensions": 1024}]
    }
  ],
  "active_providers": {"chat": "maas-default", "embedding": "maas-default"},
  "active_models": {"chat": "qwen3.7-plus", "embedding": "text-embedding-v4"}
}
```

新增供应商只需在 `model_providers` 数组中加一条配置，无需改代码；也可在应用内「设置」页图形化管理。重排与视觉模型为可选项，对应字段为供应商下的 `rerank_models` 与 `active_models` 中的 `rerank` / `vision`，可在设置页配置。

## License

MIT
