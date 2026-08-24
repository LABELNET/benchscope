"""Dashboard 统计 API。"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from benchscope.server.state import state

log = logging.getLogger("benchscope.api_dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats():
    """返回 Dashboard 统计数据。"""
    logs_dir = state.config.logs_dir
    runs = []
    if logs_dir.exists():
        for d in sorted(logs_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if not d.is_dir():
                continue
            run_info = _load_run_json(d)
            if run_info:
                runs.append(run_info)

    total_runs = len(runs)
    running_tasks = state.tasks.running_count
    avg_tpot = None
    best_model = "-"
    best_tpot = float("inf")

    for r in runs:
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
        "total_runs": total_runs,
        "running_tasks": running_tasks,
        "avg_tpot": avg_tpot,
        "best_model": best_model,
    }


def _load_run_json(d: Path) -> dict | None:
    p = d / "run.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None
