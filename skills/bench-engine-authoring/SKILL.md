---
name: bench-engine-authoring
description: >-
  Create a custom BenchScope test engine (a specific vLLM / SGLang version, or any
  other OpenAI-compatible bench tool) — generate its engine config, parameter
  descriptions and mock logic, then validate and import it into benchscope.
  Use when the user adds a new bench engine or a new framework version
  (e.g. "add vllm 0.24", "add sglang 0.4.6", "custom bench engine"), or when an
  imported engine definition fails validation.
version: 1.0.0
---

# Custom Bench Engine Authoring (skill)

Produce a **complete, validatable engine definition package** for BenchScope so a new
engine/version can be imported into Settings → Bench 引擎.

## When to use

- The user wants to add a **new framework version** (`vllm 0.24`, `sglang 0.4.6`, …).
- The user wants to add an **entirely new engine** (another OpenAI-compatible bench tool).
- An engine import **failed validation** and needs fixing.
- The user asks "how do I add a custom bench engine?".

## Prerequisites

- benchscope ≥ 1.0.7 (`pip install benchscope==1.0.7`).
- Target framework's upstream source (for parameter/truth verification — links in §2).
- Network access if the version must be looked up online.

## 1. Workflow

1. **Identify the target** — framework (`vllm` / `sglang` / other) + exact version.
   Never guess: confirm the version with the user.
2. **Fetch upstream truth** — open the pinned GitHub link (§2) at the **target version tag**
   and extract:
   - the bench entrypoint module (`vllm bench serve` / `sglang.bench_serving`);
   - the **actual parameter list** (flag names, defaults, valid values) at that tag.
   Do **not** copy parameters from another version — flags change between releases.
3. **Generate two artifacts** (templates in `templates/`):
   - `benchs-engine-entry.yaml` — one engine entry appended to `configs/benchs.yaml`;
   - `bench-params-section.yaml` — parameter descriptions for `configs/bench-params.yaml`
     (every option **must** carry a `description`).
4. **Implement the engine code by copying upstream logic + adapting the contract** (see §3.5):
   download the pinned source (§2), reuse the verified core (streaming timeline, metric
   formulas, concurrency & rate control), then wire benchscope's **Input / Core / Output / Mock**
   contract. Do **not** re-invent the metric math — copy it and keep the口径 identical.
5. **Generate mock logic** (only when the engine needs simulation, e.g. FAKE mode):
   follow the mock core contract in §3 — output must match benchscope's parser regexes.
6. **Validate before import** — the import endpoint runs these checks (see §4).
   Fix every failure and re-validate; **import succeeds only if all checks pass**.
7. **Import** — paste the final YAML into Settings → Bench 引擎 → 引擎定义 (benchs.yaml)
   → 编辑 → 保存 (validation runs server-side), or call `PUT /api/benchs/config/yaml`.

### 3.5 Copy-upstream implementation contract (Input / Core / Output / Mock)

| Contract | Requirement |
| --- | --- |
| **Input** | Accept `BuiltinOptions` (base_url / model / endpoint / backend / dataset / concurrency / num_prompts / request_rate / timeout / warmups / seed / extra_body) |
| **Core** | **Copy** upstream streaming timeline (`t0→t_first→t_i→t_end`), metric formulas (TPOT = `(lat-ttft)/(n-1)`, duration = wall-clock), semaphore concurrency, gamma/burstiness rate control |
| **Output** | Return a dict compatible with `parser.parse_metrics`: `output_mean` `total_mean` `req_per_s` `ttft_{mean,median,p99}` `tpot_{mean,median,p99}` `itl_{mean,median,p99}` `successful_requests` `failed_requests` `benchmark_duration` `total_input_tokens` `total_generated_tokens`; plus `raw` (vLLM-style text for logs) |
| **Mock** | Implement in `mocks/` only; output text **must match `parser.py` regexes** |

Reference skeleton: `benchscope/benches/builtin_bench.py` already implements this contract —
read it as the canonical example before writing a new engine.

## 2. Upstream source: links, versions & how to fetch

**You MUST pull the actual source of the target version and analyze it** — never write an
engine definition from memory or by copying another version's parameters.

### 2.1 Verified references (analysed in this repo)

| Framework | Version | Commit | Git | Zip | Bench entrypoint |
| --- | --- | --- | --- | --- | --- |
| vLLM | `v0.23.0` | `0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665` | https://github.com/vllm-project/vllm | https://github.com/vllm-project/vllm/archive/refs/tags/v0.23.0.zip | `vllm/benchmarks/serve.py` (2052 lines) + `vllm/benchmarks/lib/endpoint_request_func.py` (861) |
| SGLang | `v0.5.10` | `1519acf37c23f2189adb93f57ca9cd2db1bebf18` | https://github.com/sgl-project/sglang | https://github.com/sgl-project/sglang/archive/refs/tags/v0.5.10.zip | `python/sglang/bench_serving.py` (2352 lines) |

Built-in engines in benchscope today: `benchscope`（自研）· `vllm-0.23` · `sglang-0.5.10`.

### 2.2 Fetch commands (replace `<VERSION>`)

```bash
# vLLM — clone / zip / single file
git clone --depth 1 --branch v<VERSION> https://github.com/vllm-project/vllm
curl -L -o vllm-<VERSION>.zip https://github.com/vllm-project/vllm/archive/refs/tags/v<VERSION>.zip
curl -sL "https://api.github.com/repos/vllm-project/vllm/contents/vllm/benchmarks/serve.py?ref=v<VERSION>"

# SGLang
git clone --depth 1 --branch v<VERSION> https://github.com/sgl-project/sglang
curl -L -o sglang-<VERSION>.zip https://github.com/sgl-project/sglang/archive/refs/tags/v<VERSION>.zip
curl -sL "https://api.github.com/repos/sgl-project/sglang/contents/python/sglang/bench_serving.py?ref=v<VERSION>"
```

