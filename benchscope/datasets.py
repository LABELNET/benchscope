"""数据集管理：ShareGPT 自动下载（modelscope）、自定义数据集上传与本地路径。"""
from __future__ import annotations

import json
import logging
import shutil
import urllib.parse
from pathlib import Path
from typing import Optional

import requests

from benchscope.constants import SHAREGPT_DATASET_ID

log = logging.getLogger("benchscope.datasets")

# 期望的 ShareGPT 文件（下载源）与转换后的 jsonl 文件名
SHAREGPT_SOURCE_CANDIDATES = [
    "ShareGPT_V3_unfiltered_cleaned_split.json",
    "ShareGPT_V3_unfiltered_cleaned_split.jsonl",
    "sharegpt_v3_unfiltered_cleaned_split.jsonl",
    "sharegpt.jsonl",
]
SHAREGPT_JSONL_NAME = "ShareGPT_V3_unfiltered_cleaned_split.jsonl"

MODELSCOPE_API = "https://modelscope.cn/api/v1/datasets/{namespace}/{name}/repo"


def _split_dataset_id(dataset_id: str) -> tuple[str, str]:
    parts = dataset_id.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"无效的 modelscope 数据集 id: {dataset_id}")
    return parts[0], parts[1]


def list_dataset_files(dataset_id: str, revision: str = "master", timeout: int = 30) -> list[dict]:
    """通过 modelscope HTTP API 列出数据集文件（/repo/tree）。"""
    namespace, name = _split_dataset_id(dataset_id)
    url = MODELSCOPE_API.format(namespace=namespace, name=name) + "/tree"
    params = {"Revision": revision, "Root": "", "Recursive": "true"}
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    files = (data.get("Data") or {}).get("Files") or []
    out = []
    for f in files:
        if isinstance(f, dict) and f.get("Type") == "blob":
            out.append(f)
    return out


def convert_json_array_to_jsonl(src: Path, dst: Path) -> Path:
    """流式把 JSON 数组文件转换为 jsonl（每行一个对象），内存占用低。

    逐字符状态机跟踪对象边界与字符串（正确处理字符串内的 {} 与转义）；
    每个对象归一化为单行 json 输出（vllm/sglang 按行 json.loads 解析）。
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    with open(src, "r", encoding="utf-8", errors="replace") as fin, open(tmp, "w", encoding="utf-8") as fout:
        obj_chars: list[str] = []
        depth = 0
        in_string = False
        escaped = False
        for chunk in iter(lambda: fin.read(65536), ""):
            for ch in chunk:
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == "{":
                        depth += 1
                        if depth == 1:
                            obj_chars = ["{"]
                            continue
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                obj = json.loads("".join(obj_chars) + "}")
                                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                            except Exception:
                                pass  # 跳过损坏对象
                            obj_chars = []
                            continue
                if depth > 0:
                    obj_chars.append(ch)
    tmp.replace(dst)
    return dst


def download_file(
    dataset_id: str, file_path: str, dest: Path, revision: str = "master", timeout: int = 60
) -> Path:
    """下载 modelscope 数据集中的单个文件。"""
    namespace, name = _split_dataset_id(dataset_id)
    url = MODELSCOPE_API.format(namespace=namespace, name=name)
    params = {"Revision": revision, "FilePath": file_path}
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, params=params, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.replace(dest)
    return dest


def ensure_sharegpt(datasets_dir: Path, force: bool = False) -> Path:
    """确保 ShareGPT jsonl 已下载并转换缓存，返回 jsonl 路径。"""
    cache_dir = datasets_dir / "sharegpt"
    cache_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = cache_dir / SHAREGPT_JSONL_NAME

    # 已缓存的 jsonl
    if not force and jsonl_path.exists() and jsonl_path.stat().st_size > 0:
        return jsonl_path

    # 已下载但未转换的源文件
    source = None
    if not force:
        for cand in SHAREGPT_SOURCE_CANDIDATES:
            p = cache_dir / cand
            if p.exists() and p.stat().st_size > 0:
                source = p
                break
        if source and jsonl_path.exists() and jsonl_path.stat().st_size > 0:
            return jsonl_path

    # 尝试 modelscope SDK（若安装）
    try:
        from modelscope import snapshot_download  # type: ignore

        root = Path(snapshot_download(SHAREGPT_DATASET_ID, cache_dir=str(cache_dir)))
        if source is None:
            for cand in SHAREGPT_SOURCE_CANDIDATES:
                p = root / cand
                if p.exists():
                    source = p
                    break
        if source is None:
            jsonls = sorted(root.rglob("*.json*"))
            if jsonls:
                source = jsonls[0]
    except ImportError:
        pass
    except Exception as e:
        log.warning("modelscope SDK 下载失败，回退 HTTP 下载: %s", e)

    # HTTP API 方式
    if source is None:
        files = list_dataset_files(SHAREGPT_DATASET_ID)
        cands = []
        for f in files:
            path = f.get("Path") or ""
            if path.endswith((".json", ".jsonl")):
                cands.append((path, f.get("Size") or 0))
        if not cands:
            raise FileNotFoundError(f"数据集 {SHAREGPT_DATASET_ID} 中未找到数据文件: {files[:5]}")
        # 优先文件名含 sharegpt，其次最大文件
        cands.sort(key=lambda x: (0 if "sharegpt" in x[0].lower() else 1, -x[1]))
        candidate, cand_size = cands[0]
        source = cache_dir / Path(candidate).name
        if not source.exists() or source.stat().st_size == 0 or force:
            log.info("正在从 modelscope 下载 %s（约 %.0f MB）...", candidate, cand_size / 1e6)
            download_file(SHAREGPT_DATASET_ID, candidate, source, timeout=300)

    # 转换为 jsonl
    if jsonl_path.exists() and jsonl_path.stat().st_size > 0 and not force:
        return jsonl_path
    if source.suffix.lower() == ".jsonl":
        if source != jsonl_path:
            import shutil as _shutil

            _shutil.copyfile(source, jsonl_path)
    else:
        log.info("正在转换 %s 为 jsonl ...", source.name)
        convert_json_array_to_jsonl(source, jsonl_path)
    return jsonl_path


def is_valid_jsonl(path: Path, sample: int = 2000) -> bool:
    """粗略校验 jsonl 文件格式。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(sample):
                line = f.readline()
                if not line:
                    break
                json.loads(line)
        return True
    except Exception:
        return False
