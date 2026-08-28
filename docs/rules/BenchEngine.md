# Bench 引擎架构 — BenchEngine（v1.0.7 规划）

> **状态**：P1/P2/P4 已实施（自研引擎可用），P3/P5/P6 待实施  
> **实施进度**：P1 引擎抽象 ✅ · P2 环境校验 ✅ · P3 参数描述 ⏳ · P4 自研引擎 ✅ · P5 Settings 栏 ✅（基础版）· P6 测试文档 🔄
> **最后更新**：2026-08-28 18:14:58  
> **目标**：性能测试核心引擎改造——引擎抽象 + 多版本原生 bench + 自研 bench + 环境校验 + 参数下拉描述  
> **关联**：[Architecture.md](./Architecture.md) · [Software.md](./Software.md) · [../prds/Performance-Create.md](../prds/Performance-Create.md) · [../versions/VERSION_1_0_7.md](../versions/VERSION_1_0_7.md)

---

## 1. 背景与现状

**现状**：引擎为「框架二选一 + 单版本」，命令构建在 `benchscope/benches/`（`base.py` / `vllm_bench.py` / `sglang_bench.py`），执行靠 `runner.py` 的 `bash -lic` 子进程调用原生 CLI（`vllm bench serve` / `python -m sglang.bench_serving`），结果经 `parser.py` 正则解析。参数体系为「CURATED_PARAMS（Python 硬编码）+ 框架默认 yaml（`configs/{vllm,sglang}-default.yaml`）」。

**痛点**：
1. 引擎与框架版本强耦合——`vllm bench` 参数随版本变化（0.21 / 0.23 参数集不同），当前只维护一份硬编码参数集；
2. 无法针对「具体版本」选择原生 bench（用户环境可能装了多个 vllm/sglang 版本）；
3. **无自研 bench**——必须本地安装 vllm/sglang 才能跑性能测试，无法「装个 pip 包就远程测 OpenAI 兼容服务」；
4. 参数无描述/无版本适配，用户不知道参数含义与适用版本；
5. 无环境校验——环境不满足时仍可进入参数配置，直到执行时才失败。

**目标形态**：三种引擎并存，按「引擎 + 版本」管理，环境校验前置，参数带描述。

---

## 2. 引擎抽象（三层）

```
BenchEngineRegistry                      # 引擎注册表（configs/benchs.yaml 驱动）
│
├── benchscope（自研 builtin）            # 无框架依赖，纯 HTTP 压测 OpenAI 兼容服务
│
├── vllm（原生，版本化）
│   ├── vllm-0.23                        # vllm bench serve（参数集随版本）
│   └── vllm-<version> ...               # 可扩展更多版本
│
└── sglang（原生，版本化）
    ├── sglang-0.5.10                    # python -m sglang.bench_serving
    └── sglang-<version> ...
```

### 2.1 引擎接口（统一抽象）

```python
@dataclass
class EnvRequirement:
    name: str        # 包名，如 "torch" / "vllm" / "sglang"
    spec: str        # 版本范围，如 ">=2.0" / ">=0.23,<0.24"
    optional: bool = False
    hint: str = ""   # 不满足时的安装提示

class BenchEngine(Protocol):
    engine_id: str              # "benchscope" | "vllm-0.23" | "sglang-0.5.10"
    kind: str                   # "builtin" | "vllm" | "sglang"
    display_name: str
    description: str            # 引擎介绍（Settings 展示）
    comparison: list[dict]      # 对比项（Settings 对比表）
    requires: list[EnvRequirement]

    def params(self) -> list[ParamSpec]: ...          # 该引擎的参数定义（下拉 + 描述）
    def build_command(self, opts: BenchOptions) -> list[str] | None: ...  # 原生引擎：CLI 命令
    def run(self, opts, stream_cb, stop_event) -> dict: ...               # 自研引擎：直接执行产出 metrics
    def parse(self, output: str) -> dict: ...         # 原生引擎：文本 → metrics
```

- **原生引擎**（vllm / sglang）：沿用「构建命令 → `runner.py` 子进程执行 → `parser.py` 解析」链路；
- **自研引擎**（benchscope）：不经子进程，进程内直接执行并产出结构化 metrics，但仍走 `task_manager._record_row` / `summary.py` 汇总与前端展示，保证全链路一致。

### 2.2 引擎定义文件（yaml，与 datasets.yaml 同范式）

`benchscope/configs/benchs.yaml`——内置引擎清单（id / kind / version / 名称 / 介绍 / 对比 / 环境要求 / 参数集），后端 `benchs.py` 加载 + API 暴露，Settings 面板展示（复用 Datasets 面板「卡片 + 描述 + 状态」范式）。

