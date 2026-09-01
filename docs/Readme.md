# docs 文档目录

> **文档状态**：benchscope 文档体系说明与维护约定  
> **最后更新**：2026-09-01 10:40:00

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
| [prds/Accuracy.md](prds/Accuracy.md) | **Accuracy 独立精度测试模块（1.0.8 落地）**：Native / Serving 双模式、9 评测数据集、判分、基线对标、Token 预估、默认页 UI |
| [prds/Sessions.md](prds/Sessions.md) | Sessions：会话管理、SSE 流式、思考解析、性能栏 |
| [prds/Settings.md](prds/Settings.md) | Settings：General / Providers / Models / Datasets / Bench Engines / Skills / Plugins 七栏（1.0.7：面板化 + 每引擎 Mock 开关；Debug 已移除） |

> 命名规则：`<页面名>.md`；有子页面时 `Sessions-xxx.md` 形式。

## 2. 版本修订文档 — `versions/`

每个版本更新的功能主要概述与 TODO 清单，命名 `VERSION_x_y_z.md`，**按时间顺序维护**：

| 文档 | 内容 |
| --- | --- |
| [versions/VERSION_1_0_8.md](versions/VERSION_1_0_8.md) | **1.0.8（开发中）**：当前迭代版本，后续开发内容按时间顺序追加 |
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
| [skills/BsEngineCreate.md](skills/BsEngineCreate.md) | **自定义 Bench 引擎技能详解**（bs-engine-create）：7 步工作流 + 上游源码链接/获取命令 + 实现契约（Input/Core/Output/Mock）+ mock 核心方法 + 导入校验 8 项 + 可复制提示词 + 排错 |
| [skills/BsPerfsConcurrency.md](skills/BsPerfsConcurrency.md) | **并发压测技能说明**（bs-perfs-concurrency）：内置表单、命令、产物打包、Datas/perfs 导入、排错 |
| [skills/BsPerfsThreshold.md](skills/BsPerfsThreshold.md) | **阈值搜索压测技能说明**（bs-perfs-threshold）：内置表单、阈值探测策略、产物打包、Datas/perfs 导入、排错 |

> 上游 bench 核心逻辑分析（源码实证）见 [rules/BenchUpstream.md](rules/BenchUpstream.md)。
> **技能开发完成（强制）**：任何技能开发/变更完成后，必须同步更新 `docs/skills/` 下对应说明与变更内容（§6 清单、说明文档、维护记录、VERSION 迭代），详见 `docs/skills/Readme.md` §8。

## 5. 顶层文档

| 文档 | 内容 |
| --- | --- |
| [agents/Memory.md](../agents/Memory.md) | **项目记忆**：项目速查 + 全部强制约定（文档同步/测试/git/发布/技能/命名）+ 恢复上下文清单；切换模型时优先读 |
| [Roadmap.md](Roadmap.md) | 版本路线（各版本目标范围与状态；后续重新规划） |
| [Projects.md](Projects.md) | 项目功能总览（基于现有功能生成） |
| [agents/Readme.md](../agents/Readme.md) | **项目 harness 约定**（项目级维护约定：git/测试/发布/版本/技能/i18n/命名/最小改动等） |
| [agents/Harness.md](../agents/Harness.md) | **通用 harness 规范**（Harness Coding：有规划、有测试、有反馈；模型/项目无关） |

---

## 文档更新约定（强制）

> **项目级维护约定**（git 提交/推送、测试、发布、版本迭代、技能、i18n、命名、最小改动等）见
> **[agents/Readme.md](../agents/Readme.md)**；本文件只保留**文档体系自身的更新约定**。
>
> 开发更新功能时，按以下规则同步维护文档：
> 1. **页面功能/界面/逻辑/策略/UI 调整** → 更新 `prds/` 对应页面文档；
> 2. **版本功能与 todo** → 更新 `versions/VERSION_x_y_z.md`；
> 3. **架构/方案/设计/开发规范/软件依赖变更** → 更新 `rules/` 对应文档；**软件依赖**（Python `pyproject.toml` / 前端 `web/package.json` 的新增、升级、移除）必须同步 `rules/Software.md` §2 技术栈与 §3 依赖清单；
> 4. **技能说明/变更** → 更新 `docs/skills/<BsXxxYyy>.md`（一个技能一个说明文档）；
> 5. 文档间引用使用相对链接，移动/改名后需同步修正引用；
> 6. 本文件头部「最后更新」日期在每次文档更新时同步刷新；
> 7. **项目约定/记忆变更**（强制约定、测试/发布/git/技能约定等调整）→ 同步 `Memory.md`（项目记忆）与 `agents/Readme.md`。
>
> **时间记录规则（重要）**：**所有迭代变更记录的时间必须记录精确时间——年-月-日 时:分:秒**（含 commit 号，取自提交/落地时刻），禁止仅写日期；主导航相关变更另须在 `prds/TopBar.md` §5 追加记录（同样精确到秒）。
