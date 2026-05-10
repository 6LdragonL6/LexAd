# LexAd v0.2.0 Release Notes

> 发布日期：2026-05-10 | 从 v0.1.0 (单服务 FastAPI 骨架) 重构为单仓库前后端分离架构

---

## 一、版本概述

v0.2.0 完成了从 **FastAPI 单体 Jinja2 服务** 向 **Vue 3 + FastAPI 前后端分离** 的架构升级。所有 v0.1.0 的业务逻辑（7 个审查服务、Pydantic Schema、工具函数）均保留并迁移到新架构中。项目现在支持 Render 双服务部署（Web Service + Static Site）并预留了 Neon PostgreSQL 数据库接口。

---

## 二、架构变更

### 从

```
LexAd/
├── app/            FastAPI + Jinja2 + HTMX（单体）
├── data/           JSON 数据
├── requirements.txt
└── render.yaml     单一 Web Service
```

### 到

```
LexAd/
├── backend/         FastAPI REST API（无模板渲染）
├── frontend/        Vue 3 SPA（独立构建部署）
├── data/            保持不变
├── docs/            架构/API/部署/开发文档
├── shared/          共享产物预留
├── .github/         CI/CD
├── docker-compose.yml
├── render.yaml      双服务 Blueprint
└── .env.example
```

---

## 三、新增文件清单（76 个）

### 后端 (34 文件)

| 路径 | 说明 |
|------|------|
| `backend/app/main.py` | FastAPI 入口：CORS + 异常处理 + `/api/v1` 路由 |
| `backend/app/core/config.py` | pydantic-settings，21 个配置项，Neon PG 连接位 |
| `backend/app/core/security.py` | JWT 签发 / 验证 |
| `backend/app/core/logging.py` | 统一日志配置 |
| `backend/app/core/exceptions.py` | 5 级异常类 |
| `backend/app/api/deps.py` | 依赖注入（get_db） |
| `backend/app/api/v1/router.py` | v1 路由聚合 |
| `backend/app/api/v1/endpoints/health.py` | `/api/v1/health/` |
| `backend/app/api/v1/endpoints/auth.py` | `/api/v1/auth/*`（占位 501） |
| `backend/app/api/v1/endpoints/users.py` | `/api/v1/users/*`（占位 501） |
| `backend/app/api/v1/endpoints/review.py` | `/api/v1/review/*`（提交审查 + 结果查询 + 案例库 + 模板库） |
| `backend/app/db/base.py` | SQLAlchemy DeclarativeBase |
| `backend/app/db/session.py` | 引擎工厂（Neon PG + SQLite fallback） |
| `backend/app/models/__init__.py` | ORM 模型预留 |
| `backend/app/schemas/models.py` | 18 个 Pydantic 模型（完整迁移） |
| `backend/app/crud/placeholder.py` | 泛型 CRUDBase |
| `backend/app/services/*` (10 文件) | 7 个业务服务 + pipeline + 2 占位 |
| `backend/app/integrations/placeholder.py` | 第三方集成基类 |
| `backend/app/tasks/placeholder.py` | 异步任务基类 |
| `backend/app/storage/placeholder.py` | 文件存储基类 |
| `backend/app/permissions/placeholder.py` | 权限控制基类 |
| `backend/app/utils/*` (4 文件) | 文件处理 / ID 生成 / JSON 读取 / OCR |
| `backend/app/tests/test_health.py` | 2 个基础测试 |
| `backend/pyproject.toml` | Python 项目配置 |
| `backend/requirements.txt` | 12 个依赖 |
| `backend/Dockerfile` | python:3.11-slim |
| `backend/alembic.ini` + `env.py` + `script.py.mako` | 数据库迁移工具 |

### 前端 (20 文件)

| 路径 | 说明 |
|------|------|
| `frontend/package.json` | Vue 3 + Vite + TS + Pinia + Axios |
| `frontend/vite.config.ts` | 路径别名 + `/api` 代理 |
| `frontend/tsconfig.json` | 严格模式 TypeScript |
| `frontend/index.html` | SPA 入口 |
| `frontend/src/main.ts` | createApp + Pinia + Router |
| `frontend/src/App.vue` | 根组件 |
| `frontend/src/router/index.ts` | 5 条路由（懒加载） |
| `frontend/src/stores/review.ts` | 审查状态 Pinia store |
| `frontend/src/api/client.ts` | Axios 实例（拦截器） |
| `frontend/src/api/review.ts` | 审查 API 封装（4 个请求） |
| `frontend/src/types/index.ts` | 12 个 TS 接口（对应后端 Schema） |
| `frontend/src/layouts/DefaultLayout.vue` | 导航 + 内容区 + 页脚 |
| `frontend/src/pages/HomePage.vue` | 首页（功能介绍 + CTA） |
| `frontend/src/pages/ReviewPage.vue` | 审查页（文本 + 图片上传） |
| `frontend/src/pages/ResultPage.vue` | 结果页（7 层完整渲染） |
| `frontend/src/pages/CasesPage.vue` | 案例库列表 |
| `frontend/src/pages/TemplatesPage.vue` | 模板库列表 |
| `frontend/src/styles/main.css` | 全局样式 |
| `frontend/Dockerfile` | 多阶段构建（Node → Nginx） |
| `frontend/nginx.conf` | SPA fallback + API 代理 |

