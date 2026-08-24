"""bench 子进程流式执行器。

支持真实执行（vllm/sglang CLI）与 FAKE 模式（BENCHSCOPE_FAKE_BENCH=1，
生成仿真输出，便于无 vllm/sglang 环境下联调 UI 全流程）。
"""
from __future__ import annotations

import logging
import math
import os
import random
import shlex
import subprocess
import sys
import threading
import time
from typing import Callable, Optional

from benchscope.parser import parse_metrics

log = logging.getLogger("benchscope.runner")

StreamCallback = Callable[[str], None]  # 每行输出回调


class StopRequested(RuntimeError):
    """测试被人为停止。"""


class BenchRunner:
    def __init__(self, command_template: str | None = None):
        """command_template 形如 "vllm bench serve" / "python -m sglang.bench_serving"。"""
        self.command_template = command_template or "vllm bench serve"
        self._proc: Optional[subprocess.Popen] = None
        self._stop_flag = threading.Event()

    def kill(self) -> None:
        """终止当前执行的子进程（用于停止测试）。"""
        self._stop_flag.set()
        proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    # ------------------------------------------------------------------
    def run(
        self,
        cmd: list[str],
        stream_cb: Optional[StreamCallback] = None,
        timeout: float | None = None,
    ) -> dict:
        """执行命令，返回 parse_metrics 结果（含 raw）。失败抛 RuntimeError。"""
        self._stop_flag.clear()
        if os.environ.get("BENCHSCOPE_FAKE_BENCH") == "1":
            return self._run_fake(cmd, stream_cb)

        # 用模板指定的可执行文件替换命令头部（vllm / python -m sglang...）
        full_cmd = self._resolve(cmd)
        log.info("执行命令: %s", " ".join(full_cmd))
        if stream_cb:
            stream_cb("$ " + " ".join(full_cmd) + "\n")

        try:
            proc = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self._proc = proc
        except FileNotFoundError as e:
            raise RuntimeError(
                f"未找到命令执行环境：{full_cmd[0]}。请确认已安装 "
                f"{self.command_template.split()[0]} 相关 CLI（并在服务设置中配置 bench 命令）。"
            ) from e

        chunks: list[str] = []
        start = time.time()
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                chunks.append(line)
                if stream_cb:
                    stream_cb(line)
                if timeout and time.time() - start > timeout:
                    proc.kill()
                    raise RuntimeError(f"bench 执行超时（>{timeout}s）")
            proc.wait()
        except KeyboardInterrupt:
            proc.kill()
            raise
        finally:
            self._proc = None
        if proc.returncode != 0:
            output = "".join(chunks)
            if proc.returncode == -9 or proc.returncode == 137:
                raise StopRequested("测试已被停止")
            raise RuntimeError(
                f"bench 命令执行失败（返回码 {proc.returncode}）。\n完整日志：\n{output[-4000:]}"
            )
        output = "".join(chunks)
        metrics = parse_metrics(output)
        if "output_mean" not in metrics:
            raise RuntimeError(f"未能从 bench 输出解析出指标，输出如下：\n{output[-3000:]}")
        return metrics

    # ------------------------------------------------------------------
    def _resolve(self, cmd: list[str]) -> list[str]:
        """把命令头替换为模板指定的执行方式。"""
        tmpl = shlex.split(self.command_template)
        # 保留原始参数（从模板之后开始）
        return tmpl + cmd[len(tmpl):] if cmd[:len(tmpl)] == tmpl else tmpl + cmd

    # ------------------------------------------------------------------
    # FAKE 模式：生成仿真 vllm 风格输出
    def _run_fake(self, cmd: list[str], stream_cb: Optional[StreamCallback] = None) -> dict:
        args = " ".join(cmd)
        concurrency = 1
        input_len, output_len = 1024, 1024
        for i, tok in enumerate(cmd):
            if tok == "--max-concurrency" and i + 1 < len(cmd):
                concurrency = int(cmd[i + 1])
            if tok == "--random-input-len" and i + 1 < len(cmd):
                input_len = int(cmd[i + 1])
            if tok == "--random-output-len" and i + 1 < len(cmd):
                output_len = int(cmd[i + 1])
        rng = random.Random(int(time.time() * 1000) % 2**31)

        c = max(concurrency, 1)
        out_tps = round(50 * c**0.62 * rng.uniform(0.95, 1.05), 2)
        total = round(out_tps * (input_len + output_len) / output_len, 2)
        ttft = round(60 + 9 * c + rng.uniform(0, 20), 2)
        tpot = round(18 + 0.55 * c + rng.uniform(0, 3), 2)
        itl = round(tpot * rng.uniform(0.97, 1.02), 2)

        lines = [
            "============ Serving Benchmark Result ============",
            "Successful requests:                     %d" % c,
            "Failed requests:                         0",
            "Maximum request concurrency:             %d" % c,
            "Benchmark duration (s):                  %.2f" % rng.uniform(5, 40),
            "Total input tokens:                      %d" % (input_len * c),
            "Total generated tokens:                  %d" % (output_len * c),
            "Request throughput (req/s):              %.2f" % rng.uniform(0.1, c),
            "Output token throughput (tok/s):         %s" % out_tps,
            "Peak output token throughput (tok/s):    %s" % round(out_tps * 1.02, 2),
            "Peak concurrent requests:                %.2f" % c,
            "Total token throughput (tok/s):          %s" % total,
            "---------------Time to First Token----------------",
            "Mean TTFT (ms):                          %s" % ttft,
            "Median TTFT (ms):                        %s" % round(ttft * 0.98, 2),
            "P99 TTFT (ms):                           %s" % round(ttft * rng.uniform(1.05, 1.3), 2),
            "-----Time per Output Token (excl. 1st token)------",
            "Mean TPOT (ms):                          %s" % tpot,
            "Median TPOT (ms):                        %s" % round(tpot * 0.97, 2),
            "P99 TPOT (ms):                           %s" % round(tpot * rng.uniform(1.06, 1.35), 2),
            "---------------Inter-token Latency----------------",
            "Mean ITL (ms):                           %s" % itl,
            "Median ITL (ms):                         %s" % round(itl * 0.97, 2),
            "P99 ITL (ms):                            %s" % round(itl * rng.uniform(1.05, 1.3), 2),
            "==================================================",
            "",
        ]
        output = "\n".join(lines)
        # 模拟耗时（可被 kill 中断）
        total_sleep = min(0.6, 0.2 + c * 0.01)
        slept = 0.0
        while slept < total_sleep:
            if self._stop_flag.is_set():
                raise StopRequested("测试已被停止")
            time.sleep(0.05)
            slept += 0.05
        if self._stop_flag.is_set():
            raise StopRequested("测试已被停止")
        if stream_cb:
            stream_cb(f"$ {args}\n")
            for ln in lines:
                stream_cb(ln + "\n")
        metrics = parse_metrics(output)
        return metrics
