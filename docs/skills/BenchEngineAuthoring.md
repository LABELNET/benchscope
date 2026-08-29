# 自定义 Bench 引擎技能 — bench-engine-authoring

> **版本**：1.0.0　**技能目录**：[`skills/bench-engine-authoring/`](../../skills/bench-engine-authoring/)
> **最后更新**：2026-08-29
> **关联**：[Skills 体系总入口](./Readme.md) · [rules/BenchEngine.md](../rules/BenchEngine.md) ·
> [rules/BenchUpstream.md](../rules/BenchUpstream.md)（上游源码分析）·
> [rules/BenchCore.md](../rules/BenchCore.md)（自研引擎范例）

---

## 1. 用途与触发场景

为 BenchScope 生成**完整、可校验的引擎定义包**，使新引擎/新框架版本可导入 Settings → Bench 引擎。

**触发场景**：

- 新增**框架版本**（如「添加 vllm 0.24」「添加 sglang 0.4.6」）；
- 新增**全新引擎**（其他 OpenAI 兼容的 bench 工具）；
- 引擎导入**校验失败**需要修复；
- 用户询问「如何添加自定义 bench 引擎」。

**前置条件**：benchscope ≥ 1.0.7；目标框架上游源码（用于参数与核心逻辑核实）；按需联网。

---

## 2. 技能包结构

```
bench-engine-authoring/
├── SKILL.md                            # 技能主文档（AI 消费）
├── README.md                           # 说明（人消费）
├── references/
│   ├── engine-schema.md                # 引擎定义字段参考 + 完整示例
│   ├── upstream-analysis.md            # ⭐ 上游核心逻辑分析（源码实证，含链接与可复制代码）
│   ├── mock-core.md                    # mock 核心逻辑方法与介绍（缩放模型 / 两条硬规则）
│   └── import-checklist.md             # 导入校验项、API 与排错指引
├── templates/
│   ├── benchs-engine-entry.yaml        # 引擎条目模板
│   └── bench-params-section.yaml       # 参数段模板（选项描述必需）
└── scripts/
    ├── package.sh                      # 打包（tar.gz + 产物校验）
    └── validate.sh                     # 离线校验引擎定义
```

---

## 3. 核心工作流（7 步）

1. **确认目标** —— 框架（`vllm` / `sglang` / 其他）+ **确切版本**；不得猜测，须与用户确认。
2. **拉取上游源码核实** —— 打开**该版本 tag** 的 GitHub 链接（见 §4），提取：
   - bench 入口模块（`vllm bench serve` / `sglang.bench_serving`）；
   - **真实参数清单**（flag 名、默认值、可取范围）。
   > **禁止跨版本复制参数** —— flag 在不同 release 间会变化。
3. **生成两份产物**（模板见 `templates/`）：
   - `benchs-engine-entry.yaml` —— 追加到 `configs/benchs.yaml` 的引擎条目；
   - `bench-params-section.yaml` —— `configs/bench-params.yaml` 的参数段（**每个 option 必须带 `description`**）。
4. **实现引擎代码：复制上游逻辑 + 适配契约**（见 §5）—— 拉取固定版本源码，复用已验证的核心
   （流式时间线、指标公式、并发与速率控制），再接入 benchscope 的
   **入口 / 处理 / 出口 / Mock** 契约。
   > **不要重新发明指标公式** —— 复制上游并保持口径完全一致。
5. **生成 mock 逻辑**（仅当引擎需要仿真，如 FAKE 模式）—— 遵循 §6 mock 核心契约，
   输出文本**必须匹配** `parser.py` 正则。
6. **导入前校验** —— 服务端执行 §7 的 8 项校验；修复全部失败项后重新校验，
   **全部通过才可导入**。
7. **导入** —— Settings → Bench 引擎 → 引擎定义 (benchs.yaml) → 编辑 → 保存（服务端校验），
   或调用 `PUT /api/benchs/config/yaml`。

---

## 4. 上游源码：链接、版本与获取命令

> **必须拉取目标版本的真实源码分析**，禁止凭记忆或从其他版本复制参数。

### 4.1 已核实引用（本仓库已实证分析）

| 框架 | 版本 | Commit | Git | Zip | bench 入口 |
| --- | --- | --- | --- | --- | --- |
| vLLM | `v0.23.0` | `0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665` | https://github.com/vllm-project/vllm | https://github.com/vllm-project/vllm/archive/refs/tags/v0.23.0.zip | `vllm/benchmarks/serve.py`（2052 行）+ `vllm/benchmarks/lib/endpoint_request_func.py`（861 行） |
| SGLang | `v0.5.10` | `1519acf37c23f2189adb93f57ca9cd2db1bebf18` | https://github.com/sgl-project/sglang | https://github.com/sgl-project/sglang/archive/refs/tags/v0.5.10.zip | `python/sglang/bench_serving.py`（2352 行） |

内置引擎现状：`benchscope`（自研）· `vllm-0.23` · `sglang-0.5.10`。

### 4.2 获取命令（替换 `<VERSION>`）

