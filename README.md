# LexAd - 广告合规与舆情风险审查平台 v0.5.1

LexAd 是一个广告发布前审查系统，面向市场部、法务部和管理员。它把广告物料提交给后台审查，分别展示法律合规风险和舆情风险两条结果轴，法务作出通过、退回或有条件通过的决定。

v0.5.1 在 v0.5.0 稳定工作流基础上新增明暗双模式，并把前端样式逐步收敛到主题 token。v0.5.0 修复了 v0.4.2 的三项实测 bug，补齐了退回物料循环提交流程，接入了团队真实舆情案例数据，并统一了前端展示语言。

## 你可以用它做什么

- 提交广告文案或物料，发起 AI 审查。
- 查看法律合规风险和舆情风险两条结果轴。
- 法务在审核队列中做最终决定，退回原因和备注对市场部透明可见。
- 市场部查看退回意见后修改物料，重新提交审查（支持多轮循环）。
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

## v0.5.1 重点变化

**主题与体验：**

- 新增浅色、深色、跟随系统三种主题模式。
- 顶部栏提供主题切换，偏好保存在本地浏览器。
- 全局样式新增语义化主题 token，卡片、按钮、输入框、标题等基础元素支持明暗主题。
- 前端版本显示改为读取常量，减少硬编码版本号。

**结构打磨：**

- 新增主题状态模块 `useTheme`。
- 新增应用常量模块 `constants/app`。
- 保持后端审查逻辑和业务流程不变。

详见 [v0.5.1 发布说明](docs/v0.5.1-release-notes.md)。

## v0.5.0 重点变化

**Bug 修复：**

- 平台规则中文名与后台标识无法匹配（如"抖音"↔"douyin"），现已支持别名归一化。
- 市场部查看被退回物料时看不到法务退回原因和备注，现已透明展示。
- L1 检测覆盖"最耐用""最安全"等未被枚举的"最"类绝对化表达，并给出解释和建议。

**新功能：**

- 退回物料支持多轮修改和重新提交，版本自动递增。
- 物料支持归档（已有审查记录）和物理删除（仅无记录的草稿）。
- 接入团队舆情案例库和触发词库，舆情结果基于真实案例判断。
- 审查报告使用业务语言，不再出现"未命中硬规则"等偏技术表达。
- 前端业务页面统一使用中文平台名，内部标识仅出现在技术详情区。

详见 [v0.5.0 发布说明](docs/v0.5.0-release-notes.md)。

## 文档入口

- [本地开发指南](docs/local-development.md)
- [技术参考](docs/technical-reference.md)
- [v0.5.1 发布说明](docs/v0.5.1-release-notes.md)
- [v0.5.1 主题与结构打磨设计](docs/superpowers/specs/2026-07-08-lexad-v0.5.1-theme-polish-design.md)
- [v0.5.0 发布说明](docs/v0.5.0-release-notes.md)
- [v0.5.0 稳定发布设计](docs/superpowers/specs/2026-07-08-lexad-v0.5.0-stability-design.md)
- [v0.4.2 管理员资料中心使用说明](docs/v0.4.2-admin-knowledge-center-guide.md)
- [v0.4.2 迭代报告](docs/v0.4.2-iteration-report.md)

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| v0.5.1 | 2026-07-08 | 主题与结构打磨：明暗双模式、主题 token、版本常量、前端样式收敛、文档更新 |
| v0.5.0 | 2026-07-08 | 稳定发布：平台别名匹配、退回闭环、L1 模式检测、舆情数据接入、报告人性化、前端展示规范化 |
| v0.4.2 | 2026-07-07 | 过渡版本：管理员资料中心、舆情案例库框架、平台规则版本管理、双轴风险结果、JSON 导入、多行业兼容提交 |
| v0.4.1 | 2026-07-05 | 后台异步审查、L1-L5 知识库浏览、大尺寸左侧导航、角色权限、安全修复、迁移与测试增强 |
| v0.4.0 | 2026-05-17 | 文件上传与多格式提取、测试物料批量验证、天蓝色系统一与按钮状态修复 |
| v0.3.0 | 2026-05-15 | 两部门审查交互闭环、四层 AI 引擎、知识库集成 |
| v0.2.0 | 2026-05 | FastAPI + Vue 3 项目骨架，Mock 占位审查 |
| v0.1.0 | 2026-04 | 初始原型，单文件 FastAPI 应用 |
