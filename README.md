# LexAd — 广告合规审查平台 v0.3.0

广告合规审查平台，面向企业内部市场部与法务部的两部门审查交互闭环：提交广告物料 → AI 四层引擎审查 → 结果展示 → 法务审核 → 决策（通过/退回/有条件通过）→ 版本管理。

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
│   │   └── engine/            审查引擎（四层流水线）
│   │       ├── layer1_hard_rules.py  硬规则匹配（AC 自动机）
│   │       ├── layer2_semantic.py    语义推理（DeepSeek + ChromaDB）
│   │       ├── layer3_evidence.py    证明材料检查
│   │       ├── layer4_platform.py    平台差异适配
│   │       └── pipeline.py           流水线编排
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
│   │   ├── pages/             LoginPage, HomePage, SubmitPage, ResultPage, LegalDashboard, LegalDetail, KnowledgePage
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

### Docker Compose

```bash
docker-compose up
```

## API 端点

### 认证 `/api/v1/auth`
| 方法 | 路径    | 说明         |
|------|---------|-------------|
| POST | /login  | 用户名+密码登录 |
| GET  | /me     | 当前用户信息   |

### 物料 `/api/v1/materials`
| 方法 | 路径           | 说明               |
|------|---------------|--------------------|
| POST | /submit       | 提交广告物料         |
| GET  | /list         | 物料列表（按角色过滤）|
| GET  | /{id}         | 物料详情            |
| PUT  | /{id}         | 修改物料（退回后重提交）|
| GET  | /{id}/versions | 版本历史            |

### 审查 `/api/v1/reviews`
| 方法 | 路径                   | 说明           |
|------|-----------------------|----------------|
| POST | /ai-review            | 触发 AI 审查    |
| GET  | /queue                | 法务审核队列     |
| GET  | /by-material/{id}     | 按物料查询审查   |
| GET  | /{id}                 | 审查结果详情     |
| POST | /{id}/decision        | 法务审核决定     |

### 知识库 `/api/v1/knowledge`
| 方法 | 路径            | 说明               |
|------|----------------|--------------------|
| GET  | /laws          | L1 法律法规列表+搜索 |
| GET  | /industry-rules| L2 行业规则（按行业筛选）|
| GET  | /cases         | L3 案例列表+搜索     |
| GET  | /platforms     | L4 平台规则（按平台筛选）|
| GET  | /templates     | L5 改写模板          |

## 审查引擎

四层流水线架构，对应五级知识库：

| 引擎层 | 说明                | 数据来源                        |
|--------|--------------------|---------------------------------|
| 第一层 | 硬规则匹配（AC 自动机）| KB-L1 硬性禁止条款 + KB-L5 违禁词 |
| 第二层 | 语义推理（DeepSeek） | KB-L1 法条 + KB-L2 行业规则 + KB-L3 ChromaDB Top5 案例 |
| 第三层 | 证明材料检查         | 识别需证据支持的表述              |
| 第四层 | 平台差异适配         | KB-L4 各平台规则差异             |

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

- [设计文档](docs/superpowers/specs/2026-05-15-lexad-v0.3.0-design.md)
- [实施计划](docs/superpowers/plans/2026-05-15-lexad-v0.3.0-core.md)

## 版本历史

| 版本   | 日期       | 说明                                      |
|--------|-----------|------------------------------------------|
| v0.3.0 | 2026-05-15 | 两部门审查交互闭环、四层 AI 引擎、知识库集成    |
| v0.2.0 | 2026-05   | 项目骨架 (FastAPI + Vue 3)，Mock 占位审查     |
| v0.1.0 | 2026-04   | 初始原型，单文件 FastAPI 应用                  |
