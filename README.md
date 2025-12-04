# AI智能标书写作助手

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 基于大语言模型（LLM）的企业级智能标书撰写系统，实现招标文件智能解析、目录自动生成、内容AI撰写、知识库管理的全流程自动化。

---

## 📋 目录

- [核心特性](#-核心特性)
- [技术架构](#-技术架构)
- [快速开始](#-快速开始)
- [项目结构](#-项目结构)
- [功能模块](#-功能模块)
- [部署指南](#-部署指南)
- [API文档](#-api文档)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## ✨ 核心特性

### 🎯 智能文档解析
- **多格式支持**：PDF、Word（.docx）、图片（OCR）招标文件上传
- **双向AI分析**：自动提取项目概述 + 技术评分要求
- **流式输出**：实时显示解析进度，无需等待

### 📚 AI目录生成
- **智能结构化**：基于评分要求自动生成多级目录（2-5级可调）
- **可视化编辑**：拖拽调整章节顺序，实时编号更新
- **字数智能分配**：一键按总字数自动分配各章节目标字数

### ✍️ 专业内容撰写
- **招投标专用Prompt**：内置标书专业术语、格式规范
- **RAG增强生成**：自动检索企业知识库（历史标书、资质文件）
- **动静结合检索**：
  - **静态数据**：MySQL结构化历史项目数据（金额、时间、客户）
  - **动态知识**：ChromaDB向量检索企业文档细节
- **流式实时编辑**：支持ReactQuill富文本，类Word界面
- **AI章节重写**：基于用户反馈指令智能优化内容

### 🗄️ 双模数据管理
- **知识库管理（RAG）**：
  - 支持PDF/Word文档自动切片入库
  - 本地向量化模型（sentence-transformers）
  - ChromaDB持久化存储
- **结构化数据管理**：
  - MySQL业务数据CRUD（公司、项目、人员、资质等15+表）
  - 动态表单生成，支持分页、搜索、导出

### 📤 一键导出
- **Word标准格式**：A4纸张、标准页边距、专业排版
- **目录自动生成**：多级标题、页码、格式统一
- **格式保留**：支持表格、图片、样式完整导出

---

## 🏗️ 技术架构

### 后端技术栈
```
Python 3.8+
├── FastAPI           # 异步Web框架
├── SQLAlchemy        # ORM框架
├── MySQL             # 结构化数据存储
├── ChromaDB          # 向量数据库
├── sentence-transformers  # 本地Embedding模型
├── python-docx       # Word文档生成
├── PyMuPDF/pdfplumber # PDF解析
└── OpenAI/Qwen API   # LLM接口（支持本地/云端）
```

### 前端技术栈
```
React 18 + TypeScript
├── Ant Design        # UI组件库
├── ReactQuill        # 富文本编辑器
├── React Router      # 路由管理
└── Fetch API         # HTTP客户端（支持SSE流式）
```

### AI模型支持
- **云端模型**：OpenAI GPT-4、Claude、Gemini
- **本地模型**：Qwen（通义千问）14B/32B + vLLM推理加速
- **Embedding模型**：本地sentence-transformers（离线部署）

---

## 🚀 快速开始

### 环境要求
- **Python**: 3.8 或更高版本
- **Node.js**: 16.0 或更高版本
- **MySQL**: 5.7 或更高版本
- **内存**: 建议16GB+（本地模型推理）
- **显卡**: NVIDIA GPU（可选，用于加速推理）

### 一键启动（推荐）

#### Windows
```bash
# 双击运行
single_port.bat

# 或命令行执行
.\single_port.bat
```

#### Linux/macOS
```bash
# 添加执行权限
chmod +x single_port.sh

# 运行启动脚本
./single_port.sh
```

**脚本自动完成**：
1. 检测前端构建（缺失则自动`npm install && npm run build`）
2. 复制静态文件到`backend/static`
3. 启动FastAPI服务（集成前端，单端口8000）

### 手动启动（开发模式）

#### 1. 后端启动
```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置数据库（修改 app/db_config.py）
# MYSQL_HOST = "your_host"
# MYSQL_USER = "your_user"
# MYSQL_PASSWORD = "your_password"

# 启动服务
python run.py

# 访问API文档：http://localhost:8000/docs
```

#### 2. 前端启动
```bash
# 新终端，进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start

# 访问前端：http://localhost:3000
```

### 配置说明

#### 数据库配置（`backend/app/db_config.py`）
```python
MYSQL_HOST = "10.11.30.18"   # 数据库IP
MYSQL_PORT = "3306"
MYSQL_USER = "root"
MYSQL_PASSWORD = "123456"
MYSQL_DB = "enterprise_management_system"
```

#### AI模型配置（`backend/app/config.py`）
```python
# 使用云端模型
default_model: str = "gpt-4"

# 使用本地Qwen模型（需单独部署vLLM服务）
default_model: str = "local"  # 默认连接 http://localhost:10086
```

#### RAG Embedding模型（`backend/app/services/rag_service.py`）
```python
# 本地模型路径（需提前下载）
LOCAL_MODEL_PATH = "/path/to/embedding/model"
```

---

## 📁 项目结构

```
bidgen/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── routers/           # API路由
│   │   │   ├── content.py     # 内容生成（核心业务逻辑）
│   │   │   ├── outline.py     # 目录生成
│   │   │   ├── document.py    # 文档解析+导出
│   │   │   ├── knowledge.py   # 知识库管理
│   │   │   └── data_manager.py # 数据库管理
│   │   ├── services/          # 业务服务层
│   │   │   ├── openai_service.py    # OpenAI封装
│   │   │   ├── qwen_api.py          # Qwen本地模型
│   │   │   ├── rag_service.py       # RAG检索
│   │   │   ├── table_service.py     # 数据库操作
│   │   │   └── file_service.py      # 文件处理
│   │   ├── models/            # 数据模型
│   │   │   ├── schemas.py     # Pydantic请求/响应模型
│   │   │   └── business_models.py # SQLAlchemy ORM模型
│   │   ├── db_config.py       # 数据库配置
│   │   ├── config.py          # 全局配置
│   │   └── main.py            # FastAPI应用入口
│   ├── requirements.txt       # Python依赖
│   └── run.py                 # 启动脚本
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   │   ├── DocumentAnalysis.tsx  # 文档解析页
│   │   │   ├── OutlineEdit.tsx       # 目录编辑页
│   │   │   ├── ContentEdit.tsx       # 内容编辑页
│   │   │   └── DataManagement.tsx    # 数据管理页
│   │   ├── components/        # 公共组件
│   │   │   ├── KnowledgeBaseTab.tsx      # 知识库Tab
│   │   │   ├── DatabaseManagementTab.tsx # 数据库Tab
│   │   │   └── ConfigPanel.tsx           # 配置面板
│   │   ├── services/
│   │   │   └── api.ts         # API封装（Fetch + SSE）
│   │   ├── hooks/
│   │   │   └── useAppState.tsx # 全局状态管理
│   │   ├── types/
│   │   │   └── index.ts       # TypeScript类型定义
│   │   ├── App.tsx            # 根组件
│   │   └── index.tsx          # 入口文件
│   ├── package.json
│   └── tsconfig.json
│
├── app_launcher.py            # 桌面启动器（可选）
├── single_port.bat            # Windows一键启动
├── single_port.sh             # Linux/Mac一键启动
└── README.md                  # 本文档
```

---

## 🎯 功能模块

### 1. 智能文档解析（Document Analysis）

**核心接口**：
- `POST /api/pdf/upload` - 文件上传（支持MarkItDown OCR）
- `POST /api/document/analyze-stream` - 流式AI分析

**技术亮点**：
- 支持扫描件OCR（MarkItDown + Azure Document Intelligence）
- 并发双向分析（项目概述 + 技术要求同时生成）
- SSE流式传输，前端实时显示

**代码示例**（前端）：
```typescript
await analyzeDocumentStream(
    documentContent,
    'overview',
    (chunk) => setState(prev => ({ 
        overview: prev.overview + chunk 
    }))
);
```

### 2. AI目录生成（Outline Generation）

**核心接口**：
- `POST /api/outline/generate` - AI生成目录
- `POST /api/outline/generate-stream` - 流式生成（可选）

**Prompt工程**：
```python
# 关键配置：backend/app/routers/outline.py
SYSTEM_PROMPT = """
你是资深招投标专家，生成目录需满足：
1. 自适应层级深度（2-5级）
2. 章节宽度差异化（重点章节多子目录）
3. 符合PMBOK/ISO标准术语
4. 输出纯JSON，无Markdown标记
"""
```

**前端功能**：
- 拖拽调整顺序（Ant Design Tree组件）
- 自动重编号（`renumberOutline`递归算法）
- 智能字数分配（一键平均分配到叶子节点）

### 3. 专业内容撰写（Content Generation）

**核心接口**：
- `POST /api/content/generate-chapter-stream` - 单章节生成
- `POST /api/content/generate-full-project` - 全文并发生成
- `POST /api/content/generate-single-chapter` - 章节重写

**RAG检索流程**（动静结合）：
```python
# backend/app/routers/content.py (第536-642行)

# 1. 判定章节类型（是否为"业绩类"）
if "业绩" in title or "案例" in title:
    
    # 2. 静态数据：查MySQL历史项目
    db_context = table_service.search_projects_and_attachments(keyword)
    # 返回：[{name: "XX项目", amount: 1000000, date: "2023-01"}]
    
    # 3. 动态知识：查ChromaDB关联文件
    rag_filter = {"source": {"$in": db_context['file_sources']}}
    rag_context = rag_service.search(query, n_results=3, filter=rag_filter)
    # 返回：[{content: "...技术细节...", source: "XX项目标书.pdf"}]

# 4. 合并上下文注入Prompt
user_prompt = f"""
### 历史业绩（精确数据）
{db_context}

### 文档细节（RAG检索）
{rag_context}

请基于上述资料撰写章节...
"""
```

**流式防抖优化**（前端）：
```typescript
// frontend/src/pages/ContentEdit.tsx (第118-258行)
const streamBufferRef = useRef<string>('');
const updateTimerRef = useRef<NodeJS.Timeout | null>(null);

// 100ms防抖批量更新，避免ReactQuill每字符重渲染
(chunk) => {
    streamBufferRef.current += chunk;
    if (updateTimerRef.current) clearTimeout(updateTimerRef.current);
    updateTimerRef.current = setTimeout(() => {
        setState(prev => ({
            generatedContent: { 
                [chapterId]: streamBufferRef.current 
            }
        }));
    }, 100);
}
```

### 4. 知识库管理（Knowledge Base）

**核心接口**：
- `POST /api/knowledge/upload` - 文档上传（支持进度监听）
- `POST /api/knowledge/test-search` - 检索测试
- `GET /api/knowledge/list` - 知识库列表
- `DELETE /api/knowledge/delete` - 删除文档

**技术实现**：
```python
# backend/app/services/rag_service.py

class RagService:
    def __init__(self):
        # 1. 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(path="data/chroma_db")
        
        # 2. 加载本地Embedding模型
        self.embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name="/path/to/local/model"
        )
        
        # 3. 创建Collection
        self.collection = self.client.get_or_create_collection(
            name="bid_knowledge_base",
            embedding_function=self.embedding_fn
        )
    
    def add_document(self, text, source, doc_type):
        # 4. 文本切片（500字/块，50字重叠）
        chunks = self._split_text(text, chunk_size=500, overlap=50)
        
        # 5. 向量化 + 存储
        self.collection.add(
            documents=chunks,
            metadatas=[{"source": source, "type": doc_type}],
            ids=[str(uuid.uuid4()) for _ in chunks]
        )
```

### 5. 结构化数据管理（Database Management）

**核心接口**：
- `GET /api/data/tables` - 获取可用表列表
- `GET /api/data/{table_name}/list` - 分页查询
- `POST /api/data/t_company` - 新增公司记录
- `PUT /api/data/t_company/{id}` - 更新记录
- `DELETE /api/data/{table_name}/{id}` - 删除记录

**表结构示例**：
```python
# backend/app/models/business_models.py

class Company(Base):
    __tablename__ = 't_company'
    id = Column(String(100), primary_key=True)
    company_name = Column(String(300), nullable=False)
    address = Column(String(500))
    created_time = Column(DateTime, default=func.now())

class Project(Base):
    __tablename__ = 't_project'
    id = Column(String(100), primary_key=True)
    project_name = Column(String(300), nullable=False)
    bid_quote = Column(DECIMAL(15, 2))  # 投标报价
    is_win = Column(Boolean)            # 是否中标
    win_amount = Column(DECIMAL(15, 2)) # 中标金额
```

### 6. Word文档导出（Export）

**核心接口**：
- `POST /api/document/export` - 导出Word

**排版特性**：
- **封面生成**：标准标书格式（标题、投标人、日期）
- **页码自动添加**：页脚居中显示"第X页"
- **A4纸张尺寸**：21cm × 29.7cm，页边距2.54cm
- **多级标题**：自动识别`##`/`###`生成Word标题样式
- **表格保留**：HTML表格转Word表格
- **格式继承**：加粗、颜色、列表样式完整保留

**代码示例**：
```python
# backend/app/routers/document.py (第415-528行)

from docx import Document
from docx.shared import Pt, Cm

doc = Document()

# 1. 页面设置
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)

# 2. 生成封面
create_cover_page(doc, project_name="XX项目投标文件")

# 3. 递归处理目录结构
def add_chapter(items: List[OutlineItem], level=1):
    for item in items:
        # 添加标题
        p = doc.add_heading(level=min(level, 9))
        run = p.add_run(f"{item.id} {item.title}")
        set_font(run, '黑体', 16 if level==1 else 14)
        
        # 添加内容（HTML转Word）
        process_html_content(doc, item.content, level)
        
        # 递归子章节
        if item.children:
            add_chapter(item.children, level+1)

# 4. 导出文件流
buffer = BytesIO()
doc.save(buffer)
return StreamingResponse(buffer, media_type="application/vnd.openxmlformats...")
```

---

## 🚢 部署指南

### Docker部署（推荐生产环境）

#### 1. 构建镜像
```dockerfile
# Dockerfile示例
FROM python:3.8-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY backend/ ./backend/
COPY frontend/build/ ./backend/static/

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Docker Compose
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_USER=root
      - MYSQL_PASSWORD=yourpassword
    depends_on:
      - mysql
  
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: yourpassword
      MYSQL_DATABASE: enterprise_management_system
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

### 服务器手动部署

#### 1. 系统准备（Ubuntu 20.04示例）
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python
sudo apt install python3.8 python3-pip -y

# 安装Node.js
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install -y nodejs

# 安装MySQL
sudo apt install mysql-server -y
```

#### 2. 部署步骤
```bash
# 克隆代码
git clone https://github.com/your-repo/bidgen.git
cd bidgen

# 构建前端
cd frontend
npm install
npm run build
cp -r build/* ../backend/static/

# 安装后端依赖
cd ../backend
pip3 install -r requirements.txt

# 配置数据库（修改 app/db_config.py）

# 使用Gunicorn + Nginx部署
pip3 install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

#### 3. Nginx反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # SSE支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

### 本地Qwen模型部署（可选）

#### 使用vLLM启动推理服务
```bash
# 安装vLLM
pip install vllm

# 启动Qwen-14B服务
python -m vllm.entrypoints.openai.api_server \
    --model /path/to/Qwen-14B \
    --host 0.0.0.0 \
    --port 10086 \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.8
```

修改后端配置连接本地模型：
```python
# backend/app/services/qwen_api.py
class QwenService:
    def __init__(self, base_url="http://localhost:10086"):
        self.base_url = base_url
```

---

## 📖 API文档

### 访问交互式文档
启动服务后访问：**http://localhost:8000/docs**

### 核心API速查

#### 文档解析
```http
POST /api/pdf/upload
Content-Type: multipart/form-data

file: <招标文件.pdf>
```

#### AI分析（流式）
```http
POST /api/document/analyze-stream?stream=true
Content-Type: application/json

{
  "file_content": "招标文件原文...",
  "analysis_type": "overview"  // 或 "requirements"
}
```

#### 目录生成
```http
POST /api/outline/generate
Content-Type: application/json

{
  "overview": "项目概述内容...",
  "requirements": "技术评分要求..."
}
```

#### 内容生成（流式）
```http
POST /api/content/generate-chapter-stream?use_qwen=true
Content-Type: application/json

{
  "chapter": {
    "id": "1.1",
    "title": "项目背景",
    "word_count": 1000
  },
  "project_overview": "项目概述...",
  "parent_chapters": [],
  "regeneration_prompt": "请扩充关于数据安全的内容",
  "original_content": "原有内容..."
}
```

#### Word导出
```http
POST /api/document/export
Content-Type: application/json

{
  "content": {
    "1.1": "章节1.1的HTML内容...",
    "1.2": "章节1.2的HTML内容..."
  },
  "outline": [...]
}
```

---

## ❓ 常见问题

### Q1: 前端启动后访问报错"Cannot GET /"？
**A**: 检查是否在开发模式下运行前端（`npm start`），生产模式需先构建（`npm run build`）并使用单端口脚本启动。

### Q2: 后端报错"数据库连接失败"？
**A**: 检查`backend/app/db_config.py`配置，确保MySQL服务已启动且账号密码正确：
```bash
# 测试MySQL连接
mysql -h 10.11.30.18 -u root -p123456 -e "SHOW DATABASES;"
```

### Q3: AI生成内容为空或报错？
**A**: 可能原因：
1. API Key未配置或失效（检查前端"配置"面板）
2. 本地Qwen服务未启动（检查`http://localhost:10086/v1/models`）
3. Prompt超长（检查后端日志，调整`max_tokens`）

### Q4: 知识库上传文件后检索不到？
**A**: 
1. 检查Embedding模型路径（`backend/app/services/rag_service.py`）
2. 确认ChromaDB持久化路径有写权限（`backend/data/chroma_db`）
3. 清空重建：
```python
# 进入Python交互式
from app.services.rag_service import get_rag_service
rag = get_rag_service()
rag.clear()  # 清空知识库
```

### Q5: 导出Word格式错乱？
**A**: 
1. 检查前端ReactQuill编辑器是否使用了非标准HTML标签
2. 确认后端`process_html_content`函数是否正确解析HTML
3. 尝试使用"清除格式"按钮后重新生成

### Q6: 流式输出卡顿或每字符换行？
**A**: 已在最新版本修复（见FINAL_FIX_README.md），如仍有问题：
1. 检查`backend/app/routers/content.py`是否应用了最新修复
2. 前端检查是否启用了防抖优化（`ContentEdit.tsx`）
3. 网络原因：尝试关闭VPN或切换网络

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发流程
1. Fork本仓库
2. 创建特性分支（`git checkout -b feature/AmazingFeature`）
3. 提交更改（`git commit -m 'Add some AmazingFeature'`）
4. 推送到分支（`git push origin feature/AmazingFeature`）
5. 发起Pull Request

### 代码规范
- **Python**：遵循PEP 8，使用Black格式化
- **TypeScript**：遵循Airbnb规范，使用Prettier格式化
- **提交信息**：遵循Conventional Commits（如`feat:`, `fix:`, `docs:`）

### 测试要求
- 新功能必须包含单元测试
- 确保所有测试通过（`pytest backend/tests`）
- API变更需更新Swagger文档

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化Python Web框架
- [React](https://reactjs.org/) - 用户界面构建库
- [Ant Design](https://ant.design/) - 企业级UI组件库
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [Qwen](https://github.com/QwenLM/Qwen) - 阿里云通义千问大模型

---

<div align="center">

**⭐ 如果觉得项目有帮助，请给个Star支持一下！**

</div>