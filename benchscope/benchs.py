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
import tarfile
import tempfile
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger("benchscope.benchs")

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
BENCHS_YAML = CONFIGS_DIR / "benchs.yaml"

# 随包内置的引擎 id（引擎卡边框标色用：内置蓝 / 用户上传自定义紫）。
# 用户通过 Settings → Upload Engine 上传/新增的引擎 id 不在本集内，归为 custom。
BUILTIN_ENGINE_IDS = {"benchscope", "vllm-0.23", "sglang-0.5.10", "native-hf", "mock"}

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


# ---------------------------------------------------------------------------
# 引擎参数清单（每个引擎一套，互不干扰）
#
# 文件：configs/<params_key>-default.yaml
#   - benchscope → benchscope-default.yaml（Bench CLI 自研引擎参数清单）
#   - vllm       → vllm-default.yaml
#   - sglang     → sglang-default.yaml
# 说明：参数说明文案与可选值在 configs/bench-params.yaml 的对应 params_key 段，
#       两者一一对应（default 提供取值，bench-params 提供说明）。
# ---------------------------------------------------------------------------
ENGINE_PARAMS_FILES = {
    "benchscope": "benchscope-default.yaml",
    "vllm": "vllm-default.yaml",
    "sglang": "sglang-default.yaml",
}


def engine_params_path(engine: dict) -> Path:
    """引擎参数清单文件路径（不存在时返回预期路径，由调用方创建）。"""
    key = engine.get("params_key") or engine.get("kind") or engine.get("id") or ""
    return CONFIGS_DIR / (ENGINE_PARAMS_FILES.get(key) or f"{key}-default.yaml")


