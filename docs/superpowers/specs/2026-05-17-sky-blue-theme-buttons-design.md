# Spec: 天蓝色系统一 & 按钮状态修复

**Date**: 2026-05-17
**Scope**: LexAd 前端 — 配色统一 + 按钮状态修复，不动页面结构

---

## 1. 按钮状态 Bug 修复

**问题**：SubmitPage / LegalDetail 的按钮在 `:disabled` 或 loading 状态下与灰色背景融为一体，视觉上"消失"。

**修复**：在 `uno.config.ts` shortcuts 中为所有按钮补充 disabled 状态：

- `btn-primary`：`disabled:opacity-50 disabled:cursor-not-allowed`
- `btn-outline`：`disabled:opacity-50 disabled:cursor-not-allowed`，确保 border 可见
- `btn-danger`：`disabled:opacity-50 disabled:cursor-not-allowed`

Shortcuts 中 `transition-colors` 已有，hover/active 通过原生 UnoCSS presetUno 覆盖即可。

## 2. 天蓝色系统一

### 2.1 新配色值

| 角色 | 旧值 | 新值 |
|------|------|------|
| 品牌主色 | `#2563EB`（blue-600） | `#0EA5E9`（sky-500） |
| 品牌深色(hover) | `#1D4ED8`（blue-700） | `#0284C7`（sky-600） |
| 品牌浅色 | blue-50 | sky-50 |
| focus ring | blue-500 | sky-500 |
| 链接色 | `#e94560`（红） | `#0EA5E9`（天蓝） |

语义色（绿 success / 黄 warning / 红 danger）保留不动，用于风险评分和状态标记。

### 2.2 改动文件清单

| 文件 | 改动内容 |
|------|---------|
| `uno.config.ts` | 品牌色改为天蓝；btn shortcuts 补 disabled 状态；btn-primary hover 改为 sky-600 |
| `src/styles/main.css` | `a` 颜色从 `#e94560` 改为 `#0EA5E9` |
| `src/components/layout/TopBar.vue` | `active-class` 从 `bg-blue-50 text-blue-700` 改为 `bg-sky-50 text-sky-700` |
| `src/pages/HomePage.vue` | 统计数字 `text-blue-600` → `text-sky-500`；链接色对齐 UnoCSS |
| `src/pages/KnowledgePage.vue` | tab active 从 `border-blue-500 text-blue-600` 改为 `border-sky-500 text-sky-600` |
| `src/pages/LegalDashboard.vue` | 物料名称链接 `text-blue-600` → `text-sky-600` |
| `src/components/review/IssueList.vue` | 蓝色 tag/border 从 `blue-*` 改为 `sky-*` |
| `src/components/review/SummaryPanel.vue` | 摘要框从 `bg-blue-50 text-blue-800` 改为 `bg-sky-50 text-sky-800` |
| `src/components/review/EngineReport.vue` | `▸` 颜色 `text-blue-500` → `text-sky-500` |
| `public/favicon.svg` | 背景从 `#1a1a2e` 改为 `#0EA5E9`；文字从 `#e94560` 改为 `#ffffff` |

### 2.3 不改的文件

- `stores/`、`api/`、`router/`、`types/`、`main.ts`
- `vite.config.ts`、`tsconfig.json`
- 所有页面的业务逻辑和模板结构
- Emoji 状态标记（✅ ❌ ⚠️）保持不动
- 风险评分颜色（绿/黄/红 阶梯）保持不动

## 3. 杂项

- 检查 `SubmitPage.vue` 和 `LegalDetail.vue` 的 `:disabled` 属性是否在 loading 时正确绑定，确认 `submitting` 变量控制无误
- 修改后全量 `npm run build` 确认无 TypeScript/UnoCSS 编译错误
