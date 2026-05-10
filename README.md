# LexAd — 广告合规审查平台 v0.2.0

广告合规审查平台。覆盖法律、行业、平台三层审查体系，支持文本与图片广告合规检测。

**注意：本版本为 Demo 骨架，所有审查结论均为占位/Mock 结果，不构成真实合规意见。**

## 技术栈

| 层    | 技术                             |
|-------|----------------------------------|
| 前端  | Vue 3 + Vite + TypeScript + Pinia |
| 后端  | FastAPI + Python 3.11 + SQLAlchemy |
| 数据库 | PostgreSQL (Neon)                |
| 部署  | Render (Web Service + Static)    |

## 目录结构

```
LexAd/
├─ backend/                  FastAPI 应用
│  ├─ app/
│  │  ├─ main.py            应用入口
│  │  ├─ core/               配置、安全、日志、异常
│  │  ├─ api/v1/             API 路由与端点
│  │  ├─ db/                 数据库会话与迁移
│  │  ├─ models/             数据库模型
│  │  ├─ schemas/            Pydantic 模型
│  │  ├─ crud/               数据操作
│  │  ├─ services/           业务服务层
│  │  ├─ integrations/       第三方集成（预留）
│  │  ├─ tasks/              异步任务（预留）
│  │  ├─ storage/            文件存储（预留）
│  │  ├─ permissions/        权限控制（预留）
│  │  └─ utils/              工具函数
│  ├─ alembic/               数据库迁移
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/                 Vue 3 SPA
│  ├─ src/
│  │  ├─ api/                API 请求封装
│  │  ├─ components/         可复用组件
│  │  ├─ layouts/            布局
│  │  ├─ pages/              页面视图
│  │  ├─ router/             路由
│  │  ├─ stores/             Pinia 状态管理
│  │  ├─ types/              类型定义
│  │  └─ utils/              工具函数
│  ├─ package.json
│  └─ Dockerfile
├─ data/                     JSON 数据文件
├─ docs/                     文档
├─ shared/                   共享产物
├─ docker-compose.yml
├─ render.yaml
└─ .github/workflows/        CI/CD
```

## 快速开始

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问 http://localhost:5173

### Docker Compose

```bash
docker-compose up
```

## API 端点

| 方法 | 路径                           | 说明       |
|------|--------------------------------|-----------|
| GET  | `/health`                      | 健康检查    |
| GET  | `/api/v1/health`               | API 健康检查 |
| POST | `/api/v1/review/submit`        | 提交审查    |
| GET  | `/api/v1/review/result/{id}`   | 获取审查结果 |
| GET  | `/api/v1/review/cases`         | 案例库     |
| GET  | `/api/v1/review/templates`     | 改写模板库  |

## 部署

参见 [docs/deployment.md](docs/deployment.md)

### Render 部署

项目根目录的 `render.yaml` 定义了 Blueprint 自动部署：
- **lexad-api**: Python Web Service（后端）
- **lexad-frontend**: Static Site（前端）

### 环境变量

| 变量                | 说明            |
|---------------------|----------------|
| `DATABASE_URL`      | Neon PostgreSQL 连接字符串 |
| `SECRET_KEY`        | JWT 签名密钥    |
| `APP_ENV`           | 运行环境        |
| `FRONTEND_ORIGIN`   | 前端域名 (CORS) |
| `DEEPSEEK_API_KEY`  | DeepSeek API Key |

## 文档

- [架构设计](docs/architecture.md)
- [API 文档](docs/api.md)
- [部署指南](docs/deployment.md)
- [开发指南](docs/development.md)
