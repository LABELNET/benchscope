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
    data_dir: str | None = None
    models_dir: str | None = None
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


# ---------------------------------------------------------------------------
# 框架默认参数 yaml（创建 Perf 任务 Step2「性能参数」面板读取/保存）
#   benchscope/configs/vllm-default.yaml / sglang-default.yaml
#   第一行固定为版本号：version: <Framework> <Version>
# ---------------------------------------------------------------------------
from pathlib import Path

_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


def _params_yaml_path(framework: str) -> Path | None:
    if framework not in ("vllm", "sglang"):
        return None
    return _CONFIGS_DIR / f"{framework}-default.yaml"


def _parse_yaml(content: str) -> tuple[list[dict], str]:
    """逐行解析 yaml 为 {key, value}（重复 key 只保留最后一个），version 单独返回。"""
    lines: list[dict] = []
    version = ""
    seen: dict[str, int] = {}
    for ln in (content or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        k, v = k.strip(), v.strip()
        if k == "version":
            version = v
            continue
        if k in seen:
            lines[seen[k]]["value"] = v  # 重复 key 用最后一个值
            continue
        seen[k] = len(lines)
        lines.append({"key": k, "value": v})
    return lines, version


@router.get("/params-yaml/{framework}")
def get_params_yaml(framework: str):
    """读取框架默认参数 yaml，逐行解析为 {key, value}，version 单独返回（自动去重）。"""
    path = _params_yaml_path(framework)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"参数文件不存在: {framework}")
    content = path.read_text(encoding="utf-8")
    lines, version = _parse_yaml(content)
    return {"framework": framework, "version": version, "content": content, "lines": lines}


class YamlUpdateRequest(BaseModel):
    content: str


@router.put("/params-yaml/{framework}")
def put_params_yaml(framework: str, req: YamlUpdateRequest):
    """写回框架默认参数 yaml（Step2 编辑保存后，变更参数进入后续步骤）。

    写回前自动去重：version 仅保留一次并置于首行，其余 key 保留最后一个值。
    """
    path = _params_yaml_path(framework)
    if path is None:
        raise HTTPException(status_code=404, detail=f"未知框架: {framework}")
    lines, version = _parse_yaml(req.content)
    if version:
        content = f"version: {version}\n"
    else:
        content = ""
    content += "\n".join(f"{ln['key']}: {ln['value']}" for ln in lines)
    if content and not content.endswith("\n"):
        content += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "framework": framework, "version": version}


# ---------------------------------------------------------------- 内置数据集

@router.get("/datasets")
def list_builtin_datasets():
    """返回内置数据集定义 + 缓存状态（Settings → Datasets 面板）。"""
    from benchscope.builtin_datasets import dataset_status, load_builtin_datasets

    cache_root = state.config.data_dir / "datasets"
    datasets = load_builtin_datasets()
    return {
        "datasets": [
            {**ds, "status": dataset_status(ds, cache_root)}
            for ds in datasets
        ],
    }


class DatasetDownloadRequest(BaseModel):
    id: str


@router.post("/datasets/download")
def download_dataset(req: DatasetDownloadRequest):
    """下载内置数据集到 data_dir/datasets/{id}/。"""
    from benchscope.builtin_datasets import download_builtin_dataset, load_builtin_datasets

    ds = next((d for d in load_builtin_datasets() if d.get("id") == req.id), None)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"未知数据集: {req.id}")
    try:
        result = download_builtin_dataset(ds, state.config.data_dir)
    except Exception as e:
        log.exception("数据集 %s 下载失败", req.id)
        raise HTTPException(status_code=502, detail=f"下载失败: {e}")
    return {"ok": True, **result}
