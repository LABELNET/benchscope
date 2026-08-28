# VERSION 1.0.7 — 版本修订记录

> **版本**：1.0.7  
> **状态**：开发中（In Development）  
> **发布时间**：待定  
> **文档状态**：当前开发版本——**未特别说明版本号时，项目内容所有变更均迭代在此版本**（显示 `v1.0.7-dev`），按时间顺序追加到本文档；仅当明确「迭代下一个版本」才切换  
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

## 4. TODO 清单

- [x] **版本初始化**：VERSION_1_0_7.md + 版本号 `1.0.7.dev0` + Roadmap/Readme 同步 + 开发模式启动（2026-08-28 完成）
- [x] **核心引擎改造规划**：架构方案 `docs/rules/BenchEngine.md`（引擎抽象 / 版本化 / 环境校验 / 参数描述 / 自研 bench 核心）（2026-08-28 完成，待确认后实施）
- [x] **P1 引擎抽象**：configs/benchs.yaml（3 内置引擎 + 对比表）+ benchs.py 注册表 + /api/benchs* + Settings Bench 栏 + 创建页引擎选择（2026-08-28 完成）
- [x] **P2 环境校验**：torch/vllm/sglang 版本范围校验（_match_spec）+ CLI 探测 + 前端阻断「下一步」（2026-08-28 完成）
- [x] **P3 参数体系**：configs/bench-params.yaml（37 项参数描述 + 选项级描述）+ /api/benchs/*/params + 前端下拉描述面板（2026-08-28 完成）
- [x] **P4 自研引擎**：LoadGenerator / Requester / MetricsCollector + task_manager 集成（2026-08-28 完成）
- [x] **P5 Settings Bench 栏**：内置引擎列表 + 介绍 + 对比表 + 环境状态 + benchs.yaml 查看/编辑（2026-08-28 完成）
- [x] **P6 测试与文档**：tests/api 78 + tests/webui 20 + Architecture.md / Software.md / BenchCore.md 同步（2026-08-28 完成）

---

## 5. 相关文档

- 版本路线：[docs/Roadmap.md](../Roadmap.md)
- 上一版本：[VERSION_1_0_6.md](./VERSION_1_0_6.md)
- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Datas / Accuracy / Sessions / Settings / TopBar）
