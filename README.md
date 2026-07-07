# LexAd — 广告合规与舆情风险审查平台 v0.4.2

LexAd 是面向企业市场部、法务部和管理员的广告发布前审查系统。当前流程为：提交广告物料 → 后台 AI 审查 → 法律合规与舆情风险双轴结果展示 → 法务审核 → 决策（通过/退回/有条件通过）。

## 版本定位

v0.4.2 是 v0.5.0 前的过渡版本。

本版本重点交付可运行框架、管理员维护入口和前后端闭环，不内置真实舆情案例库，也不自动抓取平台规则或实时舆情。等真实舆情 JSON 数据补入、人工复核并完成回归测试后，再进入 v0.5.0。

## v0.4.2 新特性

**管理员资料中心**：新增 `/admin/knowledge`，管理员可维护舆情案例、平台规则版本、导入记录和操作日志。

**舆情案例库框架**：支持自然语言录入舆情文本、事件经过和后果；支持 AI 整理为结构化案例；支持发布、归档、恢复和草稿删除。

**面向普通管理员的 JSON 导入**：批量导入放在“更多工具”中，支持模板、粘贴 JSON、预检、错误提示、重复编号处理和确认导入，不要求管理员接触数据库。

**平台规则版本管理**：管理员可创建平台规则集、添加规则版本、查看差异摘要、启用新版本和回滚旧版本；审核结果会保存当次平台规则版本快照。

**双轴风险结果**：法律合规风险与舆情风险分开展示。舆情风险不计入法律合规分，避免把品牌声誉风险和广告法风险混成一个分数。

**资料库空态明确提示**：舆情资料库为空时，系统返回“资料库待补充”，不会伪装成低风险。

**提交流程简化**：提交页只要求物料内容、行业和投放平台；物料名称、类型、优先级、截止时间收进“更多设置”。

**行业可多选（兼容实现）**：前端支持多选行业。后端为避免 0.4.2 扩大迁移范围，仍使用 `industry: string` 兼容存储，多个行业以 `、` 拼接；审查引擎会拆分后按多行业匹配 L2 行业规则和舆情案例。

## v0.4.1 保留能力

- 后台异步审查任务：提交后立即返回结果页，轮询展示处理中、完成或失败状态。
- L1-L5 知识库浏览：法规、行业规则、案例、平台规则、模板按层级展示。
- 角色权限：市场、法务、管理员按角色访问不同入口。
- 安全修复：原文渲染 XSS 防护、上传路径穿越防护、资源归属校验、重复法务决定防护。
- 大尺寸左侧导航：左上角菜单按钮 + 300px 左侧抽屉。

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router、Axios、UnoCSS |
| 后端 | FastAPI、Python 3.10+、SQLAlchemy 2、Alembic、Pydantic v2 |
| 数据库 | Neon PostgreSQL；本地可回退 SQLite |
| AI | DeepSeek OpenAI-compatible API |
| 规则匹配 | pyahocorasick |
| 向量检索 | ChromaDB |
| 文件解析 | PyMuPDF、python-docx、python-pptx、openpyxl、Pillow、Tesseract |
| 部署 | Render、Docker Compose、Nginx |

## 目录结构

