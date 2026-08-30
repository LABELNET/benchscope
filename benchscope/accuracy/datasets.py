"""精度评测数据集体系：沿用 Settings → Datasets（configs/datasets.yaml）+ 自定义路径。

- 内置评测数据集：datasets.yaml 中带 `eval` 元数据的条目（scorer 绑定 / prompt 模板 /
  答案字段 / 分学科字段 / 样本量声明），下载缓存沿用 datasets_dir（ModelScope 优先）。
- 自定义数据集：① 本地 JSONL 路径直接引用（免上传）；② 上传导入
  （datasets_dir/eval_custom/<id>.jsonl + meta）。
- JSONL 标准化：统一字段 `question / choices / answer / subject`（代码类
  `prompt / test / entry_point`，对话类 `turns`）。
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Callable, Optional

import yaml

from benchscope.datasets import (
    convert_json_array_to_jsonl,
    download_file,
    is_valid_jsonl,
    list_dataset_files,
)

log = logging.getLogger("benchscope.accuracy.datasets")

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"
DATASETS_YAML = CONFIGS_DIR / "datasets.yaml"

# 精度评测分类（datasets.yaml category 前缀 accuracy-）
EVAL_CATEGORY_PREFIX = "accuracy-"
EVAL_CATEGORY_NAMES = {
    "accuracy-knowledge": "知识",
    "accuracy-math": "数学",
    "accuracy-code": "代码",
    "accuracy-chat": "对话",
    "accuracy-mix": "综合",
}
CUSTOM_DIR_NAME = "eval_custom"

# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        log.exception("解析 %s 失败", path)
        return {}


def _dataset_entry_to_meta(entry: dict) -> dict:
    eval_meta = entry.get("eval") or {}
    return {
        "id": entry.get("id"),
        "name": entry.get("name") or entry.get("id"),
        "description": entry.get("description") or "",
        "category": entry.get("category") or "",
        "category_name": EVAL_CATEGORY_NAMES.get(entry.get("category") or "", entry.get("category") or ""),
        "source": "builtin",
        "total_samples": eval_meta.get("total_samples") or 0,
        "eval": {
            "scorer": eval_meta.get("scorer") or "choice",
            "metrics": eval_meta.get("metrics") or "accuracy",
            "fewshot": int(eval_meta.get("fewshot") or 0),
            "prompt_template": eval_meta.get("prompt_template") or "",
            "answer_field": eval_meta.get("answer_field") or "",
            "subject_field": eval_meta.get("subject_field") or "",
        },
        "url": entry.get("url") or "",
    }


def list_eval_datasets(datasets_dir: Path) -> list[dict]:
    """评测数据集清单（内置 + 已导入的自定义数据集）。"""
    data = _load_yaml(DATASETS_YAML)
    out = []
    for entry in data.get("datasets") or []:
        if isinstance(entry, dict) and isinstance(entry.get("eval"), dict):
            meta = _dataset_entry_to_meta(entry)
            meta["downloaded"] = _builtin_cached_path(datasets_dir, meta["id"]) is not None
            out.append(meta)
    for meta in _list_custom(datasets_dir):
        meta["downloaded"] = True
        out.append(meta)
    return out


def get_eval_meta(datasets_dir: Path, dataset_id: str) -> Optional[dict]:
    """按 id 取数据集元数据（内置或已导入自定义；直接路径引用见 resolve_dataset）。"""
    for meta in list_eval_datasets(datasets_dir):
        if meta["id"] == dataset_id:
            return meta
    return None


# ---------------------------------------------------------------------------
# 自定义数据集（上传导入 + 本地路径直接引用）
# ---------------------------------------------------------------------------


def custom_dir(datasets_dir: Path) -> Path:
    return datasets_dir / CUSTOM_DIR_NAME


def _list_custom(datasets_dir: Path) -> list[dict]:
    root = custom_dir(datasets_dir)
    out = []
    for meta_path in sorted(root.glob("*.meta.json")) if root.exists() else []:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.setdefault("category_name", "自定义")
            meta.setdefault("source", "custom")
            out.append(meta)
        except Exception:
            log.exception("自定义数据集元数据损坏: %s", meta_path)
    return out


def import_jsonl_dataset(datasets_dir: Path, name: str, content: bytes) -> dict:
    """上传导入自定义 JSONL 数据集（校验格式后落盘 datasets_dir/eval_custom/）。"""
    text = content.decode("utf-8", "replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("数据集内容为空")
    parsed = 0
    for ln in lines[:2000]:
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                parsed += 1
        except json.JSONDecodeError:
            continue
    if parsed == 0:
        raise ValueError("JSONL 校验失败：前 2000 行中没有任何合法 JSON 对象")

    safe = re.sub(r"[^\w.-]", "_", (name or "").strip() or "custom").strip("_") or "custom"
    ds_id = f"custom-{safe}-{int(time.time()) % 100000}"
    root = custom_dir(datasets_dir)
    root.mkdir(parents=True, exist_ok=True)
    jsonl_path = root / f"{ds_id}.jsonl"
    jsonl_path.write_text("\n".join(lines) + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    meta = {
        "id": ds_id,
        "name": (name or ds_id).strip(),
        "description": "自定义上传 JSONL 数据集",
        "category": "accuracy-mix",
        "category_name": "自定义",
        "source": "custom",
        "path": str(jsonl_path),
        "total_samples": len(lines),
        "eval": {"scorer": _guess_scorer(lines), "metrics": "accuracy", "fewshot": 0,
                 "prompt_template": "", "answer_field": "", "subject_field": ""},
        "url": "",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (root / f"{ds_id}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def delete_dataset(datasets_dir: Path, dataset_id: str) -> bool:
    """删除自定义数据集（内置数据集不可删）。"""
    root = custom_dir(datasets_dir)
    removed = False
    for suffix in (".jsonl", ".meta.json"):
        p = root / f"{dataset_id}{suffix}"
        if p.exists():
            p.unlink()
            removed = True
    return removed


def _guess_scorer(lines: list[str]) -> str:
    """按样本字段猜测判分器（choices → choice；test/entry_point → code；默认 math）。"""
    try:
        obj = json.loads(lines[0])
    except Exception:
        return "math"
    if isinstance(obj, dict):
        keys = set(obj.keys())
        if {"test", "entry_point"} & keys or "test_list" in keys or "prompt" in keys:
            return "code"
        if obj.get("choices") or all(k in keys for k in ("A", "B", "C", "D")):
            return "choice"
        if "turns" in keys:
            return "judge"
    return "math"


# ---------------------------------------------------------------------------
# 数据集解析与下载
# ---------------------------------------------------------------------------


def _builtin_cached_path(datasets_dir: Path, dataset_id: str) -> Optional[Path]:
    cache = datasets_dir / dataset_id
    if not cache.exists():
        return None
    jsonls = sorted(cache.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)
    return jsonls[0] if jsonls else None


def _download_entry(datasets_dir: Path, entry: dict) -> Path:
    """按 source 定义下载数据集到 datasets_dir/<id>/，返回标准化 jsonl 路径。"""
    ds_id = entry["id"]
    cache = datasets_dir / ds_id
    cache.mkdir(parents=True, exist_ok=True)
    source = entry.get("source") or {}
    src_type = (source.get("type") or "").lower()

    raw: Optional[Path] = None
    if src_type == "modelscope":
        dataset_ms_id = source.get("dataset_id") or ""
        if not dataset_ms_id:
            raise ValueError(f"数据集 {ds_id} 的 modelscope dataset_id 未配置")
        want = source.get("file") or ""
        try:
            files = list_dataset_files(dataset_ms_id)
        except Exception as e:
            raise RuntimeError(f"ModelScope 数据集 {dataset_ms_id} 文件列表获取失败: {e}") from e
        cands = []
        for f in files:
            path = f.get("Path") or ""
            name = Path(path).name
            if path.endswith((".jsonl", ".json")) and name != "dataset_infos.json":
                cands.append((path, f.get("Size") or 0))
        if want:
            cands = [c for c in cands if want in c[0]] or cands
        if not cands:
            raise FileNotFoundError(f"数据集 {dataset_ms_id} 中未找到 json/jsonl 数据文件")
        cands.sort(key=lambda x: (0 if want and want in x[0] else 1, 0 if x[0].endswith(".jsonl") else 1, -x[1]))
        candidate, size = cands[0]
        raw = cache / Path(candidate).name
        if not raw.exists() or raw.stat().st_size == 0:
            log.info("[accuracy] 下载数据集 %s: %s（约 %.0f MB）", ds_id, candidate, size / 1e6)
            download_file(dataset_ms_id, candidate, raw, timeout=600)
        _ensure_parseable(raw, ds_id)
    elif src_type == "url":
        url = source.get("url") or ""
        if not url:
            raise ValueError(f"数据集 {ds_id} 的 url 未配置")
        raw = cache / (source.get("filename") or Path(url.split("?")[0]).name or f"{ds_id}.jsonl")
        if not raw.exists() or raw.stat().st_size == 0:
            log.info("[accuracy] 下载数据集 %s: %s", ds_id, url)
            _download_url(url, raw)
        _ensure_parseable(raw, ds_id)
    else:
        raise ValueError(f"数据集 {ds_id} 的下载源类型不支持: {src_type or '（未配置）'}")

    # 统一为 .jsonl（JSON 数组流式转换）
    if raw.suffix == ".json":
        jsonl = cache / f"{raw.stem}.jsonl"
        if not jsonl.exists() or jsonl.stat().st_size == 0:
            convert_json_array_to_jsonl(raw, jsonl)
        return jsonl
    return raw


def _ensure_parseable(path: Path, ds_id: str) -> None:
    """下载产物必须含至少一行合法 JSON 对象（防止把错误页/HTML 当数据集缓存）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(50):
                line = f.readline()
                if not line:
                    break
                try:
                    if isinstance(json.loads(line), dict):
                        return
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    raise RuntimeError(
        f"数据集 {ds_id} 下载产物不可解析（{path.name}）：请检查下载源配置或手动清理 "
        f"datasets_dir 下 {ds_id} 目录后重试"
    )


