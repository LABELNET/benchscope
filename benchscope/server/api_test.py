"""测试启停与进度 API。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from benchscope.server.state import state

log = logging.getLogger("benchscope.api_test")

router = APIRouter(prefix="/api/test", tags=["test"])


class StartRequest(BaseModel):
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
    force: bool = False


@router.post("/start")
def start_test(req: StartRequest):
    try:
        run = state.tests.start(req.model_dump())
        return {"ok": True, "run_id": run.run_id, "run": run.snapshot()}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/preview")
def preview_test(req: StartRequest):
    """预览将要执行的命令（不实际运行）。"""
    from benchscope.server.test_manager import build_command_lines

    try:
        lines = build_command_lines(req.model_dump(), state.config)
        return {"ok": True, "commands": lines, "count": len(lines)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
def stop_test():
    state.tests.stop()
    return {"ok": True}


@router.get("/status")
def test_status():
    run = state.tests.current
    return {
        "running": state.tests.running,
        "run": run.snapshot() if run else None,
    }
