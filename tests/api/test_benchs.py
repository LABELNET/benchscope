"""API 测试：内置 bench 引擎（/api/benchs*）——引擎清单 / 详情 / 环境校验。"""

from __future__ import annotations

import pytest

from benchscope.benchs import (
    _match_spec,
    _parse_version,
    check_env,
    default_engine_id,
    get_engine,
    list_engines,
    load_bench_engines,
    load_comparison,
)


def test_list_engines_api(client, base_url):
    """/api/benchs 返回三个内置引擎 + 对比表 + 默认引擎。"""
    r = client.get(f"{base_url}/api/benchs", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()

    ids = [e["id"] for e in data["engines"]]
    assert "benchscope" in ids, f"缺少自研引擎: {ids}"
    assert "vllm-0.23" in ids, f"缺少 vllm-0.23: {ids}"
    assert "sglang-0.5.10" in ids, f"缺少 sglang-0.5.10: {ids}"

    # 对比表：含维度与各引擎取值
    assert len(data["comparison"]) >= 3
    for row in data["comparison"]:
        assert row["dimension"]
        assert isinstance(row.get("values"), dict)

    # 默认引擎为自研引擎（无环境依赖，始终可用）
    assert data["default_engine_id"] == "benchscope"


def test_engine_kinds_and_requires(client, base_url):
    """自研引擎无环境要求；原生引擎要求 torch + 目标框架版本。"""
    r = client.get(f"{base_url}/api/benchs", timeout=10)
    engines = {e["id"]: e for e in r.json()["engines"]}

    builtin = engines["benchscope"]
    assert builtin["kind"] == "builtin"
    assert builtin["requires"] == [], "自研引擎不应有框架环境要求"
    assert builtin["description"], "自研引擎应有介绍文案"

    vllm = engines["vllm-0.23"]
    assert vllm["kind"] == "vllm"
    names = {x["name"] for x in vllm["requires"]}
    assert names == {"torch", "vllm"}, f"vllm 引擎环境要求应为 torch+vllm: {names}"

    sglang = engines["sglang-0.5.10"]
    assert sglang["kind"] == "sglang"
    names = {x["name"] for x in sglang["requires"]}
    assert names == {"torch", "sglang"}, f"sglang 引擎环境要求应为 torch+sglang: {names}"


def test_builtin_engine_env_always_ok(client, base_url):
    """自研引擎环境校验恒通过（不依赖 torch/vllm/sglang）。"""
    r = client.get(f"{base_url}/api/benchs/benchscope/env-check", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["engine_id"] == "benchscope"
    assert data["kind"] == "builtin"
    assert data["ok"] is True, "自研引擎无需本地框架环境，应恒通过"
    assert data["checks"] == []


def test_native_engine_env_check_reports_missing(client, base_url):
    """原生引擎环境校验：返回逐项检查结果（缺 torch/vllm/sglang 时 ok=False + hint）。"""
    for engine_id in ("vllm-0.23", "sglang-0.5.10"):
        r = client.get(f"{base_url}/api/benchs/{engine_id}/env-check", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["engine_id"] == engine_id
        assert isinstance(data["ok"], bool)
        assert len(data["checks"]) >= 2, "原生引擎至少校验 torch 与目标框架"
        for c in data["checks"]:
            assert set(["name", "required", "installed", "ok", "hint"]).issubset(c.keys())
            if not c["ok"]:
                assert c["hint"], f"未通过的检查项必须有安装提示: {c}"


def test_get_engine_detail_and_404(client, base_url):
    """单引擎详情正常返回；未知引擎 404。"""
    r = client.get(f"{base_url}/api/benchs/vllm-0.23", timeout=10)
    assert r.status_code == 200, r.text
    detail = r.json()
    assert detail["id"] == "vllm-0.23"
    assert detail["version"] == "0.23"
    assert "env" in detail

    r = client.get(f"{base_url}/api/benchs/no-such-engine", timeout=10)
    assert r.status_code == 404


# ---------------- 版本比较与环境校验纯函数 ----------------


@pytest.mark.parametrize(
    "installed,spec,expected",
    [
        ("2.1.0", ">=2.0", True),
        ("1.13.1", ">=2.0", False),
        ("0.23.0", ">=0.23,<0.24", True),
        ("0.24.0", ">=0.23,<0.24", False),
        ("0.5.10", "==0.5.10", True),
        ("0.5.9", "==0.5.10", False),
        (None, ">=2.0", False),
        ("2.0.0", "", True),
    ],
)
def test_match_spec(installed, spec, expected):
    """版本范围匹配：ops（>=,<,==）与未安装（None）场景。"""
    assert _match_spec(installed, spec) is expected


def test_parse_version_ignores_suffix():
    """版本解析忽略 rc/dev 后缀，按主次修订号比较。"""
    assert _parse_version("0.5.10") == (0, 5, 10)
    assert _parse_version("2.1") == (2, 1, 0)
    assert _parse_version("0.23.0rc1") == (0, 23, 0)
    assert _parse_version("") == (0, 0, 0)


def test_check_env_builtin_and_native():
    """check_env：builtin 恒通过；原生引擎缺包时 ok=False。"""
    builtin = get_engine("benchscope")
    assert builtin is not None
    assert check_env(builtin) == {"ok": True, "checks": []}

    vllm = get_engine("vllm-0.23")
    result = check_env(vllm)
    # 校验项存在；ok 取决于实际环境，但结构必须完整
    assert isinstance(result["ok"], bool)
    assert {"name", "required", "installed", "ok", "hint"} <= set(result["checks"][0].keys())


def test_load_bench_engines_and_comparison():
    """yaml 定义加载：三个引擎 + 对比表；默认引擎取自研。"""
    engines = load_bench_engines()
    assert {e["id"] for e in engines} == {"benchscope", "vllm-0.23", "sglang-0.5.10"}
    assert load_comparison(), "对比表不应为空"
    assert default_engine_id() == "benchscope"
    assert list_engines()["default_engine_id"] == "benchscope"
