"""benchscope 命令行入口。"""
from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
import threading
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="benchscope",
        description="LLM inference performance testing tool. Supports vLLM, SGLang, and any OpenAI-compatible API.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=8080, help="监听端口（默认 8080）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--debug", action="store_true", help="开启调试日志")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

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


if __name__ == "__main__":
    sys.exit(main())
