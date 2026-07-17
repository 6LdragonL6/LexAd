# Render + Neon 竞赛部署指南

本指南面向公开竞赛演示：GitHub 保存代码，Render 部署前后端，Neon 保存关系数据，DeepSeek Key 仅存在于 Render 后端环境变量中。

## 1. 安全边界

- 不创建公共 DeepSeek 转发代理。浏览器只能通过登录后的 LexAd 审查接口触发 AI。
- `DEEPSEEK_API_KEY` 不得写入 GitHub、前端 `VITE_*` 变量、页面或接口响应。
- `COMPETITION_MODE=true` 时，管理员资料中心、回收站和 AI Key 的所有写请求返回 `403`；资料浏览、物料提交、AI 审查和法务决定保持可用。
- 登录失败同时按用户名和来源 IP 限流；AI 任务同时按账号和来源 IP 限流。当前实现适用于 Render 单实例，服务重启后计数清空。
- 生产演示只创建 `admin`、`market01` 和 `legal01`。三个密码由 Render 环境变量提供，每次部署恢复预期角色和密码。

## 2. Neon

1. 新建仅用于比赛的 Neon 项目，区域尽量接近 Render。
2. 复制 direct PostgreSQL connection string，保留 `sslmode=require`。
3. 不要把连接串写入 `.env.example` 或 GitHub。
4. 当前免费部署在 Render build 阶段运行 Alembic，因此使用 direct URL；若以后拆分迁移和运行连接，再为应用单独使用 pooled URL。

## 3. Render Blueprint

仓库根目录的 `render.yaml` 会创建：

- `lexad-api`：Python Web Service；
- `lexad-frontend`：Vue Static Site；
- 数据库迁移和演示种子在后端 build 阶段执行；
- Vue history 路由统一 rewrite 到 `/index.html`。

首次同步 Blueprint 时填写以下后端变量：

| 变量 | 值 |
| --- | --- |
| `DATABASE_URL` | Neon direct connection string |
| `FRONTEND_ORIGIN` | `https://<前端服务名>.onrender.com`，末尾不要 `/` |
| `DEEPSEEK_API_KEY` | 比赛专用、可撤销且有限额的 Key |
| `DEMO_ADMIN_PASSWORD` | 至少 12 位，不与评委密码相同 |
| `DEMO_MARKETING_PASSWORD` | 至少 12 位 |
| `DEMO_LEGAL_PASSWORD` | 至少 12 位 |

前端变量：

| 变量 | 值 |
| --- | --- |
| `VITE_API_BASE_URL` | `https://<后端服务名>.onrender.com/api/v1` |

如果首次创建时尚未得到最终域名，可以先创建服务，取得两个 `onrender.com` 域名后更新变量并重新部署。`VITE_API_BASE_URL` 是构建时变量，修改后必须重新构建前端。

## 4. DeepSeek 调用

已有安全调用链为：

```text
浏览器登录 → Bearer JWT → POST /api/v1/reviews/ai-review
           → Render 后端读取 DEEPSEEK_API_KEY → DeepSeek
```

重新提交物料也会触发 AI 限流。竞赛保护模式下，数据库内历史 AI Key 被忽略，Render 环境变量是唯一生效来源。不要额外新增接收任意 prompt 的开放接口，否则任何人都能消耗额度并绕过业务审计。

## 5. 账号交付

- 只向评委提供 `market01` 和 `legal01` 的密码。
- 管理员密码不要放在登录页、README、比赛公开说明或前端环境变量中。
- 如果确实允许大众自由体验，应准备单独的低权限公共账号，并进一步降低 AI 限额；不要公开管理员账号。

## 6. 上线验收

依次验证：

1. `GET https://<api>/health` 返回 `200`。
2. 前端登录 `market01`，提交纯文字物料并完成 AI 审查。
3. 登录 `legal01`，查看队列并提交法务决定。
4. 直接刷新 `/legal`、`/brands` 等地址，不出现静态站点 `404`。
5. 连续输错密码达到阈值后返回 `429`，并包含 `Retry-After`。
6. 管理员在竞赛模式下仍可浏览资料，但新增、更新、删除、导入、发布、回收站写入和 AI Key 修改均返回 `403`。
7. 后端重新部署后，Neon 中的物料和审查结果仍存在，三个演示账号恢复为 Render 配置的密码。

## 7. 评审结束

1. 撤销 DeepSeek 比赛 Key。
2. 删除或冻结 Render 服务。
3. 删除 Neon 演示项目，或至少轮换数据库密码。
4. 不再公开评委账号密码。
