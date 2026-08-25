"""日志管理 API：运行目录列表、预览、下载、数据集上传、汇总解析、分析数据。"""
from __future__ import annotations

import json
import logging
import re
import shutil
import threading
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from benchscope.server.state import state

log = logging.getLogger("benchscope.api_logs")

router = APIRouter(prefix="/api/logs", tags=["logs"])

TEXT_SUFFIXES = {".log", ".csv", ".txt", ".json", ".md", ".sh", ".py"}


# ----------------------------------------------------------------------
# 运行列表
@router.get("/runs")
def list_runs():
    logs_dir = state.config.logs_dir
    runs = []
    if logs_dir.exists():
        for d in sorted(logs_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if not d.is_dir():
                continue
            files = sorted(
                (p.name, p.stat().st_size) for p in d.iterdir() if p.is_file()
            )
            run_info = _load_run_json(d)
            runs.append({
                "run_id": d.name,
                "dir": str(d),
                "files": [{"name": n, "size": s} for n, s in files],
                "meta": {
                    "framework": (run_info or {}).get("framework_name"),
                    "model": (run_info or {}).get("model"),
                    "status": (run_info or {}).get("status"),
                    "started_at": (run_info or {}).get("started_at"),
                    "finished_at": (run_info or {}).get("finished_at"),
                } if run_info else {},
            })
    return {"runs": runs}


def _load_run_json(d: Path) -> dict | None:
    p = d / "run.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    d = _resolve_run_dir(run_id)
    run_info = _load_run_json(d) or {}
    files = sorted((p.name, p.stat().st_size) for p in d.iterdir() if p.is_file())
    return {"run_id": run_id, "dir": str(d), "files": files, "run": run_info}


@router.delete("/runs/{run_id}")
def delete_run(run_id: str):
    """删除整条运行记录目录。"""
    d = _resolve_run_dir(run_id)
    shutil.rmtree(d)
    return {"ok": True}


# ----------------------------------------------------------------------
# 预览 / 下载
@router.get("/runs/{run_id}/preview")
def preview_file(run_id: str, name: str, tail: int = 500):
    d = _resolve_run_dir(run_id)
    p = _resolve_file(d, name)
    suffix = p.suffix.lower()
    if suffix not in TEXT_SUFFIXES and name not in ("run.json",):
        raise HTTPException(status_code=400, detail="该文件不是文本文件，请下载查看")
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {e}")
    lines = content.splitlines()
    if len(lines) > tail:
        preview = "\n".join(lines[-tail:])
        truncated = len(lines) - tail
    else:
        preview = content
        truncated = 0
    return {"name": name, "truncated": truncated, "total_lines": len(lines), "content": preview}


@router.get("/runs/{run_id}/download")
def download_file(run_id: str, name: str):
    d = _resolve_run_dir(run_id)
    p = _resolve_file(d, name)
    return FileResponse(p, filename=name)


# ----------------------------------------------------------------------
# 自定义数据集上传
@router.get("/datasets")
def list_datasets():
    ds_dir = state.config.datasets_dir / "uploads"
    files = []
    if ds_dir.exists():
        for p in sorted(ds_dir.iterdir(), key=lambda x: x.name):
            if p.is_file():
                files.append({"name": p.name, "size": p.stat().st_size, "path": str(p)})
    return {"datasets": files, "dir": str(ds_dir)}


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    ds_dir = state.config.datasets_dir / "uploads"
    ds_dir.mkdir(parents=True, exist_ok=True)
    dest = ds_dir / (file.filename or "dataset.jsonl")
    dest = _unique_path(dest)
    content = await file.read()
    dest.write_bytes(content)
    return {"ok": True, "name": dest.name, "path": str(dest), "size": len(content)}


@router.delete("/datasets/{name}")
def delete_dataset(name: str):
    p = state.config.datasets_dir / "uploads" / name
    if p.exists() and p.is_file():
        p.unlink()
        return {"ok": True}
    raise HTTPException(status_code=404, detail="文件不存在")


# ----------------------------------------------------------------------
# 汇总 / 分析数据
@router.get("/runs/{run_id}/summary")
def run_summary(run_id: str, threshold: float | None = None):
    """返回该次运行的 mean / P99 两套记录与分析数据。

    优先读 run.json（含完整指标），否则回退解析汇总 CSV。
    """
    d = _resolve_run_dir(run_id)
    run_info = _load_run_json(d) or {}
    threshold = threshold if threshold is not None else run_info.get("tpot_threshold_ms")

    records = _records_from_run(run_info, d)
    if not records:
        return {
            "run_id": run_id, "records_mean": [], "records_p99": [],
            "best_mean": {}, "best_p99": {}, "threshold": threshold, "meta": run_info,
        }

    mean_rows = _to_display_rows(records, "mean")
    p99_rows = _to_display_rows(records, "p99")
    return {
        "run_id": run_id,
        "records_mean": mean_rows,
        "records_p99": p99_rows,
        "records": _to_merged_rows(records),
        "best_mean": _find_best(mean_rows, threshold),
        "best_p99": _find_best(p99_rows, threshold),
        "threshold": threshold,
        "meta": run_info,
    }


def _to_merged_rows(records: list[dict]) -> list[dict]:
    """合并 mean / P99 的展示行（日志项面板用）。"""
    out = []
    for r in records:
        m = r.get("metrics", {})
        out.append({
            "label": r.get("label") or r.get("case"),
            "input_len": r.get("input_len"),
            "output_len": r.get("output_len"),
            "concurrency": r.get("concurrency"),
            "output_mean": m.get("output_mean", m.get("output")),
            "peakoutput_mean": m.get("peakoutput_mean", m.get("peakoutput")),
            "total_mean": m.get("total_mean", m.get("total")),
            "ttft_mean": m.get("ttft_mean", m.get("ttft")),
            "tpot_mean": m.get("tpot_mean", m.get("tpot")),
            "itl_mean": m.get("itl_mean", m.get("itl")),
            "ttft_p99": m.get("ttft_p99", m.get("ttft")),
            "tpot_p99": m.get("tpot_p99", m.get("tpot")),
            "itl_p99": m.get("itl_p99", m.get("itl")),
            "single_user": m.get("single_user"),
        })
    return out


def _records_from_run(run_info: dict, d: Path) -> list[dict]:
    rows = run_info.get("rows") or []
    if rows:
        return [r for r in rows if isinstance(r, dict) and "metrics" in r]
    # 回退：解析 CSV
    csvs = sorted(d.glob("*_p99.log")) or sorted(d.glob("*.log"))
    for csv in csvs:
        parsed = parse_summary_csv(csv)
        if parsed:
            return parsed
    return []


def _to_display_rows(records: list[dict], key: str) -> list[dict]:
    out = []
    for r in records:
        m = r.get("metrics", {})
        out.append({
            "label": r.get("label") or r.get("case"),
            "input_len": r.get("input_len"),
            "output_len": r.get("output_len"),
            "concurrency": r.get("concurrency"),
            # 吞吐指标无 p99 变体，两种块都取 mean
            "output": m.get(f"output_{key}", m.get("output_mean", m.get("output"))),
            "peakoutput": m.get(f"peakoutput_{key}", m.get("peakoutput_mean", m.get("peakoutput"))),
            "total": m.get(f"total_{key}", m.get("total_mean", m.get("total"))),
            "ttft": m.get(f"ttft_{key}", m.get("ttft")),
            "itl": m.get(f"itl_{key}", m.get("itl")),
            "tpot": m.get(f"tpot_{key}", m.get("tpot")),
            "single_user": m.get("single_user"),
        })
    return out


def _find_best(rows: list[dict], threshold) -> dict:
    if not rows:
        return {}
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        threshold = None
    if threshold is None:
        return {}
    by_case: dict = {}
    for r in rows:
        by_case.setdefault(r.get("label"), []).append(r)
    best = {}
    for label, items in by_case.items():
        valid = [(float(r["tpot"]), r) for r in items if r.get("tpot") is not None]
        if not valid:
            continue
        below = [(t, r) for t, r in valid if t < threshold]
        if below:
            t, r = max(below, key=lambda x: x[0])
        else:
            t, r = min(valid, key=lambda x: x[0])
        best[label] = {"concurrency": r["concurrency"], "tpot": t, "row": r}
    return best


# ----------------------------------------------------------------------
def parse_summary_csv(path: Path) -> list[dict]:
    """解析汇总 CSV（含用例块头）为记录列表。"""
    records = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return records
    cur = None
    for ln in lines:
        m = re.match(r"测试条件：(\S+)\s*\|\s*输入=(\d+)?\s*\|\s*输出=(\d+)", ln)
        if m:
            cur = {"label": m.group(1), "input_len": int(m.group(2)) if m.group(2) else None,
                   "output_len": int(m.group(3)) if m.group(3) else None}
            continue
        if ln.startswith("并发数,") or ln.startswith("=") or not ln.strip():
            continue
        parts = [x.strip() for x in ln.split(",")]
        if len(parts) >= 7 and cur:
            try:
                conc = int(parts[0])
            except ValueError:
                continue
            values = []
            for v in parts[1:7]:
                try:
                    values.append(float(v))
                except ValueError:
                    values.append(None)
            records.append({
                "label": cur["label"], "input_len": cur["input_len"], "output_len": cur["output_len"],
                "concurrency": conc,
                "metrics": {
                    "output": values[0], "peakoutput": values[1], "total": values[2],
                    "ttft": values[3], "tpot": values[4], "itl": values[5],
                },
            })
    return records


# ----------------------------------------------------------------------
# ShareGPT 数据集下载（modelscope）
_SHAREGPT_STATE = {"state": "idle", "path": None, "error": None, "thread": None}


def _sharegpt_cached_path() -> str | None:
    from benchscope.datasets import SHAREGPT_JSONL_NAME

    p = state.config.datasets_dir / "sharegpt" / SHAREGPT_JSONL_NAME
    if p.exists() and p.stat().st_size > 0:
        return str(p)
    return None


@router.get("/datasets/sharegpt")
def sharegpt_status():
    cached = _sharegpt_cached_path()
    if cached and _SHAREGPT_STATE["state"] == "idle":
        _SHAREGPT_STATE.update(state="done", path=cached, error=None)
    return dict(_SHAREGPT_STATE)


@router.post("/datasets/sharegpt/download")
def sharegpt_download():
    if _SHAREGPT_STATE["thread"] and _SHAREGPT_STATE["thread"].is_alive():
        return dict(_SHAREGPT_STATE)
    from benchscope.datasets import ensure_sharegpt

    def _work():
        try:
            _SHAREGPT_STATE.update(state="downloading", error=None)
            path = ensure_sharegpt(state.config.datasets_dir, force=True)
            _SHAREGPT_STATE.update(state="done", path=str(path), error=None)
        except Exception as e:
            log.exception("sharegpt 下载失败")
            _SHAREGPT_STATE.update(state="error", error=str(e)[:300])

    _SHAREGPT_STATE["thread"] = threading.Thread(target=_work, daemon=True)
    _SHAREGPT_STATE["thread"].start()
    return dict(_SHAREGPT_STATE)


# ----------------------------------------------------------------------
def _resolve_run_dir(run_id: str) -> Path:
    # 路径穿越校验：run_id 必须是单层目录名，禁止包含分隔符或父级引用
    if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="非法的 run_id")
    logs_dir = state.config.logs_dir
    d = (logs_dir / run_id).resolve()
    if not str(d).startswith(str(logs_dir.resolve())):
        raise HTTPException(status_code=400, detail="非法的 run_id")
    if not d.is_dir():
        raise HTTPException(status_code=404, detail=f"运行记录不存在: {run_id}")
    return d


def _resolve_file(d: Path, name: str) -> Path:
    p = (d / name).resolve()
    if not p.is_file() or not str(p).startswith(str(d.resolve())):
        raise HTTPException(status_code=404, detail="文件不存在")
    return p


def _unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    stem, suffix = p.stem, p.suffix
    i = 1
    while True:
        cand = p.with_name(f"{stem}_{i}{suffix}")
        if not cand.exists():
            return cand
        i += 1
