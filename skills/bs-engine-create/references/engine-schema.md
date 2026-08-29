# 引擎定义字段参考（configs/benchs.yaml）

> 适用：benchscope ≥ 1.0.7 · 引擎定义由 `configs/benchs.yaml` 驱动

## 顶层结构

```yaml
comparison:      # 可选：引擎对比表（Settings 面板渲染）
  - dimension: <对比维度名>
    values:
      <engine_id>: <该引擎在此维度的取值>
engines:         # 必需：引擎列表
  - id: <引擎 id>
```

## engines[] 字段

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `id` | ✅ | 唯一标识，创建任务时写入 `payload.engine_id`；建议 `<framework>-<version>` |
| `kind` | ✅ | `builtin` / `vllm` / `sglang`（决定执行方式与环境要求） |
| `framework` | 推荐 | 归属框架（`builtin` / `vllm` / `sglang`） |
| `version` | 推荐 | 引擎版本字符串；自研引擎可用 `stable` |
| `params_key` | 推荐 | 参数集键（对应 `configs/bench-params.yaml` 的顶层键）；缺省回退 `kind` |
| `name` | 推荐 | 展示名 |
| `description` | 推荐 | 引擎介绍（Settings 卡片展示） |
| `highlights` | 推荐 | 特点列表（字符串数组） |
| `requires` | 原生引擎必需 | 环境要求列表（见下） |

## requires[] 字段

| 字段 | 说明 |
| --- | --- |
| `name` | 包名（`torch` / `vllm` / `sglang`） |
| `spec` | 版本范围：`>=x` `>x` `<=x` `<x` `==x` `!=x`，逗号分隔表示同时满足 |
| `hint` | 不满足时展示的安装提示 |

**约定**：
- `kind=builtin` → `requires: []`（自研引擎无框架环境依赖，环境校验恒通过）
- `kind=vllm` → 需 `torch` + `vllm`（如 `>=0.23,<0.24`）
- `kind=sglang` → 需 `torch` + `sglang`（如 `==0.5.10`）

## 完整示例

```yaml
engines:
  # 自研引擎（无环境依赖）
  - id: benchscope
    kind: builtin
    framework: builtin
    version: stable
    params_key: benchscope
    name: Bench CLI
    description: >-
      自研测试引擎，基于 OpenAI 兼容 API 的异步流式负载生成器。
      不依赖本地 vLLM / SGLang 环境，pip 安装后即可对本地或远程的任意 OpenAI 兼容推理服务进行性能测试。
    highlights:
      - 无需本地框架环境，安装即用
      - 支持本地与远程 OpenAI 兼容服务
      - 指标口径对齐 vLLM bench，可与原生引擎对比
    requires: []

  # 原生 vLLM 引擎（指定版本）
  - id: vllm-0.23
    kind: vllm
    framework: vllm
    version: "0.23"
    params_key: vllm
    name: vLLM Bench（原生 v0.23）
    description: >-
      vLLM 官方 bench 工具（vllm bench serve），由本地安装的 vLLM 0.23.x 提供。
    highlights:
      - vLLM 官方实现，与官方口径完全一致
      - 需本地安装 torch + vllm 0.23.x
    requires:
      - name: torch
        spec: ">=2.0"
        hint: "请安装 torch：pip install 'torch>=2.0'"
      - name: vllm
        spec: ">=0.23,<0.24"
        hint: "请安装 vLLM 0.23.x：pip install 'vllm>=0.23,<0.24'"
```

## comparison 示例

```yaml
comparison:
  - dimension: 本地环境依赖
    values:
      benchscope: 无（仅需 Python）
      vllm-0.23: 需 torch + vllm 0.23.x
      sglang-0.5.10: 需 torch + sglang 0.5.10
  - dimension: 执行方式
    values:
      benchscope: 进程内异步压测（无子进程）
      vllm-0.23: 子进程执行 CLI + 输出解析
      sglang-0.5.10: 子进程执行 CLI + 输出解析
```

## 扩展新版本（示例：vllm-0.24）

只需追加一个 engines 条目 + 对应的 `params_key` 参数段（在 `configs/bench-params.yaml`）：

```yaml
  - id: vllm-0.24
    kind: vllm
    framework: vllm
    version: "0.24"
    params_key: vllm-0.24          # ← 需在 bench-params.yaml 中新增该段
    name: vLLM Bench（原生 v0.24）
    description: >-
      vLLM 官方 bench 工具（vllm bench serve），由本地安装的 vLLM 0.24.x 提供。
    requires:
      - name: torch
        spec: ">=2.0"
      - name: vllm
        spec: ">=0.24,<0.25"
        hint: "请安装 vLLM 0.24.x：pip install 'vllm>=0.24,<0.25'"
```

并在 `comparison[*].values` 中为 `vllm-0.24` 补上各维度取值（可选，缺省显示 `-`）。
