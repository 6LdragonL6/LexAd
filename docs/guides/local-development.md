# LexAd v0.7.1 本地开发指南

本文提供可直接执行的安装、启动、验证和排错步骤。默认使用本地 SQLite，不需要连接云数据库。

## 1. 环境要求

- Python 3.10 或更高版本；后端容器使用 Python 3.11
- Node.js 18 或更高版本
- npm
- 可选：Tesseract OCR，用于图片文字提取
- 可选：PostgreSQL / Neon，仅在显式选择 `neon` 模式时需要
- 可用的 DeepSeek API Key，用于完整 AI 审查；未配置时相关分域会提示人工复核

## 2. 首次安装

### Windows PowerShell

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

cd ..\frontend
npm install
```

### macOS / Linux

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

cd ../frontend
npm install
```

## 3. Windows 一键启动

在仓库根目录运行：

```text
start-dev.bat
```

脚本会：

1. 使用 `local` 数据库模式；
2. 执行本地 SQLite 迁移；
3. 幂等补充演示用户和品牌；
4. 启动后端 `8000` 端口和前端 `5173` 端口；
5. 记录本次启动的进程，供安全停止使用。

访问地址：

- Web 界面：<http://localhost:5173>
- OpenAPI 文档：<http://localhost:8000/docs>

停止服务：

```text
stop-dev.bat
```

停止脚本只处理本项目记录且身份匹配的进程，不会批量结束系统中的 Node 或 Python 进程。

## 4. 手动启动

后端：

```powershell
cd backend
venv\Scripts\activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端：

```powershell
cd frontend
npm.cmd run dev -- --host 0.0.0.0 --port 5173
```

macOS / Linux 将虚拟环境激活命令替换为 `source venv/bin/activate`，并使用 `npm run dev`。

## 5. 配置 AI 服务

推荐启动后使用管理员账号进入“系统管理 → AI 配置”：

1. 输入 DeepSeek API Key；
2. 点击验证并保存；
3. 确认状态显示已配置。

管理员数据库配置优先于 `DEEPSEEK_API_KEY` 环境变量。连接测试只验证 API 可用性，不代表法律、平台和舆情业务请求一定正确；业务正确性由结构化契约、引用校验和回归测试共同保证。

仅为兼容旧部署，也可以在 `backend/.env` 中配置：

```dotenv
DEEPSEEK_API_KEY=
```

不要把真实密钥提交到 Git。

## 6. 数据库模式

### 本地 SQLite

默认配置：

```dotenv
APP_ENV=development
DATABASE_MODE=local
LOCAL_DATABASE_URL=sqlite:///./lexad.db
SECRET_KEY=change-me-in-production
```

Windows 可显式启动：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start-dev.ps1 -DatabaseMode local
```

### Neon PostgreSQL

先设置连接串，再执行只读预检启动：

```powershell
$env:DATABASE_URL = 'postgresql://user:password@host/database?sslmode=require'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start-dev.ps1 -DatabaseMode neon
```

本地脚本的 `neon` 流程只检查连接与迁移状态，不会自动迁移远端数据库。需要升级远端数据库时，应在确认目标、备份和变更窗口后单独执行 `alembic upgrade head`。

SQLite 与 Neon 不自动同步品牌、物料、审查或资料数据。

## 7. 本地演示账号

开发种子数据包含：

| 角色 | 用户名 | 本地演示密码 |
| --- | --- | --- |
| 管理员 | `admin` | `admin123` |
| 市场部 | `market01`–`market10` | `test1234` |
| 法务部 | `legal01`–`legal10` | `test1234` |

这些账号只用于本地开发和产品演示。公开部署必须删除或替换默认凭据，并实施正式账号管理策略。

## 8. Docker Compose

```bash
docker compose up --build
```

停止：

```bash
docker compose down
```

当前 Compose 配置面向本地开发，默认使用后端配置中的本地数据库模式，并挂载 `data/`、`knowledge/` 和 `chroma_data/`。生产部署应单独配置数据库模式、密钥、持久化和备份。

## 9. 验证

后端测试：

```bash
cd backend
python -m pytest app/tests -q
```

前端生产构建：

```bash
cd frontend
npm run build
```

数据库迁移状态：

```bash
cd backend
alembic current
alembic heads
```

## 10. 常见问题

### 端口被占用

Windows：

```powershell
Get-NetTCPConnection -LocalPort 5173,8000 -ErrorAction SilentlyContinue
```

macOS / Linux：

```bash
lsof -i :5173
lsof -i :8000
```

确认进程确实属于本项目后再停止。

### 后端启动失败

依次检查：虚拟环境、依赖、`backend/.env`、数据库模式和迁移状态。

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

`APP_ENV=production` 时不能使用 `DATABASE_MODE=local`。

### AI 审查转人工复核

这通常表示 API Key 未配置、模型请求失败、资料库为空、平台缺少生效规则版本，或模型输出没有通过证据引用校验。查看结果页的分域提示和后端日志，管理员同时检查 AI 配置与资料版本。

### 平台列表为空

只有存在当前生效规则版本的平台才会作为可选项返回。请管理员创建规则集、导入结构化规则并启用有效版本。

### OCR 不可用

文字物料和可直接解析的文档仍可使用。需要图片 OCR 时安装 Tesseract，并确认系统命令可访问。
