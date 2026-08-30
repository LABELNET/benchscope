"""Dashboard 统计 API。"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from benchscope.env_info import collect_env_info
from benchscope.server.state import state

log = logging.getLogger("benchscope.api_dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _run_roots() -> list[Path]:
    """运行记录目录根：perfs（性能任务）/ evals（精度任务），兼容旧版 logs 目录中的 run 目录。"""
    cfg = state.config
    roots = [cfg.perfs_dir, cfg.evals_dir]
    logs_dir = cfg.logs_dir
    if logs_dir.is_dir() and any(
        p.is_dir() and (p / "run.json").exists() for p in logs_dir.iterdir()
    ):
        roots.append(logs_dir)
    return [r for r in roots if r and r.exists()]


@router.get("/stats")
def dashboard_stats():
    """返回 Dashboard 统计数据。"""
    runs = []
    for root in _run_roots():
        for d in sorted(root.iterdir(), key=lambda p: p.name, reverse=True):
            if not d.is_dir() or d.name == "tasks":
                # tasks: TaskManager 任务状态持久化目录（非 run 目录）
                continue
            run_info = _load_run_json(d)
            if run_info:
                runs.append(run_info)

    total_runs = len(runs)
    acc_runs = [r for r in runs if r.get("kind") == "eval"]
    best_acc = max(
        ((r.get("summary") or {}).get("accuracy") for r in acc_runs if (r.get("summary") or {}).get("accuracy") is not None),
        default=None,
    )
    running_tasks = state.tasks.running_count + state.evals.running_count
    avg_tpot = None
    best_model = "-"
    best_tpot = float("inf")

    for r in runs:
        if r.get("kind") == "eval":
            continue  # 精度任务不参与性能指标聚合
        rows = r.get("rows") or []
        model = r.get("model", "")
        for row in rows:
            m = row.get("metrics", {})
            tpot = m.get("tpot_mean")
            if tpot is not None:
                if avg_tpot is None:
                    avg_tpot = 0.0
                avg_tpot += float(tpot)
                if float(tpot) < best_tpot:
                    best_tpot = float(tpot)
                    best_model = model

    if avg_tpot is not None and total_runs > 0:
        total_metrics = sum(len(r.get("rows", [])) for r in runs)
        if total_metrics > 0:
            avg_tpot = round(avg_tpot / total_metrics, 2)

    return {
        "total_runs": total_runs - len(acc_runs),
        "total_acc_runs": len(acc_runs),
        "best_acc": best_acc,
        "running_tasks": running_tasks,
        "avg_tpot": avg_tpot,
        "best_model": best_model,
    }


@router.get("/env")
def dashboard_env():
    """返回系统环境信息（硬件 / 操作系统 / 网络 / 框架版本），缺失项为 None。"""
    return collect_env_info()


def _load_run_json(d: Path) -> dict | None:
    p = d / "run.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None
