# VERSION 1.1.0 — 版本修订记录

> **版本**：1.1.0  
> **状态**：已发布（Released）  
> **发布时间**：2026-09-05  
> **文档状态**：1.1.0 发布版本。开发阶段（1.0.8 之后至 1.1.0 前）的全部迭代明细记录在 `VERSION_1_0_9.md`（该版本未独立发布，内容并入 1.1.0）；后续开发内容迭代到下一版本  
> **目录**：页面级行为细则见 `docs/prds/`；版本路线见 `docs/Roadmap.md`

---

## 1. 版本概述

1.1.0 为 1.0.8（独立精度测试模块 + 性能页增强）发布后的**主/次版本升级**。涵盖 1.0.9 开发周期（未独立发布）的**会话体验、性能实时面板、Dashboard 概览与环境信息**等增强，以及 Settings / Datas 等 Tab 的展示收敛。主要变更方向：性能任务页第二行实时面板与单请求快照回看、Sessions 会话体验全面升级、Dashboard Overview 重构为多计数面板与环境信息补全、第三方引擎指标可得性口径显式化，以及未完成功能以「敬请期待」占位。

---

## 2. 版本规划目标

（1.0.9 开发周期累积需求，逐项落地明细见 `VERSION_1_0_9.md` 迭代记录）

- **性能页实时体验**：第二行双面板（Realtime Data / Profile Progress / Real-Time Metrics）、单个请求回看与按请求实时快照持久化、原生引擎运行中随并发点更新、单并发点“连续滚动”
- **Sessions 会话体验**：采样参数、Markdown 渲染 + 代码高亮、重命名 / 日志落盘、侧栏并会话项细化、清空确认
- **Settings / Datas 收敛**：Cache Paths 改版、四类 UI 细化、Engine 来源标色；Datas 隐藏 Evals、Analysis 占位
- **Dashboard 重构**：Overview 精简后重构为 7 计数面板（Performance / Accuracy / Sessions / Skills(内置) / Models / Datasets / Providers），Envs info 网络补全（MAC / IP / 子网 / 掩码）并统一 antd 文字样式
- **第三方引擎指标口径**：可得→值、不可得→N/A、缺失→灰横线

---

## 3. 迭代记录

> 本版本对应 `VERSION_1_0_9.md` 的全部迭代明细（迭代 1–25），该版本未独立发布，内容并入 1.1.0。详见 [VERSION_1_0_9.md](VERSION_1_0_9.md)。

---

## 版本功能清单（Release Notes）

### Feature Highlights

- **Performance page realtime panels**: second-row dual panels (Realtime Data / Profile Progress / Real-Time Metrics with direct metric computation), per-request live snapshot persisted and reviewable from Datas/Perfs detail dialog, native-engine live progress updating per concurrency point, and "continuous scroll" within a single point
- **Single-request snapshots**: per-request live snapshot extraction extended to native engines, aligned with vLLM availability, with engine import hardening
- **Third-party engine metric availability**: explicit obtainability — value (blue) / N/A (grey-black) / missing (grey dash), with a fixed 11-metric snapshot contract
- **Sessions experience**: sampling params, Markdown rendering with code syntax highlight (highlight.js + dark theme), rename + per-session logs to disk, sidebar & item UI refinements, centered clear-confirmation modal
- **Settings refinements**: Cache Paths revamp (Root Dir applies immediately without restart, read-only subdirs), four UI categories refined, Bench Engine card borders colored by origin, provider models as green tags
- **Dashboard Overview redesign**: simplified then rebuilt into 7 count panels — Performance / Accuracy / Sessions / Skills(built-in) / Models / Datasets / Providers (Providers occupies a full row with Provider count + Provider Models)
- **Dashboard Envs info completion**: network panel enriched with MAC (IPv4) / IP / subnet / mask per interface, framework versions, hardware & OS info, unified Ant Design typography with smaller text; Overview pre-release hiding of unfinished panels (Evals Records / Analysis etc. shown as "Coming Soon")
- **Datas navigation**: hidden Evals tab (route redirects to Perfs) and Analysis placeholder; Accuracy "create task" shows a Coming-Soon modal; Settings/Models homepage link hidden

### 功能清单

- **性能页实时面板**：第二行双面板（Realtime Data / Profile Progress / Real-Time Metrics，指标直接计算）、单请求回看 + 按请求实时快照持久化（Datas/Perfs 详情弹窗查看）、原生引擎运行中随并发点更新、单并发点内“连续滚动”
- **单请求快照**：按请求快照拓展到原生引擎、口径对齐 vLLM、引擎导入逻辑加固
- **第三方引擎指标可得性**：可得→数值（蓝）/ 不可得→N/A（灰黑）/ 缺失→灰横线，固定 11 指标快照契约
- **Sessions 会话体验**：采样参数、Markdown 渲染 + 代码语法高亮（highlight.js + 黑底主题）、重命名 + 会话日志落盘、侧栏与会话项 UI 细化、清空居中确认弹窗
- **Settings 细化**：Cache Paths 改版（Root Dir 即时生效无需重启、子目录只读）、四类 UI 细化、Bench 引擎卡片按来源标色、Provider 模型改回绿色标签
- **Dashboard Overview 重构**：精简后重建为 7 计数面板——Performance / Accuracy / Sessions / Skills(内置) / Models / Datasets / Providers（Providers 占整行，内含 Provider 数量 + Provider Models）
- **Dashboard Envs info 补全**：网络面板按网口展示 MAC / IP / 子网 / 掩码，框架版本、硬件、操作系统信息，统一 antd 文字样式并缩小字号；Overview 隐藏未完成面板（Evals Records / Analysis 等以「敬请期待」占位）
- **Datas 导航**：隐藏 Evals Tab（路由重定向至 Perfs）、Analysis 占位；Accuracy「创建精度任务」弹出敬请期待弹窗；Settings/Models 隐藏 Homepage 链接

---

## 4. TODO 清单

（1.1.0 后续规划，按需补充）

---

## 5. 相关文档

- 页面级功能与约束：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings / Datas / TopBar）
- 架构 / 方案 / 设计 / 开发规范：`docs/rules/`（Architecture / Software / Design / Development / BenchEngine / BenchCore / BenchUpstream / AccuracyEngine）
- 版本路线：`docs/Roadmap.md`
