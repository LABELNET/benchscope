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
    data_dir: str | None = None
    perfs_dir: str | None = None
    evals_dir: str | None = None
    analysis_dir: str | None = None
    logs_dir: str | None = None
    sessions_dir: str | None = None
    models_dir: str | None = None
    datasets_dir: str | None = None
    plugins_dir: str | None = None
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

    cache_root = state.config.datasets_dir
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
    """下载内置数据集到 datasets_dir/{id}/。"""
    from benchscope.builtin_datasets import download_builtin_dataset, load_builtin_datasets

    ds = next((d for d in load_builtin_datasets() if d.get("id") == req.id), None)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"未知数据集: {req.id}")
    try:
        result = download_builtin_dataset(ds, state.config.datasets_dir)
    except Exception as e:
        log.exception("数据集 %s 下载失败", req.id)
        raise HTTPException(status_code=502, detail=f"下载失败: {e}")
    return {"ok": True, **result}


# ---------------------------------------------------------------------------
# 缓存目录管理（Settings → General → Cache Paths）
# ---------------------------------------------------------------------------

# 目录展示配置：key -> {label, desc, sub（data_dir 下的默认子目录名或 None）}
CACHE_DIR_INFO = [
    {"key": "data_dir", "label": "Data", "sub": None,
     "desc": "数据根目录（服务端数据持久化 / 任务 / 会话等），修改后需重启服务并可选迁移数据"},
    {"key": "perfs_dir", "label": "Perf", "sub": "perfs",
     "desc": "性能测试任务目录，有运行中的任务时不可修改"},
    {"key": "evals_dir", "label": "Eval", "sub": "evals",
     "desc": "精度测试任务目录，有运行中的任务时不可修改"},
    {"key": "analysis_dir", "label": "Analysis", "sub": "analysys",
     "desc": "数据分析目录，联动主导航 / Datas 相关缓存"},
    {"key": "logs_dir", "label": "Logs", "sub": "logs",
     "desc": "日志目录：runtime_年月日.log 与任务终端输出（perf/eval_runID_月日时分秒.log）"},
    {"key": "sessions_dir", "label": "Sessions", "sub": "sessions",
     "desc": "会话缓存目录，每个会话保存的路径"},
    {"key": "models_dir", "label": "Models", "sub": "models",
     "desc": "模型下载目录，联动 Settings / Models 管理"},
    {"key": "datasets_dir", "label": "Datasets", "sub": "datasets",
     "desc": "数据集下载目录，联动 Settings / Datasets 管理"},
    {"key": "plugins_dir", "label": "Plugins", "sub": "plugins",
     "desc": "插件安装加载目录，联动 Settings / Plugins"},
]


@router.get("/dirs")
def get_cache_dirs():
    """返回缓存目录配置列表（值 / 默认值 / 是否存在 / 是否锁定）。"""
    from benchscope.constants import DEFAULT_CONFIG

    cfg = state.config
    perf_running = state.tasks.running_count > 0
    result = []
    for info in CACHE_DIR_INFO:
        key = info["key"]
        value = cfg.get(key) or DEFAULT_CONFIG.get(key, "")
        result.append({
            "key": key,
            "label": info["label"],
            "desc": info["desc"],
            "value": value,
            "default": DEFAULT_CONFIG.get(key, ""),
            "exists": cfg.resolve_dir(key).exists() if key else True,
            "locked": (perf_running if key in ("perfs_dir", "evals_dir") else False),
        })
    return {"dirs": result, "perf_running": perf_running}


class CacheDirPatch(BaseModel):
    data_dir: str | None = None
    perfs_dir: str | None = None
    evals_dir: str | None = None
    analysis_dir: str | None = None
    logs_dir: str | None = None
    sessions_dir: str | None = None
    models_dir: str | None = None
    datasets_dir: str | None = None
    plugins_dir: str | None = None


@router.post("/dirs")
def update_cache_dirs(patch: CacheDirPatch):
    """更新缓存目录配置。

    - data_dir 变化：需要重启服务（前端弹窗引导），重启可迁移数据。
    - perfs_dir / evals_dir：有运行中的任务时拒绝修改。
    """
    data = patch.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="没有需要更新的目录")

    # 运行中任务检查：perfs / evals 目录不可修改
    if state.tasks.running_count > 0:
        locked_keys = [k for k in ("perfs_dir", "evals_dir") if k in data]
        if locked_keys:
            raise HTTPException(
                status_code=409,
                detail="存在运行中的任务，Perf / Eval 目录暂不可修改，请等待任务停止后再试",
            )

    cfg = state.config
    old_data = str(cfg.data_dir)
    old_snapshot = {k: cfg.get(k) for k in data.keys()}
    cfg.update(data)
    new_data = str(cfg.data_dir)
    requires_restart = "data_dir" in data and new_data != old_data
    if requires_restart:
        # 记录迁移来源：本次修改前的 data_dir（重启迁移时使用）
        state.migration_source = old_data
    return {
        "ok": True,
        "requires_restart": requires_restart,
        "changed": {k: {"old": old_snapshot.get(k), "new": cfg.get(k)} for k in data.keys()},
    }


class RestartRequest(BaseModel):
    migrate: bool = False


@router.post("/restart")
def restart_service(req: RestartRequest):
    """迁移数据（可选）并重启服务。

    - migrate=True：将原 data_dir 内容移动到当前 data_dir（进度经 WS 广播）。
    - 无论是否迁移，均延迟数秒后重启进程。
    """
    import os
    import sys
    import threading
    import time

    cfg = state.config
    src = Path(os.path.expanduser(state.migration_source or cfg.data_dir)).resolve()
    dst = cfg.data_dir.resolve()

    def _do_restart():
        try:
            if req.migrate and src != dst:
                _migrate_dir(src, dst)
        except Exception:
            log.exception("数据迁移失败，仍将重启服务")
            state.hub.broadcast({"type": "migration", "phase": "error", "message": "数据迁移失败"})
        state.hub.broadcast({"type": "migration", "phase": "restarting", "message": "正在重启服务..."})
        time.sleep(1.0)
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            log.exception("进程重启失败")
            state.hub.broadcast({"type": "migration", "phase": "error", "message": "进程重启失败"})

    threading.Thread(target=_do_restart, daemon=True).start()
    return {"ok": True, "migrate": req.migrate, "message": "服务即将重启"}


def _migrate_dir(src: Path, dst: Path) -> None:
    """将 src 目录内容移动到 dst，并按条目广播迁移进度。"""
    import shutil

    dst.mkdir(parents=True, exist_ok=True)
    items = [p for p in src.iterdir()] if src.is_dir() else []
    total = len(items)
    state.hub.broadcast({
        "type": "migration", "phase": "migrating",
        "total": total, "done": 0,
        "message": f"正在迁移数据（共 {total} 项）...",
    })
    for i, item in enumerate(items, start=1):
        target = dst / item.name
        if target.exists():
            if target.is_dir() and item.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))
        if i % 5 == 0 or i == total:
            state.hub.broadcast({
                "type": "migration", "phase": "migrating",
                "total": total, "done": i,
                "message": f"已迁移 {i}/{total}",
            })
    state.hub.broadcast({
        "type": "migration", "phase": "migrating",
        "total": total, "done": total, "message": "数据迁移完成",
    })
