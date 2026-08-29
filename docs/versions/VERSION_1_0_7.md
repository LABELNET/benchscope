# VERSION 1.0.7 — 版本修订记录

> **版本**：1.0.7  
> **状态**：已发布（Released）  
> **发布时间**：2026-08-30  
> **文档状态**：已发布版本（`v1.0.7`），迭代记录归档如下；后续开发请创建新版本文档  
> **目录**：页面级行为细则见 `docs/prds/`；版本路线见 `docs/Roadmap.md`

---

## 1. 版本概述

1.0.7 为 1.0.6 发布后的**迭代开发版本**，规划重点：**收口 1.0.6 遗留占位能力**（Dashboard 指标 / Datas-Evals / Datas-Analysis / Models 部署 / Plugins），并延续性能页与记录管理能力增强。规划功能见 [docs/Roadmap.md](../Roadmap.md) 1.0.7 小节，逐项落地后在此按时间顺序记录迭代明细。

## 2. 版本规划目标（用户确认版）

### 主目标：性能测试核心引擎改造

详见架构方案：[docs/rules/BenchEngine.md](../rules/BenchEngine.md)（引擎抽象 / 内置引擎 / 环境校验 / 参数描述 / 自研 bench 核心设计）。

| # | 目标 | 说明 |
| --- | --- | --- |
| 1 | **自研 bench（benchscope）** | 基于 vLLM / SGLang 的 bench 思路实现**自研测试引擎**，不依赖本地框架环境，pip 安装即可远程测 OpenAI 兼容服务 |
| 2 | **vllm bench 版本化** | 支持指定具体版本的原生 vLLM bench（如 `vllm-0.23`），可因版本存在多个 |
| 3 | **sglang bench 版本化** | 支持指定具体版本的原生 SGLang bench（如 `sglang-0.5.10`），可因版本存在多个 |
| 4 | **参数下拉 + 描述** | 各引擎各项参数均有独立参数设置，下拉选择，选中后展示描述信息 |
| 5 | **Settings → Bench 配置** | 新增 Bench 配置栏：内置 `bench` / `vllm-0.23` / `sglang-0.5.10`，含介绍与对比情况 |

**环境校验约定（强制）**：
- 原生引擎（vllm / sglang）：**必须校验 `torch` 与 `vllm` / `sglang` 安装版本**，环境不存在或不匹配 → **禁止进入下一步选择参数**；
- 自研 bench（benchscope）：**无需上述环境**，本地安装即可对远程 OpenAI API 进行测试。

### 次要候选（主目标完成后评估）

| # | 候选项 | 现状 |
| --- | --- | --- |
| A | Dashboard 指标补全 | Overview 六宫格 `Max Perf/Eval Records (RUN ID)` 显示 `—` |
| B | Datas/Analysis 记录对比分析页落地 | 占位页 |
| C | Datas/Evals 精度记录页落地 | 占位页 |
| D | Settings → Models 一键下载/部署 | 部署按钮待实现 |
| E | Settings → Plugins 插件机制 | 占位 |
| F | 任务管理与导出增强 | 无搜索筛选 / 无报告导出 |

## 3. 迭代记录（按时间顺序）

### 迭代 1（2026-08-28 17:38:03）：版本初始化（1.0.7 开发启动）

**功能概述**：
- 新建 `docs/versions/VERSION_1_0_7.md`（版本概述 + 候选规划 + TODO 清单框架）
- 版本号 `1.0.6` → `1.0.7.dev0`（`benchscope/__init__.py` `__version__` / `pyproject.toml` / `web/package.json` 同步），TopBar 动态显示 `v1.0.7-dev`
- `docs/Roadmap.md`：1.0.6 标记已发布（2026-08-28）+ 新增 1.0.7 小节
- `docs/Readme.md`：版本表新增 1.0.7 行，迭代规则当前版本改为 v1.0.7
- 开发环境：`./scripts/dev.sh start`（:8080 后端+前端，:8001 mock OpenAI）

**TODO 状态**：
- [x] 工程 — 1.0.7 版本初始化（版本文档 + 版本号 + Roadmap + Readme + 开发模式启动）

### 迭代 2（2026-08-28 18:14:58）：核心引擎改造规划（方案待确认）

**背景**：用户给出 1.0.7 主目标——**性能测试核心引擎改造**（自研 bench + vllm/sglang 原生版本化 + 参数下拉描述 + Settings Bench 配置 + 环境校验），要求先规划确认。

**产出**：
- 新增架构方案 [`docs/rules/BenchEngine.md`](../rules/BenchEngine.md)：
  - **引擎抽象**（`BenchEngine` 接口 + `configs/benchs.yaml` 注册表 + `BenchEngineRegistry`），三类引擎：`benchscope`（自研）/ `vllm-<version>` / `sglang-<version>`
  - **环境校验约定**：原生引擎校验 `torch` + `vllm`/`sglang` 版本范围，不满足禁止进入参数选择；自研引擎无框架依赖
  - **参数体系**：`ParamDef` → `ParamSpec`（+ 选项级描述 `OptionMeta` / 分组 / `since`/`deprecated` 版本适配）
  - **自研 bench 核心设计**：异步负载生成器 + 流式指标采集（TTFT/ITL/TPOT/E2E）+ 口径对齐 vLLM + 技术选型待确认
  - 实施路径 P1–P6 与影响面清单
- `VERSION_1_0_7.md` / `Roadmap.md` 规划同步

**调研结论（现状）**：
- 引擎链路：`benches/{base,vllm_bench,sglang_bench}.py` 构建命令 → `runner.py`（`bash -lic` 子进程）→ `parser.py` 正则解析；参数硬编码 `CURATED_PARAMS` + `configs/{vllm,sglang}-default.yaml`
- 无版本概念、无自研引擎、无环境校验；`BenchOptions` 无 `tokenizer` 字段（外部动态挂属性，`task_manager.py:81`）
- 环境检测已有基础：`env_info.py::_pkg()` 可取 `torch`/`vllm`/`sglang` 版本（当前仅 Dashboard 展示，未做校验）

**TODO 状态**：
- [x] 规划 — 核心引擎改造方案（BenchEngine.md）+ 版本文档/Roadmap 同步
- [x] 确认 — 自研 bench 核心技术选型：aiohttp / 服务端 usage 计数 / 近似长度 / 口径严格对齐 vLLM / 内置+可扩展

### 迭代 3（2026-08-28 18:45:12）：P1 引擎抽象 + P2 环境校验（自研引擎可用，原生引擎按环境阻断）

> **完成时间**：2026-08-28 18:45:12

**功能概述**：
- **引擎定义文件** `benchscope/configs/benchs.yaml`（yaml 驱动，用户可扩展）：三个内置引擎 + 6 维对比表
  - `benchscope`（kind=builtin，自研）：无框架环境依赖，`requires: []`
  - `vllm-0.23`（kind=vllm）：要求 `torch>=2.0` + `vllm>=0.23,<0.24`
  - `sglang-0.5.10`（kind=sglang）：要求 `torch>=2.0` + `sglang==0.5.10`
- **引擎注册表** `benchscope/benchs.py`：yaml 加载（`load_bench_engines` / `load_comparison` / `get_engine` / `default_engine_id`）、版本范围匹配（`_match_spec` 支持 `>=,>,<,<=,==,!=`、忽略 rc/dev 后缀、零新增依赖）、环境校验（`check_env`：builtin 恒通过；原生引擎逐项校验 torch + 目标框架 + CLI 可用性）、摘要（`engine_summary` / `list_engines`）
- **API** `benchscope/server/api_benchs.py`（挂载 `app.py`）：
  - `GET /api/benchs`（引擎清单 + 对比表 + 默认引擎 + 环境校验）
  - `GET /api/benchs/{engine_id}`（单引擎详情）
  - `GET /api/benchs/{engine_id}/env-check`（`{ok, checks:[{name,required,installed,ok,hint}]}`）
- **前端 Settings → Bench 引擎栏**（菜单顺序：General / Environment / Models / Datasets / **Bench 引擎** / Plugins）：引擎卡片（名称 + 类型 + 版本 + 默认标签 + 环境状态标签 + 介绍 + 特点列表 + 环境要求明细（要求版本/已安装/OK-FAIL/安装提示））+ 引擎对比表（6 维 × 3 引擎）
- **前端创建页（PerfCreateView）引擎选择 + 环境阻断**：Step1 顶部新增引擎选择器（下拉 + 引擎介绍 + 环境校验明细）；默认自研引擎；**原生引擎环境不满足时点击「下一步」被阻断**并 `message.warning`（`benchEnvBlocked`）；payload 新增 `engine_id` 字段

**实现策略**：引擎定义与代码解耦（yaml 驱动，新增引擎/版本无需改代码）；环境校验复用 `importlib.metadata.version` 检测已装版本，原生引擎追加 CLI 可用性探测（`vllm` 可执行文件 / `sglang.bench_serving` 模块可导入）；自研引擎 `requires` 为空 → 恒可用，保证「pip 装完即可远程测 OpenAI 服务」。

**验证**：`check:i18n` 通过（zh/en 键集一致，新增 21 组 bench 相关文案）；`npm run build` 通过；`./tests/run_tests.sh` 全量通过（**API 65/65**（新增 `tests/api/test_benchs.py` 16 项）、**WebUI 20/20**（新增 `test_settings_benches_panel`、`test_perf_create_engine_select_and_env_block`））。

**TODO 状态**：
- [x] P1 — 引擎抽象（configs/benchs.yaml + benchs.py 注册表 + /api/benchs* + 前端 Settings Bench 栏 + 创建页引擎选择）
- [x] P2 — 环境校验（torch/vllm/sglang 版本范围 + CLI 探测 + 前端阻断交互）
- [ ] P3 — 参数体系（ParamSpec + 选项级描述 + 前端下拉描述面板）
- [ ] P4 — 自研引擎（aiohttp + 流式采集 + 口径对齐 vLLM + task_manager 集成）
- [ ] P5 — Settings Bench 栏增强（如用户自定义引擎编辑，随 P1 已落地基础版）
- [ ] P6 — 测试与文档收口（Architecture.md / Software.md 依赖同步）

### 迭代 4（2026-08-28 21:45:04）：P4 自研 bench 引擎落地（aiohttp 流式压测 + 口径对齐 vLLM）

> **完成时间**：2026-08-28 21:45:04

**功能概述**：
- **自研引擎** `benchscope/benches/builtin_bench.py`（约 500 行）：基于 **aiohttp** 的 OpenAI 兼容 API 异步流式负载生成器
  - **`Requester`**：SSE 流式执行，采集单请求时间线 `t0 → t_first → t_i → t_end`（TTFT / ITL 精确测量的前提）；输出 token 取服务端 `usage.completion_tokens`（`stream_options.include_usage`），缺失时回退 chunk 数估算
  - **`LoadGenerator`**：`concurrency` 个 worker 持续发请求直到完成 `num_prompts`（vLLM bench 同语义）；`request_rate` 泊松到达控制；支持 `num_warmups` 预热（不计入指标）；`threading.Event` → `asyncio.Event` 停止信号桥接
  - **`MetricsCollector`**：**口径严格对齐 vLLM bench**——`TPOT=(E2E-TTFT)/(completion_tokens-1)`、`output throughput=总 completion_tokens/duration`、`total throughput=(prompt+completion)/duration`、`req/s`；各指标 mean/median/p99（最近秩分位数，单样本不抛错）；新增 `peakoutput_mean`（1 秒滑窗峰值吞吐）、`single_user`（用户 QPS）
  - 输出 vLLM 风格文本（`Serving Benchmark Result`）便于日志查看与人工比对
- **任务集成** `task_manager.py`：新增 `_builtin_engine()` / `_builtin_options()`；`_run_one` 按 `engine_id` 分支——**自研引擎进程内执行**（跳过命令构建 / 子进程 / 输出解析），其余回退原生链路（旧任务兼容）
- **`api_tasks.py`**：`CreateTaskRequest` 新增 `engine_id` 字段（**关键**：pydantic 白名单，不声明会被丢弃，与 `max_concurrency_search` 同坑）
- **mock 服务** `mocks/openai_server.py`：支持 `stream_options.include_usage`（usage 独立 chunk）、按 `max_tokens` 补齐输出长度、粗略 token 计数（自研引擎依赖服务端 usage）
- **依赖**：新增 `aiohttp>=3.9`（`pyproject.toml` + `Software.md` 同步）

