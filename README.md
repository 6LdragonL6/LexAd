# LexAd — 广告合规与舆情风险审查平台 v0.6.2

LexAd 面向市场部、法务部和管理员，在广告发布前完成法律合规与舆情风险双轴审查。市场人员提交文案或文件后，系统生成可追溯的审查结果；法务人员完成通过、退回或有条件通过的决定；管理员维护舆情案例和平台规则。

v0.6.2 为管理员新增单一 DeepSeek API 配置和 15 天回收站，统一模型输入输出、超时与错误处理，并修复错误登录触发整页重载和按钮卡住的问题。

## 核心能力

- 提交广告文案或常见格式文件，发起后台 AI 审查。
- 分别展示法律合规风险与舆情风险，不混合评分口径。
- 使用 L1–L5 知识库浏览法规、行业规则、案例、平台规则和模板。
- 支持法务审核、退回原因、内部备注和多轮修改重提。
- 保存提交版本、规则版本和资料库版本，便于追溯历史结果。
- 管理舆情案例、平台规则版本、导入记录和审计日志。
- 使用品牌库关联市场部提交，沉淀品牌档案和历史审查概况。
- 支持亮色、深色和跟随系统主题，以及 320px 起的响应式布局。

## v0.6.2 更新摘要

### 管理员系统管理

- 管理员可在系统内保存、替换和测试 DeepSeek API Key；地址和模型固定，密钥加密保存且不回显明文。
- 新增物料、品牌、舆情案例和平台规则的统一回收站，15 天内可恢复，也可二次确认后永久删除。
- 导入记录和审计日志永久保留，删除、恢复和清理动作均可追踪。

### 模型调用与登录稳定性

- 固定使用 `deepseek-v4-flash`，三类模型任务统一使用结构化输入、JSON 输出校验、超时和有界重试。
- 单项模型失败时保留确定性审查结果，并明确标记模块不可用。
- 登录接口直接返回用户信息；错误账户或密码不再触发整页刷新，会话过期与登录失败分开处理。

### 数据库与安全

- 新增安全配置和回收站增量迁移，兼容 SQLite 与 PostgreSQL。
- 生产环境使用默认 `SECRET_KEY` 时拒绝保存 API Key。
- 示例、测试和 Git 均不包含真实 API 信息。

完整内容见 [v0.6.2 发布说明](docs/v0.6.2-release-notes.md)。

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm
- 可选：Tesseract OCR
- 可选：Neon PostgreSQL；本地开发默认不需要云数据库

### Windows

首次安装：

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

cd ..\frontend
npm install
```

日常启动和关闭：

```text
start-dev.bat
stop-dev.bat
```

默认以本地 SQLite 模式启动。需要显式检查 Neon 时，可在 PowerShell 中运行对应脚本参数；具体说明见 [本地开发指南](docs/local-development.md)。

### macOS / 手动启动

后端：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

启动后访问：

- 前端：<http://localhost:5173>
- API 文档：<http://localhost:8000/docs>

## 默认测试账号

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 管理员 | `admin` | `admin123` |
| 市场部 | `market01`–`market10` | `test1234` |
| 法务部 | `legal01`–`legal10` | `test1234` |

## 数据库模式

| 模式 | 用途 | 数据位置 |
| --- | --- | --- |
| `local` | 日常开发和演示，默认模式 | `backend/lexad.db` |
| `neon` | 云端 PostgreSQL 检查或正式环境 | `DATABASE_URL` 指向的 Neon 实例 |

两个模式是独立数据源。切换模式不会复制或同步品牌、物料和审核记录；正式迁移数据时应使用单独、可审计的一次性流程。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Axios、UnoCSS
- 后端：FastAPI、Python 3.10+、SQLAlchemy 2、Alembic、Pydantic v2
- 数据库：SQLite、Neon PostgreSQL
- AI：DeepSeek OpenAI-compatible API
- 检索与解析：pyahocorasick、ChromaDB、PyMuPDF、python-docx、python-pptx、openpyxl、Pillow、Tesseract

## 文档

- [文档总览](docs/README.md)
- [本地开发指南](docs/local-development.md)
- [技术参考](docs/technical-reference.md)
- [v0.6.2 发布说明](docs/v0.6.2-release-notes.md)
- [v0.6.2 管理员系统管理指南](docs/v0.6.2-admin-system-guide.md)
- [v0.6 品牌库主设计](docs/superpowers/specs/2026-07-11-lexad-v0.6-ui-brand-library-design.md)
- [v0.6 发布收尾设计](docs/superpowers/specs/2026-07-12-lexad-v0.6-release-polish-design.md)

## 版本历史

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v0.6.2 | 2026-07-14 | 管理员 API 配置、15 天回收站、统一模型网关和登录稳定性修复 |
| v0.6.1 | 2026-07-13 | 三级侧栏、知识基线与拼多多接入、命中优先报告、历史版本和轮换提醒 |
| v0.6.0 | 2026-07-12 | 响应式新 UI、品牌库、深色主题层级、显式数据库模式与可靠启动流程 |
| v0.5.1 | 2026-07-08 | 明暗主题、主题令牌、提交快照和前端结构打磨 |
| v0.5.0 | 2026-07-08 | 退回闭环、舆情数据接入、平台别名匹配和展示规范化 |
| v0.4.2 | 2026-07-07 | 管理员资料中心、平台规则版本、双轴结果和批量导入 |
| v0.4.1 | 2026-07-05 | 后台异步审查、知识库浏览、权限与安全增强 |
| v0.4.0 | 2026-05-17 | 文件上传、多格式提取、批量验证和视觉统一 |
| v0.3.0 | 2026-05-15 | 市场与法务审核闭环、四层审查引擎和知识库集成 |
