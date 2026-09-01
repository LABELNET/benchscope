"""bench 子进程流式执行器。

使用 bash -c 显式 source 系统 profile 后再执行 bench 命令，
确保子进程拿到完整的系统环境变量（PATH/LD_LIBRARY_PATH/MACA_PATH 等），
彻底解决环境变量继承问题。

支持两种模式：
  1. 真实模式（默认）：subprocess 执行 vllm/sglang CLI，实时推送输出
  2. FAKE 模式（BENCHSCOPE_FAKE_BENCH=1）：生成仿真输出，便于无 vllm/sglang 环境下联调 UI
"""
from __future__ import annotations

import logging
import os
import random
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from benchscope.parser import parse_metrics

log = logging.getLogger("benchscope.runner")

StreamCallback = Callable[[str], None]  # 每行输出回调


def _load_env_from_script(script_path: Path) -> dict[str, str]:
    """解析 shell 脚本中的 export 语句，返回 {key: value} 字典。

    支持：
      export KEY=value
      export KEY="value with spaces"
      export KEY='value'
      export KEY  (仅声明，无值则跳过)
    同时支持 shell 变量引用（如 ${OTHER}、$OTHER），会用已解析的变量展开。
    """
    if not script_path.exists():
        return {}
    result: dict[str, str] = {}
    export_re = re.compile(r'^\s*export\s+(\w+)\s*=\s*(.+?)?\s*$')
    # 先读所有行，处理变量展开时按出现顺序
    raw_lines = []
    try:
        for line in script_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = export_re.match(line)
            if m:
                key = m.group(1)
                val = m.group(2)
                if val is None:
                    continue  # export KEY（无值）跳过
                # 去除引号
                val = val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                raw_lines.append((key, val))
    except Exception:
        log.exception("解析环境脚本失败: %s", script_path)
        return {}

    # 按顺序展开变量（支持 ${VAR} 和 $VAR 引用）
    for key, val in raw_lines:
        def _expand(s: str) -> str:
            # ${VAR} 和 $VAR
            for _ in range(10):  # 最多迭代 10 次防止循环引用
                new = re.sub(
                    r'\$\{(\w+)\}|\$(\w+)',
                    lambda m: result.get(m.group(1) or m.group(2), ''),
                    s,
                )
                if new == s:
                    break
                s = new
            return s
        result[key] = _expand(val)

    return result


def _find_and_load_maca_env() -> dict[str, str]:
    """自动查找项目内的 metax/maca 初始化脚本并解析环境变量。

    查找顺序：
      1. 当前工作目录的 scripts/maca.sh
      2. benchscope 包所在目录的 ../scripts/maca.sh
      3. 常见路径 /opt/maca/env.sh
    """
    candidates = [
        Path.cwd() / "scripts" / "maca.sh",
        Path(__file__).resolve().parent.parent / "scripts" / "maca.sh",
        Path("/opt/maca/env.sh"),
        Path("/opt/maca/bin/maca_env.sh"),
    ]
    for candidate in candidates:
        if candidate.exists():
            env = _load_env_from_script(candidate)
            if env:
                log.info("从 %s 加载了 %d 个环境变量", candidate, len(env))
                return env
    return {}


class StopRequested(RuntimeError):
    """测试被人为停止。"""