def parse_params_yaml(content: str) -> tuple[list[dict], str]:
    """逐行解析参数 yaml 为 {key, value}（重复 key 取最后一个），version 单独返回。"""
    lines: list[dict] = []
    version = ""
    seen: dict[str, int] = {}
    for ln in (content or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        k, v = k.strip(), v.strip()
        if k == "version":
            version = v
            continue
        if k in seen:
            lines[seen[k]]["value"] = v
            continue
        seen[k] = len(lines)
        lines.append({"key": k, "value": v})
    return lines, version


def load_engine_params(engine: dict) -> dict:
    """读取引擎参数清单：{engine_id, params_key, version, content, lines}。"""
    path = engine_params_path(engine)
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    lines, version = parse_params_yaml(content)
    return {
        "engine_id": engine.get("id"),
        "params_key": engine.get("params_key") or engine.get("kind") or "",
        "version": version,
        "content": content,
        "lines": lines,
    }


def save_engine_params(engine: dict, content: str) -> dict:
    """保存引擎参数清单（去重后写回），返回最新解析结果。"""
    lines, version = parse_params_yaml(content)
    body = f"version: {version}\n" if version else ""
    body += "\n".join(f"{ln['key']}: {ln['value']}" for ln in lines)
    if body and not body.endswith("\n"):
        body += "\n"
    path = engine_params_path(engine)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return load_engine_params(engine)


def engine_summary(engine: dict, with_env: bool = True) -> dict:
    """引擎摘要（供 API 返回）：基础信息 + 可选环境校验结果。"""
    # 文案双语：默认英文，*_zh 为中文（界面按语言选择；缺失时回退英文）
    out = {
        "id": engine.get("id"),
        "kind": engine.get("kind"),
        "origin": "builtin" if engine.get("id") in BUILTIN_ENGINE_IDS else "custom",
        "framework": engine.get("framework"),
        "version": engine.get("version"),
        "name": engine.get("name"),
        "name_zh": engine.get("name_zh") or engine.get("name"),
        "description": (engine.get("description") or "").strip(),
        "description_zh": (engine.get("description_zh") or engine.get("description") or "").strip(),
        "highlights": engine.get("highlights") or [],
        "highlights_zh": engine.get("highlights_zh") or engine.get("highlights") or [],
        "requires": engine.get("requires") or [],
        "eval": (engine.get("eval") or "").strip().lower(),  # 精度评测能力：serving|native|mock|空
    }
    if with_env:
        out["env"] = check_env(engine)
    return out


def load_benchs_yaml_text() -> str:
    """读取 benchs.yaml 原文（供 Settings 面板查看 / 编辑）。"""
    if not BENCHS_YAML.exists():
        return ""
    return BENCHS_YAML.read_text(encoding="utf-8")


# mock 输出必须包含的指标行（对应 parser.py 的解析正则；缺失会导致指标全 0）
_MOCK_REQUIRED_LINES = (
    "Output token throughput",
    "Serving Benchmark Result",
)


def validate_benchs_yaml(content: str, mock_output: str = "", extra_param_sections: dict = None) -> dict:
    """逐项校验引擎定义，返回 {ok, checks: [{item, ok, message}]}。

    extra_param_sections：随引擎包一起提交、尚未落盘的参数说明段
      （上传场景下需先与现有 bench-params.yaml 合并后再校验 params_key）。

    校验项（与 skills/bench-engine-authoring/references/import-checklist.md 一致）：
      1. yaml         YAML 合法且顶层为对象
      2. engines      engines 为非空列表、每项含 id、id 唯一
      3. kind         kind ∈ {builtin, vllm, sglang}
      4. requires     原生引擎须声明 torch + 框架包且带版本 spec
      5. params_key   引用的键在 configs/bench-params.yaml 中存在
      6. option_desc  参数集中每个 option 必须有非空 description
      7. mock         （可选）mock 输出包含解析器要求的指标行
    """
    checks: list[dict] = []

    def add(item: str, ok: bool, message: str):
        checks.append({"item": item, "ok": ok, "message": message})

    # 1. YAML
    try:
        data = yaml.safe_load(content or "")
    except yaml.YAMLError as e:
        add("yaml", False, f"YAML 格式错误：{e}")
        return {"ok": False, "checks": checks}
    if not isinstance(data, dict):
        add("yaml", False, "配置顶层必须是对象（含 engines / comparison 键）")
        return {"ok": False, "checks": checks}
    add("yaml", True, "YAML 解析通过")

    # 2. engines
    engines = data.get("engines")
    if not isinstance(engines, list) or not engines:
        add("engines", False, "engines 必须是非空列表")
        return {"ok": False, "checks": checks}
    seen: set = set()
    id_ok = True
    for i, e in enumerate(engines):
        if not isinstance(e, dict) or not e.get("id"):
            add("engines", False, f"engines[{i}] 缺少 id 字段")
            id_ok = False
            break
        eid = e["id"]
        if eid in seen:
            add("engines", False, f"engines[{i}] id 重复：{eid}")
            id_ok = False
            break
        seen.add(eid)
    if id_ok:
        add("engines", True, f"{len(engines)} 个引擎（{', '.join(seen)}）")

    # 3. kind
    kinds_ok = True
    for i, e in enumerate(engines):
        if not isinstance(e, dict):
            continue
        if e.get("kind") not in ("builtin", "vllm", "sglang", "native", "mock"):
            add("kind", False,
                f"engines[{i}]（{e.get('id')}）的 kind 必须是 builtin / vllm / sglang / native / mock")
            kinds_ok = False
            break
    if kinds_ok:
        add("kind", True, "kind 合法")

    # 4. requires（原生引擎：vllm/sglang 需 torch+框架；native 需 torch+transformers；mock/builtin 无）
    req_ok = True
    for i, e in enumerate(engines):
        if not isinstance(e, dict):
            continue
        kind = e.get("kind")
        if kind in ("builtin", "mock"):
            continue
        requires = e.get("requires") or []
        names = {r.get("name") for r in requires if isinstance(r, dict)}
        needed = {"torch", "transformers"} if kind == "native" else {"torch", kind}
        if not needed.issubset(names):
            add("requires", False,
                f"engines[{i}]（{e.get('id')}）原生引擎必须声明 torch 与 {', '.join(sorted(needed - names) or kind)} 环境要求")
            req_ok = False
            break
        missing_spec = [r.get("name") for r in requires if isinstance(r, dict) and not r.get("spec")]
        if missing_spec:
            add("requires", False,
                f"engines[{i}]（{e.get('id')}）环境要求 {', '.join(missing_spec)} 缺少 spec")
            req_ok = False
            break
    if req_ok:
        add("requires", True, "原生引擎环境要求完整")

    # 5. params_key 存在性
    try:
        from benchscope.bench_params import load_all_param_specs

        all_params = load_all_param_specs()
    except Exception:
        all_params = {}
    # 待合并的参数段（上传引擎包时随包提供，尚未写盘）视为已存在
    for key, section in (extra_param_sections or {}).items():
        all_params[key] = section
    pkey_ok = True
    for i, e in enumerate(engines):
        if not isinstance(e, dict):
            continue
        pkey = e.get("params_key") or e.get("kind")
        if pkey and pkey not in all_params:
            add("params_key", False,
                f"engines[{i}]（{e.get('id')}）的 params_key “{pkey}” 在 bench-params.yaml 中不存在")
            pkey_ok = False
            break
    if pkey_ok:
        add("params_key", True, "params_key 均已定义")

    # 6. 选项描述完整性
    desc_ok = True
    for key, section in all_params.items():
        if not isinstance(section, dict):
            continue
        for pname, spec in section.items():
            if not isinstance(spec, dict):
                continue
            for opt in spec.get("options") or []:
                if isinstance(opt, dict) and not (opt.get("description") or "").strip():
                    add("option_desc", False,
                        f"参数 {key}/{pname} 的选项 {opt.get('value')} 缺少 description")
                    desc_ok = False
                    break
            if not desc_ok:
                break
        if not desc_ok:
            break
    if desc_ok:
        add("option_desc", True, "选项描述完整")

    # 7. mock 输出（可选）
    if mock_output:
        missing = [line for line in _MOCK_REQUIRED_LINES if line not in mock_output]
        if missing:
            add("mock", False, f"mock 输出缺少必需指标行：{', '.join(missing)}")
        else:
            add("mock", True, "mock 输出包含必需指标行")

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks}


