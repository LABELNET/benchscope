"""任务管理 API：创建、启动、停止、删除、查询任务。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from benchscope.server.state import state

log = logging.getLogger("benchscope.api_tasks")

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

MAX_LOG_LINES = 8000


class CreateTaskRequest(BaseModel):
    framework: str = "vllm"
    model: str = ""
    tokenizer: str = ""
    dataset: dict = {}
    concurrency_list: list = []
    gpu: dict = {}
    request_rate: str | float = "inf"
    tpot_threshold_ms: float | None = None


class UpdateThresholdRequest(BaseModel):
    tpot_threshold_ms: float
    precision: str = ""
    curated: dict = {}
    extra_args: list = []


@router.get("")
def list_tasks():
    return {"tasks": state.tasks.list_tasks()}


@router.get("/{task_id}")
def get_task(task_id: str):
    task = state.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task.snapshot()


@router.get("/{task_id}/logs")
def get_task_logs(task_id: str, tail: int = MAX_LOG_LINES):
    """返回任务整条测试日志（full.log）。默认只取末尾 MAX_LOG_LINES 行用于终端展示。"""
    task = state.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    full_log = task.run_dir / "full.log"
    if not full_log.exists():
        return {"task_id": task_id, "lines": [], "total_lines": 0, "truncated": 0}
    try:
        content = full_log.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")
    lines = content.splitlines()
    tail = max(1, int(tail))
    if len(lines) > tail:
        truncated = len(lines) - tail
        lines = lines[-tail:]
    else:
        truncated = 0
    return {"task_id": task_id, "lines": lines, "total_lines": len(lines) + truncated, "truncated": truncated}


@router.patch("/{task_id}/threshold")
def update_threshold(task_id: str, req: UpdateThresholdRequest):
    """实时更新 TPOT 阈值并持久化，前端失焦保存。"""
    task = state.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    task.payload["tpot_threshold_ms"] = float(req.tpot_threshold_ms)
    task.persist()
    task.persist_run_json()
    snap = task.snapshot()
    state.hub.broadcast({"type": "task_updated", "task_id": task_id, "task": snap})
    return snap


@router.post("")
def create_task(req: CreateTaskRequest):
    try:
        task = state.tasks.create_task(req.model_dump())
        return {"ok": True, "task_id": task.task_id, "task": task.snapshot()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/start")
def start_task(task_id: str):
    try:
        task = state.tasks.start_task(task_id)
        return {"ok": True, "task_id": task.task_id, "task": task.snapshot()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{task_id}/stop")
def stop_task(task_id: str):
    task = state.tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    state.tasks.stop_task(task_id)
    return {"ok": True}


@router.delete("/{task_id}")
def delete_task(task_id: str):
    state.tasks.delete_task(task_id)
    return {"ok": True}


@router.post("/{task_id}/preview")
def preview_task(req: CreateTaskRequest):
    """预览将要执行的命令。"""
    from benchscope.server.test_manager import build_command_lines
    try:
        lines = build_command_lines(req.model_dump(), state.config)
        return {"ok": True, "commands": lines, "count": len(lines)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