**实现策略**：全部请求失败时**抛错**而非返回全 0 指标（避免误判为测试成功）；分位数用最近秩（numpy/vLLM 语义）且单样本不抛错；自研引擎不经子进程，天然支持跨平台与远程服务。

**实测（对 mock 服务 :8001）**：
```
conc= 1  out_tps=  64.9  req/s= 2.03  ttft=2.43ms  tpot=15.83ms  ok=1
conc= 2  out_tps= 130.5  req/s= 4.08  ttft=2.17ms  tpot=15.73ms  ok=2
conc= 4  out_tps= 260.2  req/s= 8.13  ttft=2.06ms  tpot=15.79ms  ok=4
conc= 8  out_tps= 517.8  req/s=16.18  ttft=2.92ms  tpot=15.83ms  ok=8
```
吞吐随并发线性增长、延迟稳定，usage 精确计数生效（32 token/请求）。

**验证**：`./tests/run_tests.sh` 全量通过——**API 74/74**（新增 `tests/api/test_builtin_bench.py` 12 项：分位数边界、TPOT 口径、吞吐/失败计数、prompt 构造、mock 发压、并发扩展、不可达端点、任务级集成自研+原生双链路）、**WebUI 20/20**。

**修复记录**：
- `builtin_bench.py` 缺 `import aiohttp`（仅类型注解引用）→ 补显式导入
- `_percentile` 单样本时 `statistics.quantiles` 抛错 → 改为最近秩实现
- `engine_id` 被 `CreateTaskRequest` 白名单丢弃 → 补字段声明
- WebUI 测试在环境校验中（spin 状态）断言标签 → 改为等待标签出现

**TODO 状态**：
- [x] P4 — 自研引擎（aiohttp + 流式采集 + 口径对齐 + task_manager 集成 + mock 支持 usage）
- [ ] P3 — 参数体系（ParamSpec + 选项级描述 + 前端下拉描述面板）
- [ ] P5 — Settings Bench 栏增强（用户自定义引擎编辑）
- [ ] P6 — 测试与文档收口（Architecture.md 同步）

### 迭代 5（2026-08-28 23:20:40）：P3 参数描述体系 + P5 引擎可扩展 + P6 架构文档 + 核心实现存档

> **完成时间**：2026-08-28 23:20:40

**功能概述**：
- **P3 参数下拉 + 描述**（用户原始需求第 4 条）：
  - 新增 `benchscope/configs/bench-params.yaml`：为三引擎共 **37 项参数**提供说明文案与下拉选项（**每个选项都带描述**）——自研 7 项（backend/endpoint/request-rate/num-warmups/chars-per-token/timeout/temperature）、vLLM 19 项、SGLang 11 项
  - 新增 `benchscope/bench_params.py`：参数定义加载（按 `params_key` 取参数集 / 单参数定义 / 选项描述）
  - API：`GET /api/benchs/{id}/params`（参数集）、`GET /api/benchs/{id}/params/{key}/option-desc`（单取值描述）
  - 前端 `ParamGroupPanel.vue`：参数行改为**下拉选择**（有 options 时）→ 选中后在参数行下方**展示该选项描述**；无选项时展示参数说明；参数名优先用 `label`
  - 自研引擎读取新增参数：`timeout` / `chars_per_token` / `seed` / `temperature`
- **P5 引擎可扩展**（Settings Bench 栏增强）：
  - API：`GET/PUT /api/benchs/config/yaml`（查看 / 保存 `configs/benchs.yaml`），保存时校验（YAML 合法 / 顶层 dict / engines 非空列表 / 每项含 id / kind 属于 builtin|vllm|sglang），**校验失败返回 400 且不写文件**
  - 前端 Settings → Bench 引擎栏底部新增「引擎定义（benchs.yaml）」区：只读预览 → 点击「编辑」进入 textarea → 保存后刷新引擎列表
- **P6 文档**：`Architecture.md` 新增「§5 测试引擎架构」分层图与关键设计、操作流补充「选择测试引擎」、设计约束补充「引擎分层执行」「引擎与版本解耦」
- **⭐ 核心实现存档**：新增 [`docs/rules/BenchCore.md`](../rules/BenchCore.md)——自研 bench 核心实现总结（核心结论 / 为何必须流式 / 四子系统实现 / 与原生链路对比 / 设计决策与取舍 / 实测数据 / 已知限制 / 代码地图），并登记到 `docs/Readme.md` 文档索引

**核心结论存档（BenchCore.md 摘要）**：
> 自研 bench 的核心 = **「基于 OpenAI 兼容 API 的异步流式负载生成器」** + **「与 vLLM bench 严格对齐的指标口径」**。前者决定能不能测，后者决定测得准不准、能否与原生引擎对比。
> - **必须流式**：非流式只能测 E2E，TTFT / ITL / TPOT 均不可测；时间线 `t0 → t_first → t_i → t_end`
> - **两个易错点**：① TPOT 分母是 `tokens - 1`（首 token 已计入 TTFT）；② `benchmark_duration` 必须是墙钟时间（否则吞吐严重高估）
> - **实测**：并发 1/2/4/8 → 吞吐 64.9/130.5/260.2/517.8 tok/s（线性增长），TPOT 稳定 ≈15.8ms

**验证**：`./tests/run_tests.sh` 全量通过——**API 78/78**（新增 4 项：参数集 API、原生引擎参数描述完整性、选项描述 API、benchs.yaml 读写校验含非法输入 400 与 finally 还原）、**WebUI 20/20**；i18n 一致、构建通过。

**修复记录**：
- **模块名冲突**：`benchscope/benchs/params.py` 与 `benchscope/benchs.py`（引擎注册表）同名，Python 将 `benchscope.benchs` 解析为模块而非包 → `ModuleNotFoundError: 'benchscope.benchs' is not a package`。已迁移为 `benchscope/bench_params.py`（并在 BenchCore.md 代码地图标注该陷阱）
- 自研引擎缺 `params_key`，回退为 `builtin` 导致参数集为空 → `configs/benchs.yaml` 补 `params_key: benchscope`

**TODO 状态**：
- [x] P3 — 参数体系（yaml 参数描述 + 前端下拉 + 选中后展示描述）
- [x] P5 — Settings Bench 栏增强（benchs.yaml 查看/编辑 + 保存校验，用户可扩展引擎）
- [x] P6 — 架构文档（Architecture.md 引擎分层）+ 核心实现存档（BenchCore.md）

### 迭代 6（2026-08-29 10:01:26）：自定义引擎 skills 体系 + 导入校验落地

> **完成时间**：2026-08-29 10:01:26

