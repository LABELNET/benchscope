"""精度测试 API（/api/accuracy）：任务管理 / 引擎 / 数据集 / Token 预估 / 基线对标 / 对比。

与性能模块完全独立（独立路由 / 独立任务管理器 / 独立落库），仅共享
state.config（配置设施）与 state.hub（WS 推送）。
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from benchscope.accuracy import baselines as acc_baselines
from benchscope.accuracy import estimator as acc_estimator
from benchscope.accuracy import metrics as acc_metrics
from benchscope.accuracy import datasets as acc_datasets
from benchscope.accuracy import compare as acc_compare
from benchscope.accuracy.engines import check_eval_env, list_eval_engines
from benchscope.accuracy.task_manager import EvalTask
from benchscope.server.state import state

router = APIRouter(prefix="/api/accuracy", tags=["accuracy"])


def _manager():
    return state.evals


def _get_task(task_id: str) -> EvalTask:
    task = _manager().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"精度任务不存在: {task_id}")
    return task


# ---------------------------------------------------------------------------
# 任务管理
# ---------------------------------------------------------------------------


class CreateEvalTaskRequest(BaseModel):
    name: str = ""
    mode: str = "serving"                     # serving | native
    engine_id: str = ""
    model: str = ""
    lora_name: str = ""
    lora_path: str = ""
    dataset: dict = {}                        # {id} 或 {path}
    limit: int = 0
    seed: int = 0
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 512
    concurrency: int = 4
    judge_model: str = ""
    mock_correct_rate: float = 0.7
    use_mock_env: bool = False
    api: dict = {}                            # Provider 覆盖（base_url/endpoint/api_key/extra_headers）


@router.get("/tasks")
def list_tasks():
    return {"tasks": _manager().list_tasks(), "running": _manager().running_count}


@router.post("/tasks")
def create_task(req: CreateEvalTaskRequest):
    if not req.model:
        raise HTTPException(status_code=400, detail="模型名不能为空")
    if not req.dataset or not (req.dataset.get("id") or req.dataset.get("path")):
        raise HTTPException(status_code=400, detail="数据集不能为空（id 或本地 path）")
    # 数据集同步校验：路径必须存在；id 必须已注册（内置或已导入自定义）
    ref = req.dataset
    if ref.get("path"):
        p = Path(ref["path"]).expanduser()
        if not p.exists():
            raise HTTPException(status_code=400, detail=f"自定义数据集文件不存在: {p}")
    elif ref.get("id"):
        if not acc_datasets.get_eval_meta(state.config.datasets_dir, ref["id"]):
            raise HTTPException(status_code=400, detail=f"评测数据集不存在: {ref['id']}")
    payload = req.model_dump()
    task = _manager().create_task(payload)
    started = _manager().start_task(task.task_id)
    return {"ok": True, "task": started.snapshot()}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    return {"task": _get_task(task_id).snapshot()}


@router.post("/tasks/{task_id}/stop")
def stop_task(task_id: str):
    task = _get_task(task_id)
    _manager().stop_task(task_id)
    return {"ok": True, "task": task.snapshot(include_result=False)}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    if not _manager().delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"精度任务不存在: {task_id}")
    return {"ok": True}


@router.get("/tasks/{task_id}/samples")
def list_samples(task_id: str, filter: str = Query("all"),
                 limit: int = Query(50), offset: int = Query(0)):
    """单样本溯源（分页 / filter=all|wrong|invalid|correct）。"""
    task = _get_task(task_id)
    samples_file = task.task_dir / "samples.jsonl"
    if not samples_file.exists():
        return {"total": 0, "samples": []}
    rows = []
    for line in samples_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if filter == "all" or row.get("status") == filter:
            rows.append(row)
    total = len(rows)
    page = rows[offset: offset + max(1, limit)]
    return {"total": total, "samples": page}


@router.get("/tasks/{task_id}/export-samples")
def export_samples(task_id: str, filter: str = Query("wrong")):
    """错题集导出（filter=wrong|invalid，JSONL 下载，用于模型迭代）。"""
    task = _get_task(task_id)
    samples_file = task.task_dir / "samples.jsonl"
    if not samples_file.exists():
        raise HTTPException(status_code=404, detail="任务暂无样本数据")
    lines = []
    for line in samples_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("status") == filter:
            lines.append(json.dumps(row, ensure_ascii=False))
    if not lines:
        raise HTTPException(status_code=404, detail=f"没有状态为 {filter} 的样本")
    out = task.task_dir / f"{filter}_samples.jsonl"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return FileResponse(out, media_type="application/x-ndjson", filename=out.name)


@router.get("/tasks/{task_id}/benchmark")
def get_benchmark(task_id: str):
    result = _get_task(task_id).result or {}
    return {"benchmark": result.get("benchmark")}


# ---------------------------------------------------------------------------
# 引擎
# ---------------------------------------------------------------------------


@router.get("/engines")
def list_engines():
    return {"engines": list_eval_engines(with_env=True)}


@router.get("/engines/{engine_id}/env-check")
def engine_env_check(engine_id: str):
    try:
        return check_eval_env(engine_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ---------------------------------------------------------------------------
# 数据集
# ---------------------------------------------------------------------------


class DatasetRef(BaseModel):
    id: str = ""
    path: str = ""


@router.get("/datasets")
def list_datasets():
    return {"datasets": acc_datasets.list_eval_datasets(state.config.datasets_dir)}


@router.post("/datasets/import")
async def import_dataset(name: str = Query(""), file: UploadFile = File(...)):
    """上传导入自定义 JSONL 数据集。"""
    content = await file.read()
    try:
        meta = acc_datasets.import_jsonl_dataset(state.config.datasets_dir, name, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "dataset": meta}


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str):
    if not acc_datasets.delete_dataset(state.config.datasets_dir, dataset_id):
        raise HTTPException(status_code=404, detail=f"自定义数据集不存在或不可删除: {dataset_id}")
    return {"ok": True}


@router.post("/datasets/preview")
def preview_dataset(ref: DatasetRef):
    """数据集预览（内置 id 或本地路径）。"""
    try:
        return acc_datasets.preview(state.config, ref.model_dump(exclude_none=True), n=5)
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/datasets/stats")
def dataset_stats(ref: DatasetRef):
    """数据集统计（样本量 / 学科分布 / 实测 token 均值）。"""
    try:
        return acc_datasets.dataset_stats(state.config, ref.model_dump(exclude_none=True))
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Token 预估（Serving 强提醒前置接口）
# ---------------------------------------------------------------------------


@router.get("/estimate")
def estimate(dataset_id: str = Query(""), path: str = Query(""),
             limit: int = Query(0), mode: str = Query("serving"),
             max_tokens: int = Query(512)):
    """预估一次评测的 Token 开销（Serving 创建任务前置强提醒）。"""
    if not dataset_id and not path:
        raise HTTPException(status_code=400, detail="数据集不能为空（dataset_id 或 path）")
    try:
        return acc_estimator.estimate(state.config, {"id": dataset_id, "path": path},
                                      limit=limit, mode=mode, max_tokens=max_tokens)
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ---------------------------------------------------------------------------
# 基线对标
# ---------------------------------------------------------------------------


@router.get("/baselines")
def get_baselines():
    return acc_baselines.load_baselines()


class BaselinesUpdateRequest(BaseModel):
    content: str


@router.put("/baselines")
def update_baselines(req: BaselinesUpdateRequest):
    """管理员更新基线库（YAML 校验后写盘）。"""
    try:
        return acc_baselines.save_baselines(req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ---------------------------------------------------------------------------
# 多任务对比 / Native vs Serving 一致性
# ---------------------------------------------------------------------------


class CompareRequest(BaseModel):
    task_ids: list[str]


@router.post("/compare")
def compare_tasks(req: CompareRequest):
    """多任务横向对比 / Native vs Serving 训推一致性差值。"""
    snapshots = []
    for task_id in req.task_ids:
        task = _get_task(task_id)
        snapshot = task.snapshot(include_result=False)
        snapshot["result"] = task.result
        snapshots.append(snapshot)
    return acc_compare.compare_tasks(snapshots)
