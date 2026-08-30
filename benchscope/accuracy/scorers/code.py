"""代码判分器（HumanEval / MBPP）：代码抽取 + 受限子进程沙箱执行 + pass@1。

沙箱约束（安全边界，见 docs/rules/AccuracyEngine.md §判分流水线）：
  - 独立子进程执行（``sys.executable -I``：isolated 模式，忽略用户环境与脚本目录）
  - 临时目录作为 cwd 与程序文件位置，执行后清理
  - 超时强杀（默认 10s / 样本）；stdin 关闭；输出捕获上限
指标：pass@1（全部用例通过）、compile_rate（语法可编译比例）、case_pass_rate（用例通过比例）。
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .base import (
    STATUS_CORRECT,
    STATUS_INVALID,
    STATUS_WRONG,
    TAG_EXEC,
    TAG_FORMAT,
    Scorer,
    clean_output,
    scorer_result,
)

DEFAULT_TIMEOUT = 10.0
_FENCE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_code(output: str) -> str:
    """抽取模型输出的 Python 代码：优先最后一个 ```python 围栏，否则按原始输出。"""
    text = clean_output(output)
    if not text:
        return ""
    blocks = _FENCE_RE.findall(text)
    if blocks:
        return blocks[-1].strip("\n")
    # 无围栏：若输出像代码（含 def/import 且无中文解释行占多数），原样返回
    return text.strip("\n")


def compiles(code: str) -> bool:
    """语法可编译检查（compile_rate）。"""
    if not code.strip():
        return False
    try:
        compile(code, "<eval-sample>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


def run_program(program: str, timeout: float = DEFAULT_TIMEOUT) -> tuple[bool, str]:
    """受限子进程执行程序：返回 (是否通过, 错误信息)。

    - `sys.executable -I`（isolated）：不加载用户 site / 环境变量注入最小
    - cwd 为临时目录，程序写临时文件执行后清理；超时 kill
    """
    if not program.strip():
        return False, "空程序"
    with tempfile.TemporaryDirectory(prefix="benchscope-eval-") as tmp:
        prog = Path(tmp) / "sample_program.py"
        prog.write_text(program, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(prog.name)],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return False, f"执行超时（>{timeout:g}s）"
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"
        if proc.returncode == 0:
            return True, ""
        err = (proc.stderr or proc.stdout or "").strip()
        return False, err.splitlines()[-1][:300] if err else f"exit={proc.returncode}"


def build_program(sample: dict, code: str) -> str:
    """拼装可执行程序：HumanEval（prompt+completion+test+check） / MBPP（code+test_list）。"""
    if sample.get("prompt") is not None and sample.get("test"):
        # HumanEval：补全 prompt + 抽取代码 + 官方 test + check(entry_point)
        entry = sample.get("entry_point") or "candidate"
        return f"{sample['prompt']}{code}\n{sample['test']}\ncheck({entry})\n"
    tests = "\n".join(sample.get("test_list") or [])
    return f"{code}\n{tests}\n" if tests else code


class CodeScorer(Scorer):
    """代码判分：pass@1 / 编译通过率 / 用例通过率；错因区分执行错误 / 输出格式错误。"""

    name = "code"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def score(self, sample: dict, output: str) -> dict:
        code = extract_code(output)
        if not code.strip():
            return scorer_result(None, STATUS_INVALID, TAG_FORMAT, "输出中没有可执行的代码")
        if not compiles(code):
            return scorer_result(code, STATUS_WRONG, TAG_EXEC, "代码语法错误（编译失败）")
        program = build_program(sample, code)
        ok, err = run_program(program, timeout=self.timeout)
        if ok:
            return scorer_result(code, STATUS_CORRECT, "", "")
        if "执行超时" in err:
            return scorer_result(code, STATUS_WRONG, TAG_EXEC, err)
        return scorer_result(code, STATUS_WRONG, TAG_EXEC, err or "用例未全部通过")