```bash
# vLLM — clone / zip / 单文件
git clone --depth 1 --branch v<VERSION> https://github.com/vllm-project/vllm
curl -L -o vllm-<VERSION>.zip https://github.com/vllm-project/vllm/archive/refs/tags/v<VERSION>.zip
curl -sL "https://api.github.com/repos/vllm-project/vllm/contents/vllm/benchmarks/serve.py?ref=v<VERSION>"

# SGLang
git clone --depth 1 --branch v<VERSION> https://github.com/sgl-project/sglang
curl -L -o sglang-<VERSION>.zip https://github.com/sgl-project/sglang/archive/refs/tags/v<VERSION>.zip
curl -sL "https://api.github.com/repos/sgl-project/sglang/contents/python/sglang/bench_serving.py?ref=v<VERSION>"
```

**Pinned 文件链接**：

- vLLM → `https://github.com/vllm-project/vllm/blob/v<VERSION>/vllm/benchmarks/serve.py`
- SGLang → `https://github.com/sgl-project/sglang/blob/v<VERSION>/python/sglang/bench_serving.py`

### 4.3 需从源码提取的三项内容

1. 入口的 **argument parser** → 该 tag 下真实的 flag、默认值、取值范围；
2. **请求函数**（`async_request_openai_*` / `async_request_*`）→ 时间线记录方式；
3. `calculate_metrics(...)` → **精确指标公式**与 duration 定义。

> 两个参考版本的完整分析（带行号）存档于
> [`references/upstream-analysis.md`](../../skills/bench-engine-authoring/references/upstream-analysis.md)
> 与 [`rules/BenchUpstream.md`](../rules/BenchUpstream.md)，**实现新引擎前先读**，其中给出可直接复用的已验证核心逻辑。

**关键共识**（两上游一致，自研引擎已对齐）：

- 时间线模型 `t0 → t_first → t_i → t_end`，**必须流式**（非流式无法测 TTFT/ITL）；
- `TPOT = (latency - ttft) / (output_len - 1)`；`output_len <= 1` 时记 0；
- `duration` 为**墙钟时间**（非「请求耗时之和 ÷ 并发」）；
- token 计数**优先服务端 `usage.completion_tokens`**。

---

## 5. 实现契约（复制上游 + 适配四段）

| 契约 | 要求 |
| --- | --- |
| **入口（Input）** | 接受 `BuiltinOptions`：base_url / model / endpoint / backend / dataset / concurrency / num_prompts / request_rate / timeout / warmups / seed / extra_body |
| **处理（Core）** | **复制**上游流式时间线（`t0→t_first→t_i→t_end`）、指标公式（TPOT = `(lat-ttft)/(n-1)`、duration = 墙钟）、semaphore 并发、gamma/burstiness 速率控制 |
| **出口（Output）** | 返回与 `parser.parse_metrics` 兼容的 dict：`output_mean` `total_mean` `req_per_s` `ttft_{mean,median,p99}` `tpot_{mean,median,p99}` `itl_{mean,median,p99}` `successful_requests` `failed_requests` `benchmark_duration` `total_input_tokens` `total_generated_tokens`；另附 `raw`（vLLM 风格文本，供日志） |
| **Mock** | 只在 `mocks/` 实现；输出文本**必须匹配 `parser.py` 正则** |

**规范范例**：`benchscope/benches/builtin_bench.py` 已实现该契约，编写新引擎前先读它。

---

## 6. Mock 核心逻辑契约

Mock（仿真）代码**唯一归属 `mocks/`**（`tests/` 不携带 mock 代码）。

### 6.1 核心方法

| 方法 | 文件 | 用途 |
| --- | --- | --- |
| `generate_vllm_output(**kwargs) -> str` | `mocks/bench_outputs.py` | 生成 vLLM 风格 bench 输出文本 |
| `generate_sglang_output(**kwargs) -> str` | `mocks/bench_outputs.py` | 生成 SGLang 风格 bench 输出文本 |
| `generate_output(framework, **kwargs) -> str` | `mocks/bench_outputs.py` | 按框架分发（mock 数据单一来源） |
| `_scale_stats(concurrency, input_len, output_len, rng) -> dict` | `mocks/bench_outputs.py` | 产出一组自洽指标（吞吐随并发次线性增长、延迟随并发上升） |
| `_parse_bench_args(argv) -> (dict, dict)` | `mocks/cli.py` | 解析 bench CLI 参数为 `(parsed_args, stats_kwargs)` |
| `main(argv) -> int` | `mocks/cli.py` | FAKE bench CLI 入口（`BENCHSCOPE_FAKE_BENCH=1`） |
| `chat(req)` / `_sse_stream(...)` | `mocks/openai_server.py` | OpenAI 兼容 mock 服务；SSE 流含 `stream_options.include_usage` |
| `_count_tokens(text)` / `_fill_to_tokens(seed, n)` | `mocks/openai_server.py` | 近似 token 计数（≈4 字符/token）与按目标 token 数填充输出 |
| `list_models()` | `mocks/openai_server.py` | mock `/v1/models` |

### 6.2 两条硬规则

