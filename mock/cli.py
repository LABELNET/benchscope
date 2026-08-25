"""模拟 vLLM / SGLang bench 命令的独立调试 CLI。

在没有真实 vLLM / SGLang 运行环境时，用本脚本**冒充** ``vllm bench serve`` /
``python -m sglang.bench_serving`` 打印仿真输出，方便联调 UI 与解析逻辑。

用法（两种形式等价，均会解析 bench 参数并输出对应框架的仿真结果）:

.. code-block:: bash

    # vLLM 风格
    python -m mock.cli vllm bench serve --max-concurrency 32 --num-prompts 32 \
        --model Qwen2.5-72B-Instruct --random-input-len 3072 --random-output-len 1024

    # SGLang 风格
    python -m mock.cli python -m sglang.bench_serving --max-concurrency 16 \
        --model Qwen2.5-72B-Instruct --random-input-len 1024 --random-output-len 1024

    # 或显式指定框架
    python -m mock.cli --framework sglang --max-concurrency 8 --seed 42

    # 逐行流式输出（模拟真实 bench 过程，便于观察 UI 实时更新）
    python -m mock.cli vllm bench serve --max-concurrency 64 --stream-interval 0.05

    # 把输出存到文件
    python -m mock.cli vllm bench serve --max-concurrency 32 --save /tmp/mock_vllm.txt

支持的解析参数：``--max-concurrency`` / ``--num-prompts`` / ``--random-input-len`` /
``--random-output-len`` / ``--request-rate`` / ``--seed`` / ``--dataset-name`` /
``--sharegpt-output-len``，以及 mock 专属：``--stream-interval`` / ``--save`` /
``--no-progress`` / ``--framework``。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:  # 作为项目内包运行
    from mock.bench_outputs import generate_output
except ImportError:  # 兜底：mock 文件夹不在 sys.path 时
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from mock.bench_outputs import generate_output  # noqa: E402


# 与真实 bench 一致的参数默认值
DEFAULTS = {
    "max-concurrency": 32,
    "num-prompts": None,   # 默认跟随 max-concurrency
    "random-input-len": 3072,
    "random-output-len": 1024,
    "request-rate": "inf",
    "seed": None,
    "dataset-name": "random",
    "sharegpt-output-len": 128,
}


def _parse_bench_args(argv: list[str]) -> tuple[dict, dict]:
    """从命令行提取 bench 参数（忽略未知参数）与 mock 专属参数。"""
    bench: dict = dict(DEFAULTS)
    mock_opts: dict = {"stream_interval": 0.0, "save": None, "progress": True, "framework": None}

    def grab(target: dict, name: str, convert=str):
        for i, tok in enumerate(argv):
            if tok == f"--{name}" and i + 1 < len(argv):
                try:
                    target[name] = convert(argv[i + 1])
                except ValueError:
                    pass

    for name, conv in (
        ("max-concurrency", int),
        ("num-prompts", int),
        ("random-input-len", int),
        ("random-output-len", int),
        ("request-rate", str),
        ("seed", int),
        ("dataset-name", str),
        ("sharegpt-output-len", int),
    ):
        grab(bench, name, conv)

    grab(mock_opts, "stream-interval", float)
    grab(mock_opts, "save", str)
    grab(mock_opts, "framework", str)

    if "--no-progress" in argv:
        mock_opts["progress"] = False

    if bench.get("dataset-name") in ("sharegpt", "custom") and not bench.get("random-input-len"):
        # sharegpt 数据集没有固定的 input/output len，给一个代表性值
        bench["random-input-len"] = 2048
        bench["random-output-len"] = bench.get("sharegpt-output-len", 128)
    return bench, mock_opts


def _detect_framework(argv: list[str], explicit: str | None) -> str:
    """优先 --framework；其次从命令形态推断（argv 含 sglang 即 sglang）。"""
    if explicit:
        return "sglang" if "sglang" in str(explicit).lower() else "vllm"
    for tok in argv:
        low = tok.lower()
        if "sglang" in low:
            return "sglang"
        if low == "vllm":
            return "vllm"
    return "vllm"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # 独立 help（不带 bench 参数时打印用法）
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0

    bench, mock_opts = _parse_bench_args(argv)
    framework = _detect_framework(argv, mock_opts["framework"])
    num_prompts = bench["num-prompts"] or bench["max-concurrency"]

    output = generate_output(
        framework,
        concurrency=bench["max-concurrency"],
        num_prompts=num_prompts,
        input_len=bench["random-input-len"],
        output_len=bench["random-output-len"],
        request_rate=bench["request-rate"],
        seed=bench["seed"],
        include_progress=mock_opts["progress"],
    )

    if mock_opts["save"]:
        Path(mock_opts["save"]).write_text(output + "\n", encoding="utf-8")
        print(f"[mock] 输出已保存到 {mock_opts['save']}", file=sys.stderr)

    interval = float(mock_opts.get("stream_interval") or 0.0)
    for line in output.splitlines():
        print(line, flush=True)
        if interval > 0:
            time.sleep(interval)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[mock] interrupted", file=sys.stderr)
        sys.exit(130)