Pinned file links:
- vLLM → `https://github.com/vllm-project/vllm/blob/v<VERSION>/vllm/benchmarks/serve.py`
- SGLang → `https://github.com/sgl-project/sglang/blob/v<VERSION>/python/sglang/bench_serving.py`

### 2.3 What to extract from the source

1. The bench entrypoint's **argument parser** → real flags, defaults, valid values at that tag;
2. The **request function** (`async_request_openai_*` / `async_request_*`) → timeline recording;
3. `calculate_metrics(...)` → exact metric formulas and the duration definition.

Full analysis of the two reference versions (with line numbers) is archived in
[references/upstream-analysis.md](references/upstream-analysis.md) and
[docs/rules/BenchUpstream.md](../../../docs/rules/BenchUpstream.md) — **read it first**, it
gives you the verified core logic you can copy.

## 3. Mock core logic (contract — required when generating mock output)

Mock (simulation) code lives **only** in `mocks/` (never in `tests/`).

### 3.1 Core methods

| Method | File | Purpose |
| --- | --- | --- |
| `generate_vllm_output(**kwargs) -> str` | `mocks/bench_outputs.py` | Generate vLLM-style bench output text |
| `generate_sglang_output(**kwargs) -> str` | `mocks/bench_outputs.py` | Generate SGLang-style bench output text |
| `generate_output(framework, **kwargs) -> str` | `mocks/bench_outputs.py` | Dispatch by framework (single source of truth for mock data) |
| `_scale_stats(concurrency, input_len, output_len, rng) -> dict` | `mocks/bench_outputs.py` | Produce one self-consistent metric set (sub-linear throughput growth, latency rising with concurrency) |
| `_parse_bench_args(argv) -> (dict, dict)` | `mocks/cli.py` | Parse bench CLI args into `(parsed_args, stats_kwargs)` |
| `main(argv) -> int` | `mocks/cli.py` | FAKE bench CLI entry (`BENCHSCOPE_FAKE_BENCH=1`) |
| `chat(req)` / `_sse_stream(...)` | `mocks/openai_server.py` | Mock OpenAI-compatible service; SSE stream with `stream_options.include_usage` |
| `_count_tokens(text)` / `_fill_to_tokens(seed, n)` | `mocks/openai_server.py` | Approx token counting (≈4 chars/token) and padding output to target token count |
| `list_models()` | `mocks/openai_server.py` | Mock `/v1/models` |

### 3.2 Two hard rules

1. **Output text must match `benchscope/parser.py` regexes** — otherwise metrics parse to 0:
   - vLLM style: `Output token throughput (tok/s):         1771.23`, `Mean TTFT (ms):`, `P99 TTFT (ms):`
   - SGLang style: `Time to first token (TTFT) mean (ms):`, `Time per output token (TPOT) p99 (ms):`, `Inter-token latency (ITL) mean (ms):`
2. **Metrics must scale intuitively**: higher concurrency → higher throughput, higher latency.
   Reuse `_scale_stats()` so data stays self-consistent; support `seed` for reproducibility.

## 4. Import validation (all must pass, else import is rejected)

| # | Check | Rule |
| --- | --- | --- |
| 1 | YAML valid | Parses as a mapping |
| 2 | `engines` present | Non-empty list |
| 3 | Engine `id` | Present, unique; kebab-case recommended |
| 4 | `kind` | One of `builtin` / `vllm` / `sglang` |
| 5 | `requires` (native engines) | Must include `torch` + the framework package with a version `spec` |
| 6 | `params` cross-check | Every `params_key` referenced must exist in `configs/bench-params.yaml` |
| 7 | Option descriptions | Every parameter option must carry a non-empty `description` |
| 8 | Mock output (if provided) | Must match parser regexes (contains the required metric lines) |

Server response: `200 {ok: true}` on success; `400 {detail: "<failed check>"}` on failure —
**nothing is written to disk when validation fails**.

## 5. Copy-paste prompt (give this to an AI to generate a new engine)

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

## 6. Self-check before delivering

- [ ] Version confirmed with the user (not guessed)
- [ ] Parameters read from the **pinned upstream tag**, not from another version
- [ ] Every parameter option has a `description`
- [ ] `kind` is one of `builtin` / `vllm` / `sglang`
- [ ] Native engine declares `torch` + framework in `requires` with version `spec`
- [ ] `params_key` matches an existing section in `configs/bench-params.yaml`
- [ ] All validation checks pass

## 7. Troubleshooting

- **`400 engines[i] kind must be ...`** — `kind` must be exactly `builtin` / `vllm` / `sglang`.
- **`400 params_key not found`** — add the matching section in `configs/bench-params.yaml` first.
- **`400 option missing description`** — every option needs a `description` (enforced by design).
- **Metrics all zero after import** — mock/CLI output does not match `parser.py` regexes.
- **Environment check always fails** — `requires` version spec does not match the installed
  version; verify with `pip show vllm sglang torch`.

## References

- [engine-schema.md](references/engine-schema.md) — full field reference + example
- [mock-core.md](references/mock-core.md) — mock core methods and scaling model in depth
- [import-checklist.md](references/import-checklist.md) — validation rules and error messages
- [templates/](templates/) — copyable yaml templates