1. **输出文本必须匹配 `benchscope/parser.py` 正则**，否则指标解析为 0：
   - vLLM 风格：`Output token throughput (tok/s):         1771.23`、`Mean TTFT (ms):`、`P99 TTFT (ms):`
   - SGLang 风格：`Time to first token (TTFT) mean (ms):`、`Time per output token (TPOT) p99 (ms):`、`Inter-token latency (ITL) mean (ms):`
2. **指标必须直观缩放**：并发越高 → 吞吐越高、延迟越高。
   复用 `_scale_stats()` 保证数据自洽，并支持 `seed` 以复现。

---

## 7. 导入校验（全部通过否则拒绝导入）

| # | 校验项 | 规则 |
| --- | --- | --- |
| 1 | YAML 合法 | 可解析为 mapping |
| 2 | `engines` 存在 | 非空列表 |
| 3 | 引擎 `id` | 存在且唯一（建议 kebab-case） |
| 4 | `kind` | 只能是 `builtin` / `vllm` / `sglang` |
| 5 | `requires`（原生引擎） | 必须含 `torch` + 框架包，且带版本 `spec` |
| 6 | `params` 交叉检查 | 引用的每个 `params_key` 必须存在于 `configs/bench-params.yaml` |
| 7 | 选项描述 | 每个参数 option 必须有非空 `description` |
| 8 | mock 输出（若提供） | 必须匹配 parser 正则（含必需指标行） |

**服务端响应**：成功 `200 {ok: true}`；失败 `400 {detail: "<失败项>"}`，且**校验失败时不写磁盘**。

**离线自检**（无需启动服务）：

```bash
./scripts/validate.sh                                   # 校验仓库默认配置
./scripts/validate.sh path/to/benchs.yaml               # 校验指定引擎定义
./scripts/validate.sh path/to/benchs.yaml path/to/bench-params.yaml
```

---

## 8. 可复制提示词（交给 AI 生成新引擎）

```text
Task: create a BenchScope custom bench engine definition for <FRAMEWORK> version <VERSION>.

Steps:
1) Read the upstream bench entrypoint at the pinned tag and enumerate the REAL
   parameters at that version:
   - vLLM:  https://github.com/vllm-project/vllm/blob/v<VERSION>/vllm/benchmarks/serve.py
   - SGLang:https://github.com/sgl-project/sglang/blob/v<VERSION>/python/sglang/bench_serving.py
   Do NOT reuse parameters from another version.
2) Emit TWO yaml artifacts:
   a) an engine entry for configs/benchs.yaml:
      - id: <framework>-<version>   kind: vllm|sglang|builtin   params_key: <key>
      - name / description / highlights / requires (torch + framework, with version spec)
   b) a parameter section for configs/bench-params.yaml under key <params_key>:
      for each parameter: label, help, type, and options — EVERY option MUST have a
      non-empty description explaining what that value does.
3) If the engine needs mock/simulation output, generate it following the mock core
   contract (mocks/ only), scaling throughput/latency with concurrency and matching
   the parser regexes exactly.
4) Validate against the import checklist (yaml / engines / id / kind / requires /
   params_key exists / option descriptions / mock output) and fix all failures
   before presenting the result.
5) Output the final, importable yaml in one code block.
```

> Settings → Bench 引擎 → 「添加自定义版本」面板内置同一份提示词，可一键复制。

---

## 9. 交付自检清单

- [ ] 版本已与用户确认（非猜测）
- [ ] 参数取自**固定的上游 tag**，而非其他版本
- [ ] 每个参数 option 都有 `description`
- [ ] `kind` 属于 `builtin` / `vllm` / `sglang`
- [ ] 原生引擎在 `requires` 中声明 `torch` + 框架包，且带版本 `spec`
- [ ] `params_key` 在 `configs/bench-params.yaml` 中存在同名段
- [ ] 全部导入校验项通过

---

## 10. 排错

| 现象 | 原因与处理 |
| --- | --- |
| `400 engines[i] kind must be ...` | `kind` 必须严格是 `builtin` / `vllm` / `sglang` |
| `400 params_key not found` | 先在 `configs/bench-params.yaml` 添加同名段 |
| `400 option missing description` | 每个 option 都需要 `description`（设计上强制） |
| 导入后指标全为 0 | mock/CLI 输出文本不匹配 `parser.py` 正则 |
| 环境校验始终失败 | `requires` 版本 spec 与已安装版本不匹配；用 `pip show vllm sglang torch` 核实 |

---

## 11. 参考

- [engine-schema.md](../../skills/bench-engine-authoring/references/engine-schema.md) — 引擎定义字段参考 + 完整示例
- [mock-core.md](../../skills/bench-engine-authoring/references/mock-core.md) — mock 核心方法与缩放模型
- [import-checklist.md](../../skills/bench-engine-authoring/references/import-checklist.md) — 校验规则与错误信息
- [templates/](../../skills/bench-engine-authoring/templates/) — 可复制 yaml 模板
- [rules/BenchUpstream.md](../rules/BenchUpstream.md) — 上游核心逻辑分析（含优化项清单）
