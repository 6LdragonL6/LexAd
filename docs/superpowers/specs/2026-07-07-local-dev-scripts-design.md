# LexAd 本地一键启动/关闭脚本设计

## 背景

当前本地测试需要分别进入 `backend` 和 `frontend` 目录手动启动服务：

- 后端：`uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- 前端：`npm run dev`

测试者希望通过双击脚本完成前后端启动和关闭，同时能看到日志和错误信息。

## 推荐方案

采用 `.bat` 作为双击入口，内部调用 PowerShell `.ps1` 执行实际逻辑。

文件规划：

- `start-dev.bat`：双击启动入口。
- `stop-dev.bat`：双击关闭入口。
- `scripts/start-dev.ps1`：负责启动后端、前端、记录进程信息。
- `scripts/stop-dev.ps1`：负责读取进程信息并关闭本项目启动的服务。
- `scripts/.dev-pids.json`：运行时生成的 PID 记录文件，不需要提交。

## 启动行为

`start-dev.bat` 双击后执行 `scripts/start-dev.ps1`。

启动脚本会：

1. 定位仓库根目录，避免用户从错误目录启动。
2. 检查 `backend` 和 `frontend` 目录是否存在。
3. 优先使用 `backend/venv/Scripts/python.exe` 启动后端；如果不存在，则回退到系统 `python`。
4. 使用 `npm.cmd run dev -- --host 0.0.0.0` 启动前端。
5. 分别打开后端和前端命令行窗口，让用户能持续看到日志和报错。
6. 将启动得到的进程 PID 写入 `scripts/.dev-pids.json`。

默认端口保持项目现状：

- 后端：`8000`
- 前端：`5173`

## 关闭行为

`stop-dev.bat` 双击后执行 `scripts/stop-dev.ps1`。

关闭脚本会：

1. 读取 `scripts/.dev-pids.json`。
2. 只关闭记录文件中属于本次项目启动的进程。
3. 使用进程树关闭，避免留下子进程占用端口。
4. 删除 PID 记录文件。
5. 如果 PID 文件不存在，提示用户当前没有由脚本记录的运行实例。

关闭脚本不会批量终止所有 `node`、`npm`、`python` 或 `uvicorn` 进程，避免误伤其他项目。

## 错误处理

启动脚本需要在窗口中保留错误输出，常见问题包括：

- 未安装 Node.js 或 npm。
- 未安装 Python。
- 后端虚拟环境缺失依赖。
- 前端依赖未安装，需要先执行 `npm install`。
- 端口 `8000` 或 `5173` 已被占用。

遇到启动失败时，日志窗口保留，测试者可以直接查看错误。

## 测试方式

实现后验证：

1. 双击或执行 `start-dev.bat`，确认后端和前端窗口出现。
2. 访问 `http://localhost:5173`，确认前端可打开。
3. 访问 `http://localhost:8000/docs`，确认后端可打开。
4. 执行 `stop-dev.bat`，确认端口 `5173` 和 `8000` 释放。
5. 确认关闭脚本不会影响其他无关 Node/Python 进程。