### 基础设施 (12 文件)

| 路径 | 说明 |
|------|------|
| `render.yaml` | 双服务 Blueprint（lexad-api + lexad-frontend） |
| `docker-compose.yml` | 本地全栈编排 |
| `.env.example` | 环境变量模板 |
| `.gitignore` | 更新（Python + Node + IDE） |
| `.github/workflows/ci.yml` | 后端 pytest + 前端 build |
| `docs/architecture.md` | 架构设计文档 |
| `docs/api.md` | API 接口文档 |
| `docs/deployment.md` | 部署指南（Render + Neon + Docker） |
| `docs/development.md` | 开发指南 |
| `docs/review_and_todo.md` | 审查报告与待办清单 |
| `shared/README.md` | 共享产物说明 |
| `prompt_ai_integration.txt` | AI 集成需求规范（下一阶段） |

---

## 四、保留的 v0.1.0 代码

| 路径 | 状态 |
|------|------|
| `app/` 整体 | 保留不动（Jinja2 版本，可参考） |
| `data/*.json` (5 文件) | 保留不动（规则库模板） |
| `requirements.txt` (根目录) | 保留不动 |
| `prompt.txt` | 保留不动 |

---

## 五、审查中修复的问题

| # | 问题 | 严重度 | 修复 |
|---|------|--------|------|
| 1 | Health 路由注册无 prefix，端点 `/api/v1/` 而非 `/api/v1/health/` | 🔴 | `router.py` 添加 `prefix="/health"` |
| 2 | `config.py` 残留 `import os` 未使用 | 🟢 | 移除 |
| 3 | docker-compose 中 `VITE_API_BASE_URL` 设为容器内部地址，浏览器不可达 | 🔴 | 改为空字符串，走 nginx 代理 |
| 4 | CORS origins 空字符串污染列表 | 🟡 | 过滤空串后再 extend |
| 5 | 前端 Dockerfile 缺少 `VITE_API_BASE_URL` 构建参数 | 🟡 | 添加 `ARG` + `ENV` |
| 6 | `security.py` 中 `JWTError` 导入路径不明确 | 🟢 | 改为 `from jose.exceptions import JWTError` |
| 7 | `review.py` 残留 `File` 导入未使用 | 🟢 | 移除 |

---

## 六、已知缺口（下一阶段）

### 🔴 阻塞级

- `data/` 下 5 个 JSON 文件内容全空 → 审查始终返回 Mock 结果
- `backend/app/models/` 无 ORM 模型 → 数据库从未使用
- `POST /api/v1/auth/login` 返回 501 → 无用户认证

### 🟡 重要

- 仅 2 个测试（health check）
- `frontend/src/components/` 空目录
- `frontend/src/composables/` 空目录
- `prompt_ai_integration.txt` 全部未开始

### 🟢 可延后

- 异步任务（Celery）
- 对象存储（S3）
- Tesseract OCR 真实调用
- 管理后台模块

---

## 七、本地运行

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 八、部署

1. 推送代码到 GitHub
2. Render Dashboard → Blueprint → 选择仓库
3. `render.yaml` 自动创建两个服务：
   - `lexad-api` (Web Service, Python)
   - `lexad-frontend` (Static Site, Node → dist)
4. 在 Render 中配置 `DATABASE_URL`（Neon 连接字符串）

---

## 九、文件统计

| 指标 | v0.1.0 | v0.2.0 | 变化 |
|------|--------|--------|------|
| 总文件数 | ~30 | ~106 | +76 |
| 后端 Python 代码行 | ~900 | ~1,100 | +200 |
| 前端 TS/Vue 代码行 | 0 | ~750 | +750 |
| 文档文件 | 1 (README) | 7 | +6 |
| 测试用例 | 0 | 2 | +2 |
| 数据文件 | 5（空） | 5（空） | 0 |
| 目录数 | ~12 | ~45 | +33 |