**功能概述**：
- **skills 项目规范制定**（新增 `skills/Readme.md`）：目录结构（SKILL.md / README.md / references / templates / scripts）、frontmatter 规范（name/description/**version**）、正文结构、README 规范、**打包规范**（每个技能强制 `scripts/package.sh`，产物 `<name>-<version>.tar.gz` + 可解压校验）
- **新增技能 `skills/bench-engine-authoring/`**（自定义 bench 引擎开发）：
  - `SKILL.md`：工作流（确认版本 → **按 tag 读上游真实参数** → 生成两份 yaml → mock 逻辑 → 校验 → 导入）、**上游链接**（vLLM `vllm/benchmarks/serve.py`、SGLang `python/sglang/bench_serving.py`，含 `{version}` 模板）、**mock 核心方法与介绍**（`_scale_stats` / `generate_vllm_output` / `generate_sglang_output` / `_sse_stream` / `_count_tokens` 等 + 两条硬规则：输出匹配 parser 正则、指标随并发缩放）、**可复制 AI 提示词**、导入校验清单、自检项
  - `references/`：`engine-schema.md`（字段参考+示例）、`mock-core.md`（mock 核心方法详解）、`import-checklist.md`（校验项/API/排错）
  - `templates/`：`benchs-engine-entry.yaml`、`bench-params-section.yaml`
  - `scripts/`：`package.sh`（打包+产物校验）、**`validate.sh`（离线校验引擎定义，无需启动服务）**
  - `README.md`：用途 / 使用方式 / 目录结构 / 打包 / 关键约定 / 维护记录
- **优化已有 skills**（`vllm-bench-testing` / `sglang-bench-testing` → v1.1.0）：补 `version` frontmatter、新增「引擎选择与环境校验」章节（含环境要求表与阻断规则）、README.md、package.sh，章节重编号
- **后端导入校验**（`benchscope/benchs.py`）：新增 `validate_benchs_yaml()`——**7 项校验**（yaml / engines / id 唯一 / kind / requires（原生须 torch+框架带 spec）/ params_key 存在 / option_desc 完整 / mock 输出），`save_benchs_yaml_text()` 改为**校验通过才写文件**
- **API**（`api_benchs.py`）：`POST /api/benchs/import`（`dry_run` 预校验 / `apply` 写入，返回逐项 checks）、`GET /api/benchs/authoring`（技能信息 + 上游链接模板 + **可复制提示词**）、`PUT /api/benchs/config/yaml` 返回校验明细
- **前端**（Settings → Bench 引擎栏）：新增「**添加自定义版本**」面板——上游 GitHub 链接（可点击）、**AI 提示词一键复制**、引擎定义导入区（先「校验」→ 全部通过后「导入」按钮才可用 → 导入成功刷新列表），校验结果逐项展示（OK/FAIL + 原因）

**实现策略**：引擎定义与代码解耦（yaml 驱动）；校验逻辑前后端一致（后端 `validate_benchs_yaml` 与技能 `validate.sh` 规则对齐）；静态路由（`/authoring` `/import` `/config/yaml`）**必须注册在 `/{engine_id}` 之前**，否则被参数路由拦截 404。

**验证**：`./tests/run_tests.sh` 全量通过——**API 92/92**（新增 `tests/api/test_skills.py` 10 项：目录结构 / frontmatter 规范 / 三个技能打包产物校验 / 自定义引擎技能内容完整性 / validate.sh 正反例 / Readme 清单）、**WebUI 20/20**；i18n 一致、构建通过；三技能打包均通过（bench-engine-authoring-1.0.0 / vllm-bench-testing-1.1.0 / sglang-bench-testing-1.1.0）。

**修复记录**：
- `/api/benchs/authoring` 返回 404 —— 静态路由注册在 `/{engine_id}` 之后被拦截 → 调整注册顺序（已在代码注释标注该陷阱）
- 旧测试 `test_benchs_yaml_get_and_save` 因新增校验项（params_key / requires 完整性）失败 → 更新测试用自定义配置使其满足全部校验
- 清理遗留：删除废弃模块 `benchscope/benchs/params.py`（与 `benchs.py` 同名冲突）

**TODO 状态**：
- [x] 技能 — skills 项目规范 + bench-engine-authoring 技能 + 已有 skills 规范化
- [x] 导入 — 7 项校验 + /api/benchs/import（dry_run/apply）+ /api/benchs/authoring
- [x] 前端 — Settings「添加自定义版本」面板（提示词复制 + 上游链接 + 校验后导入）

### 迭代 7（2026-08-29 17:59:10）：上游 bench 源码实证分析 + skills 文档归口 `docs/skills/`

**变更内容**：

1. **上游 bench 核心逻辑分析（源码实证）**
   - 拉取并分析 **vLLM v0.23.0**（commit `0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665`，
     `vllm/benchmarks/serve.py` 2052 行 + `lib/endpoint_request_func.py` 861 行）与
     **SGLang v0.5.10**（commit `1519acf37c23f2189adb93f57ca9cd2db1bebf18`，
     `python/sglang/bench_serving.py` 2352 行）的 bench 核心逻辑
   - 存档 `docs/rules/BenchUpstream.md`：git/zip/tarball 链接、pinned 文件链接、获取命令、
     时间线采集与指标公式（带源码行号）、token 计数、并发与速率控制、与自研引擎对齐表、后续优化项
   - 技能侧同步 `skills/bench-engine-authoring/references/upstream-analysis.md`
2. **自定义引擎实现方法明确化**：新增「**复制上游代码 + 适配四段契约**」章节——
   入口（Input `BuiltinOptions`）/ 处理（Core 复制上游时间线与公式）/ 出口（Output 兼容
   `parser.parse_metrics`）/ Mock（仅 `mocks/`，匹配 parser 正则）；`SKILL.md` §3.5 与
   `README.md` 同步
3. **skills 文档归口整理**：新增 `docs/skills/` 目录
   - `docs/skills/Readme.md` —— Skills 体系总入口（定位 / 目录结构规范 / SKILL.md 与 README.md 规范 /
     打包规范 / 技能清单 / 文档索引 / 维护约定）
   - `docs/skills/BenchEngineAuthoring.md` —— 自定义引擎技能详解（7 步工作流 + 上游链接与获取命令 +
     实现契约 + mock 核心方法 + 导入校验 8 项 + 可复制提示词 + 排错）
   - `docs/skills/BenchTesting.md` —— vLLM/SGLang 性能测试技能说明（引擎选择与环境校验 / 配置 /
     测试流程 / 日志产物 / 排错）
   - `skills/Readme.md` 精简为**速查指针**（清单 + 强制结构 + 关键约定），规范正文统一以
     `docs/skills/Readme.md` 为准，避免两处重复维护
   - `docs/Readme.md` 索引新增「§4 技能文档 — skills/」
4. **测试修复**：`tests/api/test_skills.py` 补充上游分析文档校验（版本/commit/zip 链接/公式/
   契约关键字）与技能文档归口校验

**实现策略**：上游分析以**具体 commit + 行号**为事实依据（禁止凭记忆写参数）；
文档采用「技能产物在 `skills/`、说明文档在 `docs/skills/`」的分工，规范正文单一来源。

**验证**：`./tests/run_tests.sh` 全量通过 —— **API 97/97**（新增 4 项：`docs/skills/` 目录与三份文档内容校验、docs 索引登记）、**WebUI 20/20**。

**修复记录**：
- `tests/api/test_skills.py` 首行误插入字符 `1` → **语法错误导致 `tests/api` 整体 collection 中断**
  （0 个 API 测试执行）；连带使 `conftest.client` fixture 不运行，配置中推理地址仍为默认 `:8000`，
  导致 WebUI `test_perf_create_threshold_mode` 因「推理服务不可达」误报失败。
  → 删除多余字符恢复；**教训：collection 级语法错误会级联影响 WebUI 测试，须先查 API 收集结果**

**TODO 状态**：
- [x] 上游分析 — vLLM v0.23.0 / SGLang v0.5.10 源码实证 + BenchUpstream.md 存档
- [x] 实现方法 — 复制上游 + 四段契约（Input/Core/Output/Mock）写入技能与文档
- [x] 文档归口 — `docs/skills/` 三份文档 + `skills/Readme.md` 精简 + docs 索引同步
- [x] 测试修复 — test_skills.py 语法错误修复 + 全量回归通过

### 迭代 8（2026-08-29 19:42:00）：创建任务流程引擎联动 + Bench CLI 命名 + Settings/Bench Engines 重构

**变更内容**：

1. **创建任务流程引擎联动（参数与命令随引擎）**
   - **Step2 取消双框架 Tab（vLLM / SGLang）**，改为**单参数面板**：只显示 Step1 所选引擎的参数
     （顶部展示当前引擎名称与版本，附说明 `paramsEngineHint`）
   - 新增**引擎参数清单**（每个引擎一套，互不干扰）：
     `configs/{params_key}-default.yaml`（取值）+ `bench-params.yaml` 的 `{params_key}` 段（说明）
     - Bench CLI → `benchscope-default.yaml`（9 项：backend / endpoint / request-rate /
       num-prompts / num-warmups / chars-per-token / timeout / temperature / seed）
   - 新增接口 `GET/PUT /api/benchs/{id}/params-yaml`（读取 / 保存引擎参数清单）
   - **Step3 命令预览随引擎变化**：`build_command_lines()` 按 `kind` 分支
     - 自研（`kind=builtin`）→ `benchscope perf ...`（标题行展示引擎标签 + 复制按钮 + `commandHintBuiltin`）
     - 原生（vllm / sglang）→ 对应 CLI，参数清单以 `--key=value` 附加
   - 新增 **`benchscope perf` 子命令**（`benchscope/cli.py`），使预览命令**可直接复制执行**
   - payload 新增 `engine_params_yaml` 字段；`_builtin_options()` 优先使用引擎参数清单，
     回退旧 `curated`；`merge_extra_args()` 原生引擎同样优先引擎参数清单
2. **自研引擎命名统一为 Bench CLI**
   - `benchs.yaml`：`name: Bench CLI`，对比表「引擎类型」→ `Bench CLI（自研内置）`
   - 界面、文档（`BenchCore.md` / `BenchEngine.md` / `Performance-Create.md` / `Settings.md`）同步
3. **Settings / Bench Engines 界面重构**
   - **整页即引擎列表**，列表区独立可滑动（`.bench-list-scroll`），顶部操作栏固定
   - **右上角三个文字按钮**（点击中间弹框）：
     - **Create Engine** → 制作教程 + 上游链接 + 可复制 AI 提示词（**不再展示 Engine Definition 原文**）
     - **Upload Engine** → 拖拽上传区（`.yaml` / `.yml` / `.tar.gz` / `.tgz`）+ 校验结果
     - **Engine Comparison** → 对比表（原内联表移入弹框）
   - 新增 **`POST /api/benchs/upload`**（multipart）：支持引擎定义原文与技能包；
     引擎按 `id` 合并（新增 / 更新）、对比表按 `dimension` 去重、参数段按 `params_key` 覆盖；
     **校验通过才写盘**；20MB 上限；拒绝 `../` 路径穿越与绝对路径
4. **中英文 i18n**：新增 26 组键（Create/Upload/Comparison 弹窗、教程步骤、参数联动提示等），
   `zh` / `en` 键集合校验一致

**实现策略**：参数「取值」与「说明」分离到两个配置文件（一一对应）；
命令预览由引擎 `kind` 驱动分支；上传校验顺序上**先并入随包参数段再校验 `params_key`**。

**验证**：`./tests/run_tests.sh` 全量通过 —— **API 109**（较迭代 7 的 97 项 +12）/ **WebUI 25**（较 20 项 +5）。
新增用例 —— API：Bench CLI 命名、引擎参数清单读写（3）、引擎包上传（4，含路径穿越防护）、
命令随引擎联动、参数构造映射、参数优先级、CLI 子命令解析、技能包上传契约；
WebUI：右上角按钮、Create / Upload / Comparison 三个弹框、Step2 参数跟随引擎。

**修复记录**：
- **配置被误还原**：上传接口人工验证后用 `git checkout -- benchscope/configs/*.yaml` 还原，
  连带把「Bench CLI 命名 + 参数说明段扩展」等**功能改动一起回退** → 重新应用。
  **教训：验证脚本中不要用 `git checkout` 还原配置，应改用备份/恢复文件或仅还原测试产生的增量**
- **上传校验顺序错误**：技能包自带全新 `params_key` 时，原实现先校验（此时参数段尚未写盘）
  后合并参数段 → 必报「params_key 不存在」→ 改为 `validate_benchs_yaml(..., extra_param_sections=...)`
  将待合并参数段并入校验范围
- **WebUI 选择器错误**：`a-upload-dragger` 在 ant-design-vue 4 渲染为 `.ant-upload-drag`
  （非 `.ant-upload-dragger`）→ 修正测试选择器
- **非故障（记录）**：`tests/api/test_sessions.py` 单文件耗时约 270s（mock 流式 chat），
  全量套件约 8–10 分钟，属既有基线，非本次引入

**TODO 状态**：
- [x] 引擎联动 — Step2 单参数面板 + Step3 命令预览随引擎 + `benchscope perf` 子命令
- [x] 参数清单 — `GET/PUT /api/benchs/{id}/params-yaml` + `benchscope-default.yaml`
- [x] 命名统一 — 自研引擎统一为 Bench CLI（配置 / 界面 / 文档）
- [x] Settings 重构 — 右上角 Create / Upload / Comparison 文字按钮 + 弹框 + 可滑动列表
- [x] 引擎包上传 — `POST /api/benchs/upload`（yaml / tar.gz，校验通过才写盘）
- [x] i18n 与文档 — 中英文 26 组键 + prds / rules 同步

### 迭代 9（2026-08-29 20:20:39）：命令统一 `benchscope perf` + Environment 精简 + 弹框与滚动布局 + Bench Engines 全英文

**变更内容**：

1. **界面显示「Bench CLI」，实际命令统一为 `benchscope perf`**
   - CLI 子命令 `benchscope bench` → **`benchscope perf`**（`benchscope/cli.py`：
     `add_parser("perf")` / `_perf()` / `_add_perf_args()`）
   - `build_command()` 输出 `benchscope perf ...`；`run_builtin_bench()` 日志回显同步
   - 任务命令记录 `benchscope perf (builtin) --base-url=... --concurrency=...`
   - 预览命令与 CLI 子命令参数完全一致，可直接复制执行
2. **Settings / Environment 移除 Framework**
   - 删除 vLLM / SGLang 单选，仅保留 **Base URL（OpenAI 接口）** 与 **API Key**
   - **framework 改由所选引擎决定**：`PerfCreateView` 的 `framework` 取
     `selectedEngine.framework`（回退 config）；`test_manager.build_command_lines()`
     同样优先取引擎的 `framework`，避免「引擎是 sglang、命令却按 vllm 生成」
3. **布局与弹框规范**
   - **Bench Engines 列表可滚动**（修复）：`a-spin` 的 `.ant-spin-nested-loading` /
     `.ant-spin-container` 包裹层未传递高度约束，导致 `.bench-list-scroll` 拿不到限高而无法滚动
     → 为包裹层补 `flex: 1; min-height: 0; display: flex; flex-direction: column`
   - **所有页面底部统一保留 18px**：`.app-content-layout { padding-bottom: 18px; box-sizing: border-box }`
   - **弹框统一为 1/3 浏览器宽度**：`.bench-modal { width: 33.33vw !important; min-width: 420px; max-width: 720px }`
     （移除各弹框的 `width` 内联属性，改由 CSS 统一控制）
   - **弹框 header 为提示**：`#title` 插槽改为「标题 + 提示文案」（新增
     `benchCreateHint` / `benchUploadHintText` / `benchCompareHint`）
   - **弹框 footer 为文字操作按钮**：Create → 复制提示词 / 取消；Upload → 校验并导入 / 取消；
     Comparison → 取消
4. **Bench Engines 全英文 + Highlights 精简**
   - 引擎定义改为**双语**：`description` / `highlights` / 对比表 `dimension` / `values` 默认为**英文**，
     中文放 `*_zh`（沿用仓库既有的 `name_zh` / `label_zh` 约定）
   - `engine_summary()` 透传 `name_zh` / `description_zh` / `highlights_zh`；
     前端 `benchName()` / `benchDesc()` / `benchHighlights()` / `compTitle()` / `compValue()`
     按当前语言选择
   - `PerfCreateView` 新增 `engineName`（引擎显示名随语言）
   - **Highlights 只列「简洁特性 + 版本支持」**（≤6 条、每条 ≤80 字符），移除实现方式的描述；
     三个引擎均以 `Version support: ...` 结尾说明版本支持情况

**验证**：`./tests/run_tests.sh` 全量通过 —— **API 112**（较迭代 8 的 110 项 +2）/ **WebUI 30**（较 25 项 +5）。
新增用例 —— API：引擎文案双语（英文默认无中文 + `*_zh` 存在）、Highlights 精简性
（≤6 条 / ≤80 字符 / 含 `Version support`）；WebUI：Environment 无 Framework、
Bench Engines 全英文（列表与对比表）、弹框 header 提示 + footer 文字按钮 + 1/3 宽度、
列表可滚动、全页面底部 18px。

**修复记录**：
- **YAML 冒号陷阱**：highlight 条目 `Version support: any service version ...` 含 `: `，
  被 YAML 解析为 **mapping（dict）** 而非字符串 → 界面渲染异常、断言报
  `'dict' object has no attribute 'startswith'` → 加引号修正，并补充「highlights 必须是字符串」的解析校验。
  **教训：yaml 列表项若含 `: `（半角冒号 + 空格）必须加引号；中文全角「：」无此问题**
- **弹框 class 落点**：ant-design-vue 的 `<a-modal class="bench-modal">` 会把 class 落在
  `.ant-modal` **本身**（不是外层包裹）→ 原选择器 `.bench-modal .ant-modal` 匹配不到，
  宽度规则不生效且测试 `bounding_box()` 超时 → 改为 `.bench-modal { ... }` 直接命中
- **弹框宽度测量偏小**：ant 弹框有缩放动画，打开后立即测量得到 364px（真实 480px）
  → 测量前等待 600ms
- **测试未导航**：`test_all_pages_bottom_padding` 在 `about:blank` 上取样式得到 `None`
  → 先 `goto` 并等待 `.app-content-layout`

**TODO 状态**：
- [x] 命令统一 — CLI 子命令与预览命令统一为 `benchscope perf`
- [x] Environment 精简 — 移除 Framework，保留 Base URL + API Key；framework 改由引擎决定
- [x] 布局 — Bench Engines 可滚动 + 全页面底部 18px + 弹框 1/3 宽（header 提示 / footer 文字按钮）
- [x] 全英文 — 引擎文案双语（英文默认 + `*_zh`）+ Highlights 精简为特性与版本支持

### 迭代 10（2026-08-29 21:15:00）：修复 Step3 旧命令 / 列表滚动 / 弹框宽度 1/2 + 测试约定改为增量

**变更内容**：

1. **Step3 命令仍显示 `benchscope bench`（问题 1，非代码 bug）**
   - 根因：dev 服务（8080）进程启动于 19:07，代码改动在 20:14 —— **服务运行旧代码**；
     重启后 Step3 正确显示 `benchscope perf`
   - **教训：改完代码必须重启 dev 服务再验证；判断「改动是否生效」先比对进程启动时间与文件 mtime**
2. **Bench Engines 列表仍无法滚动（问题 2，迭代 9 修复无效的真因）**
   - 迭代 9 的 `.ant-spin-container` 规则写在 `<style scoped>` 内，编译后变为
     `.ant-spin-container[data-v-xxx]`；该元素是 `a-spin` 的**内部元素（非根元素）**，
     不携带本组件的 data-v 属性 → **规则匹配不到，等于没写**
   - 修复：改为 `:deep(.ant-spin-nested-loading)` / `:deep(.ant-spin-container)` 穿透 scoped
   - 实测验证链：`container display=flex + minH=0` → 列表 `h < scrollH` → `scrollTop` 位移 > 0
3. **弹框宽度 1/3 → 1/2（问题 3）**
   - `.bench-modal { width: 50vw !important; min-width: 480px; max-width: 960px }`
   - 迭代 9 的 1/3 宽度**实际从未生效**：Modal 被 Teleport 到 body，`.bench-modal` 不带 data-v，
     scoped 规则编译为 `.bench-modal[data-v-xxx]` 匹配不到 → 一直是 ant 默认 520px；
     当时测试容差 60px（520 vs 480 差 40）**误判通过**
   - 修复：弹框相关 27 条规则统一包裹 `:global()`（Teleport 元素一律用 :global，不用 :deep——
     后者对插槽内容同样拿不到 scopeId）；**测试容差收紧到 20px**、定位器限定 `:visible`
     （关闭后的 Modal 仍留在 DOM）
   - 尝试过 `:get-container="false"` 就地渲染让 scoped 生效，但多层组件根链丢失 scopeId，
     且就地渲染使 `.bench-modal` 匹配到多个实例，已回退为 Teleport + :global
4. **测试约定（问题 4，长期生效）**：**不做全量测试；按增量/变更测试**——每次改动只运行
   涉及变更功能的测试（前端 → `tests/webui -k <关键词>`，后端 → `tests/api/test_<模块>.py`）
   - 配套修复 `tests/conftest.py`：mock 指向改为 **session 级 autouse fixture**（`point_to_mock`），
     增量单独跑 `tests/webui` 时环境自备（此前依赖 API 测试先跑、由 `client` fixture 间接配置，
     单跑 WebUI 会因 base_url 未指向 mock 而 Step1 校验失败 —— 本次 `params_follow` 单跑失败即此因）
   - WebUI 增量命令：`BS_TEST_URL=... BS_MOCK_URL=... pytest tests/webui -k "bench"`；
     后端增量：`pytest tests/api/test_benchs.py`
5. **测试基建加固**：`test_settings_benches_list_scrollable` 由「恒真表达式」改为硬断言
   （约束链 display/min-height + 实际滚动位移 > 0），防止再次出现「样式未生效但测试通过」

**验证**（增量）：WebUI `-k "bench or environment or bottom_padding or params_follow"` **11/11**；
API `test_benchs + test_builtin_bench` **47/47**（含 conftest fixture 改动回归）；
`verify_all.py` 实测滚动位移与三弹框宽度（720px = 视口 1/2）均通过。

**修复记录**：
- 上述 4 项根因均属「样式作用域 / 服务旧代码 / 测试断言过松」三类问题，产品逻辑无需改动

**TODO 状态**：
- [x] Step3 命令 — 重启 dev 服务后正确显示 `benchscope perf`
- [x] 列表滚动 — `:deep()` 穿透 a-spin 内部容器，实测滚动位移 > 0
- [x] 弹框 1/2 宽 — :global 化 27 条规则 + 容差 20px 测试防误判
- [x] 测试约定 — 增量/变更测试落地（conftest autouse 自备 mock 环境）

### 迭代 11（2026-08-29 22:00:00）：mocks 环境联调 + Providers 多提供方 + 阈值 Max Requests 强制结束 + 文案调整

**变更内容**：

1. **原生引擎 mocks 环境可测试**：创建任务选 vllm/sglang 且环境校验失败时，
   展示 `Use Mock Environment (mocks)` 勾选；勾选后放行后续步骤，执行走 FAKE 模式
   （`BenchRunner` 新增实例级 `fake` 开关，由 payload `use_mock_env` 驱动，优先于环境变量），
   无本地框架也可完成全流程联调
2. **Performance 默认页介绍卡片改为按模式/能力介绍**：Concurrency Testing（并发测试模式）/
   Threshold Search（阈值模式及功能）/ Realtime Performance Charts（实时可视化性能数据），
   移除旧「Multi-Framework Compare / Multi-Combo Test / Realtime Data Analysis」文案
3. **Create Engine 提示词改为生成压缩包**：要求 AI 直接产出
   `<framework>-<version>-engine.tar.gz`（内含 `configs/benchs.yaml` + `configs/bench-params.yaml`
   + `README.md`，含打包命令），**导入即上传该压缩包**（Upload Engine），不再手贴 yaml
4. **Settings/Environment → Providers**：菜单与面板头改名 Providers（去掉 Envs 字样）；
   支持**多个 Provider**（每个一个面板，header 显示 Provider Name + Active 标签）；
   **Add Provider 按钮与弹窗**（Provider Name 必填）；Activate 激活同步到 `config.api`；
   Delete 删除（激活项被删回退首个）；接口
   `GET/POST /api/config/providers`、`PUT/DELETE .../{id}`、`POST .../{id}/activate`；
   旧配置启动时自动迁移出名为 Default 的 Provider（`_migrate_providers`，全新/存量配置均覆盖）
5. **Conditions 移除 Request Rate**：请求速率移至 Step2 引擎参数（`request-rate` 默认 Inf），
   预览条件中的 Request Rate 读取引擎参数清单；
   **阈值模式新增 Max Requests（默认 4096）**：探测中**下一次执行的请求数（= 并发数）超过上限**
   → 任务直接强制结束，状态显示 **Finish**（快照 `forced_finish: true`），不再执行后续 case；
   与 `max_concurrency_search`（搜索上限，到顶正常结束）语义区分——仅当 `max_requests`
   先被突破才强制结束

**验证（增量）**：API 69/69（test_config + test_tasks + test_benchs，新增 7 项：
Providers 迁移与 CRUD/激活 2、强制结束 1、mocks 环境 1、提示词压缩包 1，及既有阈值执行回归）；
WebUI 4/4（Providers 面板与弹窗、Conditions 无 Rate + Max Requests 默认 4096、
mocks 勾选放行、介绍卡片新文案）。

**TODO 状态**：
- [x] mocks 环境 — 原生引擎勾选 Use Mock Environment 即可测试（FAKE 模式）
- [x] 介绍卡片 — 并发/阈值/实时可视化三张功能介绍卡
- [x] 引擎包 — 提示词产出 tar.gz 压缩包，导入上传压缩包
- [x] Providers — 多 Provider 管理（Name 必填 + Add 弹窗 + 面板 header 显示名称，无 Envs 字样）
- [x] Conditions/Max Requests — 移除 Request Rate；阈值模式超限强制结束标记 Finish

### 迭代 12（2026-08-29）：use_mock_env 贯穿展示层

**变更内容**：

1. **任务快照透出 `use_mock_env`**：`task_manager.py::Task.snapshot()` 新增
   `use_mock_env` 字段（读 payload，默认 False），API 返回的任务详情可标识 FAKE 仿真任务
2. **Perf 面板 Mock 标识**：PerformanceView Perf 面板 Framework 行右侧，当
   `theTask.use_mock_env` 为真时显示橙色 **Mock** tag（`.mock-env-tag`），
   title 提示仿真运行（`mockEnvTagHint`）；新增 zh/en i18n 键 `mockEnvTag` / `mockEnvTagHint`
3. **测试**：
   - 后端 `test_native_engine_with_mock_env` 增加断言：快照 `use_mock_env is True`
   - WebUI 新增 `test_mock_env_tag_in_task_detail`：创建并运行 `use_mock_env: true` 任务，
     详情页断言 `.mock-env-tag` 可见且文本为 Mock

**验证（增量）**：后端 `tests/api/test_tasks.py -k mock` 通过；WebUI `-k "mock"` **2/2**
（创建页勾选放行 + 详情 Mock 标识）；前端 `npm run build` 通过、i18n 键集一致。

**修复记录**：
- **18081 测试服务运行旧代码**：`test_tasks.py -k mock` 断言快照 `use_mock_env` 失败——
  snapshot 代码已改，但常驻测试服务进程仍是旧代码 → **重启测试服务**（kill + 以
  `BENCHSCOPE_FAKE_BENCH=1` 临时数据目录重启）后通过。教训：改完后端代码需重启
  18081 测试服务再验证，判断「改动是否生效」先比对进程启动时间与文件 mtime

**TODO 状态**：
- [x] 展示层 — snapshot 透出 `use_mock_env` + Perf 面板 Mock 标识 tag + i18n
- [x] 测试 — 后端快照断言 + WebUI 详情 Mock 标识用例

### 迭代 13（2026-08-29 23:30:00）：Provider 贯穿三项改造（创建任务 Base→Provider / Settings 去 Activate / 会话页 Provider 下拉 + 后端链路）

**变更内容**：

1. **创建任务 Base 面板改为 Provider 选择（1.0.7 用户需求①）**
   - BaseEnvPanel 重写：移除 Framework 单选，改为 **Provider 下拉**（来自 Settings → Providers 列表）
   - Base URL **不再手工固定**，自动取自所选 Provider；**默认选择第一个 Provider**
   - 切换 Provider → 联动刷新模型列表与在线状态（`POST /api/config/test-connection` 探测）
   - payload 新增 `provider_id` + `api`（该 Provider 的 base_url / endpoint / api_key / extra_headers 内联）
2. **Settings Providers 去 Activate（1.0.7 用户需求②）**
   - Provider 面板移除 **Activate 按钮与 Active 标签**（使用处自行选择 Provider，无需激活）
   - **状态与模型内嵌各 Provider 面板**：新增「模型状态」行（在线绿 / 离线红 badge）与「模型」行（可用模型 tags / 无模型提示）；新增/编辑/删除后自动重新探测
   - 后端 `POST /api/config/providers/{id}/activate` 路由保留（兼容旧客户端），前端不再调用
3. **会话页 Provider 下拉 + header 状态色（1.0.7 用户需求③）**
   - 输入栏模型下拉左侧新增 **Provider 下拉**（联动该 Provider 模型列表，localStorage `benchscope_chat_provider` 记忆，默认第一个）
   - chat-header 颜色标记所选模型状态：探测在线 → **绿色**（`.chat-ok` #52c41a）；默认/离线 → **红色**（`.chat-bad` #ff4d4f）
   - chat 请求体新增 `provider_id`；`session_manager.stream_chat` 按 Provider 解析 API 配置调用，会话持久化 `provider_id`
4. **后端链路**
   - `session_manager`：`Session.provider_id`（to_dict / 恢复）、`create_session(provider_id=)`、新增 `_provider_api_config()`（按 id 从 `config.list_providers()` 解析 base_url/endpoint/api_key/extra_headers）、`stream_chat` 缺省沿用会话已绑定的 provider_id，无则回退全局 `config.api`
   - `api_sessions.ChatRequest` 新增 `provider_id`
   - `task_manager._run_one`：`api = dict(task.payload.get("api") or self.config.api)`——**任务 payload.api（所选 Provider 配置）优先于全局 api**

**验证（增量）**：
- 后端新增 3 用例：`test_sessions.py` `test_chat_with_provider_id`（chat 带 provider_id 走对应 Provider 配置 + 会话持久化）、`test_chat_invalid_provider_uses_own_config`（指向不可达地址的 Provider 报错，证明配置真实生效而非回退全局 mock）、`test_tasks.py` `test_task_payload_api_overrides_global`（payload.api 的 base_url 进入命令而非全局 mock 地址）——均通过
- WebUI 新增 3 用例：`test_create_page_base_provider_select`、`test_settings_providers_no_activate_with_status`、`test_sessions_provider_select_header_color`——`-k "provider_select or no_activate or header_color"` **3/3** 通过
- `npm run build` 通过、i18n 键集一致、lint 无错误

**修复记录**：
- **`_provider_api_config` 遍历 dict**：`config.list_providers()` 返回 `{"providers": [...], "active_provider": "..."}`，原代码直接 `for p in providers` 会迭代字典键（字符串）触发 `AttributeError: 'str' object has no attribute 'get'` → 改为 `(list_providers() or {}).get("providers") or []`
- **`CreateTaskRequest` 缺 `api` 字段**：Pydantic `model_dump()` 白名单丢弃 payload.api（与迭代 4 的 `engine_id` 同坑），导致任务执行回退全局 api → 补 `api: dict = {}` 字段声明
- **测试断言格式**：vllm 原生命令 base-url 为 `--host X --port Y` 分写格式（非 `X:Y` 连写）→ 断言改为 `--port 9` / 不含 `--port 8001`
- **18081 测试服务旧代码**：重启测试服务（kill + `BENCHSCOPE_FAKE_BENCH=1` 临时数据目录）后再验证（沿用迭代 12 教训）

**TODO 状态**：
- [x] 创建任务 — Base 面板改 Provider 选择（默认第一个 + 联动模型/状态 + payload 携带 provider_id/api）
- [x] Settings — Providers 去 Activate（状态/模型内嵌各面板 + 自动探测）
- [x] 会话页 — Provider 下拉联动模型 + chat-header 颜色标记模型状态（默认红/在线绿）
- [x] 后端链路 — session.provider_id + _provider_api_config + stream_chat 按 Provider 调用 + task payload.api 优先
- [x] 测试 — 后端 3 用例（会话 Provider 链路 ×2 / 任务 payload.api 优先 ×1）+ WebUI 3 用例

### 迭代 14（2026-08-29 23:59:00）：Settings 面板化 + Skills/Debug 新栏 + Mock 迁移 Debug + 创建页双语（8 项用户需求）

**变更内容**：

1. **Settings/Models 面板化（需求①）**
   - 分类副导航紧贴右侧主导航（`.content-fill` 布局），内容多时内部滚动（`.fill-scroll`）
   - 模型 item 改为**面板**（`.model-panel-card`，`a-card size="small"`，宽度与 General 面板一致）：
     Header 左侧 = 模型名称、右侧 = **详情操作高亮链接**（`.mp-action`，蓝字，目录匹配时显示）；
     内容 = 简介（`intro.zh/en` 双语）+ **精度列表**（`.mp-tags`，BF16/FP8/W8A8/AWQ/GPTQ/INT4）+ **访问链接**（`.mp-link`）+ **下载命令**（`.mp-cmd` 可复制）；
     未命中目录显示「暂无目录信息」（`.mp-intro.muted`）；**详情抽屉已移除**
2. **Settings/Datasets 面板化（需求②）**：布局同 Models；数据集面板（`.ds-panel-card`）
   Header 左侧 = 名称 + 缓存状态 tag、右侧 = **下载按钮**（Header 内）；内容 = 描述 / 访问链接 / 下载命令（可复制）
3. **Settings/Bench Engines 面板化（需求③）**：卡片宽度统一为面板宽度（`.bench-list.narrow`）；
   Header **左右分栏**（`space-between`）：左侧 title = 引擎名称 + 标识（默认标记 + kind 标签），右侧 = **版本号**（`.bench-version`）
4. **Settings 侧边栏图标更新（需求④）**：General `Control` / Providers `CloudServer` / Models `Robot` /
   Datasets `Database` / Bench Engines `Experiment` / Skills `Book` / Plugins `Api` / Debug `Bug`
5. **Settings/Skills 新增（需求⑤）**
   - 后端 `benchscope/server/api_skills.py` 新建：`GET /api/skills` 扫描 `skills/*/SKILL.md` front-matter，
     返回 `name/version/description/features/usage/prompt/download({path,name})`；`app.py` include_router
   - 前端 `web/src/api/index.js::getSkills()`
   - 技能面板（`.skill-card`，与 Bench Engines 同款）：Header 左 = 名称 + id tag、右 = 版本号；
     内容 = 功能描述 / **功能特性** ul / **使用说明** ol / **提示词** `pre`（`max-height:220px` 滚动）；
     footer 两个**文字按钮**（`a-button type="link"`）：下载安装技能、复制提示词（成功/失败 toast）
6. **Performance/创建任务（需求⑥）**：Step1 Provider 默认选第一个（`providerId = providers[0].id`）；
   Step2 参数页中英双语（`bench-params.yaml` vllm/sglang 参数 label 补双语：信任远程代码 trust-remote-code、
   Top-P top-p、频率惩罚 Frequency Penalty、禁用流式 Disable Stream、预分词 Tokenize Prompt、刷新缓存 Flush Cache、
   打印请求 Print Requests、禁用进度条 Disable Progress、ShareGPT 输出长度 Output Len、ShareGPT 上下文长度 Context Len）
7. **Performance/默认页 Threshold Search 描述补全（需求⑦）**：i18n `featThresholdModeDesc` 中英补全
   逐步搜索机制（逐档提升并发快速压测 → 任一指标跌破阈值即停止 → 输出最后达标并发档位）
8. **Use Mock Environment 移至 Settings/Debug（需求⑧）**
   - `DEFAULT_CONFIG` 新增 `debug` 段：`{mocks_enabled, mocks_vllm_data, mocks_sglang_data, mock_vllm_env, mock_sglang_env}`
     （`benchscope/constants.py`）；`ConfigPatch` 增加 `debug`（`api_config.py`）
   - Settings Debug 栏（仅开发模式 `!isRelease` 显示，release 不显示）：`.debug-head-card`
     Header 左 = 开发模式 + Debug tag、右 = **一键总开关**（`debug.mocks_enabled`）；
     `.debug-config-card` 4 行开关（mocks vllm/sglang 数据 + mock vllm/sglang 环境），总开关关闭时禁用
   - `task_manager._run_one`：`config.debug.mocks_enabled` 按框架匹配 FAKE（vllm：`mocks_vllm_data|mock_vllm_env`；
     sglang：`mocks_sglang_data|mock_sglang_env`），或任务级 `payload.use_mock_env`
   - 创建页：Use Mock Environment 勾选**仅 Bench CLI（builtin）显示**（非 bench cli 原生引擎不显示）；
     原生引擎环境校验失败时以 `debug.mocks_enabled` 放行（`nextToParams`）；
     payload `use_mock_env` 修复反逻辑 BUG（`!== 'builtin'` → `=== 'builtin'`）
   - i18n 新增 Skills 键（skills/skillsDesc/skillFeatures/skillUsage/skillPrompt/skillDownload/
     skillCopyPrompt/skillCopySuccess/skillCopyFail/skillDownloaded/modelNoCatalog）与 Debug 键
     （debugMode/debugModeTag/debugHint/debugDevConfig/debugMasterSwitch/debugMocksVllmData[Desc]/
     debugMocksSglangData[Desc]/debugMockVllmEnv[Desc]/debugMockSglangEnv[Desc]）

**验证（增量）**：
- 后端：`tests/api/test_config.py` 新增 `test_debug_config_update`（debug 默认 5 键 + POST 更新持久化）与
  `test_skills_list`（≥3 技能，字段完整性 name/version/description/features≥2/usage≥2/prompt/download.path）——均通过
- WebUI：更新 `test_create_page_mock_env_option`（Bench CLI 显示勾选 / vllm 原生不显示）+ 新增
  `test_settings_models_panel` / `test_settings_datasets_panel` / `test_settings_skills_panel` /
  `test_settings_debug_panel` / `test_perf_landing_intro_cards`（Threshold 描述断言）——`-k` 6 用例全部通过
- `npm run build` 通过、i18n 键集一致、lint 无错误

**修复记录**：
- **`api_skills` 未 import 导致服务启动失败**：`app.py` include_router(api_skills.router) 前需
  `from benchscope.server import …, api_skills`（补 import 后重启服务恢复）
- **`PuzzlePieceOutlined` 构建失败**：图标 `PuzzlePieceOutlined` 在当前 antd 版本不可用 → 改回 `ApiOutlined`
- **Skills footer 不渲染**：ant-design-vue 4.2.6 的 `a-card` **无 `#footer` 插槽** → footer 按钮改放
  card body 内普通 `div.skill-footer`