---

## 3. 内置引擎清单（规划）

| engine_id | kind | 命令 | 环境要求 | 说明 |
| --- | --- | --- | --- | --- |
| `benchscope` | builtin | 无（进程内执行） | **无**（Python 标准库 + 可选异步 HTTP 依赖） | 自研引擎，可 pip 安装后远程测任意 OpenAI 兼容服务 |
| `vllm-0.23` | vllm | `vllm bench serve ...` | torch + vllm（版本范围匹配 0.23） | vLLM 原生 bench，参数集按 0.23 |
| `sglang-0.5.10` | sglang | `python -m sglang.bench_serving ...` | torch + sglang（版本范围匹配 0.5.10） | SGLang 原生 bench，参数集按 0.5.10 |

> 后续扩展：新增版本只需在 `benchs.yaml` 追加条目 + 对应参数集，不改代码。

---

## 4. 环境校验约定（强制）

**规则**：
- `kind = vllm` / `sglang`：**必须校验** `torch` 与目标框架（`vllm` / `sglang`）的安装版本，任一缺失或版本不匹配 → **禁止进入下一步（参数选择）**，前端展示缺失项与安装提示；
- `kind = builtin`（自研 bench）：**不做框架环境校验**，只需本地 Python 可用，即可远程测 OpenAI 兼容 API。

**检测手段**：复用 `benchscope/env_info.py` 的 `_pkg()`（`importlib.metadata.version()`）+ 版本范围比较（`packaging.version`，或自研轻量比较避免新依赖）。

**API 草案**：

```
GET /api/benchs                       # 引擎清单（含介绍/对比/环境状态）
GET /api/benchs/{engine_id}           # 单引擎详情（参数集 + 环境检查）
GET /api/benchs/{engine_id}/env-check # { ok, checks: [{name, required, installed, ok, hint}] }
```

**前端交互**（创建页 Step1）：选择引擎 → 触发 `env-check` →
- 通过：可进入 Step2 参数配置；
- 不通过：引擎项标红 + 「下一步」禁用 + 提示「未检测到 vllm 0.23（需 torch ≥ 2.0、vllm 0.23.x），请安装后重试；或选择自研 bench（benchscope）无需本地框架环境」。

---

## 5. 参数体系（下拉选择 + 描述信息）

扩展现有 `ParamDef`（`benches/base.py:8`）为 `ParamSpec`：

```python
@dataclass
class ParamSpec:
    key: str
    flag: str
    label: str
    help: str = ""            # 参数描述（选中/悬停展示）
    type: str = "str"         # str | int | float | bool | select
    default: Any = None
    options: list[OptionMeta] # 下拉选项（含选项级描述）
    advanced: bool = False
    group: str = "other"      # server | sampling | resource | benchmark | other
    since: str | None = None  # 从哪个引擎版本开始支持
    deprecated: str | None = None  # 从哪个版本废弃

@dataclass
class OptionMeta:
    value: str
    label: str
    description: str = ""     # 【选择后展示描述信息】
```

**交互**（Step2 参数面板）：
- 参数行 = 标签 + 控件（下拉 `a-select` / 输入 / 开关）+ 描述区；
- 下拉选中某选项后，在参数行下方展示该选项的 `description`（如 `backend` 选 `openai-chat` → 「使用 /v1/chat/completions 接口，适用于对话（instruct/chat）模型」）；
- 参数本身 `help` 常驻（灰色小字或 tooltip）；
- 版本适配：`since` / `deprecated` 标注，非当前引擎版本适用的参数置灰并说明。

---

## 6. 自研 bench（benchscope）核心设计 ★

> 这是本次改造的核心问题：**自研 bench 的「核心」= 基于 OpenAI 兼容 API 的异步负载生成器 + 精确指标采集，且指标口径与 vLLM / SGLang 原生 bench 严格对齐（保证可比性）**。

### 6.1 四个核心子系统

```
① 负载生成 LoadGenerator
   并发模型（concurrency 个 worker）+ 请求总量（num_prompts）+ 速率（request_rate）
   数据集：random（按 input_len/output_len 构造）| sharegpt（真实长度分布）| custom（jsonl）
        ↓
② 请求执行 Requester（async HTTP，SSE 流式）
   记录每个请求的时间线：t0 → t_first → t_1..t_n → t_end
        ↓
③ 指标计算 MetricsCollector
   TTFT / TPOT / ITL / E2E + 吞吐量，mean / median / p99（口径对齐 vLLM bench）
        ↓
④ 结果输出 ResultSink
   结构化 metrics → task_manager._record_row → summary（CSV/xlsx）→ 前端展示（复用现有链路）
```

