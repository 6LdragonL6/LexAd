# LexAd — 广告合规审查平台 v0.4.1

广告合规审查平台，面向企业内部市场部与法务部的两部门审查流程：提交广告物料 → 后台 AI 审查 → 结果展示 → 法务审核 → 决策（通过/退回/有条件通过）。

## v0.4.1 新特性

**后台审查任务**：提交后立即返回审查任务，结果页通过轮询展示处理中、完成或失败状态；支持返回工作台和失败后重试，不再无限停留在“审查进行中”。

**五级知识库浏览**：法规数据库按 L1 法律、L2 行业、L3 案例、L4 平台、L5 模板分类，并支持站内查看知识库正文。

**角色与安全修复**：法务端不再显示或访问提交物料页面；后端增加角色和资源归属校验；修复原文渲染 XSS、上传路径穿越、正文重复、AI 异常残留及重复法务决定问题。

**大尺寸左侧导航**：功能入口统一收纳到左上角菜单按钮和 300px 左侧抽屉，使用纵向大尺寸菜单项；支持遮罩、关闭按钮和 Esc 关闭，并按市场、法务和管理员角色过滤入口。

**可靠性改进**：增加审查任务数据库迁移和安全回归测试，CI 不再忽略后端测试失败，Render 启动时自动执行数据库迁移。

## v0.4.0 新特性

**文件上传与多格式提取**：支持 JPG / PNG / GIF / BMP / PDF / DOCX / PPTX / XLSX / TXT，自动提取文本内容（PDF→PyMuPDF、Office→python-docx/pptx/openpyxl、图片→Tesseract OCR），提取失败自动降级 OCR 兜底，提交前可预览编辑。

**测试物料批量验证**：内置 65 条标注广告案例（55违规+10合规），端到端验证审查引擎的合规/违规二分类与风险等级判定，输出 CSV 报告，支持自动清理测试数据。