- **mock-env-row 恒不显示（需求 8 关键 BUG）**：勾选行原被包在 `v-if="envResult && !envResult.ok"` 的环境
  校验明细块内，而 Bench CLI（builtin）**恒 ok=True** → 勾选永远不渲染；将 `.mock-env-row` 移出该块，
  仅以 `selectedEngine.kind === 'builtin'` 控制（WebUI 用例先行暴露后修复）
- **测试选择器校正**：Models 默认选中 Baidu(ERNIE-4.5) 不在前端 `modelCatalog.js` → 测试改选
  DeepSeek（DeepSeek-V3 命中目录）；Datasets 下载按钮无 `.ds-action` 包装类 → 改断言
  `.ant-card-head .ant-btn`

**TODO 状态**：
- [x] Settings — Models/Datasets/Bench Engines 面板化 + 侧边栏图标更新 + 内容内部滚动
- [x] Settings — Skills 新栏（/api/skills + 技能面板 + footer 下载/复制按钮）
- [x] Settings — Debug 新栏（一键总开关 + 4 行 mocks 开关，release 隐藏）
- [x] Mock 迁移 — 创建页勾选仅 Bench CLI 显示；原生引擎由 config.debug.mocks_enabled 放行；use_mock_env 反逻辑修复
- [x] 创建页 — Step1 Provider 默认第一个 + Step2 参数中英双语
- [x] 默认页 — Threshold Search 描述补全（逐步搜索机制）
- [x] 测试 — 后端 2 用例 + WebUI 6 用例（含 1 更新 5 新增）