### 6.2 负载生成（LoadGenerator）

| 项 | 设计 |
| --- | --- |
| 并发模型 | `concurrency` 个 worker 并发持续发请求，直到累计完成 `num_prompts` 个请求（与 vLLM bench 语义一致） |
| 速率控制 | `request_rate=inf` 全速；数值 → 泊松到达（或固定间隔，待确认） |
| 数据集 random | 按 `input_len` / `output_len` 构造 prompt 与 `max_tokens` |
| 数据集 sharegpt | 从 `sharegpt*.jsonl` 采样，按真实输入/输出长度分布（可截取/填充到目标长度） |
| 数据集 custom | 用户 jsonl（`{"prompt": ...}` 或 messages） |
| 端点 | `/v1/chat/completions`（默认，backend=openai-chat）/ `/v1/completions`（backend=openai） |
| 预热 / 超时 | `num_warmups` 预热请求不计入指标；单请求超时可配 |

### 6.3 指标采集（核心中的核心：流式时间线）

单个请求 Timeline（**streaming 是准确测量 TTFT / ITL 的前提**）：

```
t0        发出请求
t_first   首个内容 chunk 到达  → TTFT  = t_first - t0
t_i       第 i 个 chunk 到达   → ITL_i = t_i - t_{i-1}
t_end     流结束（[DONE]）     → E2E   = t_end - t0
N         输出 token 数        → 服务端 usage.completion_tokens（stream_options.include_usage）
```

### 6.4 指标口径对齐（决定能否与原生 bench 对比）

| 指标 | 计算口径（对齐 vLLM bench serve） |
| --- | --- |
| Output token throughput | `总 completion_tokens / benchmark_duration` |
| Total token throughput | `(总 prompt_tokens + 总 completion_tokens) / duration` |
| Request throughput | `成功请求数 / duration` |
| TTFT | 首 token 延迟，mean / median / p99（ms） |
| TPOT | `(E2E - TTFT) / (completion_tokens - 1)`，mean / median / p99（ms） |
| ITL | 相邻 chunk 间隔（`t_i - t_{i-1}`），mean / median / p99（ms） |
| E2E latency | `t_end - t0`，mean / median / p99（ms） |
| Successful / Failed | 成功 / 失败请求数（失败含超时、HTTP 错误、连接错误） |

> `benchmark_duration` 定义需与 vLLM 一致（所有 worker 从开始到最后一个请求完成的墙钟时间），这是 throughput 可比的关键。

### 6.5 技术选型（**已确认**）

| 维度 | 决策 | 说明 |
| --- | --- | --- |
| 异步 HTTP | **aiohttp** | 成熟高并发、SSE 流式支持好；新增依赖，实施时需同步 `docs/rules/Software.md` §2/§3 |
| 输出 token 计数 | **服务端 `usage.completion_tokens`** | 请求带 `stream_options.include_usage: true`；服务端不返回时回退按 chunk 数估算 |
| input 长度控制 | **近似构造** | 按字符/token 比（默认 ~4 字符≈1 token，可配）构造 prompt，零额外依赖 |
| 分位数计算 | 纯 Python `statistics` | 零依赖 |
| 指标口径 | **严格对齐 vLLM bench** | 保证自研引擎与原生引擎结果可直接对比 |
| 引擎版本策略 | **内置 + 用户可扩展** | 内置 `bench` / `vllm-0.23` / `sglang-0.5.10`，yaml 驱动支持用户自定义新增引擎与版本 |

**依赖变更（待实施）**：新增 `aiohttp`（建议 `>=3.9`），须同步 `docs/rules/Software.md` §2 技术栈与 §3 依赖清单（软件依赖变更约定）。

### 6.6 与现有链路的集成

- 复用：`BenchOptions`（`benches/base.py:22`）、`task_manager._execute_case_*` 编排、`_record_row`、`summary.py`（CSV/xlsx）、阈值模式二分探测、前端 Realtime / Perf Datas 展示；
- 差异：自研引擎 `run()` 直接返回 metrics dict，跳过 `build_command` / `runner` / `parser`；
- 兼容：为便于日志查看与解析复用，可选输出 vLLM 风格文本摘要（非必需）。

---

## 7. 已确认决策（2026-08-28 用户确认）

