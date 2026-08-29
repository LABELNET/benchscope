"""benchscope 命令行入口。

子命令：
  benchscope               启动 Web 服务（默认，等价 `benchscope serve`）
  benchscope serve         启动 Web 服务
  benchscope perf         直接执行一次 Bench CLI（自研引擎）压测并打印指标
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading
import webbrowser
from datetime import datetime


def _setup_runtime_logging() -> None:
    """将服务运行日志落盘到 logs 目录：runtime_年月日.log。"""
    try:
        from benchscope.server.state import state

        logs_dir = state.config.logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        rt_file = logs_dir / f"runtime_{datetime.now().strftime('%Y%m%d')}.log"
        fh = logging.FileHandler(rt_file, encoding="utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(fh)
        logging.getLogger("benchscope").info("runtime 日志已落盘: %s", rt_file)
    except Exception:
        logging.getLogger("benchscope").exception("runtime 日志配置失败")


def _serve(args) -> int:
    """启动 Web 服务（前后端统一入口）。"""
    import uvicorn

    from benchscope.server.app import create_app

    app = create_app()
    _setup_runtime_logging()
    url = f"http://127.0.0.1:{args.port}"

    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    print("=" * 56)
    print("  BenchScope - LLM inference performance testing tool")
    print(f"  打开浏览器访问: {url}")
    print("=" * 56)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _perf(args) -> int:
    """执行一次 Bench CLI（自研引擎）压测——与创建任务页 Step3 预览命令一致。"""
    from benchscope.benches.builtin_bench import (
        BUILTIN_PARAM_DEFAULTS,
        build_options,
        build_command,
        run_builtin_bench,
    )

    params = dict(BUILTIN_PARAM_DEFAULTS)
    params.update({
        "backend": args.backend,
        "endpoint": args.endpoint,
        "request-rate": args.request_rate,
        "num-prompts": str(args.num_prompts),
        "num-warmups": str(args.num_warmups),
        "chars-per-token": str(args.chars_per_token),
        "timeout": str(args.timeout),
        "temperature": str(args.temperature),
        "seed": str(args.seed),
    })

    dataset = {"type": "random", "input_len": args.input_len, "output_len": args.output_len}
    opts = build_options(
        params,
        base_url=args.base_url,
        model=args.model,
        dataset=dataset,
        concurrency=args.concurrency,
        api_key=args.api_key,
    )

    print(" ".join(build_command(opts, args.engine)), flush=True)
    metrics = run_builtin_bench(opts, stream_cb=lambda line: print(line, end=""))
    print()
    print("-" * 56)
    print(f"successful_requests : {metrics.get('successful_requests')}")
    print(f"failed_requests     : {metrics.get('failed_requests')}")
    print(f"benchmark_duration  : {metrics.get('benchmark_duration')}")
    print(f"output_mean (tok/s) : {metrics.get('output_mean')}")
    print(f"total_mean  (tok/s) : {metrics.get('total_mean')}")
    print(f"ttft_mean   (ms)    : {metrics.get('ttft_mean')}")
    print(f"tpot_mean   (ms)    : {metrics.get('tpot_mean')}")
    print(f"itl_mean    (ms)    : {metrics.get('itl_mean')}")
    return 0 if metrics.get("successful_requests") else 1


def _add_serve_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    p.add_argument("--port", type=int, default=8080, help="监听端口（默认 8080）")
    p.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")


def _add_perf_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--engine", default="benchscope", help="引擎 id（默认 benchscope）")
    p.add_argument("--model", required=True, help="被测模型名")
    p.add_argument("--base-url", default="http://127.0.0.1:8000", help="被测服务地址")
    p.add_argument("--api-key", default="", help="被测服务 API Key（可选）")
    p.add_argument("--backend", default="openai-chat", help="接口协议：openai-chat / openai")
    p.add_argument("--endpoint", default="/v1/chat/completions", help="接口路径")
    p.add_argument("--concurrency", type=int, default=1, help="并发数")
    p.add_argument("--num-prompts", type=int, default=0, help="请求总数（0 = 跟随并发数）")
    p.add_argument("--input-len", type=int, default=1024, help="输入 token 数")
    p.add_argument("--output-len", type=int, default=1024, help="输出 token 数")
    p.add_argument("--request-rate", default="inf", help="请求速率（req/s，inf 表示不限速）")
    p.add_argument("--num-warmups", type=int, default=0, help="预热请求数（不计入指标）")
    p.add_argument("--chars-per-token", type=float, default=4.0, help="字符 / token 近似比")
    p.add_argument("--timeout", type=float, default=600.0, help="单请求超时（秒）")
    p.add_argument("--temperature", type=float, default=0.0, help="采样温度")
    p.add_argument("--seed", type=int, default=0, help="随机种子（0 = 不固定）")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # 无参数 / 首个参数为选项 → 走旧的「启动服务」行为（向后兼容 `benchscope --port 8080`）
    if not argv or argv[0].startswith("-"):
        parser = argparse.ArgumentParser(
            prog="benchscope",
            description="LLM inference performance testing tool. Supports vLLM, SGLang, and any OpenAI-compatible API.",
        )
        _add_serve_args(parser)
        parser.add_argument("--debug", action="store_true", help="开启调试日志")
        args = parser.parse_args(argv)
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        return _serve(args)

    parser = argparse.ArgumentParser(
        prog="benchscope",
        description="LLM inference performance testing tool. Supports vLLM, SGLang, and any OpenAI-compatible API.",
    )
    sub = parser.add_subparsers(dest="command")

    serve_p = sub.add_parser("serve", help="启动 Web 服务（前后端统一入口）")
    _add_serve_args(serve_p)
    serve_p.add_argument("--debug", action="store_true", help="开启调试日志")

    perf_p = sub.add_parser("perf", help="执行一次 Bench CLI（自研引擎）压测")
    _add_perf_args(perf_p)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "debug", False) else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "perf":
        return _perf(args)
    return _serve(args)


if __name__ == "__main__":
    sys.exit(main())
