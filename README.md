# LexAd - 广告合规与舆情风险审查平台 v0.4.2

LexAd 是一个广告发布前审查系统，面向市场部、法务部和管理员。它把广告物料提交给后台审查，并分别展示法律合规风险和舆情风险，最后由法务给出通过、退回或有条件通过的决定。

当前版本仍为 `v0.4.2`。这是进入 `v0.5.0` 前的过渡版本，重点是把前后端、管理员资料维护、规则版本管理和审查闭环跑通。项目不内置真实舆情案例库，也不自动抓取平台规则或实时舆情。

## 你可以用它做什么

- 提交广告文案或物料，发起 AI 审查。
- 查看法律合规风险和舆情风险两条结果轴。
- 法务在审核队列中做最终决定。
- 管理员维护舆情案例、平台规则版本、导入记录和操作日志。
- 使用 L1-L5 知识库浏览法规、行业规则、案例、平台规则和模板。

## 快速运行

环境要求：

- Python 3.10+
- Node.js 18+
- npm
- 可选：PostgreSQL。不配置 `DATABASE_URL` 时，后端使用本地 SQLite。

### Windows

第一次运行先准备依赖：

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

cd ..\frontend
npm install
```

之后日常启动直接双击项目根目录的：

- `start-dev.bat`：一键启动前端和后端，并打开日志窗口。
- `stop-dev.bat`：一键关闭由启动脚本记录的前后端进程。

如果想手动启动，也可以打开两个 PowerShell 窗口。

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

### macOS

第一次运行先准备依赖：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

cd ../frontend
npm install
```

之后日常启动时，打开第一个终端启动后端：

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

再打开第二个终端启动前端：

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

停止时，在前端和后端终端中按 `Ctrl + C`。

启动后访问：

- 前端：<http://localhost:5173>
- 后端 API 文档：<http://localhost:8000/docs>

Docker、端口占用、依赖缺失等排错说明见 [本地开发指南](docs/local-development.md)。

## 默认测试账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | `admin` | `admin123` |
| 市场部 | `market01` ~ `market10` | `test1234` |
| 法务部 | `legal01` ~ `legal10` | `test1234` |

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Axios、UnoCSS
- 后端：FastAPI、Python 3.10+、SQLAlchemy 2、Alembic、Pydantic v2
- 数据库：Neon PostgreSQL；本地可回退 SQLite
- AI：DeepSeek OpenAI-compatible API
- 部署：Render、Docker Compose、Nginx

更多目录结构、API 端点、环境变量和验证命令见 [技术参考](docs/technical-reference.md)。

## v0.4.2 重点变化

- 新增管理员资料中心 `/admin/knowledge`。
- 支持舆情案例草稿、AI 结构化整理、发布、归档和恢复。
- 支持普通管理员通过 JSON 批量导入舆情案例。
- 支持平台规则版本管理、启用和回滚。
- 法律合规风险与舆情风险分开展示。
- 舆情资料库为空时明确提示“资料库待补充”。
- 提交流程更轻，行业支持多选并兼容旧后端字段。

## 文档入口

- [本地开发指南](docs/local-development.md)
- [技术参考](docs/technical-reference.md)
- [v0.4.2 管理员资料中心使用说明](docs/v0.4.2-admin-knowledge-center-guide.md)
- [v0.4.2 迭代报告](docs/v0.4.2-iteration-report.md)
- [v0.4.2 / v0.5.0 设计](docs/superpowers/specs/2026-07-07-lexad-v0.4.2-v0.5.0-design.md)
- [v0.4.2 / v0.5.0 实施计划](docs/superpowers/plans/2026-07-07-lexad-v0.4.2-v0.5.0-implementation.md)

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| v0.4.2 | 2026-07-07 | 过渡版本：管理员资料中心、舆情案例库框架、平台规则版本管理、双轴风险结果、JSON 导入、多行业兼容提交 |
| v0.4.1 | 2026-07-05 | 后台异步审查、L1-L5 知识库浏览、大尺寸左侧导航、角色权限、安全修复、迁移与测试增强 |
| v0.4.0 | 2026-05-17 | 文件上传与多格式提取、测试物料批量验证、天蓝色系统一与按钮状态修复 |
| v0.3.0 | 2026-05-15 | 两部门审查交互闭环、四层 AI 引擎、知识库集成 |
| v0.2.0 | 2026-05 | FastAPI + Vue 3 项目骨架，Mock 占位审查 |
| v0.1.0 | 2026-04 | 初始原型，单文件 FastAPI 应用 |
