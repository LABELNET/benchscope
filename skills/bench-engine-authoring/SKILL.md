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
4. **Generate mock logic** (only when the engine needs simulation, e.g. FAKE mode):
   follow the mock core contract in §3 — output must match benchscope's parser regexes.
5. **Validate before import** — the import endpoint runs these checks (see §4).
   Fix every failure and re-validate; **import succeeds only if all checks pass**.
6. **Import** — paste the final YAML into Settings → Bench 引擎 → 引擎定义 (benchs.yaml)
   → 编辑 → 保存 (validation runs server-side), or call `PUT /api/benchs/config/yaml`.

## 2. Upstream reference links (pin to the target version tag)

| Framework | Repo | Bench entrypoint | Pin format |
| --- | --- | --- | --- |
| vLLM | https://github.com/vllm-project/vllm | `vllm bench serve` → `vllm/benchmarks/serve.py` | `https://github.com/vllm-project/vllm/tree/v<VERSION>` |
| SGLang | https://github.com/sgl-project/sglang | `python -m sglang.bench_serving` → `python/sglang/bench_serving.py` | `https://github.com/sgl-project/sglang/tree/v<VERSION>` |

- Built-in engines in benchscope today: `benchscope`（自研）· `vllm-0.23` · `sglang-0.5.10`.
- **How to use these links**: replace `<VERSION>` with the target version, open the bench
  entrypoint file at that tag, and read the argument parser to enumerate real flags.
  Example pinned URLs:
  - vLLM 0.23 → `https://github.com/vllm-project/vllm/blob/v0.23.0/vllm/benchmarks/serve.py`
  - SGLang 0.5.10 → `https://github.com/sgl-project/sglang/blob/v0.5.10/python/sglang/bench_serving.py`

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
