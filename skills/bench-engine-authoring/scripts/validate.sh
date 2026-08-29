#!/usr/bin/env bash
# 离线校验引擎定义（configs/benchs.yaml 与 configs/bench-params.yaml）
#
# 用法:
#   ./scripts/validate.sh                      # 校验仓库内的默认配置
#   ./scripts/validate.sh <benchs.yaml>        # 校验指定引擎定义文件
#   ./scripts/validate.sh <benchs.yaml> <bench-params.yaml>
#
# 说明：纯 Python 实现，不依赖运行的 benchscope 服务；
#       校验项与后端导入校验保持一致（见 references/import-checklist.md）。
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_DIR/../.." && pwd)"

BENCHS="${1:-$REPO_ROOT/benchscope/configs/benchs.yaml}"
PARAMS="${2:-$REPO_ROOT/benchscope/configs/bench-params.yaml}"

PYTHON="${PYTHON:-python3}"
"$PYTHON" - "$BENCHS" "$PARAMS" <<'PYEOF'
import sys
import yaml

benchs_path, params_path = sys.argv[1], sys.argv[2]
errors: list[str] = []

def load(path, label):
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        errors.append(f"[{label}] YAML 解析失败：{e}")
        return None
    if not isinstance(data, dict):
        errors.append(f"[{label}] 顶层必须是对象")
        return None
    return data

benchs = load(benchs_path, "benchs.yaml")
params = load(params_path, "bench-params.yaml")

VALID_KINDS = {"builtin", "vllm", "sglang"}

if benchs is not None:
    engines = benchs.get("engines")
    if not isinstance(engines, list) or not engines:
        errors.append("[benchs.yaml] engines 必须是非空列表")
        engines = []

    seen = set()
    for i, e in enumerate(engines):
        if not isinstance(e, dict) or not e.get("id"):
            errors.append(f"[benchs.yaml] engines[{i}] 缺少 id 字段")
            continue
        eid = e["id"]
        if eid in seen:
            errors.append(f"[benchs.yaml] engines[{i}] id 重复：{eid}")
        seen.add(eid)

        kind = e.get("kind")
        if kind not in VALID_KINDS:
            errors.append(f"[benchs.yaml] engines[{i}]（{eid}）的 kind 必须是 builtin / vllm / sglang")
            continue

        # 原生引擎环境要求
        requires = e.get("requires") or []
        if kind != "builtin":
            names = {r.get("name") for r in requires if isinstance(r, dict)}
            needed = {"torch", kind}
            if not needed.issubset(names):
                errors.append(
                    f"[benchs.yaml] engines[{i}]（{eid}）原生引擎必须声明 torch 与 {kind} 环境要求"
                )
            for r in requires:
                if isinstance(r, dict) and not r.get("spec"):
                    errors.append(f"[benchs.yaml] engines[{i}]（{eid}）环境要求 {r.get('name')} 缺少 spec")

        # params_key 必须存在
        pkey = e.get("params_key") or kind
        if params is not None and pkey not in params:
            errors.append(
                f"[benchs.yaml] engines[{i}]（{eid}）的 params_key “{pkey}” 在 bench-params.yaml 中不存在"
            )

if params is not None:
    # 选项描述完整性
    for key, section in params.items():
        if not isinstance(section, dict):
            continue
        for pname, spec in section.items():
            if not isinstance(spec, dict):
                continue
            for opt in spec.get("options") or []:
                if not isinstance(opt, dict):
                    continue
                if not (opt.get("description") or "").strip():
                    errors.append(
                        f"[bench-params.yaml] 参数 {key}/{pname} 的选项 {opt.get('value')} 缺少 description"
                    )

if errors:
    print(f"❌ 校验失败（{len(errors)} 项）：")
    for e in errors:
        print(f"   - {e}")
    sys.exit(1)

engine_ids = [e.get("id") for e in (benchs or {}).get("engines", []) if isinstance(e, dict)]
print(f"✅ 校验通过：{len(engine_ids)} 个引擎（{', '.join(engine_ids)}），参数段 {len(params or {})} 个")
PYEOF