def save_benchs_yaml_text(content: str, mock_output: str = "") -> dict:
    """保存 benchs.yaml（用户自定义引擎 / 版本扩展），保存前逐项校验。

    全部校验通过才写文件；任一项失败抛 ValueError（不写文件）。
    返回校验结果 {ok, checks}。
    """
    result = validate_benchs_yaml(content, mock_output)
    if not result["ok"]:
        failed = "; ".join(c["message"] for c in result["checks"] if not c["ok"])
        raise ValueError(f"引擎定义校验失败：{failed}")
    BENCHS_YAML.write_text(content, encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# 引擎包上传（Settings → Upload Engine）
#
# 支持两种形态：
#   1. .yaml / .yml —— 引擎定义原文（含 engines 段），直接校验合并
#   2. .tar.gz / .tgz —— 技能包（skills/bench-engine-authoring 打包产物），
#      自动查找其中的引擎定义（benchs.yaml / configs/benchs.yaml / 含 engines 段的 yaml）
#      与参数说明（bench-params.yaml），合并进仓库配置
# 合并策略：id 已存在 → 更新；id 不存在 → 追加。参数说明段按 params_key 覆盖合并。
# ---------------------------------------------------------------------------
_ENGINE_PKG_SUFFIXES = (".tar.gz", ".tgz", ".yaml", ".yml")


def _safe_extract(tar: "tarfile.TarFile", dest: Path) -> None:
    """安全解压（阻止 ../ 路径穿越与绝对路径）。"""
    dest_root = dest.resolve()
    for member in tar.getmembers():
        name = member.name.lstrip("/")
        target = (dest_root / name).resolve()
        if not str(target).startswith(str(dest_root)):
            raise ValueError(f"引擎包包含非法路径: {member.name}")
        if member.isdir() or member.issym():
            continue
    try:
        tar.extractall(dest_root, filter="data")  # Python ≥3.12
    except TypeError:
        tar.extractall(dest_root)


def _collect_yaml_files(root: Path) -> list[Path]:
    """收集包内所有 yaml 文件（排除无关目录）。"""
    skip = {".git", "node_modules", "__pycache__", "dist", ".venv"}
    files = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in (".yaml", ".yml"):
            continue
        if any(part in skip or part.startswith(".") for part in p.relative_to(root).parts):
            continue
        files.append(p)
    return sorted(files)


def _load_yaml_file(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    return data if isinstance(data, dict) else {}


def import_engine_package(data: bytes, filename: str) -> dict:
    """上传并合并引擎包，返回 {ok, checks, added, updated, engines}。

    - 先做与手动导入一致的全量校验（validate_benchs_yaml）
    - 校验通过才写文件（benchs.yaml 与 bench-params.yaml 一起更新）
    """
    name = (filename or "").lower()
    if not name.endswith(_ENGINE_PKG_SUFFIXES):
        raise ValueError(
            f"不支持的文件类型：{filename or '（无文件名）'}；仅支持 .yaml / .yml / .tar.gz / .tgz"
        )

    new_engines: list[dict] = []
    new_comparison: list[dict] = []
    new_param_sections: dict = {}

    if name.endswith((".tar.gz", ".tgz")):
        from io import BytesIO

        try:
            with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as tar:
                with tempfile.TemporaryDirectory(prefix="benchscope-pkg-") as tmp:
                    _safe_extract(tar, Path(tmp))
                    for path in _collect_yaml_files(Path(tmp)):
                        doc = _load_yaml_file(path)
                        if not doc:
                            continue
                        # 引擎定义：显式含 engines 段，或文件名就是 benchs.yaml
                        if isinstance(doc.get("engines"), list) and doc["engines"]:
                            new_engines.extend(e for e in doc["engines"] if isinstance(e, dict))
                            if isinstance(doc.get("comparison"), list):
                                new_comparison.extend(doc["comparison"])
                        elif path.name in ("bench-params.yaml", "params.yaml") and not doc.get("engines"):
                            new_param_sections.update(
                                {k: v for k, v in doc.items() if isinstance(v, dict)}
                            )
        except tarfile.TarError as e:
            raise ValueError(f"引擎包解压失败（需为 gzip 压缩包）：{e}")
    else:
        doc = _load_yaml_file_from_bytes(data)
        if not isinstance(doc.get("engines"), list) or not doc["engines"]:
            raise ValueError("引擎定义文件缺少 engines 段（或为空列表）")
        new_engines = [e for e in doc["engines"] if isinstance(e, dict)]
        new_comparison = doc.get("comparison") or []

    if not new_engines:
        raise ValueError("引擎包中未找到任何引擎定义（engines 段）")

    # ---- 与现有配置合并 ----
    current_text = load_benchs_yaml_text()
    try:
        current = yaml.safe_load(current_text) or {}
        if not isinstance(current, dict):
            current = {}
    except yaml.YAMLError:
        current = {}
    cur_engines = [e for e in (current.get("engines") or []) if isinstance(e, dict)]
    cur_comparison = [c for c in (current.get("comparison") or []) if isinstance(c, dict)]

    added: list[str] = []
    updated: list[str] = []
    by_id = {e.get("id"): i for i, e in enumerate(cur_engines)}
    for eng in new_engines:
        eid = eng.get("id")
        if not eid:
            raise ValueError("引擎定义存在缺少 id 的条目")
        if eid in by_id:
            cur_engines[by_id[eid]] = eng
            updated.append(eid)
        else:
            by_id[eid] = len(cur_engines)
            cur_engines.append(eng)
            added.append(eid)

    # 对比表：按 dimension 去重合并
    dim_index = {c.get("dimension"): i for i, c in enumerate(cur_comparison)}
    for comp in new_comparison:
        dim = comp.get("dimension")
        if not dim:
            continue
        if dim in dim_index:
            merged = dict(cur_comparison[dim_index[dim]])
            values = dict(merged.get("values") or {})
            values.update(comp.get("values") or {})
            merged["values"] = values
            cur_comparison[dim_index[dim]] = merged
        else:
            dim_index[dim] = len(cur_comparison)
            cur_comparison.append(comp)

    merged_doc = {**current, "engines": cur_engines, "comparison": cur_comparison}
    merged_text = yaml.safe_dump(merged_doc, allow_unicode=True, sort_keys=False)

    # 全量校验（与手动导入一致）；随包的参数说明段需先并入校验范围，通过后才写文件
    result = validate_benchs_yaml(merged_text, extra_param_sections=new_param_sections)
    if not result["ok"]:
        failed = "; ".join(c["message"] for c in result["checks"] if not c["ok"])
        raise ValueError(f"引擎包校验失败：{failed}")

    # 参数说明段合并（bench-params.yaml）
    merged_params: list[str] = []
    if new_param_sections:
        from benchscope.bench_params import PARAMS_YAML

        try:
            doc = yaml.safe_load(PARAMS_YAML.read_text(encoding="utf-8")) or {}
            if not isinstance(doc, dict):
                doc = {}
        except (OSError, yaml.YAMLError):
            doc = {}
        for key, section in new_param_sections.items():
            doc[key] = section
            merged_params.append(key)
        PARAMS_YAML.write_text(
            yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    BENCHS_YAML.write_text(merged_text, encoding="utf-8")
    return {
        "ok": True,
        "checks": result["checks"],
        "added": added,
        "updated": updated,
        "param_sections": merged_params,
        "engines": list_engines(with_env=False)["engines"],
    }


def _load_yaml_file_from_bytes(data: bytes) -> dict:
    doc = yaml.safe_load(data.decode("utf-8", errors="replace"))
    return doc if isinstance(doc, dict) else {}


def list_engines(with_env: bool = True) -> dict:
    """全部引擎 + 对比表 + 默认引擎。"""
    engines = load_bench_engines()
    return {
        "engines": [engine_summary(e, with_env) for e in engines],
        "comparison": load_comparison(),
        "default_engine_id": default_engine_id(),
    }
