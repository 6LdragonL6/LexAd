# LexAd 本地开发指南

本文说明如何在 Windows 和 macOS 上运行 LexAd。版本号保持 `v0.4.2`。

## 环境要求

- Python 3.10+
- Node.js 18+
- npm
- 可选：PostgreSQL。不配置 `DATABASE_URL` 时，后端使用本地 SQLite 回退。
- 可选：Tesseract OCR。只有需要 OCR 文件解析时才需要。

## Windows

### 第一次准备

在项目根目录打开 PowerShell：

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

cd ..\frontend
npm install
```

### 日常启动

双击项目根目录的：

```text
start-dev.bat
```

脚本会打开两个窗口：

- `LexAd Backend`：后端日志，默认端口 `8000`。
- `LexAd Frontend`：前端日志，默认端口 `5173`。

访问：

- 前端：<http://localhost:5173>
- 后端 API 文档：<http://localhost:8000/docs>

### 日常关闭

双击：

```text
stop-dev.bat
```

关闭脚本只会关闭 `start-dev.bat` 记录的进程，不会批量结束所有 Node、npm、Python 或 uvicorn 进程。

### 手动启动

如果不使用一键脚本，可以手动打开两个 PowerShell 窗口。

后端：

```powershell
cd backend
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端：

```powershell
cd frontend
npm.cmd run dev -- --host 0.0.0.0 --port 5173
```

PowerShell 下推荐使用 `npm.cmd`，可以减少脚本执行策略带来的干扰。

## macOS

### 第一次准备

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

cd ../frontend
npm install
```

### 日常启动

打开第一个终端启动后端：

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

打开第二个终端启动前端：

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

访问：

- 前端：<http://localhost:5173>
- 后端 API 文档：<http://localhost:8000/docs>

### 日常关闭

在前端和后端对应终端中按：

```text
Ctrl + C
```

如果终端已关闭但端口仍被占用，可以先查询端口，再确认进程属于本项目后关闭。

```bash
lsof -i :5173
lsof -i :8000
kill <PID>
```

不要直接批量结束所有 Node 或 Python 进程。

## Docker Compose

Windows 和 macOS 都可以使用 Docker Compose：

```bash
docker-compose up
```

停止：

```bash
docker-compose down
```

Docker Compose 会挂载：

- `data/`
- `knowledge/`
- `chroma_data/`

单独部署后端镜像时，也必须提供这些目录或对应环境变量。

## 常见问题

### 端口已被占用

默认端口：

- 前端：`5173`
- 后端：`8000`

Windows 查询：

```cmd
netstat -ano | findstr :5173
netstat -ano | findstr :8000
```

macOS 查询：

```bash
lsof -i :5173
lsof -i :8000
```

确认 PID 属于本项目后再结束。

### 前端启动失败

通常是依赖未安装或 Node 版本过低：

```bash
cd frontend
npm install
npm run dev
```

### 后端启动失败

通常是虚拟环境未激活、依赖未安装、数据库迁移未执行，或缺少环境变量：

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

后端环境变量可参考 `backend/.env.example`。

## 本地验证

后端测试：

```bash
cd backend
python -m pytest app/tests -q
```

前端构建：

```bash
cd frontend
npm run build
```

Windows PowerShell 下也可以使用：

```powershell
npm.cmd run build
```