def _download_url(url: str, dest: Path, timeout: int = 600) -> None:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.replace(dest)


def resolve_dataset(cfg, dataset_ref: dict) -> tuple[dict, Path]:
    """解析数据集引用 → (meta, jsonl 路径)。

    dataset_ref: {id}（内置/已导入自定义） | {path}（本地 JSONL 直接引用）。
    需要下载的内置数据集自动下载（失败抛错，错误信息含数据集 id）。
    """
    datasets_dir = cfg.datasets_dir
    ds_id = (dataset_ref or {}).get("id") or ""
    path_ref = (dataset_ref or {}).get("path") or ""

    if path_ref:
        p = Path(path_ref).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.exists():
            raise FileNotFoundError(f"自定义数据集文件不存在: {p}")
        if not is_valid_jsonl(p):
            raise ValueError(f"自定义数据集不是合法 JSONL: {p}")
        # 判分器：引用显式指定优先，否则按样本字段自动探测（choices→choice / test→code / turns→judge）
        scorer = (dataset_ref or {}).get("scorer")
        if not scorer:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                first_lines = [f.readline() for _ in range(3)]
            scorer = _guess_scorer([ln for ln in first_lines if ln.strip()])
        meta = {
            "id": str(p),
            "name": p.stem,
            "description": "自定义路径 JSONL 数据集",
            "category": "accuracy-mix",
            "category_name": "自定义",
            "source": "custom-path",
            "path": str(p),
            "total_samples": 0,
            "eval": {"scorer": scorer, "metrics": "accuracy",
                     "fewshot": 0, "prompt_template": "", "answer_field": "", "subject_field": ""},
        }
        return meta, p

    meta = get_eval_meta(datasets_dir, ds_id)
    if not meta:
        raise KeyError(f"评测数据集不存在: {ds_id}")

    if meta.get("path"):
        return meta, Path(meta["path"])
    cached = _builtin_cached_path(datasets_dir, ds_id)
    if cached:
        return meta, cached

    # 触发下载
    data = _load_yaml(DATASETS_YAML)
    entry = next((e for e in data.get("datasets") or [] if isinstance(e, dict) and e.get("id") == ds_id), None)
    if not entry:
        raise KeyError(f"评测数据集下载定义缺失: {ds_id}")
    jsonl = _download_entry(datasets_dir, entry)
    return meta, jsonl


