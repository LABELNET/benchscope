"""内置数据集模块：读取 configs/datasets.yaml，支持下载并缓存到 datasets_dir。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from benchscope.datasets import download_file, list_dataset_files

log = logging.getLogger("benchscope.builtin_datasets")

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
DATASETS_YAML = CONFIGS_DIR / "datasets.yaml"


def load_builtin_datasets() -> list[dict]:
    """读取内置数据集定义（configs/datasets.yaml）。"""
    if not DATASETS_YAML.exists():
        log.warning("datasets.yaml 不存在: %s", DATASETS_YAML)
        return []
    try:
        data = yaml.safe_load(DATASETS_YAML.read_text(encoding="utf-8"))
        datasets = data.get("datasets", []) if isinstance(data, dict) else []
        return [d for d in datasets if isinstance(d, dict) and d.get("id")]
    except Exception:
        log.exception("解析 datasets.yaml 失败")
        return []


def _cache_root(datasets_dir: Path) -> Path:
    """内置数据集缓存根目录：datasets_dir（Settings/Datasets 管理的数据集下载目录）。"""
    return datasets_dir


def _ds_cache_dir(cache_root: Path, ds_id: str) -> Path:
    return cache_root / ds_id


def dataset_status(ds: dict, cache_root: Path) -> dict:
    """返回数据集缓存状态：cached（文件列表）/ not_cached。"""
    d = _ds_cache_dir(cache_root, ds.get("id", ""))
    files: list[str] = []
    if d.is_dir():
        files = sorted(p.name for p in d.iterdir() if p.is_file())
    return {"id": ds.get("id"), "cached": bool(files), "files": files}


def download_builtin_dataset(ds: dict, data_dir: Path, timeout: int = 300) -> dict:
    """下载内置数据集到缓存目录（data_dir/datasets/{id}/），返回下载结果。"""
    ds_id = ds.get("id", "")
    if not ds_id:
        raise ValueError("数据集缺少 id")
    source = ds.get("source") or {}
    stype = source.get("type", "")
    dest_dir = _ds_cache_dir(_cache_root(data_dir), ds_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if stype == "modelscope":
        dataset_id = source.get("dataset_id")
        if not dataset_id:
            raise ValueError(f"数据集 {ds_id} 缺少 modelscope dataset_id")
        files = list_dataset_files(dataset_id, timeout=timeout)
        cands = [
            (f.get("Path"), f.get("Size") or 0)
            for f in files
            if (f.get("Path") or "").endswith((".json", ".jsonl", ".parquet", ".csv"))
        ]
        if not cands:
            raise FileNotFoundError(f"数据集 {dataset_id} 中未找到可下载文件")
        wanted = source.get("file")
        if wanted:
            matched = [c for c in cands if c[0].endswith(wanted)]
            if matched:
                cands = matched
        # 优先真正的数据文件：按大小降序（排除 dataset_infos.json 等小元数据）
        cands.sort(key=lambda x: -x[1])
        target = cands[0][0]
        dest = dest_dir / Path(target).name
        if not dest.exists() or dest.stat().st_size == 0:
            log.info("下载内置数据集 %s 文件 %s ...", ds_id, target)
            download_file(dataset_id, target, dest, timeout=timeout)
        return {"id": ds_id, "path": str(dest), "size": dest.stat().st_size}
    elif stype == "url":
        url = source.get("url")
        if not url:
            raise ValueError(f"数据集 {ds_id} 缺少 url")
        import requests

        dest = dest_dir / Path(url.split("?")[0]).name
        if not dest.exists() or dest.stat().st_size == 0:
            log.info("下载内置数据集 %s（%s）...", ds_id, url)
            tmp = dest.with_suffix(dest.suffix + ".part")
            with requests.get(url, stream=True, timeout=timeout) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            tmp.replace(dest)
        return {"id": ds_id, "path": str(dest), "size": dest.stat().st_size}
    else:
        raise ValueError(f"数据集 {ds_id} 不支持的类型: {stype!r}")
