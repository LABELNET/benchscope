"""vLLM `vllm bench serve` 命令构建。"""
from __future__ import annotations

import urllib.parse

from benchscope.benches.base import BenchOptions, ParamDef, build_arg_list, normalize_extra_args

FRAMEWORK = "vllm"

# 常用参数表单（前端按此渲染，勾选/填写的值会合并进 extra_args）
CURATED_PARAMS: list[ParamDef] = [
    ParamDef("backend", "--backend", "后端 Backend", "openai-chat / openai 等", "select",
             default="openai-chat", options=["openai-chat", "openai"]),
    ParamDef("endpoint", "--endpoint", "接口 Endpoint", "默认 /v1/chat/completions", "str",
             default="/v1/chat/completions"),
    ParamDef("trust_remote_code", "--trust-remote-code", "trust-remote-code", "", "bool", default=True),
    ParamDef("ignore_eos", "--ignore-eos", "忽略 EOS ignore-eos", "", "bool", default=True),
    ParamDef("burstiness", "--burstiness", "突发因子 Burstiness", "请求到达的突发程度", "float", default=1.0),
    ParamDef("seed", "--seed", "随机种子 Seed", "", "int", default=0),
    ParamDef("num_warmups", "--num-warmups", "预热请求数 Warmups", "", "int", default=0),
    ParamDef("metric_percentiles", "--metric-percentiles", "百分位 Percentiles", "如 99", "str", default="99"),
    ParamDef("temperature", "--temperature", "采样温度 Temperature", "", "float", default=0.0),
    ParamDef("top_p", "--top-p", "top-p", "", "float", default=1.0),
    ParamDef("top_k", "--top-k", "top-k", "", "int", default=-1),
    ParamDef("min_p", "--min-p", "min-p", "", "float", default=0.0),
    ParamDef("frequency_penalty", "--frequency-penalty", "频率惩罚", "", "float", default=0.0),
    ParamDef("presence_penalty", "--presence-penalty", "存在惩罚", "", "float", default=0.0),
    ParamDef("sharegpt_output_len", "--sharegpt-output-len", "ShareGPT 输出长度", "sharegpt 数据集平均输出 token 数", "int", default=128, advanced=True),
    ParamDef("no_stream", "--no-stream", "禁用流式输出", "", "bool", default=False, advanced=True),
    ParamDef("disable_tqdm", "--disable-tqdm", "禁用进度条", "", "bool", default=False, advanced=True),
    ParamDef("save_result", "--save-result", "保存结果 save-result", "保存详细结果文件", "bool", default=False, advanced=True),
    ParamDef("profile", "--profile", "性能剖析 profile", "", "bool", default=False, advanced=True),
]

_CORE_KEYS = {"model", "tokenizer", "max-concurrency", "num-prompts",
              "random-input-len", "random-output-len", "dataset-name",
              "dataset-path", "request-rate", "host", "port", "endpoint"}


def build_command(opts: BenchOptions) -> list[str]:
    """构建 vllm bench serve 命令。"""
    api = opts.api
    ds = opts.dataset
    base_url = api.get("base_url") or ""
    parsed = urllib.parse.urlparse(base_url)
    host = api.get("host") or parsed.hostname or "127.0.0.1"
    port = api.get("port") or parsed.port or "8000"

    base = ["vllm", "bench", "serve"]
    flags: list[list] = [
        ["--max-concurrency", opts.concurrency],
        ["--num-prompts", opts.concurrency],
        ["--model", opts.model],
        ["--tokenizer", opts.tokenizer if opts.tokenizer else opts.model],
        ["--host", host],
        ["--port", port],
        ["--request-rate", str(opts.request_rate)],
    ]

    if ds.get("type") in ("sharegpt", "custom"):
        flags.append(["--dataset-name", "sharegpt"])
        if ds.get("path"):
            flags.append(["--dataset-path", ds["path"]])
        if ds.get("sharegpt_output_len"):
            flags.append(["--sharegpt-output-len", ds["sharegpt_output_len"]])
    else:
        flags.append(["--dataset-name", "random"])
        flags.append(["--random-input-len", ds.get("input_len", 1024)])
        flags.append(["--random-output-len", ds.get("output_len", 1024)])

    # 表单单选参数（curated），已存在于核心参数中的跳过
    used = set()
    for f in flags:
        used.add(f[0])
    for item in _expand_curated(opts):
        if item[0] not in used:
            flags.append(item)
            used.add(item[0])

    # Step2 编辑的 yaml / extra_args 参数（跳过已存在的 flag 避免重复）
    for item in normalize_extra_args(opts.extra_args):
        if item[0] not in used:
            flags.append(item)
            used.add(item[0])

    return base + build_arg_list(flags)


def _expand_curated(opts: BenchOptions) -> list[list]:
    """将 curated 表单值展开为 flag 列表。"""
    out: list[list] = []
    for key, value in opts.curated.items():
        if value is None or value == "" or value is False:
            continue
        param = next((p for p in CURATED_PARAMS if p.key == key), None)
        flag = param.flag if param else f"--{key.replace('_', '-')}"
        if param and param.type == "bool" and value is True:
            out.append([flag, ""])
        else:
            out.append([flag, value])
    return out