# ---------------------------------------------------------------------------
# 样本标准化（raw → question/choices/answer/subject[/prompt/test/entry_point/turns]）
# ---------------------------------------------------------------------------

_LETTERS = "ABCDEFGH"


def _to_letter(value, choices) -> str:
    """答案归一化为选项字母（int 索引 / 字母 / 选项原文均兼容）。"""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)) and 0 <= int(value) < len(choices or []):
        return _LETTERS[int(value)]
    s = str(value or "").strip()
    if not s:
        return ""
    if s.upper() in _LETTERS[: len(choices or _LETTERS)]:
        return s.upper()
    for i, choice in enumerate(choices or []):
        if str(choice).strip() == s:
            return _LETTERS[i]
    return s


def _extract_after_marker(text: str, markers: tuple[str, ...]) -> str:
    for marker in markers:
        idx = text.rfind(marker)
        if idx >= 0:
            tail = text[idx + len(marker):].strip()
            if tail:
                return tail.splitlines()[0].strip()
    return ""


def _adapt_sample(ds_id: str, raw: dict) -> dict:
    """按数据集适配 raw 字段（各主流数据集格式差异），未知格式走通用回退。"""
    sid = str(raw.get("task_id") or raw.get("question_id") or raw.get("id") or "")

    if ds_id in ("cmmlu", "c-eval") or {"A", "B", "C", "D"} <= set(raw.keys()):
        choices = [raw.get(k, "") for k in "ABCD"]
        return {"sample_id": sid, "question": raw.get("question") or raw.get("Question") or "",
                "choices": choices, "answer": _to_letter(raw.get("answer") or raw.get("Answer"), choices),
                "subject": raw.get("subject") or raw.get("Subject") or ""}

    if ds_id == "mmlu" or (isinstance(raw.get("choices"), list) and isinstance(raw.get("answer"), int)):
        choices = raw.get("choices") or []
        return {"sample_id": sid, "question": raw.get("question") or "", "choices": choices,
                "answer": _to_letter(raw.get("answer"), choices), "subject": raw.get("subject") or ""}

    if ds_id == "gsm8k" or "#### " in str(raw.get("answer") or ""):
        answer_raw = str(raw.get("answer") or "")
        final = answer_raw.split("####")[-1].strip().replace(",", "") if "####" in answer_raw else answer_raw
        return {"sample_id": sid, "question": raw.get("question") or "", "choices": [],
                "answer": final, "subject": raw.get("subject") or ""}

    if ds_id in ("humaneval", "mbpp") or {"prompt", "test", "entry_point"} <= set(raw.keys()) or "test_list" in raw:
        if "test_list" in raw or ds_id == "mbpp":
            return {"sample_id": sid, "question": raw.get("text") or raw.get("question") or "",
                    "answer": raw.get("code") or "", "test_list": raw.get("test_list") or [],
                    "entry_point": raw.get("entry_point") or "", "prompt": "", "test": ""}
        return {"sample_id": sid, "question": "", "answer": raw.get("canonical_solution") or "",
                "prompt": raw.get("prompt") or "", "test": raw.get("test") or "",
                "entry_point": raw.get("entry_point") or "", "choices": []}

    if ds_id in ("mt-bench",) or "turns" in raw:
        return {"sample_id": sid, "question": "", "choices": [],
                "answer": "", "subject": raw.get("category") or "",
                "turns": raw.get("turns") or [], "reference": raw.get("reference") or []}

    if ds_id in ("math", "gaokao-bench") or raw.get("problem"):
        answer = str(raw.get("answer") or "")
        if not answer and raw.get("solution"):
            answer = _extract_after_marker(str(raw.get("solution")), (r"\boxed{",))
        return {"sample_id": sid, "question": raw.get("problem") or raw.get("question") or "",
                "choices": raw.get("choices") or [], "answer": answer,
                "subject": raw.get("subject") or raw.get("level") or ""}

    # 通用回退：question/problem/text/prompt + answer/Answer
    question = raw.get("question") or raw.get("problem") or raw.get("text") or raw.get("prompt") or ""
    choices = raw.get("choices") or []
    return {"sample_id": sid, "question": question, "choices": choices,
            "answer": _to_letter(raw.get("answer") or raw.get("Answer"), choices) if choices else str(raw.get("answer") or raw.get("Answer") or ""),
            "subject": raw.get("subject") or raw.get("Subject") or raw.get("category") or ""}


