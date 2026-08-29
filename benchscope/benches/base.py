"""bench 命令构建的公共定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParamDef:
    """UI 表单中一个可配置参数的定义。"""

    key: str          # 表单字段名
    flag: str         # 实际 CLI flag，如 "--temperature"
    label: str        # 中文标签
    help: str = ""
    type: str = "str"  # str | int | float | bool | select
    default: Any = None
    options: list = field(default_factory=list)
    advanced: bool = False  # 是否归入“高级参数”折叠区


@dataclass
class BenchOptions:
    """一次 bench 执行所需的全部选项。"""

    framework: str
    model: str
    api: dict            # {host, port, base_url, endpoint, api_key, extra_headers}
    dataset: dict        # {type, path, input_len, output_len, sharegpt_output_len}
    concurrency: int
    request_rate: str | float = "inf"
    curated: dict = field(default_factory=dict)   # 表单参数 key -> value
    extra_args: list = field(default_factory=list)  # [{"flag": "--x", "value": "y"}]


def build_arg_list(flags: list[list]) -> list[str]:
    """将 [["--flag","value"], ["--bool",""]] 展开为命令行列表。"""
    out: list[str] = []
    for item in flags:
        flag, value = item[0], item[1] if len(item) > 1 else ""
        if isinstance(value, bool):
            if value:
                out.append(flag)
            continue
        if value is None or value == "":
            out.append(flag)
        else:
            out.extend([flag, str(value)])
    return out


def flag_value(flag: str, value: Any) -> list[str]:
    """单个 flag 的展开（供参数校验后使用）。"""
    return build_arg_list([[flag, value]])


# 命令核心参数（由 payload / dataset 直接生成），yaml 参数附加时跳过以免重复
_CORE_FLAGS = {
    "--model", "--tokenizer", "--max-concurrency", "--num-prompts",
    "--random-input-len", "--random-output-len", "--dataset-name",
    "--dataset-path", "--request-rate", "--host", "--port",
    "--base-url", "--endpoint", "--backend", "--sharegpt-output-len",
    "--sharegpt-context-len", "--apply-chat-template",
}


# ---------------------------------------------------------------------------
# 框架参数 yaml 的出厂默认内容（仅用于对比：命令只附加“被修改的参数”）
#   与 benchscope/configs/{framework}-default.yaml 的初始内容保持一致；
#   用户修改保存后，configs 文件变化，但此处出厂值不变，作为差异基线。
# ---------------------------------------------------------------------------
PARAM_YAML_DEFAULTS: dict[str, str] = {
    "vllm": """version: vLLM v0.21.0
backend: openai-chat
endpoint: /v1/chat/completions
trust-remote-code: true
ignore-eos: true
burstiness: 1.0
seed: 0
num-warmups: 0
metric-percentiles: "99"
temperature: 0.0
top-p: 1.0
top-k: -1
min-p: 0.0
frequency-penalty: 0.0
presence-penalty: 0.0
sharegpt-output-len: 128
max-model-len: 32768
gpu-memory-utilization: 0.90
""",
    "sglang": """version: SGLang v0.5.7
backend: openai
endpoint: /v1/chat/completions
trust-remote-code: true
ignore-eos: true
burstiness: 1.0
seed: 1
num-warmups: 0
metric-percentiles: "99"
temperature: 0.0
top-p: 1.0
top-k: -1
min-p: 0.0
frequency-penalty: 0.0
presence-penalty: 0.0
sharegpt-output-len: 128
max-model-len: 32768
mem-fraction-static: 0.90
""",
}


def _parse_yaml_map(content: str | None) -> dict[str, str]:
    """解析 yaml 文本为 {key: value}，跳过注释、空行与 version 行。"""
    out: dict[str, str] = {}
    for ln in (content or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        k, v = k.strip(), v.strip()
        if not k or k == "version":
            continue
        out[k] = v
    return out


def yaml_params_to_args(content: str | None, defaults_map: dict[str, str] | None = None) -> list[str]:
    """将框架默认参数 yaml 文本（每行 key: value）解析为 --key=value 列表。
    跳过注释、空行与 version 行（版本仅展示用，不进入命令）。
    若提供 defaults_map（出厂默认值），只输出“与默认值不同”的参数行——
    即仅把 Step2 中用户修改过的参数附加到测试命令，未修改的默认参数不进入命令。"""
    args: list[str] = []
    for ln in (content or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        k, v = k.strip(), v.strip()
        if not k or k == "version":
            continue
        # 差异过滤：与出厂默认一致则跳过（未修改参数不进入命令）
        if defaults_map is not None and defaults_map.get(k) == v:
            continue
        args.append(f"--{k}={v}" if v else f"--{k}")
    return args


def merge_extra_args(payload: dict, extra_args: list | None = None) -> list:
    """合并 payload.extra_args 与 Step2 编辑的引擎参数（engine_params_yaml），
    跳过核心参数与已存在的 flag，避免命令中出现重复参数。

    参数来源优先级：
      1. `engine_params_yaml` —— 当前所选引擎的参数清单（1.0.7 起，随引擎切换）
      2. `params_yaml[framework]` —— 旧版按框架保存的参数（向后兼容）
    """
    framework = payload.get("framework", "vllm")
    extra = list(extra_args if extra_args is not None else (payload.get("extra_args") or []))
    used = set()
    for item in extra:
        if isinstance(item, str):
            used.add(item.split("=", 1)[0])
        elif isinstance(item, dict):
            used.add(item.get("flag", ""))
    py = payload.get("engine_params_yaml") or (payload.get("params_yaml") or {}).get(framework)
    if py:
        defaults_map = _parse_yaml_map(PARAM_YAML_DEFAULTS.get(framework))
        for a in yaml_params_to_args(py, defaults_map):
            key = a.split("=", 1)[0]
            if key in _CORE_FLAGS or key in used:
                continue
            extra.append(a)
            used.add(key)
    return extra


def normalize_extra_args(extra_args: list | None) -> list[list]:
    """将 extra_args 统一为 [[flag, value]] 形式，供 build_command 追加。
    兼容两种来源：字符串（"--temperature=0.7" / "--flag"）与 dict（{"flag","value"}）。"""
    out: list[list] = []
    for item in extra_args or []:
        if isinstance(item, str):
            s = item.strip()
            if not s:
                continue
            if "=" in s:
                flag, value = s.split("=", 1)
                out.append([flag, value])
            else:
                out.append([s, ""])
        elif isinstance(item, dict):
            flag = (item.get("flag") or "").strip()
            if not flag:
                continue
            out.append([flag, item.get("value", "")])
    return out
