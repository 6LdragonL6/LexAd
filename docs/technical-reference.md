# LexAd 技术参考

本文承接首页 README 中不适合展开的技术细节。当前版本为 `v0.6.0`。

## 目录结构

```text
LexAd/
├── backend/                         FastAPI 应用
│   ├── app/
│   │   ├── api/v1/endpoints/         auth, materials, reviews, brands, knowledge, admin_knowledge
│   │   ├── core/                     配置、安全、日志、异常
│   │   ├── db/                       数据库会话、模型基类、种子数据
│   │   ├── engine/                   L1/L2/L4 审查、舆情审查、行业兼容解析
│   │   ├── models/                   User, Material, Review, Brand, Knowledge models
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
├── scripts/                          本地运行辅助脚本
├── docker-compose.yml
├── render.yaml
└── README.md
```

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router、Axios、UnoCSS |
| 后端 | FastAPI、Python 3.10+、SQLAlchemy 2、Alembic、Pydantic v2 |
| 数据库 | 本地 SQLite；显式模式可连接 Neon PostgreSQL |
| AI | DeepSeek OpenAI-compatible API |
| 规则匹配 | pyahocorasick |
| 向量检索 | ChromaDB |
| 文件解析 | PyMuPDF、python-docx、python-pptx、openpyxl、Pillow、Tesseract |
| 部署 | Render、Docker Compose、Nginx |

## 数据库升级

升级前建议备份数据库，然后执行：

```bash
cd backend
alembic upgrade head
```

关键迁移版本：

```text
c7f4a8b9d012  v0.4.2 舆情资料库、平台规则版本、导入记录、审计日志
d8a1f0e3b5c6  v0.5.0 物料 archived 状态
f3a8c2d9e714  v0.5.1 有条件通过状态
a4b7d1c6e825  v0.5.1 审查提交快照
294f05fbf95c  v0.6.0 品牌库与物料品牌关联
```

`c7f4a8b9d012` 还会为 `reviews` 表新增双模块状态、舆情结果和资料版本快照字段。

## 环境变量

| 变量 | 说明 |
|---|---|
| `DATABASE_MODE` | 数据库模式：`local` 或 `neon`，默认 `local` |
| `LOCAL_DATABASE_URL` | local 模式使用的 SQLite URL，默认 `sqlite:///./lexad.db` |
| `DATABASE_URL` | neon 模式使用的 PostgreSQL 连接字符串 |
| `SECRET_KEY` | JWT 签名密钥 |
| `APP_ENV` | 运行环境 |
| `FRONTEND_ORIGIN` | 前端域名 |
| `CORS_ORIGINS` | 额外 CORS 域名，逗号分隔 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | 模型名称，默认 `deepseek-chat` |
| `KNOWLEDGE_DIR` | L1-L5 知识库目录 |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目录 |

环境变量示例见：

- `backend/.env.example`
- `.env.example`

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
| GET | `/{id}/versions` | 版本历史（含已提交输入快照） |

### 审查 `/api/v1/reviews`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/ai-review` | 创建后台 AI 审查任务，返回 HTTP 202 |
| GET | `/queue` | 法务审核队列 |
| GET | `/by-material/{id}` | 按物料查询审查 |
| GET | `/{id}` | 审查结果详情 |
| POST | `/{id}/decision` | 法务审核决定 |

### 品牌 `/api/v1/brands`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 搜索 active 品牌列表 |
| POST | `/` | 创建品牌 |
| GET | `/{id}/profile` | 查询品牌聚合档案 |
| PATCH | `/{id}` | 编辑、归档或恢复品牌 |

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