### 迭代 15（2026-08-30）：技能命名规范（bs-模块-xxx）+ 技能重命名与 Settings/Skills 列表整理

**变更内容**：

1. **技能命名规范（强制）**
   - `skills/Readme.md` 新增 **§1.1 命名规范**、`docs/skills/Readme.md` 新增 **§2.1 命名规范**：
     - 技能名：`bs-<模块>-<目标>`（如 `bs-engine-create` · `bs-bench-vllm` · `bs-bench-sglang`）
     - 产物目录：`bs-<模块>-<目标>-<版本>-pkgs/`（如 `bs-engine-vllm-0.28-pkgs/`）
     - 产物包：`bs-<模块>-<目标>-<版本>.tar.gz`（如 `bs-engine-vllm-0.28.tar.gz`）
   - `bs-engine-create/SKILL.md` 新增 **§8 Naming convention**，并在 Workflow 步骤 3 与复制提示词中落地产物打包命名
2. **技能重命名（git mv 保留历史）**
   - `skills/bench-engine-authoring/` → `skills/bs-engine-create/`（模块 engine + 目标 create）
   - `skills/vllm-bench-testing/` → `skills/bs-bench-vllm/`（模块 bench + 目标 vllm）
   - `skills/sglang-bench-testing/` → `skills/bs-bench-sglang/`（模块 bench + 目标 sglang）
   - 三个 SKILL.md frontmatter `name` / 标题、README（目录树/打包产物/解压命令）、package.sh 注释全部同步
