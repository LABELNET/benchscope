# docs 文档目录

> **文档状态**：benchscope 文档体系说明与维护约定  
> **最后更新**：2026-08-28 16:56:30

本目录组织项目全部技术文档。**开发更新功能时，必须同步更新对应文档**（见文末「维护约定」）。

---

## 1. 页面功能文档 — `prds/`

每个界面功能与模块说明，含**实现策略、限制条件、联动条件**；页面变动更新到对应文件。

| 文档 | 内容 |
| --- | --- |
| [prds/Performance.md](prds/Performance.md) | 性能任务执行页：双模式（并发/阈值）、Cases / Realtime / Statistics 面板、唯一组 id、Best/BestPerf 高亮、进度计数 |
| [prds/Performance-Create.md](prds/Performance-Create.md) | 创建任务子页（`/performance/create`）：三步表单、条件组、参数 YAML、payload 构建 |
| [prds/Dashboard.md](prds/Dashboard.md) | Dashboard：Overview 六宫格、Envs info 四宫格、Perf/Eval Records 表格 |
| [prds/Datas.md](prds/Datas.md) | Datas（1.0.6）：副导航（Perfs/Evals/Analysis）+ Records 记录面板（导入恢复/刷新）+ Perfs 详情 5 行布局（删除备份分享、Perf-Cases-Logs 等高、Perf Datas、分析面板）+ 占位页 |
| [prds/TopBar.md](prds/TopBar.md) | **TopBar 主导航（1.0.6 新增）**：全局参数（品牌区/6 栏菜单/Service 状态/StatusBadge prop）+ **导航变更记录（含精确到秒的 commit 时间）** |
| [prds/Accuracy.md](prds/Accuracy.md) | Accuracy 占位页与 v5.0 规划 |
| [prds/Sessions.md](prds/Sessions.md) | Sessions：会话管理、SSE 流式、思考解析、性能栏 |
| [prds/Settings.md](prds/Settings.md) | Settings：General / Envs / Models / Datasets / Plugins 五栏（1.0.6：Models 厂商目录、Datasets 分类行式、双语缓存路径） |

> 命名规则：`<页面名>.md`；有子页面时 `Sessions-xxx.md` 形式。

## 2. 版本修订文档 — `versions/`

每个版本更新的功能主要概述与 TODO 清单，命名 `VERSION_x_y_z.md`，**按时间顺序维护**：

| 文档 | 内容 |
| --- | --- |
| [versions/VERSION_1_0_6.md](versions/VERSION_1_0_6.md) | **1.0.6（开发中）**：当前迭代版本，后续开发内容按时间顺序追加 |
| [versions/VERSION_1_0_4.md](versions/VERSION_1_0_4.md) | 1.0.4 规划与 1.0.5 范围定义/收口期文档归档（原 `.trae/` 内容，按时间顺序） |
| [versions/VERSION_1_0_5.md](versions/VERSION_1_0_5.md) | 1.0.5 版本概述 + 各迭代 PRD 汇总（260824 → 260825 → 260826-1 → 260826-2，按时间顺序）+ TODO |

> 维护约定：后续新版本创建 `VERSION_x_y_z.md`；同版本迭代内容按时间先后追加到对应版本文档，不再保留独立 PRD 文件。

## 3. 约定规则 — `rules/`

| 文档 | 内容 |
| --- | --- |
| [rules/Architecture.md](rules/Architecture.md) | 系统架构、核心模块、操作模块 |
| [rules/Software.md](rules/Software.md) | 软件架构/方案/选型/依赖 |
| [rules/Design.md](rules/Design.md) | 设计规范：UI / 字体 / 颜色 |
| [rules/Development.md](rules/Development.md) | 开发 / 验证 / 部署规范 |

## 4. 顶层文档

| 文档 | 内容 |
| --- | --- |
| [Roadmap.md](Roadmap.md) | 版本路线（各版本目标范围与状态；后续重新规划） |
| [Projects.md](Projects.md) | 项目功能总览（基于现有功能生成） |

---

## 维护约定（强制）

> 开发更新功能时，请按以下规则同步维护文档：
> 1. **页面功能/界面/逻辑/策略/UI 调整** → 更新 `prds/` 对应页面文档；
> 2. **版本功能与 todo** → 更新 `versions/VERSION_x_y_z.md`；
> 3. **架构/方案/设计/开发规范/软件依赖变更** → 更新 `rules/` 对应文档；**软件依赖**（Python `pyproject.toml` / 前端 `web/package.json` 的新增、升级、移除）必须同步 `rules/Software.md` §2 技术栈与 §3 依赖清单；
> 4. 文档间引用使用相对链接，移动/改名后需同步修正引用。
>
> **版本迭代规则**：未特别说明版本号时，项目内容所有变更默认归属当前版本 **v1.0.6**（开发中显示 `v1.0.6-dev`），全部迭代到 `versions/VERSION_1_0_6.md`；**除非用户明确说「迭代下一个版本」**，才创建 `VERSION_x_y_z.md` 并同步升级版本号（`__init__.py` / `pyproject.toml`），否则不得擅自变更版本号。
>
> **时间记录规则（重要）**：**所有迭代变更记录的时间必须记录精确时间——年-月-日 时:分:秒**（含 commit 号，取自提交/落地时刻），禁止仅写日期；主导航相关变更另须在 `prds/TopBar.md` §5 追加记录（同样精确到秒）。