```text
LexAd/
├── backend/                         FastAPI 应用
│   ├── app/
│   │   ├── api/v1/endpoints/         auth, materials, reviews, knowledge, admin_knowledge
│   │   ├── core/                     配置、安全、日志、异常
│   │   ├── db/                       数据库会话、模型基类、种子数据
│   │   ├── engine/                   L1/L2/L4 审查、舆情审查、行业兼容解析
│   │   ├── models/                   User, Material, Review, Knowledge models
│   │   ├── schemas/                  Pydantic 模型
│   │   ├── services/                 物料、审查、模型、资料中心、文件解析服务
│   │   └── tests/                    后端回归测试
│   ├── alembic/versions/             数据库迁移
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                         Vue 3 SPA
│   ├── src/
│   │   ├── api/                      API 请求封装
│   │   ├── components/layout/         TopBar 等布局组件
│   │   ├── pages/                    Home, Submit, Result, Legal, Knowledge, AdminKnowledge
│   │   ├── router/                   路由与角色守卫
│   │   ├── stores/                   Pinia 用户状态
│   │   └── types/                    TypeScript 类型
│   ├── package.json
│   └── Dockerfile
├── data/                             结构化规则数据
├── knowledge/                        L1-L5 本地知识库
├── chroma_data/                      ChromaDB 持久化目录
├── docs/                             设计、计划、迭代报告、管理员说明
├── docker-compose.yml
├── render.yaml
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL，或本地 SQLite 回退
- 可选：Tesseract OCR

### 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量，参考 backend/.env.example
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

macOS/Linux 激活虚拟环境时使用：

```bash
source venv/bin/activate
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
docker-compose up
```

Docker Compose 会挂载 `data/`、`knowledge/` 和 `chroma_data/`。单独部署后端镜像时，也必须提供这些目录或对应环境变量。

## 数据库升级

升级前建议备份数据库，然后执行：

```bash
cd backend
alembic upgrade head
```

v0.4.2 目标迁移版本：

```text
c7f4a8b9d012
```

该迁移新增舆情资料库、平台规则版本、导入记录、审计日志，以及 `reviews` 表中的双模块状态、舆情结果和资料版本快照字段。

## API 端点

### 认证 `/api/v1/auth`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/login` | 用户名和密码登录 |
| GET | `/me` | 当前用户信息 |

### 物料 `/api/v1/materials`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/submit` | 提交广告物料，支持文件上传 |
| POST | `/preview-text` | 预览文件提取文本 |
| GET | `/list` | 按角色过滤物料列表 |
| GET | `/{id}` | 物料详情 |
| PUT | `/{id}` | 修改物料 |
| GET | `/{id}/versions` | 版本历史 |

### 审查 `/api/v1/reviews`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/ai-review` | 创建后台 AI 审查任务，返回 HTTP 202 |
| GET | `/queue` | 法务审核队列 |
| GET | `/by-material/{id}` | 按物料查询审查 |
| GET | `/{id}` | 审查结果详情 |
| POST | `/{id}/decision` | 法务审核决定 |

### 知识库 `/api/v1/knowledge`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/catalog/{layer}` | 获取 L1-L5 指定分类和分组目录 |
| GET | `/content` | 读取目录内指定 TXT 正文 |

### 管理员资料中心 `/api/v1/admin/knowledge`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/public-opinion/events` | 舆情事件列表与创建 |
| GET/PUT/DELETE | `/public-opinion/events/{id}` | 舆情事件详情、编辑、删除草稿 |
| POST | `/public-opinion/events/{id}/structure` | 调用统一模型服务整理舆情事件 |
| POST | `/public-opinion/events/{id}/publish` | 发布舆情事件 |
| POST | `/public-opinion/events/{id}/archive` | 归档舆情事件 |
| POST | `/public-opinion/events/{id}/restore` | 恢复舆情事件 |
| GET | `/public-opinion/import-template` | 获取 JSON 导入模板 |
| POST | `/public-opinion/import/preview` | 预检舆情 JSON |
| POST | `/public-opinion/imports/{job_id}/confirm` | 确认导入 |
| GET/POST | `/platform-rules` | 平台规则集列表与创建 |
| GET/PUT | `/platform-rules/{id}` | 平台规则集详情与编辑 |
| POST | `/platform-rules/{id}/versions` | 新建平台规则版本 |
| POST | `/platform-rule-versions/{id}/activate` | 启用规则版本 |
| POST | `/platform-rule-versions/{id}/rollback` | 回滚规则版本 |
| GET | `/imports` | 导入记录 |
| GET | `/audit-logs` | 操作日志 |

## 审查引擎

| 模块 | 说明 |
|---|---|
| L1 硬规则 | 使用 AC 自动机匹配硬性禁止条款和违禁词 |
| L2 语义推理 | 调用统一模型服务，结合 L1 法条、L2 行业规则和相似案例进行语义审查 |
| L3 证明材料 | 标记“经临床验证”“数据显示”等需要证明材料支撑的表述 |
| L4 平台规则 | 使用管理员启用的平台规则版本，记录版本快照 |
| 舆情风险 | 使用已发布舆情案例库，结合触发词、行业/平台标签、相似案例和模型解释输出独立风险轴 |