3. **Settings/Skills 列表整理**：`api_skills.py` `_SKILL_EXTRA` 键与展示名改为新规范名
   （`bs-engine-create` / `bs-bench-vllm` / `bs-bench-sglang`），列表自动扫描新目录名
4. **引用同步**：`tests/api/test_skills.py`（`EXPECTED_SKILLS` 三技能名 + 目录/脚本/文档断言 + 新增
   `bs-` 前缀命名断言）、`docs/skills/BenchEngineAuthoring.md` / `BenchTesting.md`、
   `docs/rules/BenchUpstream.md` / `BenchEngine.md` 全部引用更新

**验证（增量）**：
- 后端：`pytest tests/api/test_skills.py` 全量通过（含 bs- 前缀断言）
- WebUI：`-k skills` 用例通过（Settings Skills 面板显示新技能名）
- lint 无错误

**TODO 状态**：
- [x] 技能命名规范 — `bs-<模块>-<目标>`（技能）+ `bs-<模块>-<目标>-<版本>.tar.gz`（产物）+ 规范文档落地
- [x] 技能重命名 — 三技能目录 / SKILL.md frontmatter / README / package.sh（git mv 保留历史）
- [x] Settings 列表 — api_skills 元数据与展示名同步新规范名
- [x] 引用与测试 — test_skills.py / docs/skills / docs/rules 全量同步

### 迭代 16（2026-08-30）：创建页 Use Mock 移除 + Step2 参数双语补齐 + 默认页描述完整展示（需求 3/4/5 修正）

**变更内容**：

1. **创建页移除 Use Mock Environment 勾选（需求 5 修正）**
   - `PerfCreateView.vue`：删除 `.mock-env-row` 勾选行（原 `v-if="selectedEngine?.kind === 'builtin'"` 选择 Bench CLI 时反而显示，与需求相反）；
     - 删除 `useMockEnv` ref 与 payload 中 `use_mock_env` 字段（创建页不再携带）、清理 `.mock-env-row` CSS
   - mock 完全移至 Settings → Debug（`config.debug.mocks_enabled` 一键总开关）；任务级 `use_mock_env` 字段保留（API/工具直传仍生效）
   - `web/src/i18n/zh.js` / `en.js`：清理无引用的 `useMockEnv` / `useMockEnvHint` 键
2. **Step2 参数 label 双语全量补齐（需求 3 修正）**
   - `bench-params.yaml` 剩余纯中文 label 补齐中英双语：
     - benchscope：`字符 / Token 比 Chars/Token`、`单请求超时（秒） Timeout (s)`
     - vllm：`禁用进度条 Disable Progress`
     - sglang：`应用聊天模板 Apply Chat Template`、`不忽略 EOS Don't Ignore EOS`
   - Step1 Provider 默认第一个（迭代 14 已实现，本轮复核无改动）
3. **默认页描述完整展示（需求 4 根因修复）**
   - `PerformanceView.vue`：`.feature-card .ant-card-meta-description` 移除 `-webkit-line-clamp: 2` 截断——
     Threshold Search 等长描述此前被 CSS 截断为 2 行显示不全（i18n 文本迭代 14 已补全，根因在截断样式）
4. **测试**
   - `tests/webui/test_ui.py`：重写 `test_create_page_mock_env_option` —— 断言创建页**任何引擎**（含 Bench CLI / vLLM）均**不显示** Use Mock Environment 勾选
   - `test_mock_env_tag_in_task_detail`（API 直传 `use_mock_env`）与 `test_create_page_base_provider_select`（Provider 默认第一个）不受影响，继续有效

**验证（增量）**：
- WebUI：`-k "mock_env or create_page or landing"` 用例通过
- 后端：`pytest tests/api/test_benchs.py tests/api/test_config.py` 通过（参数 schema / debug 开关不受影响）
- lint 无错误

**TODO 状态**：
- [x] 创建页 — Use Mock Environment 勾选移除（bench cli 与原生引擎均不显示），mock 完全由 Settings → Debug 控制
- [x] 参数页 — bench-params.yaml 剩余纯中文 label 全量补齐中英双语
- [x] 默认页 — 描述取消 2 行截断，Threshold Search 机制说明完整展示
- [x] 测试与文档 — WebUI 断言重写 + Performance-Create / Performance / VERSION 同步

### 迭代 17（2026-08-30）：创建页阈值 Max Requests 描述换行 + Step2 参数 help/description 双语 + Settings 三栏布局优化（4 项需求）

**变更内容**：

1. **创建页阈值模式 Max Requests 描述单独一行（需求 1）**
   - `PerfCreateView.vue`：`maxreq-row` 内描述从 `<span class="cond-hint">` 同行内联拆分为 `maxreq-line`（label + 输入框同行）+ `maxreq-hint`（描述独立一行）
   - CSS：`.maxreq-hint` 为块级元素、`font-size: 11px`、浅色（`--ant-color-text-tertiary`），不再与输入框同行
2. **Step2 参数 help/description 全量双语（需求 2）**
   - `bench-params.yaml`：全部 `help` 与选项 `description` 补齐「中文 English」双语（benchscope 21 处 / vllm 30 处 / sglang 20 处），与 label 双语风格一致，前端 `.param-desc` 直接展示
3. **Settings/Bench Engines 布局（需求 3）**
   - `SettingsView.vue`：`.bench-tab` 移除 `narrow`——顶部操作栏（标题 + 3 个文字按钮）宽度与右侧页面一致
   - `.bench-list` 增加 `max-width: 720px; margin: 0 auto`——引擎卡片居中为面板宽度，列表滚动条保持在页面最右侧
4. **Settings/Models 与 Datasets 布局（需求 4）**
   - 移除左侧分类副侧边栏（`.catalog-sidebar` / `.catalog-item` / `.catalog-group`），分类信息（Datasets 分类 / Models 厂商分组）上移到内容区顶部 `.cat-bar`（chip 样式，可点击筛选）
   - 卡片改为三分区（`.card-body` + `.card-footer`）：Header = 标题 + 操作（下载按钮 / Details 链接）；内容 = 描述 / 访问链接 / 精度；footer = 下载命令（浅底色 + 上边框）
   - 卡片宽度 = 面板宽度（窄面板 720px），面板列表内部滚动
   - 清理 `collapsedGroups` / `toggleGroup` / `isCollapsed` 未用代码（Models 分组折叠已移除）
5. **测试**
   - `tests/webui/test_ui.py`：`test_settings_models_panel` / `test_settings_datasets_panel` 改用 `.cat-chip` 选择器 + 新增顶部分类 chip 断言 + `.card-body` / `.card-footer` 三分区断言
   - `test_perf_create_params_follow_engine` 新增参数描述中英双语断言（`.param-desc` 同时含中英文字符）

**验证（增量）**：
- WebUI：`-k "settings_benches or settings_models or settings_datasets or perf_create or create_page"` 用例全部通过
- 后端：bench-params.yaml 重新解析正常，三引擎 help/description 均含英文
- lint 无错误

**TODO 状态**：
- [x] 创建页 — 阈值模式 Max Requests 描述独立一行（小字浅色）
- [x] 参数页 — bench-params.yaml help/description 全量中英双语
- [x] Settings — Bench Engines 顶栏全宽 / 卡片面板宽 / 滚动条最右
- [x] Settings — Models/Datasets 分类移至顶部 + 卡片三分区（header/内容/footer）
- [x] 测试与文档 — WebUI 断言同步 + Settings / Performance-Create / VERSION 更新

### 迭代 18（2026-08-30）：Settings 布局细化（分类/面板宽度）+ Bench 面板化 + Max Requests 面板化（4 项需求）

**变更内容**：

1. **Settings/Models 与 Datasets 分类面板全宽（需求 1/2）**
   - `SettingsView.vue`：Models / Datasets 的 `tab-content` 移除 `narrow` 约束——顶部**分类面板（`.cat-bar`）宽度与右侧页面宽度一致**（不再受 720px 窄栏限制）
   - 下方内容列表位置不变：`.panel-list` 内卡片（`.ds-panel-card` / `.model-panel-card`）及 `provider-head` / `a-empty` 设 `width: 100%; max-width: 720px` 居中（`.panel-list` 改用 `align-items: center`）
   - 滚动条在页面最右侧：`.panel-list` 为全宽滚动容器，内部卡片居中 720px
2. **Settings/Bench Engines 内容改面板（需求 3）**
   - `.bench-card` 由普通 div 改为面板化：`.bench-head`（header：引擎名/标识/版本）+ body（描述/亮点）+ **`.bench-foot`（footer：环境要求与校验结果，浅底色 + 上边框）**
   - `.bench-list` 改为 `margin: 0 0 20px auto`（**靠右，非居中**），宽度与 Settings 面板一致（`max-width: 720px`）；滚动条保持在页面最右侧
   - 移除 `.bench-env` / `.bench-env-none` 原有内嵌虚线边框（并入 footer 分区）
3. **PerfCreate 阈值模式 Max Requests 面板化（需求 4）**
   - `PerfCreateView.vue`：`.maxreq-row` → `.maxreq-panel`，改为**面板形式**（边框 + 圆角 + padding + 白底，与 Step1 引擎选择 `bench-picker` 样式一致）；描述 `maxreq-hint` 保持在面板内输入框下一行
4. **测试**
   - `tests/webui/test_ui.py`：`test_create_page_conditions_no_rate_and_max_requests` 中 Max Requests 选择器 `.maxreq-row input` → `.maxreq-panel input`

**验证（增量）**：
- WebUI：`-k "settings or perf_create or create_page or max_requests"` 用例全部通过（24 项）
- lint 无错误

**TODO 状态**：
- [x] Settings — Models/Datasets 分类面板全宽，内容列表位置不变，滚动条最右
- [x] Settings — Bench Engines 列表改面板（header + footer），靠右、宽度与设置一致、滚动条最右
- [x] 创建页 — 阈值模式 Max Requests 面板化（类似 Test Engine 样式）
- [x] 测试与文档 — WebUI 断言同步 + Settings / Performance-Create / VERSION 更新

### 迭代 19（2026-08-30）：Settings 内容靠左 + 参数配置按语言切换（默认英文 / 切换中文显示中文）（2 项需求）

**变更内容**：

1. **Settings/Models、Datasets、Bench Engines 内容靠左（需求 1）**
   - `SettingsView.vue`：
     - `.panel-list`（Models / Datasets）由 `align-items: center` 改为 `align-items: flex-start`——内容（面板卡片 / provider-head / a-empty）**靠左显示**（仍 720px 面板宽），滚动条在 `.panel-list`（全宽容器）最右侧
     - `.bench-list`（Bench Engines）由 `margin: 0 0 20px auto`（靠右）改为 `margin: 0 auto 20px 0`（**靠左**），滚动条保持在页面最右侧
2. **参数配置按语言切换（需求 2）**
   - `bench-params.yaml`：每个 `label`/`help`/`description` 拆为**英文（`label`/`help`/`description`，默认语言）+ 中文（`label_zh`/`help_zh`/`description_zh`）**，不再是「中文 English」混合字符串
   - `ParamGroupPanel.vue`：引入 `i18nState.locale`（默认 `en`），`pick()` 按当前语言选择 `_zh` 或英文字段——**默认显示英文，切换中文后显示中文**（label / 下拉选项 / 描述均随语言切换）
   - `i18n/index.js`：暴露全局 `window.__switchLocale`（测试/调试辅助，不参与生产逻辑）
   - 后端 `option-desc` 接口仍返回英文 `description`（默认语言），兼容既有 API 测试
3. **测试**
   - `tests/webui/test_ui.py`：`test_perf_create_params_follow_engine` 重写——默认语言断言参数 label 与描述**不含中文**（纯英文），调用 `__switchLocale('zh')` 后断言**含中文**，末尾恢复英文避免影响依赖默认英文的用例

**验证（增量）**：
- WebUI：`-k "settings or perf_create or create_page or params_follow"` 用例全部通过（24 项）
- 后端：bench-params.yaml 解析正常，全部 label/help/description 均含 `_zh` 与英文字段；`get_option_description` 返回英文（含 "completions"）兼容
- lint 无错误

