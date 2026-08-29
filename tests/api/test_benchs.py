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


def test_benchs_yaml_get_and_save(client, base_url):
    """引擎定义 yaml：可读；保存需校验（非法内容 400 且不写文件）；合法内容生效后还原。

    校验项：yaml / engines / id / kind / requires / params_key / option_desc（详见
    skills/bench-engine-authoring/references/import-checklist.md）。

    注意：该测试会临时修改 configs/benchs.yaml，务必在 finally 中还原。
    """
    from benchscope.benchs import load_benchs_yaml_text, save_benchs_yaml_text

    original = load_benchs_yaml_text()
    assert "engines:" in original, "原始配置应含 engines 段"

    try:
        # 读取 API
        r = client.get(f"{base_url}/api/benchs/config/yaml", timeout=10)
        assert r.status_code == 200, r.text
        assert "engines:" in (r.json().get("content") or "")

        # 非法内容：kind 不合法 → 400，文件不变
        bad = "engines:\n  - id: bad-engine\n    kind: unknown-kind\n"
        r = client.put(f"{base_url}/api/benchs/config/yaml", json={"content": bad}, timeout=10)
        assert r.status_code == 400, f"非法 kind 应返回 400: {r.status_code} {r.text}"
        assert load_benchs_yaml_text() == original, "校验失败时不应写文件"

        # 缺 id → 400
        bad2 = "engines:\n  - kind: builtin\n"
        r = client.put(f"{base_url}/api/benchs/config/yaml", json={"content": bad2}, timeout=10)
        assert r.status_code == 400, "缺 id 应返回 400"

        # 非 yaml → 400
        r = client.put(f"{base_url}/api/benchs/config/yaml", json={"content": "a: [1,\n  b: ::\n"}, timeout=10)
        assert r.status_code == 400, "非法 yaml 应返回 400"

        # 合法：新增一个自定义引擎 → 保存成功且出现在清单中
        # 注意：须满足全部校验项（自研引擎带 params_key；原生引擎声明 torch + 框架）
        custom = (
            "engines:\n"
            "  - id: benchscope\n    kind: builtin\n    params_key: benchscope\n"
            "    name: BenchScope Bench（自研）\n    requires: []\n"
            "  - id: vllm-0.99\n    kind: vllm\n    version: '0.99'\n    params_key: vllm\n"
            "    name: Custom vLLM\n"
            "    requires:\n"
            "      - {name: torch, spec: '>=2.0'}\n"
            "      - {name: vllm, spec: '>=0.99,<1.0'}\n"
        )
        r = client.put(f"{base_url}/api/benchs/config/yaml", json={"content": custom}, timeout=10)
        assert r.status_code == 200, f"合法配置应保存成功: {r.text}"
        ids = [e["id"] for e in r.json()["engines"]]
        assert "vllm-0.99" in ids, f"自定义引擎未生效: {ids}"
        assert "builtin" == [e for e in r.json()["engines"] if e["id"] == "benchscope"][0]["kind"]

        # 清单 API 同步反映自定义引擎
        r = client.get(f"{base_url}/api/benchs", timeout=10)
        assert "vllm-0.99" in [e["id"] for e in r.json()["engines"]]
    finally:
        save_benchs_yaml_text(original)
        restored = load_benchs_yaml_text()
        assert restored == original, "测试结束必须还原原始配置"


