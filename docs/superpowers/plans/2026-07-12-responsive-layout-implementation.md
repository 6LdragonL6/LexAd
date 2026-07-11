# LexAd v0.6 响应式布局修复实施计划

> 依据：`docs/superpowers/specs/2026-07-12-responsive-layout-design.md`。
>
> 约束：在已有未提交代码上增量修改；不引入 UI 框架；不修改业务 API 或认证逻辑；不创建全局文档 `min-width`。

## 实施前检查

1. 记录 `git status --short`，确认已有的 v0.6 未提交变更属于当前工作范围，不能回退或覆盖。
2. 执行 `cd frontend; npm run build`，保存当前构建基线。
3. 启动本地前后端后，在浏览器 DevTools 中分别打开登录页、首页、提交页、法务详情、结果页、品牌档案、知识库与管理页，记录当前横向滚动或遮挡位置。

## 任务 1：统一全局断点和流式容器

**文件：** `frontend/src/styles/main.css`

1. 将现有 `--breakpoint-mobile: 1024px` 拆分为明确的语义断点：
   - `--breakpoint-compact: 1280px`：固定侧栏和三栏/宽屏辅助栏的临界点；
   - `--breakpoint-phone: 768px`：手机单列和登录页上下布局的临界点。
   CSS 自定义属性不能直接用于 media query，因此所有 `@media` 使用相同的字面值，并在注释中标明对应令牌。
2. 在 reset/base 区添加 `html`、`body`、`#app` 的 `max-width: 100%` 与 `overflow-x: hidden`（或 `clip`，以浏览器兼容性为准）。不要设置全局 `min-width`。
3. 新增共享 `.page-container`：`width: 100%`、`min-width: 0`、合理 `max-width`、水平居中和响应式内边距。
   - 默认/手机：`padding-inline: 16px`；
   - 平板：`padding-inline: 24px`；
   - 宽屏：`padding-inline: 32px`。
4. 新增 `.page-stack` 或等价公共规则，使页面块以统一的纵向 `gap` 排列；新增 `.responsive-toolbar`，使用 `display: flex; flex-wrap: wrap; gap: ...`。
5. 为公共 `.card` 的内边距提供手机覆盖（手机 `16px`，平板/桌面维持既有视觉值）。不要影响弹层或没有 `.card` 的专门组件。
6. 新增仅限局部容器的 `.table-scroll`：`max-width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch`。禁止在页面根节点使用它。

**验收：** 在空页面和现有页面中，窄视口时 `document.documentElement.scrollWidth <= window.innerWidth`；公共容器不会将宽度撑出可视区。

## 任务 2：统一 AppShell 与导航断点

**文件：** `frontend/src/styles/main.css`；必要时 `frontend/src/layouts/AppShell.vue`、`frontend/src/components/layout/TopBar.vue`、`frontend/src/components/layout/MobileNavigation.vue`

1. 保持 AppShell 的单一职责：`AppSidebar` 只在 `min-width: 1280px` 显示；同一 media query 内给 `.app-shell-main` 设置 `margin-left: var(--sidebar-width)`。
2. 在 `max-width: 1279px` 显式清除主内容偏移并隐藏桌面侧栏，防止只隐藏侧栏而保留偏移，或只显示侧栏而未留空间。
3. 将移动顶部栏的显示阈值改为 `max-width: 1279px`，与侧栏切换完全一致；桌面 `TopBar` 同时只在 `min-width: 1280px` 显示。
4. 调整 `.app-shell-content` 为 `min-width: 0; overflow-x: clip;`，保留纵向内容访问。不要用固定高度锁定全部页面。
5. 为窄顶栏补充可收缩规则：缩小主题切换器与退出按钮的占用；在不足宽度时隐藏非必要文案但保留图标、`aria-label` 和触控尺寸。移动顶部栏口号可以在手机宽度隐藏，保留品牌名和菜单按钮。
6. 检查 `MobileNavigation` 抽屉在 `320px` 的 `max-width`：抽屉不应宽于视口，背景遮罩不造成横向溢出，打开时 `body` 只禁止纵向背景滚动。

**验收：**

- `1279px`：无固定侧栏、无 `margin-left`、有移动顶部栏和抽屉。
- `1280px`：有固定侧栏、主内容精确避开 `--sidebar-width`、无移动顶部栏。
- 320px 打开/关闭抽屉后无横向滚动，Escape 与点击遮罩仍可关闭。

## 任务 3：修复登录页三档响应式布局与控件间距

**文件：** `frontend/src/styles/main.css`；必要时 `frontend/src/pages/LoginPage.vue`

1. 保留 `.login-page` 的独立登录结构和 `min-height: 100dvh`，但允许当内容高度大于视口时自然增长并让文档纵向滚动。
2. 宽屏（`>=1280px`）保留品牌区 `flex: 1` 和约 `480px` 表单面板。
3. 紧凑区（`768px–1279px`）保持左右结构：
   - 品牌区使用较小、响应式 `padding`；
   - 隐藏或淡化大装饰 SVG 和超大符号，而不是隐藏整个品牌区；
   - 表单面板改为 `width: clamp(360px, 42vw, 480px)`（最终数值以 768px 不溢出为准），并使用较小的响应式内边距；
   - 两侧设 `min-width: 0`。