**TODO 状态**：
- [x] Settings — Models/Datasets/Bench Engines 内容靠左显示，滚动条在页面最右侧
- [x] 参数配置 — 默认英文，切换中文显示中文（label/help/options 随语言切换）
- [x] 测试与文档 — WebUI 断言重写 + VERSION / Settings / Performance-Create 同步

### 迭代 20（2026-08-30）：移除 Settings/Debug，mock 跟 engine 走（每引擎 Mock 开关）+ bs-perfs 技能 + 技能下载端点

**变更内容**：

1. **移除 Settings/Debug，mock 环境和数据跟 engine 走（核心）**
   - 删除 Settings/Debug 面板（模板 / 菜单 / script / CSS / i18n / `isRelease` / `versionInfo` / `ConfigPatch.debug`）
   - 新增 `config.engine_mocks`（`{engine_id: bool}`，`constants.py::DEFAULT_CONFIG`），按引擎记忆 mock 状态
   - `task_manager._run_one`：`runner.fake = payload.use_mock_env OR config.engine_mocks[engine_id]`（按 engine_id 判定，动态注册的自定义引擎同样支持）
   - `api_benchs.py`：`POST /api/benchs/{engine_id}/mock` 切换开关（整体 `set` 支持移除 key）；
     `list_bench_engines` / `env-check` 注入 `mock` / `mock_state`（mock 开启时环境校验直接通过）
   - 前端 Bench Engines 卡片 footer 加 **Mock 开关**（`.bench-mock`，默认关）；Header 与创建页 Step1 显示 **Mock / Real** 状态 tag
   - 创建任务选择引擎时 `/env-check` 联动：mock 引擎显示 Mock + 环境通过（放行 Step2）
2. **bs-perfs-concurrency / bs-perfs-threshold 新技能**
   - 删除 `bs-bench-vllm` / `bs-bench-sglang`（用户要求移除）
   - 新增 `bs-perfs-concurrency`（`benchscope perf` 并发压测）与 `bs-perfs-threshold`（`--mode threshold` 阈值搜索），均含 SKILL.md / README / templates 内置表单 / package.sh，产物为可导入 Datas/perfs 的 zip
   - `benchscope perf` CLI 增加 `--mode`（concurrency/threshold）+ 阈值参数，threshold 走 2 幂递增 + 二分找 best_concurrency；`_save_perf_artifacts` 落盘 run.json + 日志占位
3. **技能版本约定 + 下载端点（约定 4）**
   - 约定：技能有版本，每次更新自动递增；更新多建议加大版本号；每次发版到本地 `dist/`；服务启动可下载技能包
   - `GET /api/skills/{id}/download` 返回 tar.gz（优先 `dist/` 产物，未发版实时打包）；技能列表注入 `download_url` / `package`
   - 前端 Skills 面板下载优先走版本包（回退 SKILL.md）
4. **bs-engine-create 增强**
   - 补「Mock 数据动态注册」章节（每引擎独立 Mock 开关，开启即 FAKE 仿真验证）+ self-check；版本 1.1.0 → 1.2.0
5. **测试**
   - `test_skills.py`：`EXPECTED_SKILLS` 改为新 3 技能；新增 `test_skill_download_endpoint`；`test_bench_testing_doc` 改断言新技能
   - `test_benchs.py`：新增 `test_engine_mock_switch`；`test_config.py`：`test_debug_config_update` → `test_engine_mocks_config_update`
   - `test_tasks.py`：新增 `test_native_engine_engine_mocks_config`（engine_mocks 触发 FAKE）
   - WebUI：移除 `test_settings_debug_panel` → `test_settings_benches_mock_switch`；创建页环境校验 wait 适配 Mock/Real tag

**验证（增量）**：
- API：test_benchs / test_config / test_skills / test_tasks 相关用例通过
- WebUI：`-k "settings or create_page or params_follow or max_requests"` 21 项通过
- CLI threshold / concurrency 模式在 FAKE+mock 下运行正常（输出 best_concurrency）
- lint 无错误

**TODO 状态**：
- [x] 后端 — config.engine_mocks 映射 + task_manager 按 engine_id 判定 mock
- [x] 后端 — env-check/engine 列表注入 mock/real 状态 + mock 开关 API
- [x] 前端 — 移除 Settings/Debug 面板
- [x] 前端 — Bench Engines 每引擎 Mock 开关（默认关）+ 刷新环境状态标记 mock/real
- [x] 前端 — 创建任务按所选 engine 联动 mock
- [x] 技能 — bs-perfs-concurrency / bs-perfs-threshold 新技能 + bs-engine-create mock 动态注册 + 版本约定 + 下载端点
- [x] 测试与文档 — 断言同步 + Settings / Performance-Create / VERSION / skills 文档更新

### 迭代 21（2026-08-30）：Skills 页可滚动 + perfs 记录 framework 标记（2 项需求）

**变更内容**：

1. **Settings/Skills 页面可滚动（需求 1）**
   - `SettingsView.vue`：Skills `tab-content` 移除 `narrow`，`.skill-list` 改为**全宽滚动容器**（`flex:1 + overflow-y:auto`，滚动条在页面最右侧）；技能卡片**靠左**显示（`align-items:flex-start`，`max-width:720px`）
   - **滚动生效修复**：`.settings-content.content-fill > .tab-content` 补充 `display:flex; flex-direction:column`——原先 `.tab-content` 非 flex 容器导致内部 `.fill-spin` 的 `flex:1` 失效、`.skill-list` 高度被内容撑开（无法滚动）；补 flex 后高度链打通，`.skill-list` 正确限高滚动
   - 每个技能卡片 footer 文字按钮**仅 Download 与 Copy Prompt**（断言收紧为 ==2，且包含 Download/Copy）；按钮文案**随语言切换**（en：Download/Copy Prompt；zh：下载技能/复制提示词）
   - **卡片 header 无高亮**：`.skill-card :deep(.ant-card-head)` 加 `background:transparent`
   - **提示词优化**：`_SKILL_EXTRA` 为每个技能提供**精简操作提示词**（`prompt`），引导用户输入框架/版本/阈值等参数（如 bs-engine-create：询问框架及版本 → 生成 bench engine 压缩包），`_collect_skills` 优先用 `extra.prompt`，回退 SKILL.md 全文
   - **技能内容双语（1.0.7）**：`_collect_skills` 返回 `description_zh` / `features_zh` / `usage_zh` / `prompt_zh`（`_SKILL_EXTRA` 提供中英双语），前端 Skills 面板按 `locale` 选择 `_zh` 或英文——描述、功能特性、使用说明、提示词**均随语言切换**
   - `_USAGE` 优化：第一项改为「下载技能：下载技能包（.tar.gz），导入其他支持 skills 的 agents 平台即可使用」
2. **Datas/perfs 左侧记录 framework 标记（需求 2）**
   - `DatasPerfsView.vue`：每个记录项在任务 ID 右侧增加 **framework 高亮标记**（`.record-framework`，蓝色小字 `font-size:9px` + 浅蓝底），数据来自 `listRuns` 的 `meta.framework`（run.json 的 `framework_name`）
   - `record-head` 改 `justify-content:flex-start`（ID+framework 靠左紧挨），status 用 `margin-left:auto` 推右
3. **测试**
   - `test_settings_benches_mock_switch`：改为先 API 关闭首个引擎 mock + `try/finally` 恢复，避免跨测试 config 持久化污染
   - `test_datas_perfs_record_list`：新增记录存在时断言 `.record-framework` 存在

**验证（增量）**：
- WebUI：`-k "settings or datas"` 19 项全部通过；Skills 可滚动 + perfs framework 标记生效
- lint 无错误

**TODO 状态**：
- [x] Settings — Skills 页面可滚动（滚动条最右，卡片位置不变）+ 优化 Usage + footer 仅 Download/Copy Prompt
- [x] Datas/perfs — 每条记录在任务 ID 右侧显示 framework 高亮标记（小字）
- [x] 测试与文档 — 断言同步 + VERSION / Settings / Datas 文档更新

### 迭代 22（2026-08-30）：发布规则按版本号区分（补丁不推 PyPI，主/次推送全量）

**变更内容**：

1. **发布规则（`scripts/release.sh`）**：
   - 新增 `NEED_PYPI` 判定：取新旧版本号的 **X.Y 前两段**（用 `awk -F.` 稳定提取，兼容 `dev` 后缀如 `1.0.7.dev0`）比较
   - **仅 Z（补丁）更新**（X.Y 相同，如 `1.0.7 → 1.0.8`）：**不推送 PyPI**，仍构建产物（本地产出 `dist/`）+ `git tag vX.Y.Z` + GitHub Release；完成输出提示"补丁版本已跳过 PyPI"
   - **X.Y（主/次）更新**（如 `1.0.8 → 1.1.0`、`1.1.0 → 2.0.0`）：完整发布 = **PyPI 上传 + GitHub tag + Release**
   - PyPI 上传（含重试加固）整体包在 `if [ "$NEED_PYPI" -eq 1 ]` 内；脚本头部用法注释同步更新
2. **Release 说明仍总结版本更新功能清单**：GitHub Release 说明（无论是否推 PyPI）都从 `VERSION_x_y_z.md` 提取**迭代标题 + 该迭代「变更内容」的一级功能项**（截断验证/TODO 块、排除缩进子项），生成简洁的「版本更新功能清单」；补丁版本也照常推送带功能清单的 Release
3. **文档**：`docs/rules/Development.md` §5 发布规则更新（补丁只推 tag+release；主/次推 PyPI+tag+release）

**验证**：
- `bash -n scripts/release.sh` 语法通过
- 判定逻辑用例验证：`1.0.7.dev0→1.0.7`（skip）· `1.0.7→1.0.8`（skip）· `1.0.8→1.1.0`（push）· `1.1.0→2.0.0`（push）全部正确
- 功能清单提取：`VERSION_1_0_7.md` 生成 67 条功能项（迭代标题 + 一级变更），无验证/TODO 混入

**TODO 状态**：
- [x] 发布规则 — Z（补丁）更新不推 PyPI，只推 GitHub tag + release
- [x] 发布规则 — X.Y（主/次）更新推送 PyPI + GitHub tag + release
- [x] 测试与文档 — 判定用例验证 + Development.md §5 / VERSION 同步

## 4. TODO 清单

