"""API 测试：精度数据集体系（/api/accuracy/datasets*）——清单 / 自定义路径 / 上传 / 预览 / 统计。"""

from __future__ import annotations

import json

from benchscope.accuracy.datasets import (
    filter_samples,
    import_jsonl_dataset,
    load_samples,
    standardize_samples,
)


def test_builtin_eval_datasets_registered(client, base_url):
    """9 个内置评测数据集注册于 datasets.yaml（带 eval 元数据）。"""
    r = client.get(f"{base_url}/api/accuracy/datasets", timeout=10)
    assert r.status_code == 200, r.text
    datasets = {d["id"]: d for d in r.json()["datasets"]}
    expected = {"mmlu", "cmmlu", "c-eval", "gsm8k", "math", "humaneval", "mbpp", "mt-bench", "gaokao-bench"}
    assert expected <= set(datasets), f"缺少评测数据集: {expected - set(datasets)}"
    assert datasets["mmlu"]["eval"]["scorer"] == "choice"
    assert datasets["mmlu"]["total_samples"] == 14079
    assert datasets["gsm8k"]["eval"]["scorer"] == "math"
    assert datasets["humaneval"]["eval"]["scorer"] == "code"
    assert datasets["mt-bench"]["eval"]["scorer"] == "judge"
    assert datasets["mt-bench"]["category"].startswith("accuracy-")


def _make_choice_jsonl(tmp_path, n=8):
    """构造可控正确率的四选一自定义数据集（标准格式 question/choices/answer/subject）。"""
    lines = []
    for i in range(n):
        answer = "ABCD"[i % 4]
        lines.append(json.dumps({
            "question": f"第 {i} 题的题干，正确答案是 {answer}",
            "choices": ["甲选项", "乙选项", "丙选项", "丁选项"],
            "answer": answer,
            "subject": f"学科{i % 2}",
        }, ensure_ascii=False))
    p = tmp_path / "choice_ds.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_custom_path_dataset_resolution(client, base_url, tmp_path):
    """本地路径数据集：解析 / 标准化 / 过滤 / prompt 构建。"""
    p = _make_choice_jsonl(tmp_path)
    cfg = type("Cfg", (), {"datasets_dir": tmp_path / "ds"})()
    meta, samples = load_samples(cfg, {"path": str(p), "scorer": "choice"}, limit=0, seed=1)
    assert meta["source"] == "custom-path"
    assert len(samples) == 8
    assert samples[0]["answer"] == "A" and samples[1]["answer"] == "B"
    assert samples[0]["subject"] == "学科0"


def test_custom_path_preview_and_stats_api(client, base_url, tmp_path):
    """/datasets/preview 与 /datasets/stats 支持本地路径直接引用（免上传）。"""
    p = _make_choice_jsonl(tmp_path)
    r = client.post(f"{base_url}/api/accuracy/datasets/preview",
                    json={"path": str(p)}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 5 and "答案是" in data["samples"][0]["prompt"]

    r = client.post(f"{base_url}/api/accuracy/datasets/stats",
                    json={"path": str(p)}, timeout=10)
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["total"] == 8
    assert stats["subjects"] == {"学科0": 4, "学科1": 4}
    assert stats["avg_prompt_chars"] > 0


def test_upload_import_dataset_api(client, base_url, tmp_path):
    """POST /datasets/import：上传校验 + 清单出现 + 删除。"""
    p = _make_choice_jsonl(tmp_path)
    r = client.post(f"{base_url}/api/accuracy/datasets/import?name=my-choice-ds",
                    files={"file": ("choice_ds.jsonl", p.read_bytes(), "application/octet-stream")},
                    timeout=10)
    assert r.status_code == 200, r.text
    meta = r.json()["dataset"]
    assert meta["id"].startswith("custom-") and meta["source"] == "custom"
    assert meta["eval"]["scorer"] == "choice"  # 字段猜测

    r = client.get(f"{base_url}/api/accuracy/datasets", timeout=10)
    assert meta["id"] in {d["id"] for d in r.json()["datasets"]}

    r = client.delete(f"{base_url}/api/accuracy/datasets/{meta['id']}", timeout=10)
    assert r.status_code == 200 and r.json()["ok"] is True


def test_import_rejects_invalid_content(client, base_url):
    r = client.post(f"{base_url}/api/accuracy/datasets/import?name=bad",
                    files={"file": ("bad.jsonl", b"not json at all\n{broken", "text/plain")},
                    timeout=10)
    assert r.status_code == 400


def test_preview_unknown_dataset_400(client, base_url):
    r = client.post(f"{base_url}/api/accuracy/datasets/preview", json={"id": "no-such-ds"}, timeout=10)
    assert r.status_code == 400
