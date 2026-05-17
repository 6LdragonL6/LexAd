# 天蓝色系统一 & 按钮状态修复 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 LexAd 前端配色全面统一为天蓝色系，修复按钮 disabled/loading 状态不可见 bug，不改页面结构

**Architecture:** 修改集中在 UnoCSS 配置（主题 color + shortcuts）和 Vue 组件模板中的硬编码颜色类名。所有改动为 CSS 类名替换和 disabled 状态补充，不涉及业务逻辑

**Tech Stack:** Vue 3 + UnoCSS (presetUno) + TypeScript + Vite

**改动文件:** `uno.config.ts` → `main.css` / `favicon.svg` → 组件文件（TopBar / HomePage / KnowledgePage / LegalDashboard / IssueList / SummaryPanel / EngineReport）

---

### Task 1: 更新 UnoCSS 配置（颜色 + 按钮状态）

**Files:**
- Modify: `frontend/uno.config.ts`

- [ ] **Step 1: 修改 uno.config.ts**

将 `frontend/uno.config.ts` 替换为以下内容：

```ts
import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [presetUno(), presetAttributify()],
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-primary': 'btn bg-sky-500 text-white hover:bg-sky-600',
    'btn-danger': 'btn bg-red-600 text-white hover:bg-red-700',
    'btn-outline': 'btn border border-sky-300 bg-white text-sky-600 hover:bg-sky-50',
    'card': 'bg-white rounded-xl shadow-sm border border-gray-200 p-6',
    'input': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500',
  },
  theme: {
    colors: {
      brand: { primary: '#0EA5E9', danger: '#DC2626', warning: '#F59E0B', success: '#16A34A' },
    },
  },
})
```

- [ ] **Step 2: Commit**

```bash
git add frontend/uno.config.ts
git commit -m "feat: switch brand color to sky-blue, add disabled states to all buttons"
```

---

### Task 2: 全局样式 + Favicon

**Files:**
- Modify: `frontend/src/styles/main.css`
- Modify: `frontend/public/favicon.svg`

- [ ] **Step 1: 修改 main.css — 链接颜色**

将 `frontend/src/styles/main.css` 第 24 行：

```css
a {
  color: #e94560;
  text-decoration: none;
}
```

改为：

```css
a {
  color: #0EA5E9;
  text-decoration: none;
}
```

- [ ] **Step 2: 修改 favicon.svg**

将 `frontend/public/favicon.svg` 替换为：

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#0EA5E9"/>
  <text x="16" y="22" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" font-weight="bold" fill="#ffffff">L</text>
</svg>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/main.css frontend/public/favicon.svg
git commit -m "feat: link color to sky-blue, favicon to sky-blue background"
```

---

### Task 3: 布局组件 — TopBar 导航色

**Files:**
- Modify: `frontend/src/components/layout/TopBar.vue`

- [ ] **Step 1: 修改 TopBar active-class**

`TopBar.vue` 第 23 行，将：

```html
active-class="bg-blue-50 text-blue-700"
```

改为：

```html
active-class="bg-sky-50 text-sky-700"
```

同时将第 16 行标题色的 `text-brand-primary`（已经是 UnoCSS theme 引用，Task 1 已改 brand.primary 值）确认无需改动。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/layout/TopBar.vue
git commit -m "feat: TopBar nav active color to sky-blue"
```

---

### Task 4: 页面组件颜色更新

**Files:**
- Modify: `frontend/src/pages/HomePage.vue`
- Modify: `frontend/src/pages/KnowledgePage.vue`
- Modify: `frontend/src/pages/LegalDashboard.vue`

- [ ] **Step 1: HomePage — 统计数字 + 链接**

第 38 行，`text-blue-600` → `text-sky-500`：

```html
<p class="text-3xl font-bold text-sky-500">{{ pendingCount }}</p>
```

第 55 行，`text-blue-600` → `text-sky-600`：

```html
<router-link :to="`/result/${m.id}`" class="text-sky-600 hover:underline">{{ m.name }}</router-link>
```

第 69 行，`text-blue-600` → `text-sky-600`：

```html
<p v-else-if="!loading" class="text-gray-400 text-center py-8">暂无提交记录，<router-link to="/submit" class="text-sky-600 hover:underline">去提交物料</router-link></p>
```

- [ ] **Step 2: KnowledgePage — tab 激活色**

第 39 行，将：

```html
:class="tab === t.k ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500'"
```

改为：

```html
:class="tab === t.k ? 'border-b-2 border-sky-500 text-sky-600' : 'text-gray-500'"
```

- [ ] **Step 3: LegalDashboard — 物料名称链接**

第 44 行，`text-blue-600` → `text-sky-600`：

```html
<span class="text-sky-600 truncate">{{ item.material_name }}</span>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/HomePage.vue frontend/src/pages/KnowledgePage.vue frontend/src/pages/LegalDashboard.vue
git commit -m "feat: page component colors to sky-blue"
```

---

### Task 5: 审查组件颜色更新

**Files:**
- Modify: `frontend/src/components/review/IssueList.vue`
- Modify: `frontend/src/components/review/SummaryPanel.vue`
- Modify: `frontend/src/components/review/EngineReport.vue`

- [ ] **Step 1: IssueList — 蓝色 tag/border 改为 sky**

第 17 行，`border-blue-200 bg-blue-50` → `border-sky-200 bg-sky-50`：

```html
'border-sky-200 bg-sky-50': issue.match_type === '需证明材料',
```

第 23 行，`bg-blue-100 text-blue-700` → `bg-sky-100 text-sky-700`：

```html
'bg-sky-100 text-sky-700': issue.match_type === '需证明材料',
```

- [ ] **Step 2: SummaryPanel — 摘要框**

第 10 行，`bg-blue-50` → `bg-sky-50`；第 11 行 `text-blue-800` → `text-sky-800`；第 12 行 `text-blue-700` → `text-sky-700`：

```html
<div class="p-3 bg-sky-50 rounded-lg">
  <p class="font-medium text-sky-800">摘要</p>
  <p class="text-sky-700 mt-1 whitespace-pre-wrap">{{ result.summary }}</p>
</div>
```

- [ ] **Step 3: EngineReport — 项目符号**

第 24 行，`text-blue-500` → `text-sky-500`：

```html
<span class="text-sky-500">▸</span> {{ s }}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/review/IssueList.vue frontend/src/components/review/SummaryPanel.vue frontend/src/components/review/EngineReport.vue
git commit -m "feat: review component colors to sky-blue"
```

---

### Task 6: 构建验证

- [ ] **Step 1: 安装依赖（如未安装）并构建**

```bash
cd frontend && npm install && npm run build
```

Expected: 无 TypeScript 错误，无 UnoCSS 编译错误，dist 目录正常生成。

- [ ] **Step 2: 检查构建产物**

```bash
ls frontend/dist/assets/
```

Expected: 看到所有 chunk 文件正常输出。

- [ ] **Step 3: 最终 commit（如有lint/format调整）**

```bash
git add -A
git diff --cached --stat
# 仅当有额外改动时提交
```
