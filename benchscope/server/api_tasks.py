"""任务管理 API：创建、启动、停止、删除、查询任务。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from benchscope.server.state import state

log = logging.getLogger("benchscope.api_tasks")

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    framework: str = "vllm"
    model: str = ""
    tokenizer: str = ""
    dataset: dict = {}
    concurrency_list: list = []
    gpu: dict = {}
    request_rate: str | float = "inf"
    tpot_threshold_ms: float | None = None
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
