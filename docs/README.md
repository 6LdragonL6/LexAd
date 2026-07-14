# LexAd 文档总览

当前项目版本：`v0.6.2`。

本文档是 `docs/` 的统一入口。README 负责项目概览；使用方法、技术细节、发布记录和历史设计分别维护在下列文档中。

## 使用与维护

- [本地开发指南](local-development.md)：安装、启动、关闭、数据库模式和常见问题。
- [技术参考](technical-reference.md)：目录结构、迁移、环境变量、API 和审查引擎。
- [v0.4.2 管理员资料中心指南](v0.4.2-admin-knowledge-center-guide.md)：舆情案例和平台规则维护流程。
- [v0.6.2 管理员系统管理指南](v0.6.2-admin-system-guide.md)：API 配置、回收站、恢复和永久清理。

## 发布说明

- [v0.6.2](v0.6.2-release-notes.md)：管理员 API 配置、15 天回收站、统一模型网关和登录稳定性修复。
- [v0.6.1](v0.6.1-release-notes.md)：三级侧栏、知识基线与拼多多接入、命中优先报告、历史版本和轮换提醒。
- [v0.6.0](v0.6.0-release-notes.md)：响应式 UI、品牌库、主题层级、数据库模式和启动可靠性。
- [v0.5.1](v0.5.1-release-notes.md)：明暗主题与结构打磨。
- [v0.5.0](v0.5.0-release-notes.md)：稳定性、退回闭环与舆情数据接入。
- [v0.4.2 迭代报告](v0.4.2-iteration-report.md)
- [v0.4.1 迭代报告](v0.4.1-iteration-report.md)

## 当前版本设计

- [v0.6.2 管理能力设计](superpowers/specs/2026-07-14-lexad-v0.6.2-design.md) / [实施计划](superpowers/plans/2026-07-14-lexad-v0.6.2-implementation.md)
- [v0.6 品牌库主设计](superpowers/specs/2026-07-11-lexad-v0.6-ui-brand-library-design.md)：品牌库的数据、接口、权限和页面结构。
- [v0.6 发布收尾设计](superpowers/specs/2026-07-12-lexad-v0.6-release-polish-design.md)：登录页、响应式布局、深色主题、品牌加载、数据库模式和启动脚本。
- [v0.6 发布收尾实施计划](superpowers/plans/2026-07-12-lexad-v0.6-release-polish-implementation.md)：上述收尾工作的实施和验收顺序。
- [可靠演示体验设计](superpowers/specs/2026-07-11-lexad-reliability-demo-experience-design.md)
- [可靠演示体验实施计划](superpowers/plans/2026-07-11-lexad-reliability-demo-experience-implementation.md)

## 历史设计档案

### v0.5

- [v0.5.1 主题与结构打磨](superpowers/specs/2026-07-08-lexad-v0.5.1-theme-polish-design.md)
- [v0.5.0 发布完善设计](superpowers/specs/2026-07-08-lexad-v0.5.0-release-design.md)
- [v0.4.2–v0.5.0 总体设计](superpowers/specs/2026-07-07-lexad-v0.4.2-v0.5.0-design.md)
- [v0.4.2–v0.5.0 实施计划](superpowers/plans/2026-07-07-lexad-v0.4.2-v0.5.0-implementation.md)

### v0.4 及更早

- [v0.4.1 稳定与安全设计](superpowers/specs/2026-07-05-lexad-v0.4.1-stability-security-design.md)
- [v0.4.0 设计](superpowers/specs/2026-05-17-lexad-v0.4.0-design.md)
- [文件上传设计](superpowers/specs/2026-05-17-lexad-file-upload-design.md) / [实施计划](superpowers/plans/2026-05-17-lexad-file-upload.md)
- [测试验证设计](superpowers/specs/2026-05-17-lexad-test-validation-design.md) / [实施计划](superpowers/plans/2026-05-17-lexad-test-validation.md)
- [天蓝主题按钮设计](superpowers/specs/2026-05-17-sky-blue-theme-buttons-design.md) / [实施计划](superpowers/plans/2026-05-17-sky-blue-theme-buttons.md)
- [v0.3.0 设计](superpowers/specs/2026-05-15-lexad-v0.3.0-design.md) / [核心实施计划](superpowers/plans/2026-05-15-lexad-v0.3.0-core.md)

## 维护约定

- README 不展开完整 API、迁移和排错细节，只链接到对应专题文档。
- 同一版本、同一天的短设计优先合并为一个发布完善文档。
- 大型主设计和实施计划保留独立文件，避免丢失关键决策背景。
- 历史迁移和历史发布说明中的旧版本号是事实记录，不随当前版本机械替换。
- 新增、删除或重命名文档时同步更新本索引，并检查 Markdown 相对链接。