def test_import_dry_run_valid(client, base_url):
    """/api/benchs/import dry_run：合法定义逐项校验通过，applied=False（不写文件）。"""
    from benchscope.benchs import load_benchs_yaml_text

    original = load_benchs_yaml_text()
    try:
        content = (
            "engines:\n"
            "  - id: benchscope\n    kind: builtin\n    params_key: benchscope\n    requires: []\n"
            "  - id: vllm-0.24\n    kind: vllm\n    version: '0.24'\n    params_key: vllm\n"
            "    requires:\n      - {name: torch, spec: '>=2.0'}\n      - {name: vllm, spec: '>=0.24,<0.25'}\n"
        )
        r = client.post(
            f"{base_url}/api/benchs/import",
            json={"content": content, "dry_run": True, "apply": False},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True, data
        assert data["applied"] is False, "dry_run 不应写入文件"
        items = {c["item"] for c in data["checks"]}
        # 七项校验齐全
        for key in ("yaml", "engines", "kind", "requires", "params_key", "option_desc"):
            assert key in items, f"缺少校验项 {key}: {items}"
        assert all(c["ok"] for c in data["checks"]), data["checks"]
        assert load_benchs_yaml_text() == original, "dry_run 不应修改文件"
    finally:
        from benchscope.benchs import save_benchs_yaml_text
        save_benchs_yaml_text(original)


def test_import_invalid_rejected(client, base_url):
    """/api/benchs/import：非法定义被拒绝（ok=False + 失败明细），不写文件。"""
    from benchscope.benchs import load_benchs_yaml_text, save_benchs_yaml_text

    original = load_benchs_yaml_text()
    cases = [
        ("kind 非法", "engines:\n  - id: x\n    kind: unknown-kind\n", "kind"),
        ("缺 requires", "engines:\n  - id: vllm-0.24\n    kind: vllm\n    params_key: vllm\n", "requires"),
        (
            "params_key 不存在",
            "engines:\n  - id: vllm-0.24\n    kind: vllm\n    params_key: nope\n"
            "    requires:\n      - {name: torch, spec: '>=2.0'}\n      - {name: vllm, spec: '>=0.24'}\n",
            "params_key",
        ),
        ("id 重复", "engines:\n  - {id: a, kind: builtin}\n  - {id: a, kind: builtin}\n", "engines"),
        ("非 yaml", "a: [1,\n  b: ::\n", "yaml"),
    ]
    try:
        for label, content, expect_item in cases:
            r = client.post(
                f"{base_url}/api/benchs/import",
                json={"content": content, "dry_run": True},
                timeout=15,
            )
            assert r.status_code == 200, f"{label}: {r.text}"
            data = r.json()
            assert data["ok"] is False, f"{label} 应校验失败: {data}"
            failed = [c for c in data["checks"] if not c["ok"]]
            assert any(c["item"] == expect_item for c in failed), f"{label} 失败项应含 {expect_item}: {failed}"
            assert load_benchs_yaml_text() == original, f"{label} 不应修改文件"
    finally:
        save_benchs_yaml_text(original)


def test_import_apply_writes_config(client, base_url):
    """/api/benchs/import apply=true：校验通过后写入并生效（测试结束还原）。"""
    from benchscope.benchs import load_benchs_yaml_text, save_benchs_yaml_text

    original = load_benchs_yaml_text()
    try:
        content = (
            "engines:\n"
            "  - id: benchscope\n    kind: builtin\n    params_key: benchscope\n    requires: []\n"
            "  - id: sglang-0.4.6\n    kind: sglang\n    version: '0.4.6'\n    params_key: sglang\n"
            "    requires:\n      - {name: torch, spec: '>=2.0'}\n      - {name: sglang, spec: '==0.4.6'}\n"
        )
        r = client.post(
            f"{base_url}/api/benchs/import",
            json={"content": content, "dry_run": False, "apply": True},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True and data["applied"] is True, data
        assert "sglang-0.4.6" in [e["id"] for e in data["engines"]]

        # 清单 API 反映新引擎
        r = client.get(f"{base_url}/api/benchs", timeout=10)
        assert "sglang-0.4.6" in [e["id"] for e in r.json()["engines"]]
    finally:
        save_benchs_yaml_text(original)
        assert load_benchs_yaml_text() == original


def test_authoring_guide_api(client, base_url):
    """/api/benchs/authoring：技能信息 + 上游链接模板 + 可复制提示词。"""
    r = client.get(f"{base_url}/api/benchs/authoring", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["skill"]["name"] == "bench-engine-authoring"
    assert "SKILL.md" in data["skill"]["path"]

    upstream = data["upstream"]
    for fw in ("vllm", "sglang"):
        assert fw in upstream, f"缺少 {fw} 上游链接"
        assert upstream[fw]["repo"].startswith("https://github.com/"), upstream[fw]
        assert "{version}" in upstream[fw]["link_template"], "链接模板应含 {version} 占位"
        assert upstream[fw]["command"], f"{fw} 应提供 bench 命令"

    prompt = data["prompt"]
    assert "github.com/vllm-project/vllm" in prompt, "提示词应含 vLLM 上游链接"
    assert "github.com/sgl-project/sglang" in prompt, "提示词应含 SGLang 上游链接"
    assert "description" in prompt.lower(), "提示词应要求选项描述"


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


def test_engine_params_api(client, base_url):
    """/api/benchs/{id}/params 返回参数定义（描述 + 下拉选项含选项级描述）。"""
    r = client.get(f"{base_url}/api/benchs/benchscope/params", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["engine_id"] == "benchscope"
    assert data["params_key"] == "benchscope"

    params = data["params"]
    assert "backend" in params, f"缺少 backend 参数定义: {list(params)}"
    backend = params["backend"]
    assert backend["help"], "参数应有说明文案"
    values = [o["value"] for o in backend["options"]]
    assert "openai-chat" in values and "openai" in values, f"backend 选项异常: {values}"
    # 每个选项必须有描述（选择后展示）
    for opt in backend["options"]:
        assert opt["description"], f"选项缺少描述: {opt}"


def test_native_engine_params(client, base_url):
    """原生引擎参数定义：vllm / sglang 各自的参数集与选项描述。"""
    for engine_id, expect_key in (("vllm-0.23", "vllm"), ("sglang-0.5.10", "sglang")):
        r = client.get(f"{base_url}/api/benchs/{engine_id}/params", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["params_key"] == expect_key
        params = data["params"]
        assert "backend" in params
        # 每个带 options 的参数，其选项都必须有描述
        for key, spec in params.items():
            for opt in spec.get("options") or []:
                assert opt.get("description"), f"{engine_id}/{key} 选项无描述: {opt}"


def test_param_option_desc_api(client, base_url):
    """/api/benchs/{id}/params/{key}/option-desc 返回指定取值的描述。"""
    r = client.get(
        f"{base_url}/api/benchs/benchscope/params/backend/option-desc",
        params={"value": "openai"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["value"] == "openai"
    assert data["description"], "openai 选项应有描述"
    assert "completions" in data["description"]

    # 无对应描述时返回空串（不报错）
    r = client.get(
        f"{base_url}/api/benchs/benchscope/params/backend/option-desc",
        params={"value": "not-exist"},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["description"] == ""


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