4. 手机区（`<768px`）才设为 `flex-direction: column`；品牌区变为短页头，隐藏装饰和能力列表，表单面板为 `width: 100%`。
5. 表单区使用单一纵向布局：标题/副标题、字段组、错误信息、提交按钮、测试账号区通过 `gap` 或稳定 margin 分隔。移除会在矮窗口或错误出现时压缩/重叠的固定高度、负边距或绝对定位。
6. 保证输入与按钮最小 `44px` 高，测试账号区在最小宽度可换行，所有长文本可断行。

**验收：** `320px` 为上下布局；`768px`、`1024px`、`1279px` 为左右布局且无横向滚动；`1280px` 恢复完整装饰。以 `568px` 高度检查登录按钮与测试账号区之间至少保留设计间隙且可向下滚动。

## 任务 4：迁移通用页面容器和固定工具栏

**文件：**

- `frontend/src/pages/HomePage.vue`
- `frontend/src/pages/SubmitPage.vue`
- `frontend/src/pages/LegalDashboard.vue`
- `frontend/src/pages/ResultPage.vue`
- `frontend/src/pages/BrandArchivePage.vue`
- `frontend/src/pages/KnowledgePage.vue`
- `frontend/src/pages/AdminKnowledgePage.vue`

1. 把各页面的 `max-w-* mx-auto p-4 lg:p-8` 外层逐步迁移为 `.page-container`，保留每页原有的最大内容宽度（可通过页面修饰类或额外 max-width 工具类表达）。不修改页面的数据请求和事件处理。
2. 将标题+操作按钮、筛选器+按钮等 `flex ... justify-between` 容器改为 `.responsive-toolbar` 或等价的 `flex-wrap` 结构。按钮在手机宽度可占整行或换行，不能压缩文字到重叠。
3. 首页：统计卡和快捷入口在手机单列、平板两列（若视觉需要）、宽屏三列；最近提交条目的操作区允许换行。
4. 提交页：文件区标题/大小提示可换行；行业选择按 `2/3/4` 合理列数变化；“更多设置”标题行和表单字段不产生溢出。
5. 法务看板：标题工具栏可换行；桌面行与手机卡片视图继续保持，但其包装容器不能撑宽页面。
6. 品牌档案：在 `>=1280px` 保留品牌列表+档案双栏；小于该宽度切为单列，选择品牌后档案置于列表之后。头部操作区可换行。
7. 知识库与管理页：标签栏保留自己的局部横向滚动；管理表格包入 `.table-scroll`，并确认外层 `min-width: 0`。不要让标签或表格影响 body 宽度。

**验收：** 每页在 `320/768/1024/1279/1280px` 宽度下无横向页面滚动；按钮、筛选器、标题均不重叠。

## 任务 5：复杂详情页的栏目重排

**文件：** `frontend/src/styles/main.css`、`frontend/src/components/layout/ThreeColLayout.vue`、`frontend/src/layouts/ReviewLayout.vue`、`frontend/src/pages/LegalDetail.vue`、`frontend/src/pages/ResultPage.vue`

1. 将 `.three-col` 的宽屏规则固定在 `min-width: 1280px`；左右栏使用受控 `clamp()` 宽度，中栏必须为 `min-width: 0; flex: 1`。
2. 小于 `1280px` 时，三栏完全回到正常文档流：左栏、中心栏、右栏按业务阅读顺序纵向堆叠；清除固定高度、内部独立滚动和固定侧栏宽度。
3. 宽屏允许三栏独立纵向滚动；中等和手机宽度只用页面纵向滚动，避免“外层不可滚、内层很窄”的状态。
4. `LegalDetail.vue` 中的版本行、标签行、法务决策单选项、评分/状态区都加入 `flex-wrap`、`min-width: 0` 或手机纵向布局，避免长内容在中心栏或手机上重叠。
5. `ResultPage.vue` 的审查信息侧栏只在 `xl`/宽屏显示为右栏；低于该宽度自然移到主结果下方。各 `justify-between` 行为长文本添加换行或纵向覆盖。

**验收：** 在 `1279px`，法务详情没有固定左右栏且全部内容可按从摘要到正文到报告的顺序纵向访问；在 `1280px`，三栏不相互遮挡，中心栏可读；在 320px 没有横向滚动。

## 任务 6：验证与回归

1. 运行 `cd frontend; npm run build`。
2. 启动本地服务，使用浏览器响应式模式检查宽度 `320、360、390、768、1024、1279、1280、1440px` 和高度 `568、667、800、900px`。
3. 每个关键页面在亮色与深色主题下检查：
   - 登录页；
   - 首页；
   - 提交页；
   - 法务看板和法务详情；
   - 审查结果页；
   - 品牌档案；
   - 知识库和管理页。
4. 每次检查都在 DevTools 控制台或通过自动化断言：`document.documentElement.scrollWidth <= window.innerWidth`。
5. 验证侧栏/抽屉临界点：1279px 与 1280px；验证登录页临界点：767px 与 768px。
6. 回归登录、登出、抽屉开关、提交表单、品牌档案选择与法务详情加载。确认视觉修复没有改变认证、路由或数据行为。
7. 完成后仅暂存本计划涉及的前端文件；不要把数据库、构建产物或与本任务无关的未提交文件纳入提交。