class BenchRunner:
    """bench 子进程执行器。

    使用流程：
        runner = BenchRunner(command_template="vllm bench serve")
        metrics = runner.run(cmd, stream_cb=print)  # 阻塞执行并返回指标
    """

    def __init__(self, command_template: str | None = None, run_dir=None):
        """command_template 形如 "vllm bench serve" / "python -m sglang.bench_serving"。"""
        self.command_template = command_template or "vllm bench serve"
        self._proc: Optional[subprocess.Popen] = None
        self._stop_flag = threading.Event()
        # FAKE 模式开关（mocks 环境联调）：True 时不启动真实子进程，
        # 由 mocks/ 生成仿真输出；也可用环境变量 BENCHSCOPE_FAKE_BENCH=1 全局开启
        self.fake = False

    # ------------------------------------------------------------------
    def kill(self) -> None:
        """终止当前执行的子进程组（用于停止测试）。"""
        self._stop_flag.set()
        proc = self._proc
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
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
        shell_init: str = "",
    ) -> dict:
        """执行命令，返回 parse_metrics 结果（含 raw）。失败抛 RuntimeError。

        shell_init：可选，用户自定义的初始化脚本（如 source /opt/maca/env.sh），
        会在执行 bench 命令前在同一个 bash -lic shell 里先执行。
        """
        self._stop_flag.clear()
        if self.fake or os.environ.get("BENCHSCOPE_FAKE_BENCH") == "1":
            return self._run_fake(cmd, stream_cb)

        # 用模板指定的可执行文件替换命令头部
        full_cmd = self._resolve(cmd)
        cmd_str = " ".join(shlex.quote(c) for c in full_cmd)
        log.info("执行命令: %s", cmd_str)
        if stream_cb:
            stream_cb("$ " + cmd_str + "\n")

        # 关键：用最小 env 启动 bash -lic，让它从 profile 重建完整 PATH
        # （如果传 Trae 的 PATH，profile 里的 export PATH 很多是追加/条件判断，
        #  导致 source 后 PATH 仍是残缺的 Trae 版）
        minimal_env = {
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "TERM": os.environ.get("TERM", "xterm-256color"),
            "SHELL": os.environ.get("SHELL", "/bin/bash"),
        }
        # 数据根目录以环境变量形式透传给 bench 子进程（改 Root Dir 后无需重启服务，ConfigManager 已同步 os.environ）
        if os.environ.get("BENCHSCOPE_DATA_DIR"):
            minimal_env["BENCHSCOPE_DATA_DIR"] = os.environ["BENCHSCOPE_DATA_DIR"]
        # 保留 conda 相关环境变量（如果有）
        for key in ("CONDA_EXE", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            if key in os.environ:
                minimal_env[key] = os.environ[key]

        # 自动加载 metax/maca 平台环境变量（从 scripts/maca.sh 等脚本解析）
        maca_env = _find_and_load_maca_env()
        if maca_env:
            # 注入到 Python env（子进程直接继承）
            for k, v in maca_env.items():
                minimal_env[k] = v
            log.info("注入 metax 环境变量: MACA_PATH=%s, PATH 含 maca=%s",
                     maca_env.get("MACA_PATH", "?"),
                     "maca" in maca_env.get("PATH", ""))

        # 同时在 bash 命令里也 source 这些脚本（双重保险）
        auto_source = ""
        if maca_env:
            # 找到实际的 maca.sh 路径并 source
            for candidate in [
                Path.cwd() / "scripts" / "maca.sh",
                Path(__file__).resolve().parent.parent / "scripts" / "maca.sh",
                Path("/opt/maca/env.sh"),
            ]:
                if candidate.exists():
                    auto_source = f"source {candidate} 2>/dev/null; "
                    break

        # 构造完整的 bash -lic 命令：先自动 source maca.sh，再用户自定义 init，再 exec bench
        # bash -lic 会自动 source /etc/profile、~/.bash_profile、~/.bashrc 等
        init_part = f"{shell_init}; " if shell_init else ""
        bash_cmd = f"{auto_source}{init_part}exec {cmd_str}"

        try:
            bash_bin = shutil.which("bash") or "/bin/bash"
            proc = subprocess.Popen(
                [bash_bin, "-lic", bash_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=minimal_env,
                cwd=os.getcwd(),
                preexec_fn=os.setsid,  # 创建新进程组，便于整体杀死
            )
            self._proc = proc
        except FileNotFoundError as e:
            raise RuntimeError(
                f"未找到命令执行环境：{full_cmd[0]}。请确认已安装 "
                f"{self.command_template.split()[0]} 相关 CLI。"
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
        return tmpl + cmd[len(tmpl):] if cmd[:len(tmpl)] == tmpl else tmpl + cmd

    # ------------------------------------------------------------------
    # FAKE 模式：生成仿真 vllm/sglang 风格输出（优先复用 mocks 包，见 mocks/README.md）
    def _run_fake(self, cmd: list[str], stream_cb: Optional[StreamCallback] = None) -> dict:
        args = " ".join(cmd)
        concurrency, input_len, output_len, request_rate = self._fake_args(cmd)
        framework = "sglang" if any("sglang" in t for t in cmd) else "vllm"
        output = self._fake_output(framework, concurrency, input_len, output_len, request_rate)
        lines = output.splitlines()

        # 模拟耗时（可被 kill 中断）
        total_sleep = min(0.6, 0.2 + concurrency * 0.01)
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

    def _fake_args(self, cmd: list[str]) -> tuple:
        """从命令中提取并发度与输入/输出长度（解析不到用默认值）。"""
        concurrency = 1
        input_len, output_len = 1024, 1024
        request_rate = "inf"
        for i, tok in enumerate(cmd):
            if tok == "--max-concurrency" and i + 1 < len(cmd):
                concurrency = int(cmd[i + 1])
            if tok == "--random-input-len" and i + 1 < len(cmd):
                input_len = int(cmd[i + 1])
            if tok == "--random-output-len" and i + 1 < len(cmd):
                output_len = int(cmd[i + 1])
            if tok == "--request-rate" and i + 1 < len(cmd):
                request_rate = cmd[i + 1]
        return concurrency, input_len, output_len, request_rate

    def _fake_output(
        self,
        framework: str,
        concurrency: int,
        input_len: int,
        output_len: int,
        request_rate: str = "inf",
    ) -> str:
        """生成 FAKE 输出文本。

        优先使用项目根目录 mocks/ 包（能区分 vLLM / SGLang 两种输出格式）；
        若 mocks 包不可导入（例如 pip 独立安装、无源码目录），回退到内置的
        vLLM 风格简化生成器，保证两种场景行为一致。
        """
        try:
            from mocks.bench_outputs import generate_output

            return generate_output(
                framework,
                concurrency=concurrency,
                input_len=input_len,
                output_len=output_len,
                request_rate=request_rate,
                seed=int(time.time() * 1000) % 2**31,
            )
        except Exception:
            log.warning("mocks.bench_outputs 不可用，回退到内置仿真输出", exc_info=True)
            return "\n".join(self._fake_lines_vllm(concurrency, input_len, output_len))

    def _fake_lines_vllm(self, concurrency: int, input_len: int, output_len: int) -> list[str]:
        """内置 vLLM 风格仿真输出（mocks 包不可用时的兜底）。"""
        rng = random.Random(int(time.time() * 1000) % 2**31)

        c = max(concurrency, 1)
        out_tps = round(50 * c**0.62 * rng.uniform(0.95, 1.05), 2)
        total = round(out_tps * (input_len + output_len) / output_len, 2)
        ttft = round(60 + 9 * c + rng.uniform(0, 20), 2)
        tpot = round(18 + 0.55 * c + rng.uniform(0, 3), 2)
        itl = round(tpot * rng.uniform(0.97, 1.02), 2)

        return [
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
