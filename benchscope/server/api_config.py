"""配置 / 模型 / GPU / 状态 相关 API。"""
from __future__ import annotations

import logging

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from benchscope.constants import STATUS_READY
from benchscope.gpu import detect_gpu
from benchscope.server.state import state

log = logging.getLogger("benchscope.api_config")

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config():
    return state.config.snapshot()


class ConfigPatch(BaseModel):
    api: dict | None = None
    gpu: dict | None = None
    logs_dir: str | None = None
    datasets_dir: str | None = None
    tpot_threshold_ms: float | None = None
    request_rate: str | None = None
    bench_commands: dict | None = None
    framework: str | None = None
    theme: str | None = None
    locale: str | None = None
    providers: list | None = None


@router.post("")
def update_config(patch: ConfigPatch):
    data = patch.model_dump(exclude_none=True)
    state.config.update(data)
    return state.config.snapshot()


@router.get("/status")
def get_status():
    snap = state.monitor.check_once(broadcast=False)
    snap["web"] = STATUS_READY
    return snap


@router.get("/models")
def get_models():
    """返回推理服务当前模型列表（优先用状态缓存，必要时实时探测）。"""
    snap = state.monitor.check_once(broadcast=False)
    if not snap["models"] and snap["error"]:
        raise HTTPException(status_code=502, detail=f"推理服务不可达: {snap['error']}")
    return {"models": snap["models"], "inference": snap["inference"], "error": snap["error"]}


class ConnTest(BaseModel):
    base_url: str
    endpoint: str = "/v1/chat/completions"
    api_key: str = ""
    extra_headers: dict = {}


@router.post("/test-connection")
def test_connection(req: ConnTest):
    base = req.base_url.rstrip("/")
    headers = {}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"
    headers.update(req.extra_headers or {})
    try:
        resp = requests.get(f"{base}/v1/models", headers=headers, timeout=6)
        resp.raise_for_status()
        models = [m.get("id") for m in resp.json().get("data", []) if m.get("id")]
        return {"ok": True, "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


@router.get("/gpu")
def get_gpu():
    auto = detect_gpu()
    cfg = state.config.get("gpu", {"auto": True, "name": "", "count": 8})
    return {"auto_detected": auto, "config": cfg}


@router.get("/params/{framework}")
def get_params(framework: str):
    """返回指定框架的可配置参数定义（前端表单渲染用）。"""
    if framework == "sglang":
        from benchscope.benches.sglang_bench import CURATED_PARAMS
    elif framework == "vllm":
        from benchscope.benches.vllm_bench import CURATED_PARAMS
    else:
        raise HTTPException(status_code=404, detail="未知框架")
    return {"framework": framework, "params": [p.__dict__ for p in CURATED_PARAMS]}
