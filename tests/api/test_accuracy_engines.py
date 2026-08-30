"""API 测试：精度引擎（/api/accuracy/engines*）——eval 能力 / 环境校验 / mock 引擎。"""

from __future__ import annotations

from benchscope.benchs import get_engine, list_engines


def test_engines_have_eval_capability():
    """benchscope=serving / native-hf=native / mock=mock；原生压测引擎不支持精度。"""
    engines = {e["id"]: e for e in list_engines(with_env=False)["engines"]}
    assert engines["benchscope"]["eval"] == "serving"
    assert engines["native-hf"]["eval"] == "native"
    assert engines["mock"]["eval"] == "mock"
    assert engines["vllm-0.23"]["eval"] == ""
    assert engines["sglang-0.5.10"]["eval"] == ""


def test_benchscope_highlights_accuracy_content():
    """bench 引擎介绍纳入精度评测内容（用户需求：bench engines 增加精度相关测试内容）。"""
    engine = get_engine("benchscope")
    assert "benchscope eval" in engine["description"]
    assert any("eval" in h for h in engine["highlights"])
    assert any("精度" in h for h in engine["highlights_zh"])


def test_comparison_has_eval_support_dimension():
    """对比表新增「Eval Support / 精度评测」维度。"""
    comparison = list_engines(with_env=False)["comparison"]
    row = next(c for c in comparison if c["dimension"] == "Eval Support")
    assert row["values"]["benchscope"].startswith("Yes")
    assert row["values"]["vllm-0.23"].startswith("No")
    assert row["values"]["native-hf"].startswith("Yes")
    assert "精度" in row["values_zh"]["mock"]


def test_list_eval_engines_api(client, base_url):
    """/api/accuracy/engines 仅返回具备精度评测能力的引擎。"""
    r = client.get(f"{base_url}/api/accuracy/engines", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    ids = {e["id"]: e["eval"] for e in data["engines"]}
    assert ids == {"benchscope": "serving", "native-hf": "native", "mock": "mock"}


def test_mock_engine_env_always_ok(client, base_url):
    """/api/accuracy/engines/mock/env-check：mock 引擎无环境依赖，恒通过。"""
    r = client.get(f"{base_url}/api/accuracy/engines/mock/env-check", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["eval"] == "mock"
    assert data["ok"] is True


def test_native_engine_env_check_includes_cuda(client, base_url):
    """/api/accuracy/engines/native-hf/env-check：torch/transformers + CUDA 检测。"""
    r = client.get(f"{base_url}/api/accuracy/engines/native-hf/env-check", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["eval"] == "native"
    names = [c["name"] for c in data["checks"]]
    assert "cuda" in names, names
    assert {"torch", "transformers"} <= set(names)


def test_unknown_eval_engine_404(client, base_url):
    r = client.get(f"{base_url}/api/accuracy/engines/vllm-0.23/env-check", timeout=10)
    assert r.status_code == 404  # vllm 引擎不支持精度评测
