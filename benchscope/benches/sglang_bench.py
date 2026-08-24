"""SGLang `python -m sglang.bench_serving` 命令构建。"""
from __future__ import annotations

from benchscope.benches.base import BenchOptions, ParamDef, build_arg_list

FRAMEWORK = "sglang"

CURATED_PARAMS: list[ParamDef] = [
    ParamDef("backend", "--backend", "后端 Backend", "openai / sglang", "select",
             default="openai", options=["openai", "sglang"]),
    ParamDef("apply_chat_template", "--apply-chat-template", "应用聊天模板", "sharegpt/自定义数据集时按模板构造", "bool", default=True),
    ParamDef("disable_ignore_eos", "--disable-ignore-eos", "不忽略 EOS", "开启后不忽略 EOS", "bool", default=False),
    ParamDef("seed", "--seed", "随机种子 Seed", "", "int", default=0),
    ParamDef("warmup_requests", "--warmup-requests", "预热请求数 Warmups", "", "int", default=0),
    ParamDef("tokenize_prompt", "--tokenize-prompt", "预分词 tokenize-prompt", "", "bool", default=True),
    ParamDef("flush_cache", "--flush-cache", "刷新缓存 flush-cache", "每次运行前清空 radix cache", "bool", default=False, advanced=True),
    ParamDef("print_requests", "--print-requests", "打印请求", "", "bool", default=False, advanced=True),
    ParamDef("disable_tqdm", "--disable-tqdm", "禁用进度条", "", "bool", default=False, advanced=True),
    ParamDef("sharegpt_output_len", "--sharegpt-output-len", "ShareGPT 输出长度", "sharegpt 数据集平均输出 token 数", "int", default=128, advanced=True),
    ParamDef("sharegpt_context_len", "--sharegpt-context-len", "ShareGPT 上下文长度", "", "int", default=None, advanced=True),
]

_CORE_KEYS = {"model", "tokenizer", "max-concurrency", "num-prompts",
              "random-input-len", "random-output-len", "dataset-name",
              "dataset-path", "request-rate", "base-url"}


def build_command(opts: BenchOptions) -> list[str]:
    """构建 sglang.bench_serving 命令。"""
    api = opts.api
    ds = opts.dataset
    base_url = api.get("base_url") or f"http://{api.get('host', '127.0.0.1')}:{api.get('port', '8000')}"

    cmd = ["python", "-m", "sglang.bench_serving"]
    flags: list[list] = [
        ["--backend", opts.curated.get("backend", "openai")],
        ["--base-url", base_url],
        ["--model", opts.model],
        ["--tokenizer", opts.tokenizer if opts.tokenizer else opts.model],
        ["--num-prompts", opts.concurrency],
        ["--max-concurrency", opts.concurrency],
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

    used = {f[0] for f in flags}
    for item in _expand_curated(opts):
        if item[0] not in used:
            flags.append(item)

    return cmd + build_arg_list(flags)


def _expand_curated(opts: BenchOptions) -> list[list]:
    out: list[list] = []
    for key, value in opts.curated.items():
        if value is None or value == "" or value is False:
            continue
        param = next((p for p in CURATED_PARAMS if p.key == key), None)
        flag = param.flag if param else f"--{key.replace('_', '-')}"
        if key == "disable_ignore_eos" and value is False:
            continue
        if param and param.type == "bool" and value is True:
            out.append([flag, ""])
        else:
            out.append([flag, value])
    return out
