"""API 测试：运行记录与数据集（/api/logs*）。

依赖一次真实 FAKE perf 运行（module 级 fixture），验证：
runs 列表 / 详情 / 汇总 / 预览 / 下载 / 备份 / 导入回环 / 数据集上传删除。
"""

from __future__ import annotations

import io
import zipfile

import pytest

import tests.helpers as helpers
from tests.helpers import create_and_run_task, run_id_of

RUN_TIMEOUT = 120


@pytest.fixture(scope="module")
def perf_run(client, base_url):
    """跑一次 FAKE perf 任务，返回 (task_id, snapshot, run_id)。"""
    snap = create_and_run_task(client, base_url, timeout=RUN_TIMEOUT)
    return snap["task_id"], snap, run_id_of(snap["task_id"])


def test_list_runs_contains(perf_run, client, base_url):
    _, _, run_id = perf_run
    r = client.get(f"{base_url}/api/logs/runs", timeout=10)
    assert r.status_code == 200, r.text
    runs = r.json()["runs"]
    ids = [item["run_id"] for item in runs]
    assert run_id in ids
    item = next(x for x in runs if x["run_id"] == run_id)
    assert any(f["name"] == "run.json" for f in item["files"])
    assert item["meta"].get("status") == "done"


def test_get_run(perf_run, client, base_url):
    _, _, run_id = perf_run
    r = client.get(f"{base_url}/api/logs/runs/{run_id}", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["run_id"] == run_id
    assert data["run"]["kind"] == "perf"
    assert any(f["name"] == "run.json" for f in data["files"])


def test_run_summary(perf_run, client, base_url):
    _, _, run_id = perf_run
    r = client.get(f"{base_url}/api/logs/runs/{run_id}/summary", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["run_id"] == run_id
    assert isinstance(data["records_mean"], list)
    assert len(data["records_mean"]) > 0
    assert len(data["records_p99"]) > 0
    row = data["records_mean"][0]
    for key in ("label", "concurrency", "output", "peakoutput", "total", "ttft", "tpot", "itl"):
        assert key in row
    assert "meta" in data


def test_run_preview(perf_run, client, base_url):
    _, _, run_id = perf_run
    r = client.get(f"{base_url}/api/logs/runs/{run_id}/preview", params={"name": "run.json"}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "run.json"
    assert data["total_lines"] > 0
    assert data["content"]


def test_run_download(perf_run, client, base_url):
    _, _, run_id = perf_run
    r = client.get(f"{base_url}/api/logs/runs/{run_id}/download", params={"name": "run.json"}, timeout=10)
    assert r.status_code == 200, r.text
    assert len(r.content) > 0


def test_run_download_unknown_file(perf_run, client, base_url):
    _, _, run_id = perf_run
    r = client.get(f"{base_url}/api/logs/runs/{run_id}/download", params={"name": "nope.bin"}, timeout=10)
    assert r.status_code == 404


def test_run_backup_zip(perf_run, client, base_url):
    _, _, run_id = perf_run
    r = client.get(f"{base_url}/api/logs/runs/{run_id}/backup", timeout=10)
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "run.json" in names
    assert any(n.endswith(".log") or n.endswith(".csv") for n in names)


def test_import_roundtrip(client, base_url):
    """备份 -> 删除 -> 导入恢复：独立 run，避免影响共享 fixture。"""
    snap = create_and_run_task(client, base_url, timeout=RUN_TIMEOUT)
    run_id = run_id_of(snap["task_id"])

    backup = client.get(f"{base_url}/api/logs/runs/{run_id}/backup", timeout=10)
    assert backup.status_code == 200 and backup.content[:2] == b"PK"

    r = client.delete(f"{base_url}/api/logs/runs/{run_id}", timeout=10)
    assert r.status_code == 200 and r.json()["ok"] is True

    r = client.get(f"{base_url}/api/logs/runs", timeout=10)
    assert all(x["run_id"] != run_id for x in r.json()["runs"])

    r = client.post(
        f"{base_url}/api/logs/runs/import",
        files={"file": (f"{run_id}.zip", backup.content, "application/zip")},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["run_id"] == run_id
    assert "run.json" in data.get("files", [])

    r = client.get(f"{base_url}/api/logs/runs/{run_id}", timeout=10)
    assert r.status_code == 200
    assert r.json()["run"]["status"] == "done"

    # 清理：删除恢复的记录
    r = client.delete(f"{base_url}/api/logs/runs/{run_id}", timeout=10)
    assert r.status_code == 200


def test_import_bad_zip(client, base_url):
    r = client.post(
        f"{base_url}/api/logs/runs/import",
        files={"file": ("bad.zip", b"not-a-zip", "application/zip")},
        timeout=10,
    )
    assert r.status_code == 400


def test_datasets_list_empty_ok(client, base_url):
    r = client.get(f"{base_url}/api/logs/datasets", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data["datasets"], list)


def test_datasets_upload_delete(client, base_url):
    content = '{"messages": [{"role": "user", "content": "hi"}]}\n'.encode()
    r = client.post(
        f"{base_url}/api/logs/datasets/upload",
        files={"file": ("ds_upload.jsonl", content, "application/octet-stream")},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    name = data["name"]
    assert name.startswith("ds_upload")

    r = client.get(f"{base_url}/api/logs/datasets", timeout=10)
    assert any(d["name"] == name for d in r.json()["datasets"])

    r = client.delete(f"{base_url}/api/logs/datasets/{name}", timeout=10)
    assert r.status_code == 200 and r.json()["ok"] is True

    r = client.get(f"{base_url}/api/logs/datasets", timeout=10)
    assert not any(d["name"] == name for d in r.json()["datasets"])


def test_sharegpt_status(client, base_url):
    r = client.get(f"{base_url}/api/logs/datasets/sharegpt", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["state"] in ("idle", "downloading", "done", "error")


def test_run_unknown_404(client, base_url):
    r = client.get(f"{base_url}/api/logs/runs/000000-000000", timeout=10)
    assert r.status_code == 404
    r = client.get(f"{base_url}/api/logs/runs/000000-000000/summary", timeout=10)
    assert r.status_code == 404