| # | 决策项 | 结论 |
| --- | --- | --- |
| Q1 | 异步 HTTP 技术栈 | **aiohttp** |
| Q2 | 输出 token 计数 | **服务端 usage.completion_tokens**（`stream_options.include_usage`） |
| Q3 | input 长度控制 | **近似构造**（字符/token 比，零额外依赖） |
| Q4 | 指标口径 | **严格对齐 vLLM bench**（可与原生引擎直接对比） |
| Q5 | 引擎版本策略 | **内置 + 用户可扩展**（内置 `bench` / `vllm-0.23` / `sglang-0.5.10`，yaml 驱动扩展） |
| Q6 | 旧任务兼容（无引擎字段） | **读取时回退默认引擎**（`vllm` 当前参数集），新建任务必须显式指定引擎 |

---

## 8. 实施路径（草案，确认后细化）

| 阶段 | 内容 | 依赖 |
| --- | --- | --- |
| P1 引擎抽象 | 定义 `BenchEngine` 接口 + `configs/benchs.yaml` + 注册表 + API（`/api/benchs*`） | Q5、Q6 |
| P2 环境校验 | `env-check`（torch / vllm / sglang 版本范围）+ 前端阻断交互 | P1、Q4 |
| P3 参数体系 | `ParamSpec` + 选项级描述 + 前端下拉描述面板 | P1 |
| P4 自研引擎 | LoadGenerator / Requester / MetricsCollector / ResultSink + 集成 task_manager | Q1、Q2、Q3、Q4 |
| P5 Settings Bench 栏 | 内置引擎列表 + 介绍 + 对比表 + 环境状态 | P1、P2 |
| P6 测试与文档 | tests/api（引擎注册/环境校验/自研引擎指标）+ tests/webui（引擎选择/参数描述/阻断）+ prds/Architecture/Software 同步 | 全部 |

---

## 8.1 实施落地说明（2026-08-28）

| 阶段 | 落地内容 | 关键文件 |
| --- | --- | --- |
| P1 | yaml 驱动注册表 + API + Settings Bench 栏 + 创建页引擎选择 | `configs/benchs.yaml`、`benchscope/benchs.py`、`server/api_benchs.py`、`SettingsView.vue`、`PerfCreateView.vue` |
| P2 | 版本范围校验（`_match_spec`）+ CLI 探测 + 前端阻断「下一步」 | `benchs.py::check_env`、`PerfCreateView.vue::nextToParams` |
| P4 | 自研引擎：aiohttp SSE 采集 + 指标口径对齐 vLLM + task_manager 集成 | `benches/builtin_bench.py`、`task_manager.py::_builtin_engine/_builtin_options` |

**任务执行分支**（`task_manager._run_one`）：
- `engine_id` 对应引擎 `kind=builtin` → **进程内执行**（`run_builtin_bench`），不经命令构建 / 子进程 / 输出解析；
- 其余（含未指定 `engine_id` 的旧任务）→ 回退原生链路（`build_single_command` + `runner.run` + `parser`）。

**注意**：`engine_id` 必须在 `CreateTaskRequest`（`api_tasks.py`）声明为 pydantic 字段，否则会被请求模型白名单丢弃（与 `max_concurrency_search` 曾遇到的坑一致）。

**实测（对 mock 服务）**：并发 1/2/4/8 → 输出吞吐 64.9 / 130.5 / 260.2 / 517.8 tok/s（线性增长），TPOT 稳定 ≈15.8ms，usage 精确计数生效。

---

## 9. 影响面（现有代码）

| 文件 | 改动 |
| --- | --- |
| `benchscope/benches/base.py` | `ParamDef` → `ParamSpec`（+ 选项描述 / 分组 / 版本适配）；`BenchOptions` 补 `tokenizer` 正式字段（当前外部动态挂属性，见 `task_manager.py:81`） |
| `benchscope/benches/vllm_bench.py` / `sglang_bench.py` | 参数集按版本拆分，命令构建适配引擎版本 |
| `benchscope/benches/runner.py` | 原生引擎沿用；自研引擎不经此层 |
| `benchscope/task_manager.py` | 执行分支按 `engine.kind` 分发（子进程 / 进程内） |
| `benchscope/env_info.py` | 复用 `_pkg()` 做版本范围校验 |
| `web/src/views/PerfCreateView.vue` | Step1 增加引擎选择 + 环境校验阻断；Step2 参数下拉 + 描述 |
| `web/src/views/SettingsView.vue` | 新增 Bench 栏（引擎列表 + 介绍 + 对比） |
| `benchscope/configs/` | 新增 `benchs.yaml`（引擎定义），现有 `{vllm,sglang}-default.yaml` 按版本演进或并入 |
