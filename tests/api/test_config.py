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


def test_cache_dirs_root_readonly_contract(client, base_url):
    """Root Dir（data_dir）可编辑；其余子目录只读 + 高亮展示。"""
    r = client.get(f"{base_url}/api/config/dirs", timeout=10)
    assert r.status_code == 200, r.text
    dirs = {d["key"]: d for d in r.json()["dirs"]}
    assert dirs["data_dir"]["readonly"] is False
    # 子目录（非 data_dir）一律只读
    for d in r.json()["dirs"]:
        if d["key"] != "data_dir":
            assert d["readonly"] is True, d["key"]
    # Root Dir 命名：英文 Root Dir / 中文 根目录
    assert dirs["data_dir"]["label_en"] == "Root Dir"
    assert dirs["data_dir"]["label_zh"] == "根目录"


def test_update_data_dir_no_restart_and_subdirs_reset(client, base_url):
    """改 Root Dir：无需重启（requires_restart=False），8 个子目录全部重置为新根下的默认子目录。"""
    import os
    import tempfile

    new_root = tempfile.mkdtemp(prefix="bs-root-")

    r = client.post(f"{base_url}/api/config/dirs", json={"data_dir": new_root}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["requires_restart"] is False, "Root Dir 修改不应再要求重启"
    assert data["ok"] is True

    # 子目录全部跟随新根目录（断配置值；文件系统创建行为由单元测试 test_config_update_creates_subdirs 覆盖）
    r2 = client.get(f"{base_url}/api/config/dirs", timeout=10)
    dirs = {d["key"]: d for d in r2.json()["dirs"]}
    sub_map = {"perfs_dir": "perfs", "evals_dir": "evals", "analysis_dir": "analysys",
               "logs_dir": "logs", "sessions_dir": "sessions", "models_dir": "models",
               "datasets_dir": "datasets", "plugins_dir": "plugins"}
    for key, sub in sub_map.items():
        expected = os.path.join(new_root, sub)
        assert os.path.realpath(dirs[key]["value"]) == os.path.realpath(expected), key


def test_config_update_creates_subdirs_and_sync_env():
    """ConfigManager.update(data_dir)：同进程内应创建新根下的子目录，并把 data_dir 同步到环境变量。"""
    import os
    import tempfile
    from pathlib import Path

    from benchscope.config import ConfigManager

    cfg = ConfigManager(path=Path(tempfile.mkdtemp(prefix="bs-cfg-unit-")) / "settings.json")
    new_root = tempfile.mkdtemp(prefix="bs-root-unit-")

    cfg.update({"data_dir": new_root})

    assert cfg.get("data_dir") == new_root
    # 8 个子目录全部重置为新根下的默认子目录
    for key, sub in [("perfs_dir", "perfs"), ("evals_dir", "evals"), ("analysis_dir", "analysys"),
                     ("logs_dir", "logs"), ("sessions_dir", "sessions"), ("models_dir", "models"),
                     ("datasets_dir", "datasets"), ("plugins_dir", "plugins")]:
        assert os.path.realpath(cfg.get(key)) == os.path.realpath(os.path.join(new_root, sub)), key
        # ensure_dirs 已创建
        assert os.path.isdir(os.path.join(new_root, sub)), sub
    # 环境变量同步（「以环境变量形式使用」）
    assert os.environ.get("BENCHSCOPE_DATA_DIR") == os.path.realpath(new_root)

    # 恢复环境变量，避免影响其他测试
    os.environ.pop("BENCHSCOPE_DATA_DIR", None)


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


# ---------------- Providers（推理服务提供方，1.0.7） ----------------


def test_providers_migration_and_list(client, base_url):
    """旧配置（仅 api）启动时自动迁移出名为 Default 的 Provider 并激活。"""
    r = client.get(f"{base_url}/api/config/providers", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    providers = data["providers"]
    assert isinstance(providers, list) and providers, "应至少迁移出一个 Provider"
    assert data["active_provider"], "应有激活的 Provider"
    names = [p["name"] for p in providers]
    assert "Default" in names, f"迁移 Provider 应命名为 Default: {names}"
    # 激活项与 api 字段同步（重新激活以排除 point_to_mock fixture 直接改 api 的干扰）
    active = next(p for p in providers if p["id"] == data["active_provider"])
    r = client.post(f"{base_url}/api/config/providers/{active['id']}/activate", timeout=10)
    assert r.status_code == 200, r.text
    api = client.get(f"{base_url}/api/config", timeout=10).json()["api"]
    assert api["base_url"] == active["base_url"], "激活 Provider 应同步 api.base_url"


def test_providers_crud_and_activate(client, base_url):
    """Provider 增改删 + 激活：激活项同步到 api；删除激活项后回退到剩余首个。"""
    # 新增
    r = client.post(f"{base_url}/api/config/providers",
                    json={"name": "CRUD Test", "base_url": "http://10.0.0.9:8000", "api_key": "sk-x"},
                    timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    pid = data["provider"]["id"]
    assert data["provider"]["name"] == "CRUD Test"

    # 更新
    r = client.put(f"{base_url}/api/config/providers/{pid}",
                   json={"name": "CRUD Renamed", "base_url": "http://10.0.0.10:8000"}, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["provider"]["base_url"] == "http://10.0.0.10:8000"

    # 激活 → api 同步
    r = client.post(f"{base_url}/api/config/providers/{pid}/activate", timeout=10)
    assert r.status_code == 200, r.text
    api = client.get(f"{base_url}/api/config", timeout=10).json()["api"]
    assert api["base_url"] == "http://10.0.0.10:8000", "激活后 api.base_url 应同步"

    # name 置空 → 400
    r = client.put(f"{base_url}/api/config/providers/{pid}", json={"name": "  "}, timeout=10)
    assert r.status_code == 400, f"空 name 应拒绝: {r.status_code}"

    # 删除激活项 → 回退到剩余首个
    r = client.delete(f"{base_url}/api/config/providers/{pid}", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert all(p["id"] != pid for p in data["providers"])
    if data["providers"]:
        assert data["active_provider"] == data["providers"][0]["id"]

    # 删除不存在的 → 404
    r = client.delete(f"{base_url}/api/config/providers/{pid}", timeout=10)
    assert r.status_code == 404


def test_engine_mocks_config_update(client, base_url):
    """引擎 mock 开关配置（Settings → Bench Engines，每引擎一个）：写入 config.engine_mocks 映射。"""
    r = client.get(f"{base_url}/api/config", timeout=10)
    assert "engine_mocks" in r.json(), "默认 config 应含 engine_mocks 映射"

    r = client.post(f"{base_url}/api/config",
                    json={"engine_mocks": {"vllm-0.23": True, "sglang-0.5.10": False}},
                    timeout=10)
    assert r.status_code == 200, r.text
    mocks = r.json().get("engine_mocks", {})
    assert mocks.get("vllm-0.23") is True
    assert mocks.get("sglang-0.5.10") is False

    # 复原
    client.post(f"{base_url}/api/config", json={"engine_mocks": {}}, timeout=10)


def test_skills_list(client, base_url):
    """内置技能清单（Settings → Skills）：返回技能面板所需字段（名称/版本/描述/特性/使用说明/提示词）。"""
    r = client.get(f"{base_url}/api/skills", timeout=10)
    assert r.status_code == 200, r.text
    skills = r.json().get("skills", [])
    assert len(skills) >= 3, f"应至少返回 3 个内置技能: {len(skills)}"
    for s in skills:
        assert s.get("name"), "技能名"
        assert s.get("version"), "版本号"
        assert s.get("description"), "功能描述"
        assert isinstance(s.get("features"), list) and s["features"], "功能特性"
        assert isinstance(s.get("usage"), list) and len(s["usage"]) >= 2, "使用说明（下载安装 / 复制提示词）"
        assert s.get("prompt"), "提示词应非空（滚动显示）"
        assert s.get("download", {}).get("path"), "下载路径"
