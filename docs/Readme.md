# docs 文档目录

> **文档状态**：benchscope 文档体系说明与维护约定  
> **最后更新**：2026-08-31 01:40:00

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
| [prds/Settings.md](prds/Settings.md) | Settings：General / Providers / Models / Datasets / Bench Engines / Skills / Plugins 七栏（1.0.7：面板化 + 每引擎 Mock 开关；Debug 已移除） |

> 命名规则：`<页面名>.md`；有子页面时 `Sessions-xxx.md` 形式。

## 2. 版本修订文档 — `versions/`

每个版本更新的功能主要概述与 TODO 清单，命名 `VERSION_x_y_z.md`，**按时间顺序维护**：

| 文档 | 内容 |
| --- | --- |
| [versions/VERSION_1_0_7.md](versions/VERSION_1_0_7.md) | **1.0.7（已发布 2026-08-30）**：PyPI `benchscope==1.0.7`（补丁发布，未推 PyPI）|
| [versions/VERSION_1_0_6.md](versions/VERSION_1_0_6.md) | **1.0.6（已发布 2026-08-28）**：PyPI `benchscope==1.0.6` |
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
| [rules/BenchEngine.md](rules/BenchEngine.md) | **Bench 引擎架构（1.0.7）**：引擎抽象（自研 bench / vllm-<ver> / sglang-<ver>）+ 环境校验 + 参数描述 + 自研引擎核心设计 |
| [rules/BenchCore.md](rules/BenchCore.md) | ⭐ **自研 bench 核心实现总结（存档）**：流式时间线采集、指标口径对齐 vLLM、四子系统实现、设计取舍与实测数据 |
| [rules/BenchUpstream.md](rules/BenchUpstream.md) | ⭐ **上游 bench 核心逻辑分析（源码实证）**：vLLM v0.23.0 / SGLang v0.5.10 的 git+zip 链接、commit、时间线与指标公式（带行号）、与自研引擎对齐表、优化项 |

## 4. 技能文档 — `skills/`

Skills（给 AI 消费的技能包）的**说明文档归口**；技能可分发产物在仓库根目录 `skills/`。

| 文档 | 内容 |
| --- | --- |
| [skills/Readme.md](skills/Readme.md) | **Skills 体系总入口（规范）**：定位、目录结构规范、SKILL.md / README.md 规范、打包规范、技能清单、维护约定 |
| [skills/BenchEngineAuthoring.md](skills/BenchEngineAuthoring.md) | **自定义 Bench 引擎技能详解**：7 步工作流 + 上游源码链接/获取命令 + 实现契约（Input/Core/Output/Mock）+ mock 核心方法 + 导入校验 8 项 + 可复制提示词 + 排错 |
| [skills/BenchTesting.md](skills/BenchTesting.md) | **benchscope perf 压测技能说明**（bs-perfs-concurrency 并发 / bs-perfs-threshold 阈值）：内置表单、命令、产物打包、Datas/perfs 导入、排错 |

> 上游 bench 核心逻辑分析（源码实证）见 [rules/BenchUpstream.md](rules/BenchUpstream.md)。
> **技能开发完成（强制）**：任何技能开发/变更完成后，必须同步更新 `docs/skills/` 下对应说明与变更内容（§6 清单、说明文档、维护记录、VERSION 迭代），详见 `docs/skills/Readme.md` §8。

## 5. 顶层文档

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
> **版本迭代规则**：未特别说明版本号时，项目内容所有变更默认归属当前版本 **v1.0.7**（开发中显示 `v1.0.7-dev`），全部迭代到 `versions/VERSION_1_0_7.md`；**除非用户明确说「迭代下一个版本」**，才创建 `VERSION_x_y_z.md` 并同步升级版本号（`__init__.py` / `pyproject.toml`），否则不得擅自变更版本号。
>
> **发布规则（强制）**：**发布 = 打包推送 PyPI + 推送 GitHub Release 总结 + 推送版本 tag**（三者缺一不算完整发布）。执行 `./scripts/release.sh X.Y.Z`（自动升版本 → 构建 → `twine upload` → 创建 GitHub Release（`gh` 或 `GITHUB_TOKEN`，说明默认取自 `VERSION_x_y_z.md` 迭代摘要，可 `--notes <file>` 覆盖）→ `git tag` + push）；**发布完成后必须同步更改 docs 文件状态并提交**——将 `VERSION_x_y_z.md` 状态置为「已发布（Released）」+ 发布时间、`docs/Readme.md` 版本表标记已发布并刷新「最后更新」日期、`docs/Roadmap.md` 更新状态，然后按 git 提交规范（英文简短）提交并推送。详见 `rules/Development.md` §5。
>
> **时间记录规则（重要）**：**所有迭代变更记录的时间必须记录精确时间——年-月-日 时:分:秒**（含 commit 号，取自提交/落地时刻），禁止仅写日期；主导航相关变更另须在 `prds/TopBar.md` §5 追加记录（同样精确到秒）。
>
> **git 提交规范（强制）**：提交描述一律使用**英文**、**简短总结**（Conventional Commits，如 `feat:` / `fix:` / `docs:` / `refactor:` / `test:` 前缀），禁止中文或冗长描述；发布后同步 docs 状态也按此规范提交（如 `docs: mark vX.Y.Z as released`）。**不自动 push**——只执行 `git commit`，推送远端须用户明确发出指令后才执行。详见 `rules/Development.md` §4。
