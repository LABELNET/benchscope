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
    """执行 Bench CLI（自研引擎）压测——与创建任务页 Step3 预览命令一致。

    - `--mode concurrency`（默认）：单并发压测一次。
    - `--mode threshold`：从 1 并发起以 2 的次方递增，找到满足阈值（TTFT/TPOT/吞吐）
      的最大并发（二分收敛），输出 best_concurrency。
    结果会写入终端日志（perf_<run_id>_*.log）并落盘 run.json，便于打包导入 Datas/perfs。
    """
    from benchscope.benches.builtin_bench import (
        BUILTIN_PARAM_DEFAULTS,
        build_options,
        build_command,
        run_builtin_bench,
    )

    base_params = dict(BUILTIN_PARAM_DEFAULTS)
    base_params.update({
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

    def make_opts(concurrency: int):
        return build_options(
            base_params,
            base_url=args.base_url,
            model=args.model,
            dataset=dataset,
            concurrency=concurrency,
            api_key=args.api_key,
        )

    def run_one(concurrency: int) -> dict:
        opts = make_opts(concurrency)
        print(" ".join(build_command(opts, args.engine)), flush=True)
        metrics = run_builtin_bench(opts, stream_cb=lambda line: print(line, end=""))
        print()
        return metrics

    if getattr(args, "mode", "concurrency") == "threshold":
        return _perf_threshold(args, run_one)

    metrics = run_one(args.concurrency)
    print("-" * 56)
    print(f"successful_requests : {metrics.get('successful_requests')}")
    print(f"failed_requests     : {metrics.get('failed_requests')}")
    print(f"benchmark_duration  : {metrics.get('benchmark_duration')}")
    print(f"output_mean (tok/s) : {metrics.get('output_mean')}")
    print(f"total_mean  (tok/s) : {metrics.get('total_mean')}")
    print(f"ttft_mean   (ms)    : {metrics.get('ttft_mean')}")
    print(f"tpot_mean   (ms)    : {metrics.get('tpot_mean')}")
    print(f"itl_mean    (ms)    : {metrics.get('itl_mean')}")
    # 保存 run.json + 终端日志（供打包导入 Datas/perfs）
    _save_perf_artifacts(args, mode="concurrency", rows={args.concurrency: metrics})
    return 0 if metrics.get("successful_requests") else 1


def _perf_threshold(args, run_one) -> int:
    """阈值模式：2 的幂递增 + 二分，找满足阈值的最大并发。"""
    ttft_thr = args.ttft_threshold_ms
    tpot_thr = args.tpot_threshold_ms
    out_thr = args.output_threshold
    search_cap = args.max_concurrency_search
    max_requests = args.max_requests

    def violated(m) -> bool:
        if ttft_thr > 0 and m.get("ttft_mean") is not None and float(m["ttft_mean"]) > ttft_thr:
            return True
        if tpot_thr > 0 and m.get("tpot_mean") is not None and float(m["tpot_mean"]) > tpot_thr:
            return True
        if out_thr > 0 and m.get("output_mean") is not None and float(m["output_mean"]) < out_thr:
            return True
        return False

    results: dict[int, dict] = {}

    def test(conc: int) -> dict:
        conc = int(conc)
        if conc in results:
            return results[conc]
        # 强制结束：并发数超过 max_requests 上限
        if conc > max_requests:
            return {"forced_finish": True, "concurrency": conc, "metrics": {}}
        m = run_one(conc)
        results[conc] = m
        return m

    # 从 1 并发以 2 的幂递增，找第一个不满足的 hi
    lo = 1
    m1 = test(1)
    if not m1.get("successful_requests"):
        print("❌ 1 并发压测失败（successful_requests=0），无法继续阈值搜索")
        return 1
    if violated(m1):
        best = 1
        print(f"best_concurrency : {best}（1 并发即不满足阈值）")
    else:
        # 找 hi
        hi = None
        k = 1
        while True:
            conc = 2 ** k
            if conc > search_cap:
                hi = search_cap
                break
            m = test(conc)
            if m.get("forced_finish"):
                hi = conc
                break
            if not m.get("successful_requests"):
                hi = conc
                break
            if violated(m):
                hi = conc
                break
            k += 1
        if hi is None:
            hi = search_cap
        # 若 hi 仍满足（达上限），最佳=上限
        if not violated(results.get(hi, {})) and hi not in results:
            m_hi = test(hi)
            if m_hi.get("forced_finish") or violated(m_hi):
                hi = search_cap if not results.get(hi) else hi
        # 二分 (lo, hi]，lo 满足阈值
        while hi - lo > 1:
            mid = (lo + hi) // 2
            m = test(mid)
            if m.get("forced_finish"):
                hi = mid
            elif not m.get("successful_requests") or violated(m):
                hi = mid
            else:
                lo = mid
        best = lo

    print("-" * 56)
    print("threshold 探测结果（concurrency -> output/total/ttft/tpot）：")
    for conc in sorted(results):
        m = results[conc]
        if not m.get("successful_requests"):
            print(f"  conc={conc}: FAILED")
            continue
        print(f"  conc={conc}: out={m.get('output_mean')} tot={m.get('total_mean')} "
              f"ttft={m.get('ttft_mean')} tpot={m.get('tpot_mean')}")
    print("-" * 56)
    print(f"best_concurrency : {best}（满足阈值的最大并发）")
    _save_perf_artifacts(args, mode="threshold", rows=results, best_concurrency=best)
    return 0


def _save_perf_artifacts(args, mode: str, rows: dict, best_concurrency: int | None = None) -> None:
    """把本次运行写为 run.json + 终端日志，供打包导入 Datas/perfs。"""
    import json
    import time
    from pathlib import Path

    from benchscope.config import ConfigManager
    try:
        cfg = ConfigManager()
        run_dir = Path(cfg.perfs_dir)
        logs_dir = Path(cfg.logs_dir)
    except Exception:
        run_dir = Path.cwd() / "perfs"
        logs_dir = Path.cwd() / "logs"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d%H%M%S")
    run_id = f"perf_{args.model.replace('/', '_')}_{stamp}"
    summary = {}
    for conc, m in rows.items():
        if not m.get("successful_requests"):
            continue
        summary[conc] = {
            "output_mean": m.get("output_mean"),
            "total_mean": m.get("total_mean"),
            "ttft_mean": m.get("ttft_mean"),
            "tpot_mean": m.get("tpot_mean"),
            "itl_mean": m.get("itl_mean"),
        }
    run_info = {
        "task_id": run_id,
        "run_id": run_id,
        "kind": "perf",
        "framework": "benchscope",
        "model": args.model,
        "mode": mode,
        "status": "done",
        "concurrency_list": list(rows.keys()),
        "best_concurrency": best_concurrency,
        "summary": summary,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (run_dir / "run.json").write_text(
        json.dumps(run_info, ensure_ascii=False, indent=2), encoding="utf-8")
    log_file = logs_dir / f"perf_{run_id}.log"
    log_file.touch()
    print(f"已保存 run.json: {run_dir / 'run.json'}")
    print(f"已生成日志占位: {log_file}（打包时请将终端输出写入 perf_{run_id}_*.log）")


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
    p.add_argument("--mode", default="concurrency", choices=["concurrency", "threshold"],
                   help="压测模式：concurrency（单并发） / threshold（阈值搜索找最佳并发）")
    p.add_argument("--concurrency", type=int, default=1, help="并发数（concurrency 模式）")
    p.add_argument("--num-prompts", type=int, default=0, help="请求总数（0 = 跟随并发数）")
    p.add_argument("--input-len", type=int, default=1024, help="输入 token 数")
    p.add_argument("--output-len", type=int, default=1024, help="输出 token 数")
    p.add_argument("--request-rate", default="inf", help="请求速率（req/s，inf 表示不限速）")
    p.add_argument("--num-warmups", type=int, default=0, help="预热请求数（不计入指标）")
    p.add_argument("--chars-per-token", type=float, default=4.0, help="字符 / token 近似比")
    p.add_argument("--timeout", type=float, default=600.0, help="单请求超时（秒）")
    p.add_argument("--temperature", type=float, default=0.0, help="采样温度")
    p.add_argument("--seed", type=int, default=0, help="随机种子（0 = 不固定）")
    # threshold 模式专属参数
    p.add_argument("--ttft-threshold-ms", type=float, default=0.0,
                   help="TTFT 阈值（ms），0 = 不判定")
    p.add_argument("--tpot-threshold-ms", type=float, default=100.0,
                   help="TPOT 阈值（ms），0 = 不判定")
    p.add_argument("--output-threshold", type=float, default=0.0,
                   help="输出吞吐阈值（tok/s），低于该值判为不满足，0 = 不判定")
    p.add_argument("--max-concurrency-search", type=int, default=4096,
                   help="阈值搜索上限：达到仍满足阈值则取上限为最佳并发")
    p.add_argument("--max-requests", type=int, default=4096,
                   help="阈值探测中并发数超过该上限则强制结束")


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