def _iter_jsonl(path: Path):
    """逐行解析 jsonl（兼容 JSON 数组文件与 .jsonl.gz？——仅 json/jsonl）。"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        first = f.readline()
        if not first.strip():
            return
        try:
            obj = json.loads(first)
        except json.JSONDecodeError:
            return
        if isinstance(obj, list):  # 整个数组存成单行
            for item in obj:
                if isinstance(item, dict):
                    yield item
            return
        if isinstance(obj, dict):
            yield obj
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                yield item


def standardize_samples(meta: dict, path: Path) -> list[dict]:
    """读取数据集文件并标准化为统一样本结构。"""
    ds_id = Path(str(meta.get("path") or meta.get("id") or "")).stem if meta.get("source", "").startswith("custom") else meta["id"]
    if meta.get("source", "").startswith("custom"):
        ds_id = "custom"
    out = []
    for i, raw in enumerate(_iter_jsonl(path)):
        sample = _adapt_sample(ds_id, raw)
        if not sample.get("sample_id"):
            sample["sample_id"] = f"{meta['id']}-{i}"
        sample["index"] = i
        out.append(sample)
    return out


def sample_fingerprint(meta: dict, path: Path) -> str:
    """数据集文件指纹（用于实测统计缓存）。"""
    h = hashlib.sha256()
    h.update(str(path).encode("utf-8"))
    h.update(str(path.stat().st_size if path.exists() else 0).encode("utf-8"))
    return h.hexdigest()[:16]


def filter_samples(meta: dict, samples: list[dict]) -> list[dict]:
    """过滤可评测样本：GAOKAO 等混合数据集仅保留可自动判分的客观题。"""
    scorer = (meta.get("eval") or {}).get("scorer") or "choice"
    out = []
    for s in samples:
        if scorer == "choice":
            if s.get("question") and (s.get("choices") or s.get("answer")):
                out.append(s)
        elif scorer == "math":
            if s.get("question") and str(s.get("answer") or "") != "":
                out.append(s)
        elif scorer == "code":
            if (s.get("prompt") or s.get("question")) and (s.get("test") or s.get("test_list")):
                out.append(s)
        elif scorer == "judge":
            if s.get("turns"):
                out.append(s)
        else:
            out.append(s)
    return out


def load_samples(cfg, dataset_ref: dict, limit: int = 0, seed: int = 0,
                 progress_cb: Optional[Callable[[int, int], None]] = None) -> tuple[dict, list[dict]]:
    """加载并标准化评测样本（固定种子抽样；limit>0 时随机抽取 limit 条）。"""
    meta, path = resolve_dataset(cfg, dataset_ref)
    samples = standardize_samples(meta, path)
    samples = filter_samples(meta, samples)

    total = len(samples)
    limit = int(limit or 0)
    if 0 < limit < total:
        rng = random.Random(seed or None)
        samples = rng.sample(samples, limit)
        samples.sort(key=lambda s: s.get("index", 0))
    return meta, samples


# ---------------------------------------------------------------------------
# Prompt 构建（数据集元数据模板优先，缺省按判分器给标准指令）
# ---------------------------------------------------------------------------

_CHOICE_INSTRUCTION = (
    "以下是一道单项选择题，请从给出的选项中选择正确答案。\n"
    "请直接回答正确选项的字母，回答格式：答案是 X"
)
_MATH_INSTRUCTION = (
    "请解答以下数学问题，一步步推理后给出最终答案。\n"
    "最终答案请放在最后一行，回答格式：答案是 <数值>"
)
_CODE_MBPP_INSTRUCTION = (
    "你是一个 Python 专家。请根据下面的描述编写一个 Python 函数。\n"
    "只返回可执行的 Python 代码，不要任何解释。\n\n描述："
)


def build_prompt(meta: dict, sample: dict) -> str:
    """由数据集元数据与样本构建完整输入 Prompt。"""
    scorer = (meta.get("eval") or {}).get("scorer") or "choice"
    template = (meta.get("eval") or {}).get("prompt_template") or ""

    if scorer == "code":
        if sample.get("prompt"):  # HumanEval：补全式 prompt 原样发送
            return sample["prompt"]
        tests = "\n".join(sample.get("test_list") or [])
        return f"{_CODE_MBPP_INSTRUCTION}{sample.get('question') or ''}\n\n测试用例：\n{tests}"

    if scorer == "judge":
        return str((sample.get("turns") or [""])[0])

    question = sample.get("question") or ""
    if scorer == "choice" and sample.get("choices"):
        lines = [question.rstrip()]
        for i, choice in enumerate(sample["choices"]):
            lines.append(f"{_LETTERS[i]}. {choice}")
        body = "\n".join(lines)
        return f"{template}\n\n{body}\n\n{_CHOICE_INSTRUCTION}" if template else f"{body}\n\n{_CHOICE_INSTRUCTION}"

    body = question
    if template:
        body = f"{template}\n\n{body}"
    if scorer == "math":
        return f"{body}\n\n{_MATH_INSTRUCTION}"
    return body


def dataset_stats(cfg, dataset_ref: dict) -> dict:
    """数据集统计：样本量 / 学科分布 / prompt 字符均值（token 均值实测用）。"""
    meta, path = resolve_dataset(cfg, dataset_ref)
    samples = filter_samples(meta, standardize_samples(meta, path))
    subjects: dict[str, int] = {}
    char_lens = []
    for s in samples:
        if s.get("subject"):
            subjects[str(s["subject"])] = subjects.get(str(s["subject"]), 0) + 1
        try:
            char_lens.append(len(build_prompt(meta, s)))
        except Exception:
            char_lens.append(len(s.get("question") or ""))
    return {
        "id": meta["id"],
        "name": meta["name"],
        "total": len(samples),
        "declared_total": meta.get("total_samples") or 0,
        "subjects": subjects,
        "avg_prompt_chars": round(sum(char_lens) / len(char_lens), 1) if char_lens else 0.0,
        "path": str(path),
    }


def preview(cfg, dataset_ref: dict, n: int = 5) -> dict:
    """数据集预览（前 n 条标准化样本 + 构建后的 prompt）。"""
    meta, path = resolve_dataset(cfg, dataset_ref)
    samples = filter_samples(meta, standardize_samples(meta, path))[: max(1, int(n))]
    items = []
    for s in samples:
        items.append({
            "sample_id": s.get("sample_id"),
            "subject": s.get("subject") or "",
            "question": (s.get("question") or s.get("prompt") or "")[:500],
            "choices": s.get("choices") or [],
            "answer": s.get("answer") or "",
            "prompt": build_prompt(meta, s)[:800],
        })
    return {"id": meta["id"], "name": meta["name"], "count": len(items), "samples": items}