法律合规审查与舆情审查使用同一模型服务和统一 API 配置，内部按任务类型区分提示词与解析逻辑。

## 管理员资料流程

### 舆情案例

1. 管理员在资料中心填写事件标题、舆情文本/事件经过、事件后果。
2. 保存为草稿。
3. 点击“AI 帮我整理事件”。
4. 人工复核结构化结果。
5. 发布后进入舆情资料库。
6. 不再适用的案例使用归档，草稿可删除。

### 批量 JSON

1. 打开“更多工具：JSON 批量导入”。
2. 填入模板或粘贴 JSON。
3. 预检导入。
4. 修复错误或确认重复编号处理方式。
5. 确认导入为草稿。
6. 逐条复核后发布。

### 平台规则

1. 每个平台建立一个规则集。
2. 每次规则更新建立一个新版本。
3. 填写来源、正文、生效时间和结构化规则。
4. 查看差异摘要。
5. 启用或回滚版本。

## 预置测试账户

| 角色 | 用户名 | 密码 | 数量 |
|---|---|---|---|
| 管理员 | `admin` | `admin123` | 1 |
| 市场部 | `market01` ~ `market10` | `test1234` | 10 |
| 法务部 | `legal01` ~ `legal10` | `test1234` | 10 |

## 环境变量

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 连接字符串；为空时本地回退 SQLite |
| `SECRET_KEY` | JWT 签名密钥 |
| `APP_ENV` | 运行环境 |
| `FRONTEND_ORIGIN` | 前端域名 |
| `CORS_ORIGINS` | 额外 CORS 域名，逗号分隔 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | 模型名称，默认 `deepseek-chat` |
| `KNOWLEDGE_DIR` | L1-L5 知识库目录 |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目录 |

## 本地验证

```bash
cd backend
python -m pytest app/tests -q

cd ../frontend
npm.cmd run build
```

PowerShell 下使用 `npm.cmd run build` 可以避开脚本执行策略问题。

## 停止本地服务（Windows）

正常停止时，在对应终端按：

```text
Ctrl + C
```

如果终端已关闭但端口仍被占用：

```cmd
netstat -ano | findstr :5173
netstat -ano | findstr :8000
taskkill /PID <PID> /T /F
```

确认 PID 属于本项目后再结束，不要批量终止所有 Node 或 Python 进程。

## 文档

- [v0.4.2 迭代报告](docs/v0.4.2-iteration-report.md)
- [v0.4.2 管理员资料中心使用说明](docs/v0.4.2-admin-knowledge-center-guide.md)
- [v0.4.2 / v0.5.0 设计](docs/superpowers/specs/2026-07-07-lexad-v0.4.2-v0.5.0-design.md)
- [v0.4.2 / v0.5.0 实施计划](docs/superpowers/plans/2026-07-07-lexad-v0.4.2-v0.5.0-implementation.md)
- [v0.4.1 迭代报告](docs/v0.4.1-iteration-report.md)

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| v0.4.2 | 2026-07-07 | 过渡版本：管理员资料中心、舆情案例库框架、平台规则版本管理、双轴风险结果、JSON 导入、多行业兼容提交 |
| v0.4.1 | 2026-07-05 | 后台异步审查、L1-L5 知识库浏览、大尺寸左侧导航、角色权限、安全修复、迁移与测试增强 |
| v0.4.0 | 2026-05-17 | 文件上传与多格式提取、测试物料批量验证、天蓝色系统一与按钮状态修复 |
| v0.3.0 | 2026-05-15 | 两部门审查交互闭环、四层 AI 引擎、知识库集成 |
| v0.2.0 | 2026-05 | FastAPI + Vue 3 项目骨架，Mock 占位审查 |
| v0.1.0 | 2026-04 | 初始原型，单文件 FastAPI 应用 |
