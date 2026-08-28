"""内置 bench 引擎注册表：读取 configs/benchs.yaml，提供引擎清单与环境校验。

引擎三类：
  - builtin：自研引擎（benchscope），无需本地框架环境，进程内异步压测
  - vllm   ：vLLM 原生 bench（vllm bench serve），按版本管理，需 torch + vllm
  - sglang ：SGLang 原生 bench（sglang.bench_serving），按版本管理，需 torch + sglang

用户扩展：在 configs/benchs.yaml 追加 engines 条目即可新增引擎/版本（yaml 驱动）。
"""
from __future__ import annotations

import logging
import re
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger("benchscope.benchs")

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
BENCHS_YAML = CONFIGS_DIR / "benchs.yaml"

# 版本比较：轻量实现，避免新增 packaging 依赖
_VER_RE = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(.*)$")


def _parse_version(v: str) -> tuple:
    """将版本字符串解析为可比较元组（忽略后缀如 rc1 / dev0）。"""
    m = _VER_RE.match((v or "").strip())
    if not m:
        return (0, 0, 0)
    major, minor, patch = m.group(1), m.group(2), m.group(3)
    return (int(major or 0), int(minor or 0), int(patch or 0))


def _installed_version(pkg: str) -> Optional[str]:
    """已安装包的版本，未安装返回 None。"""
    try:
        return _pkg_version(pkg)
    except PackageNotFoundError:
        return None
    except Exception:
        return None


def _match_spec(installed: Optional[str], spec: str) -> bool:
    """判断已安装版本是否满足版本范围。

    支持语法：>=x, >x, <=x, <x, ==x, !=x（逗号分隔表示需同时满足）；
    版本按主次修订号数值比较，忽略 rc/dev 等后缀（与 pip 宽松语义一致，满足引擎校验场景）。
    """
    if not spec:
        return installed is not None
    if installed is None:
        return False
    ins = _parse_version(installed)
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(>=|<=|==|!=|>|<)?\s*(.+)$", part)
        if not m:
            continue
        op, want = m.group(1) or "==", m.group(2).strip()
        target = _parse_version(want)
        if op == ">=" and not ins >= target:
            return False
        if op == ">" and not ins > target:
            return False
        if op == "<=" and not ins <= target:
            return False
        if op == "<" and not ins < target:
            return False
        if op == "==" and ins != target:
            return False
        if op == "!=" and ins == target:
            return False
    return True


def load_bench_engines() -> list[dict]:
    """读取内置引擎定义（configs/benchs.yaml）。"""
    if not BENCHS_YAML.exists():
        log.warning("benchs.yaml 不存在: %s", BENCHS_YAML)
        return []
    try:
        data = yaml.safe_load(BENCHS_YAML.read_text(encoding="utf-8"))
        engines = data.get("engines", []) if isinstance(data, dict) else []
        return [e for e in engines if isinstance(e, dict) and e.get("id")]
    except Exception:
        log.exception("解析 benchs.yaml 失败")
        return []


def load_comparison() -> list[dict]:
    """读取引擎对比表定义。"""
    if not BENCHS_YAML.exists():
        return []
    try:
        data = yaml.safe_load(BENCHS_YAML.read_text(encoding="utf-8"))
        items = data.get("comparison", []) if isinstance(data, dict) else []
        return [c for c in items if isinstance(c, dict) and c.get("dimension")]
    except Exception:
        log.exception("解析 benchs.yaml（comparison）失败")
        return []


def get_engine(engine_id: str) -> Optional[dict]:
    """按 id 获取引擎定义。"""
    for e in load_bench_engines():
        if e.get("id") == engine_id:
            return e
    return None


def default_engine_id() -> str:
    """默认引擎：优先自研引擎（无环境依赖），否则第一个可用引擎。"""
    engines = load_bench_engines()
    if not engines:
        return "benchscope"
    for e in engines:
        if e.get("kind") == "builtin":
            return e["id"]
    return engines[0]["id"]


def check_env(engine: dict) -> dict:
    """校验引擎的环境要求。

    返回 {ok, checks: [{name, required, installed, ok, hint}]}：
      - builtin 引擎无 requires，恒 ok=True（不依赖本地框架环境）
      - vllm / sglang 原生引擎：校验 torch 与目标框架安装版本，任一不满足 ok=False
    """
    requires = engine.get("requires") or []
    checks: list[dict] = []
    ok = True
    for req in requires:
        if not isinstance(req, dict):
            continue
        name = req.get("name", "")
        spec = req.get("spec", "")
        hint = req.get("hint", "")
        installed = _installed_version(name)
        passed = _match_spec(installed, spec)
        if not passed:
            ok = False
        checks.append({
            "name": name,
            "required": spec or "any",
            "installed": installed,
            "ok": passed,
            "hint": "" if passed else (hint or f"请安装 {name}{spec}"),
        })

    # 原生引擎（有 requires）还需命令行可用：vllm → vllm 可执行文件；sglang → python 模块
    kind = engine.get("kind")
    if kind in ("vllm", "sglang") and ok:
        cli_ok = _check_cli_available(kind)
        if not cli_ok:
            ok = False
        checks.append({
            "name": f"{kind}-cli",
            "required": "命令可执行",
            "installed": "可用" if cli_ok else "不可用",
            "ok": cli_ok,
            "hint": "" if cli_ok else f"未检测到 {kind} 可执行命令，请检查安装与环境（PATH）",
        })

    return {"ok": ok, "checks": checks}


def _check_cli_available(kind: str) -> bool:
    """检测原生 bench 命令是否可执行（不实际运行，仅探测存在性）。"""
    import shutil
    import subprocess
    import sys

    try:
        if kind == "vllm":
            return shutil.which("vllm") is not None
        if kind == "sglang":
            code = "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('sglang.bench_serving') else 1)"
            r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=20)
            return r.returncode == 0
    except Exception:
        log.exception("检测 %s 命令可用性失败", kind)
    return False


def engine_summary(engine: dict, with_env: bool = True) -> dict:
    """引擎摘要（供 API 返回）：基础信息 + 可选环境校验结果。"""
    out = {
        "id": engine.get("id"),
        "kind": engine.get("kind"),
        "framework": engine.get("framework"),
        "version": engine.get("version"),
        "name": engine.get("name"),
        "description": (engine.get("description") or "").strip(),
        "highlights": engine.get("highlights") or [],
        "requires": engine.get("requires") or [],
    }
    if with_env:
        out["env"] = check_env(engine)
    return out


def list_engines(with_env: bool = True) -> dict:
    """全部引擎 + 对比表 + 默认引擎。"""
    engines = load_bench_engines()
    return {
        "engines": [engine_summary(e, with_env) for e in engines],
        "comparison": load_comparison(),
        "default_engine_id": default_engine_id(),
    }