**天蓝色系统一与无障碍修复**：品牌色从蓝色(#2563EB)统一为天蓝色(#0EA5E9)，覆盖所有页面、组件、链接和 favicon；修复按钮 disabled/loading 状态下视觉消失问题。

## 技术栈

| 层     | 技术                              |
|--------|-----------------------------------|
| 前端   | Vue 3 + Vite + TypeScript + Pinia + Vue Router + Axios + UnoCSS |
| 后端   | FastAPI + Python 3.11 + SQLAlchemy 2.0 + Alembic + Pydantic v2 |
| 数据库 | Neon PostgreSQL（云端用户数据）     |
| AI引擎 | DeepSeek API (deepseek-chat)      |
| 向量库 | ChromaDB（本地案例语义检索）        |
| 规则匹配 | pyahocorasick（AC 自动机多模式匹配）|
| 部署   | Render (Web Service + Static) + Docker Compose |

## 目录结构

```
LexAd/
├── backend/                    FastAPI 应用
│   ├── app/
│   │   ├── main.py            应用入口
│   │   ├── api/v1/            API 路由与端点
│   │   │   ├── router.py
│   │   │   └── endpoints/     auth, materials, reviews, knowledge
│   │   ├── core/              配置、安全、日志、异常
│   │   ├── db/                数据库会话、模型基类、种子数据
│   │   ├── models/            数据库模型 (User, Material, Review)
│   │   ├── schemas/           Pydantic 模型
│   │   ├── services/          业务逻辑层
│   │   │   ├── material_service.py
│   │   │   ├── review_service.py
│   │   │   ├── file_extraction.py    文件提取服务（v0.4.0 新增）
│   │   │   └── parsers/              格式解析器（v0.4.0 新增）
│   │   │       ├── image_parser.py   OCR（Tesseract）
│   │   │       ├── pdf_parser.py     PDF（PyMuPDF + OCR 降级）
│   │   │       ├── office_parser.py  DOCX/PPTX/XLSX
│   │   │       └── text_parser.py    TXT（编码检测）
│   │   ├── engine/            审查引擎流水线
│   │   │   ├── layer1_hard_rules.py  硬规则匹配（AC 自动机）
│   │   │   ├── layer2_semantic.py    语义推理（DeepSeek + ChromaDB）
│   │   │   └── pipeline.py           流水线编排
│   │   └── scripts/           批量工具脚本（v0.4.0 新增）
│   │       └── validate_materials.py  测试物料批量验证
│   ├── alembic/               数据库迁移
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   Vue 3 SPA
│   ├── src/
│   │   ├── api/               API 请求封装 (client, auth, materials, reviews, knowledge)
│   │   ├── components/
│   │   │   ├── layout/        TopBar, ThreeColLayout
│   │   │   ├── review/        ScoreBox, IssueList, EngineReport, SummaryPanel
│   │   │   └── common/        通用组件（预留）
│   │   ├── composables/       组合式函数（预留）
│   │   ├── layouts/           DefaultLayout, ReviewLayout
│   │   ├── pages/             LoginPage, HomePage, SubmitPage（含文件上传+预览编辑）, ResultPage, LegalDashboard, LegalDetail, KnowledgePage
│   │   ├── router/            路由配置 + 角色守卫
│   │   ├── stores/            Pinia 状态管理 (user)
│   │   ├── types/             TypeScript 类型定义
│   │   └── styles/            UnoCSS 配置 + CSS 变量
│   ├── package.json
│   └── Dockerfile
├── knowledge/                  法律知识库（本地）
│   ├── L1_laws/               法律法规全文（13 部）
│   ├── L2_industry/           行业专项规则（7 个行业）
│   ├── L3_cases/              行政处罚案例（1651 件）
│   ├── L4_platforms/          平台规则库
│   └── L5_templates/          违禁词映射 + 改写模板
├── data/                       预处理生成的结构化规则数据（JSON）
├── chroma_data/               ChromaDB 持久化目录（案例向量）
├── docs/                       设计文档与实施计划
├── docker-compose.yml
├── render.yaml
└── .github/workflows/         CI/CD
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL（或使用 Neon 云端实例）

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量（参考 backend/.env.example）
cp backend/.env.example backend/.env

# 数据库迁移
alembic upgrade head

# 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 停止本地服务（Windows）

前端和后端分别占用当前终端运行。正常停止时，应在对应 CMD 或 PowerShell 窗口按：

```text
Ctrl + C
```

看到终止提示后再关闭终端窗口。不要直接关闭正在运行服务的 CMD；Node/Vite 子进程有时会继续在后台监听端口。

如果终端已经关闭，可以先检查端口：

```cmd
netstat -ano | findstr :5173
netstat -ano | findstr :8000
```

输出最后一列是 PID。确认 PID 属于本项目后，按进程树停止：

```cmd
taskkill /PID <PID> /T /F
```

结束后再次运行 `netstat`，没有 `LISTENING` 输出即表示端口已经释放。不要直接结束所有 `node.exe` 或 `python.exe`，否则可能误停其他项目。

### Docker Compose

```bash
docker-compose up
```

Docker Compose 会挂载 `data/`、`knowledge/` 和 `chroma_data/`。单独构建后端镜像时，也必须把这三个目录部署到配置对应的位置。

## API 端点

### 认证 `/api/v1/auth`
| 方法 | 路径    | 说明         |
|------|---------|-------------|
| POST | /login  | 用户名+密码登录 |
| GET  | /me     | 当前用户信息   |

### 物料 `/api/v1/materials`
| 方法 | 路径           | 说明               |
|------|---------------|--------------------|
| POST | /submit       | 提交广告物料（支持文件上传） |
| POST | /preview-text | 预览文件提取文本（v0.4.0 新增） |
| GET  | /list         | 物料列表（按角色过滤）|
| GET  | /{id}         | 物料详情            |
| PUT  | /{id}         | 修改物料（退回后重提交）|
| GET  | /{id}/versions | 版本历史            |

### 审查 `/api/v1/reviews`
| 方法 | 路径                   | 说明           |
|------|-----------------------|----------------|
| POST | /ai-review            | 创建后台 AI 审查任务（HTTP 202） |
| GET  | /queue                | 法务审核队列     |
| GET  | /by-material/{id}     | 按物料查询审查   |
| GET  | /{id}                 | 审查结果详情     |
| POST | /{id}/decision        | 法务审核决定     |

### 知识库 `/api/v1/knowledge`
| 方法 | 路径             | 说明                         |
|------|-----------------|------------------------------|
| GET  | /catalog/{layer}| 获取 L1-L5 指定分类和分组目录 |
| GET  | /content        | 读取目录内指定 TXT 正文        |

## 审查引擎

四层流水线架构，对应五级知识库：

| 引擎层 | 说明                | 数据来源                        |
|--------|--------------------|---------------------------------|
| 第一层 | 硬规则匹配（AC 自动机）| KB-L1 硬性禁止条款 + KB-L5 违禁词 |
| 第二层 | 语义推理（DeepSeek） | KB-L1 法条 + KB-L2 行业规则 + KB-L3 ChromaDB Top5 案例 |
| 第三层 | 基础证明材料检查      | 当前使用需证据表述关键词，待增强    |
| 第四层 | 平台差异适配占位      | 已展示目标平台，完整规则引擎待实现   |

审查任务由 FastAPI 进程内后台任务执行。当前方案适用于单实例或轻量部署；若需要进程重启恢复、自动重试或多实例调度，应升级为 Redis + Celery/RQ。

## 预置测试账户

| 角色   | 用户名             | 密码     | 数量 |
|--------|-------------------|----------|------|
| 管理员 | admin             | admin123 | 1    |
| 市场部 | market01~market10 | test1234 | 10   |
| 法务部 | legal01~legal10   | test1234 | 10   |

## 环境变量

| 变量                | 说明                      |
|---------------------|--------------------------|
| `DATABASE_URL`      | Neon PostgreSQL 连接字符串  |
| `SECRET_KEY`        | JWT 签名密钥               |
| `APP_ENV`           | 运行环境 (development/production) |
| `FRONTEND_ORIGIN`   | 前端域名 (CORS)            |
| `CORS_ORIGINS`      | 额外 CORS 域名（JSON 数组）  |
| `DEEPSEEK_API_KEY`  | DeepSeek API Key          |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址          |
| `DEEPSEEK_MODEL`    | 模型名称（默认 deepseek-chat）|

## 文档

- [v0.4.1 迭代报告](docs/v0.4.1-iteration-report.md)
- [v0.4.1 稳定性与安全设计](docs/superpowers/specs/2026-07-05-lexad-v0.4.1-stability-security-design.md)
- [v0.4.0 设计文档](docs/superpowers/specs/2026-05-17-lexad-v0.4.0-design.md)
- [v0.3.0 设计文档](docs/superpowers/specs/2026-05-15-lexad-v0.3.0-design.md)
- [v0.3.0 实施计划](docs/superpowers/plans/2026-05-15-lexad-v0.3.0-core.md)

## 版本历史

| 版本   | 日期       | 说明                                      |
|--------|-----------|------------------------------------------|
| v0.4.1 | 2026-07-05 | 后台异步审查、L1-L5 知识库浏览、大尺寸左侧导航、角色权限、安全修复、迁移与测试增强 |
| v0.4.0 | 2026-05-17 | 文件上传与多格式提取（8种格式+OCR降级）、测试物料批量验证（65条标注案例）、天蓝色系统一与按钮状态修复 |
| v0.3.0 | 2026-05-15 | 两部门审查交互闭环、四层 AI 引擎、知识库集成    |
| v0.2.0 | 2026-05   | 项目骨架 (FastAPI + Vue 3)，Mock 占位审查     |
| v0.1.0 | 2026-04   | 初始原型，单文件 FastAPI 应用                  |
