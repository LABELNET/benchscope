"""API 测试：配置 / 模型 / 状态 / 参数 / 目录 / 数据集目录（/api/config*）。"""

from __future__ import annotations

import pytest

import tests.helpers as helpers


def test_get_config(client, base_url):
    r = client.get(f"{base_url}/api/config", timeout=10)
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["framework"] in ("vllm", "sglang")
    assert isinstance(cfg.get("api"), dict)
    assert "data_dir" in cfg
    # locale 键首次可能不存在（DEFAULT_CONFIG 未内置），更新后才会出现
    assert isinstance(cfg.get("locale"), (str, type(None)))


def test_update_config_roundtrip(client, base_url):
    """更新 locale 后能读回，测试结束恢复默认。"""
    r = client.post(f"{base_url}/api/config", json={"locale": "zh"}, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["locale"] == "zh"

    r = client.get(f"{base_url}/api/config", timeout=10)
    assert r.json()["locale"] == "zh"

    # 恢复默认 locale（en）
    r = client.post(f"{base_url}/api/config", json={"locale": "en"}, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["locale"] == "en"


def test_status(client, base_url):
    r = client.get(f"{base_url}/api/config/status", timeout=30)
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["web"] == "ready"
    assert "inference" in snap
    assert isinstance(snap.get("models"), list)
    # error 仅在探测失败时存在
    assert isinstance(snap.get("error"), (str, type(None)))


def test_models(client, base_url):
    r = client.get(f"{base_url}/api/config/models", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data.get("models"), list)
    assert len(data["models"]) > 0  # mock 推理服务已就绪


def test_test_connection(client, base_url, mock_url):
    r = client.post(
        f"{base_url}/api/config/test-connection",
        json={"base_url": mock_url, "api_key": ""},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True, data
    assert len(data["models"]) > 0


def test_gpu(client, base_url):
    r = client.get(f"{base_url}/api/config/gpu", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "auto_detected" in data
    assert isinstance(data.get("config"), dict)


@pytest.mark.parametrize("framework", ["vllm", "sglang"])
def test_params(client, base_url, framework):
    r = client.get(f"{base_url}/api/config/params/{framework}", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["framework"] == framework
    assert isinstance(data.get("params"), list)
    assert len(data["params"]) > 0


def test_params_unknown_framework(client, base_url):
    r = client.get(f"{base_url}/api/config/params/unknown", timeout=10)
    assert r.status_code == 404


@pytest.mark.parametrize("framework", ["vllm", "sglang"])
def test_params_yaml_roundtrip(client, base_url, framework):
    """读取默认参数 yaml -> 修改 -> 验证 -> 恢复原文（避免污染仓库配置文件）。"""
    r = client.get(f"{base_url}/api/config/params-yaml/{framework}", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    original = data["content"]
    assert data["framework"] == framework
    assert "version:" in original
    assert isinstance(data.get("lines"), list)

    # 修改：增加一个 key
    patched = original + f"# test-{framework}\nmax-num-seqs: 8\n"
    r = client.put(f"{base_url}/api/config/params-yaml/{framework}", json={"content": patched}, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    r = client.get(f"{base_url}/api/config/params-yaml/{framework}", timeout=10)
    assert r.status_code == 200, r.text
    assert "max-num-seqs: 8" in r.json()["content"]

    # 恢复原文
    r = client.put(f"{base_url}/api/config/params-yaml/{framework}", json={"content": original}, timeout=10)
    assert r.status_code == 200, r.text
    r = client.get(f"{base_url}/api/config/params-yaml/{framework}", timeout=10)
    assert r.json()["content"] == original


def test_params_yaml_unknown_framework(client, base_url):
    r = client.get(f"{base_url}/api/config/params-yaml/unknown", timeout=10)
    assert r.status_code == 404


def test_cache_dirs(client, base_url):
    r = client.get(f"{base_url}/api/config/dirs", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    keys = [d["key"] for d in data["dirs"]]
    for k in ("data_dir", "perfs_dir", "evals_dir", "datasets_dir"):
        assert k in keys
    assert all(d["value"] for d in data["dirs"])


def test_model_catalog(client, base_url):
    r = client.get(f"{base_url}/api/config/model-catalog", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data.get("groups"), list)
    assert len(data["groups"]) > 0


def test_builtin_datasets(client, base_url):
    r = client.get(f"{base_url}/api/config/datasets", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data.get("categories"), list)
    assert isinstance(data.get("datasets"), list)
    assert len(data["datasets"]) > 0
    for ds in data["datasets"]:
        assert ds["id"]
        assert "status" in ds