- [x] **版本初始化**：VERSION_1_0_7.md + 版本号 `1.0.7.dev0` + Roadmap/Readme 同步 + 开发模式启动（2026-08-28 完成）
- [x] **核心引擎改造规划**：架构方案 `docs/rules/BenchEngine.md`（引擎抽象 / 版本化 / 环境校验 / 参数描述 / 自研 bench 核心）（2026-08-28 完成，待确认后实施）
- [x] **P1 引擎抽象**：configs/benchs.yaml（3 内置引擎 + 对比表）+ benchs.py 注册表 + /api/benchs* + Settings Bench 栏 + 创建页引擎选择（2026-08-28 完成）
- [x] **P2 环境校验**：torch/vllm/sglang 版本范围校验（_match_spec）+ CLI 探测 + 前端阻断「下一步」（2026-08-28 完成）
- [x] **P3 参数体系**：configs/bench-params.yaml（37 项参数描述 + 选项级描述）+ /api/benchs/*/params + 前端下拉描述面板（2026-08-28 完成）
- [x] **P4 自研引擎**：LoadGenerator / Requester / MetricsCollector + task_manager 集成（2026-08-28 完成）
- [x] **P5 Settings Bench 栏**：内置引擎列表 + 介绍 + 对比表 + 环境状态 + benchs.yaml 查看/编辑（2026-08-28 完成）
- [x] **P6 测试与文档**：tests/api 92 + tests/webui 20 + Architecture.md / Software.md / BenchCore.md 同步（2026-08-29 完成）
- [x] **Skills 体系**：skills 项目规范（结构/frontmatter/打包）+ `bench-engine-authoring` 自定义引擎技能（mock 核心方法 + 上游链接 + 提示词）+ 已有 vllm/sglang skills 规范化至 v1.1.0（2026-08-29 完成）
- [x] **导入校验**：7 项校验（yaml/engines/id/kind/requires/params_key/option_desc/mock）+ `POST /api/benchs/import`（dry_run 预校验 / apply 写入）+ Settings「添加自定义版本」面板（提示词复制 + GitHub 链接 + 校验后导入）（2026-08-29 完成）
- [x] **上游源码分析**：拉取 vLLM v0.23.0 / SGLang v0.5.10 源码分析 bench 核心逻辑（时间线 / 指标公式 / 并发速率 / token 计数），存档 `docs/rules/BenchUpstream.md` + 技能 `references/upstream-analysis.md`（2026-08-29 完成）
- [x] **自定义引擎实现方法**：明确「复制上游代码 + 适配入口/处理/出口/mock 四段契约」并写入技能与文档（2026-08-29 完成）
- [x] **Skills 文档归口**：新增 `docs/skills/`（Readme 规范 / BenchEngineAuthoring / BenchTesting）+ `skills/Readme.md` 精简为指针 + docs 索引同步（2026-08-29 完成）
- [x] **测试修复**：`tests/api/test_skills.py` 首行多余字符导致的语法错误（连带 WebUI 级联失败）修复 + 全量回归通过（2026-08-29 完成）
- [x] **创建任务引擎联动**：Step2 取消双框架 Tab 改为单参数面板（参数随引擎）+ Step3 命令预览随引擎分支 + 新增 `benchscope perf` 子命令（预览命令可直接执行）（2026-08-29 完成）
- [x] **引擎参数清单**：`configs/{params_key}-default.yaml`（取值）+ `bench-params.yaml`（说明）一一对应；新增 `GET/PUT /api/benchs/{id}/params-yaml`；Bench CLI 9 项参数（2026-08-29 完成）
- [x] **自研引擎命名统一**：「BenchScope Bench（自研）」→ **Bench CLI**（配置 / 界面 / 对比表 / 文档同步）（2026-08-29 完成）
- [x] **Settings/Bench Engines 重构**：整页可滑动引擎列表 + 右上角 Create Engine / Upload Engine / Engine Comparison 文字按钮（均为中间弹框）；移除内联的 Engine Definition 与对比表（2026-08-29 完成）
- [x] **引擎包上传**：`POST /api/benchs/upload` 支持 `.yaml` / `.tar.gz` 技能包，按 id 合并、校验通过才写盘、防路径穿越（2026-08-29 完成）
- [x] **中英文 i18n**：新增 26 组键（三个弹窗、教程步骤、参数联动提示等），zh/en 键集合一致（2026-08-29 完成）
- [x] **命令统一 `benchscope perf`**：CLI 子命令 `bench` → `perf`，预览命令、任务命令记录与日志回显同步（2026-08-29 完成）
- [x] **Environment 精简**：移除 Framework 单选，仅保留 Base URL + API Key；`framework` 改由所选引擎决定（2026-08-29 完成）
- [x] **布局规范**：Bench Engines 列表可滚动（修复 a-spin 高度约束）、全页面底部 18px、弹框 1/3 浏览器宽度 + header 提示 + footer 文字按钮（2026-08-29 完成）
- [x] **Bench Engines 全英文**：引擎文案双语（英文默认 + `*_zh`），Highlights 精简为「简洁特性 + 版本支持」（2026-08-29 完成）
- [x] **修复：Step3 旧命令 / 列表滚动 / 弹框宽度**：dev 服务重启显示 `benchscope perf`；`:deep()` 修复 a-spin 高度约束；弹框规则 `:global()` 化后宽度真正生效（1/3 → 1/2）（2026-08-29 完成）
- [x] **测试约定**：改为增量/变更测试（不做全量）；conftest mock 指向改 session 级 autouse，单跑 WebUI 环境自备（2026-08-29 完成）
- [x] **mocks 环境联调**：原生引擎环境不满足时勾选 Use Mock Environment 即可测试（FAKE 模式）（2026-08-29 完成）
- [x] **Providers 多提供方**：Environment 改名 Providers，支持多个 Provider（Name 必填 + Add 弹窗 + 激活同步 api + 旧配置迁移）（2026-08-29 完成）
- [x] **阈值 Max Requests**：默认 4096，下一次执行请求数超限 → 强制结束标记 Finish；Conditions 移除 Request Rate（2026-08-29 完成）
- [x] **引擎包提示词**：Create Engine 提示词改为产出 tar.gz 压缩包，导入上传压缩包（2026-08-29 完成）
- [x] **use_mock_env 贯穿展示层**：任务快照透出 `use_mock_env` + Perf 面板 Mock 标识 tag + i18n + 后端/WebUI 测试（2026-08-29 完成）
- [x] **创建任务 Base→Provider**：Base 面板改 Provider 选择（默认第一个 + 联动模型/在线状态 + payload 携带 provider_id/api，任务执行 payload.api 优先）（2026-08-29 完成）
- [x] **Settings 去 Activate**：Providers 移除 Activate 按钮与 Active 标签，状态/模型内嵌各 Provider 面板（自动探测）（2026-08-29 完成）
- [x] **会话页 Provider**：输入栏 Provider 下拉联动模型 + chat 请求携带 provider_id + header 颜色标记模型状态（默认红/在线绿）（2026-08-29 完成）
- [x] **后端 Provider 链路**：`session_manager` 按 provider_id 解析 API 配置 + 会话持久化 + `task_manager` payload.api 优先 + 修复 `_provider_api_config` 遍历 dict 与 `CreateTaskRequest` 缺 api 字段（2026-08-29 完成）
- [x] **Settings 面板化**：Models/Datasets/Bench Engines 三栏面板化（Header 左名称/右操作或版本）+ 分类副导航贴右 + 内容内部滚动 + 侧边栏图标更新（Control/CloudServer/Robot/Database/Experiment/Book/Api/Bug）（2026-08-29 完成）
- [x] **Settings Skills 栏**：`GET /api/skills`（api_skills.py）+ 技能面板（名称+id tag / 版本号 / 描述 / 特性 ul / 使用说明 ol / 提示词滚动）/ footer 下载与复制提示词文字按钮（2026-08-29 完成）
- [x] **Mock 迁移 Settings/Debug**：config.debug 段（mocks_enabled + 4 开关）+ Debug 栏一键总开关 + 4 行开关（总开关关闭禁用）+ release 隐藏 + 创建页非 bench cli 不显示勾选 + `_run_one` 按框架匹配 FAKE + use_mock_env 反逻辑修复（2026-08-29 完成）
- [x] **创建页双语与默认**：Step1 Provider 默认选第一个 + Step2 参数 label 中英双语（bench-params.yaml 10 项）+ 默认页 Threshold Search 描述补全（逐步搜索机制）（2026-08-29 完成）
- [x] **后端测试**：`test_config.py` 新增 `test_debug_config_update` + `test_skills_list`（2026-08-29 完成）
- [x] **WebUI 测试**：更新 `test_create_page_mock_env_option` + 新增 `test_settings_models_panel` / `test_settings_datasets_panel` / `test_settings_skills_panel` / `test_settings_debug_panel` / `test_perf_landing_intro_cards`（Threshold 描述断言）（2026-08-29 完成）
- [x] **技能命名规范与整理**：技能统一 `bs-<模块>-<目标>` 命名（bs-engine-create / bs-bench-vllm / bs-bench-sglang），产物 `bs-<模块>-<目标>-<版本>.tar.gz`（如 bs-engine-vllm-0.28.tar.gz）；git mv 重命名 + SKILL.md/README/package.sh 同步 + api_skills 展示名 + 测试与文档引用全量更新（2026-08-30 完成）
- [x] **创建页阈值 Max Requests 描述换行 + 参数描述双语 + Settings 三栏布局**：Max Requests 描述独立一行（小字浅色）；bench-params.yaml help/description 全量中英双语；Bench Engines 顶栏全宽 + 卡片面板宽 + 滚动条最右；Models/Datasets 分类移至顶部 + 卡片 header/内容/footer 三分区（2026-08-30 完成）
- [x] **Settings 布局细化 + Bench 面板化 + Max Requests 面板化**：Models/Datasets 分类面板全宽（内容列表位置不变、滚动条最右）；Bench Engines 改面板（header + footer、靠右、宽度与设置一致）；创建页阈值 Max Requests 面板化（2026-08-30 完成）
- [x] **Settings 内容靠左 + 参数配置按语言切换**：Models/Datasets/Bench Engines 内容靠左显示、滚动条最右；bench-params.yaml 拆英文+`_zh` 双语文案，创建页参数默认英文、切换中文显示中文（2026-08-30 完成）
- [x] **移除 Debug + mock 跟 engine 走 + bs-perfs 技能 + 技能下载端点**：删除 Settings/Debug，mock 环境与数据随引擎（每引擎 Mock 开关，`config.engine_mocks`）；移除 bs-bench-vllm/sglang，新增 bs-perfs-concurrency/threshold 技能 + CLI `--mode threshold`；技能版本约定 + `GET /api/skills/{id}/download` 下载版本包（2026-08-30 完成）
- [x] **Skills 页可滚动 + perfs 记录 framework 标记**：Skills 全宽滚动（滚动条最右、卡片位置不变）+ 优化 Usage（下载技能包导入 agents 平台）+ footer 仅 Download/Copy Prompt；Datas/perfs 每条记录任务 ID 右侧显示 framework 高亮标记（小字）（2026-08-30 完成）
- [x] **发布规则按版本号区分**：`release.sh` 新增 `NEED_PYPI` 判定（X.Y 前两段比较）——补丁（仅 Z）更新不推 PyPI、只推 GitHub tag + release；主/次（X.Y）更新推送 PyPI + tag + release（2026-08-30 完成）

---

## 版本功能清单（Release Notes）

### Feature Highlights

- **Create task: bilingual parameters that switch with UI language** (English by default, switch to Chinese via UI language; label / help / options / description all have `_zh` bilingual)
- **Threshold-mode Max Requests as a panel** (independent small-light description + panel style consistent with engine selector)
- **Settings layout rework: full-width left-aligned + right-side scrollbar** (Models / Datasets / Bench Engines / Skills left-aligned, scrollbar on the far right)
- **Remove Settings/Debug; mock env & data follow the engine** (per-engine Mock switch, default off; `config.engine_mocks` per engine_id, also supports dynamically-registered engines)
- **Skills: bs-perfs-concurrency & bs-perfs-threshold** (`benchscope perf` concurrency + `--mode threshold` search, built-in form, produces zip importable in Datas/perfs; removed bs-bench-vllm/sglang)
- **Skill versioning + version-package download** (skills are versioned, auto-increment on update, release to local; `GET /api/skills/{id}/download` downloads the package)
- **Skills page scrollable + one-skill-one-doc** (scrollbar on far right, cards left-aligned; each skill has its own `<BsXxxYyy>.md` in docs/skills, content & buttons switch with language)
- **Perfs records show framework badge** (each record shows a small blue framework badge right of the task ID)

### 功能清单

- **创建任务：参数中英双语随语言切换**（默认英文，切换中文显示中文；label / help / options / 描述全量 `_zh` 双语）
- **阈值模式 Max Requests 面板化**（独立小字浅色描述 + 面板形式，与引擎选择一致）
- **Settings 布局重构（全宽靠左 + 滚动条最右）**（Models / Datasets / Bench Engines / Skills 内容靠左，滚动条在页面最右侧）
- **移除 Settings/Debug，mock 环境与数据跟随引擎**（每个引擎独立 Mock 开关，默认关闭；`config.engine_mocks` 按 engine_id 判定，动态注册引擎同样支持）
- **技能体系：bs-perfs 并发/阈值压测技能**（`benchscope perf` 并发压测 + `--mode threshold` 阈值搜索，内置表单，生成可导入 Datas/perfs 的 zip；移除 bs-bench-vllm/sglang）
- **技能版本约定 + 版本包下载**（技能有版本、更新自动递增、发版本包到本地；`GET /api/skills/{id}/download` 服务可下载）
- **Skills 页可滚动 + 一个技能一个说明文档**（滚动条最右、卡片靠左；docs/skills 每技能独立 `<BsXxxYyy>.md` 说明，内容与按钮随语言切换）
- **Datas/perfs 记录 framework 标记**（每条记录任务 ID 右侧显示蓝色小字 framework 标记）

## 5. 相关文档

- 版本路线：[docs/Roadmap.md](../Roadmap.md)
- 上一版本：[VERSION_1_0_6.md](./VERSION_1_0_6.md)
- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Datas / Accuracy / Sessions / Settings / TopBar）
