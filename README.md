# LexAd — 广告合规与舆情风险审查平台 v0.6.3

LexAd 面向市场部、法务部和管理员，在广告发布前完成法律合规与舆情风险双轴审查。市场人员提交文案或文件后，系统生成可追溯的审查结果；法务人员完成通过、退回或有条件通过的决定；管理员维护舆情案例和平台规则。

v0.6.3 修复法律第二层业务模型请求，正式接入 34 条真实舆情案例，并以本地可信证据优先、AI 有效可信度参与的方式融合判断开放式舆情风险。

## 核心能力

- 提交广告文案或常见格式文件，发起后台 AI 审查。
- 分别展示法律合规风险与舆情风险，不混合评分口径。
- 使用 L1–L5 知识库浏览法规、行业规则、案例、平台规则和模板。
- 支持法务审核、退回原因、内部备注和多轮修改重提。
- 保存提交版本、规则版本和资料库版本，便于追溯历史结果。
- 管理舆情案例、平台规则版本、导入记录和审计日志。
- 使用品牌库关联市场部提交，沉淀品牌档案和历史审查概况。
- 支持亮色、深色和跟随系统主题，以及 320px 起的响应式布局。

## v0.6.3 更新摘要

### 审查请求可靠性

- 第二层语义审查和舆情业务请求提供明确 JSON 契约、输出示例、完成状态检查和有界重试。
- 管理员连接测试保持只验证 API 连通性；业务正确性由审查代码与回归测试保证。
- 模型失败时继续保留法律确定性层和本地舆情证据。

### 真实案例与混合舆情判断

- 项目内置 34 条带来源和核验信息的真实案例，规范化后形成 33 个事件；重复桃李面包案例合并为一个规范记录。
- 启动同步、管理员导入和命令行导入共用同一规范化与幂等同步逻辑。
- 触发词只用于候选召回，不直接决定中高风险；本地案例证据与 AI 原文证据按有效可信度动态融合。
- 无本地案例时 AI 仍可发现新风险；AI 不可用时仍返回本地可解释结果。

### 结果解释

- 结果页展示风险分数、判断来源、原文证据、相似事件匹配依据和舆情修改建议。
- 本地与 AI 高可信度冲突或证据不足时明确提示人工复核。

完整内容见 [v0.6.3 发布说明](docs/v0.6.3-release-notes.md)。

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
- [v0.6.3 发布说明](docs/v0.6.3-release-notes.md)
- [v0.6.2 发布说明](docs/v0.6.2-release-notes.md)
- [v0.6.2 管理员系统管理指南](docs/v0.6.2-admin-system-guide.md)
- [v0.6 品牌库主设计](docs/superpowers/specs/2026-07-11-lexad-v0.6-ui-brand-library-design.md)
- [v0.6 发布收尾设计](docs/superpowers/specs/2026-07-12-lexad-v0.6-release-polish-design.md)

## 版本历史

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v0.6.3 | 2026-07-14 | 第二层请求修复、真实舆情案例、统一导入与本地/AI 可信度融合 |
| v0.6.2 | 2026-07-14 | 管理员 API 配置、15 天回收站、统一模型网关和登录稳定性修复 |
| v0.6.1 | 2026-07-13 | 三级侧栏、知识基线与拼多多接入、命中优先报告、历史版本和轮换提醒 |
| v0.6.0 | 2026-07-12 | 响应式新 UI、品牌库、深色主题层级、显式数据库模式与可靠启动流程 |
| v0.5.1 | 2026-07-08 | 明暗主题、主题令牌、提交快照和前端结构打磨 |
| v0.5.0 | 2026-07-08 | 退回闭环、舆情数据接入、平台别名匹配和展示规范化 |
| v0.4.2 | 2026-07-07 | 管理员资料中心、平台规则版本、双轴结果和批量导入 |
| v0.4.1 | 2026-07-05 | 后台异步审查、知识库浏览、权限与安全增强 |
| v0.4.0 | 2026-05-17 | 文件上传、多格式提取、批量验证和视觉统一 |
| v0.3.0 | 2026-05-15 | 市场与法务审核闭环、四层审查引擎和知识库集成 |
