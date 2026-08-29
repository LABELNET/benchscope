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


def test_engine_mock_switch(client, base_url):
    """引擎 mock 开关（POST /api/benchs/{id}/mock）：开启后环境校验通过并标记 Mock；关闭恢复 Real。"""
    engine_id = "vllm-0.23"
    # 打开 mock → env 通过 + mock 状态
    r = client.post(f"{base_url}/api/benchs/{engine_id}/mock", json={"enabled": True}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mock"] is True
    assert data["mock_state"] == "mock"
    assert data["env"]["ok"] is True, "mock 开启时环境应通过"
    assert data["env"]["mock"] is True

    # env-check 同步反映 mock
    r = client.get(f"{base_url}/api/benchs/{engine_id}/env-check", timeout=10)
    data = r.json()
    assert data["mock"] is True and data["mock_state"] == "mock" and data["ok"] is True

    # 引擎列表也带 mock 状态
    r = client.get(f"{base_url}/api/benchs", timeout=10)
    eng = next(e for e in r.json()["engines"] if e["id"] == engine_id)
    assert eng["mock"] is True and eng["mock_state"] == "mock"

    # 关闭 mock → 恢复真实环境校验
    r = client.post(f"{base_url}/api/benchs/{engine_id}/mock", json={"enabled": False}, timeout=10)
    data = r.json()
    assert data["mock"] is False and data["mock_state"] == "real"

    # 未知引擎 → 404
    r = client.post(f"{base_url}/api/benchs/does-not-exist/mock", json={"enabled": True}, timeout=10)
    assert r.status_code == 404


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
            "    name: Bench CLI\n    requires: []\n"
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


# ---------------- 自研引擎命名：Bench CLI ----------------


def test_builtin_engine_named_bench_cli():
    """自研引擎名称统一为 Bench CLI（界面与文档一致）。"""
    engine = get_engine("benchscope")
    assert engine is not None
    assert engine["name"] == "Bench CLI", f"自研引擎应命名为 Bench CLI: {engine['name']}"
    comparison = load_comparison()
    kinds = [r for r in comparison if r.get("dimension") == "Engine Type"]
    assert kinds, "对比表应含「Engine Type」维度"
    assert "Bench CLI" in kinds[0]["values"]["benchscope"], kinds[0]["values"]


def test_engine_content_is_bilingual():
    """引擎文案双语：默认英文，*_zh 为中文（英文界面不应出现硬编码中文）。"""
    import re

    from benchscope.benchs import engine_summary, get_engine, load_comparison

    cjk = re.compile(r"[\u4e00-\u9fff]")
    engine = engine_summary(get_engine("benchscope"))

    # 摘要须透传双语字段
    for key in ("name", "name_zh", "description", "description_zh",
                "highlights", "highlights_zh"):
        assert engine.get(key), f"引擎摘要缺少 {key}"

    # 默认（英文）文案不得含中文字符
    assert not cjk.search(engine["description"]), f"默认描述应为英文: {engine['description'][:60]}"
    for h in engine["highlights"]:
        assert not cjk.search(h), f"默认亮点应为英文: {h}"

    # 中文文案须存在且与英文不同
    assert engine["highlights_zh"] != engine["highlights"], "中英文亮点应不同"
    assert cjk.search(engine["description_zh"] or ""), "description_zh 应为中文"

    # 对比表：维度与取值均双语
    for row in load_comparison():
        assert not cjk.search(row["dimension"]), f"默认维度应为英文: {row['dimension']}"
        assert row.get("dimension_zh"), f"维度缺少中文: {row['dimension']}"
        assert row.get("values_zh"), f"取值缺少中文: {row['dimension']}"


def test_highlights_are_concise():
    """Highlights 只列「简洁特性 + 版本支持」，条目短小且不含实现方式描述。"""
    from benchscope.benchs import load_bench_engines

    for engine in load_bench_engines():
        eid = engine.get("id")
        highlights = engine.get("highlights") or []
        for key in ("highlights", "highlights_zh"):
            items = engine.get(key) or []
            assert items, f"{eid} 缺少 {key}"
            assert len(items) <= 6, f"{eid} 的 {key} 条目过多: {len(items)}"
            for h in items:
                assert len(h) <= 80, f"{eid} 的 {key} 条目过长: {h}"
        # 版本支持情况必须有一项（英文以 Version support 开头）
        assert any(h.startswith("Version support") for h in highlights), \
            f"{eid} 应说明版本支持情况: {highlights}"


# ---------------- 引擎参数清单（随引擎切换） ----------------


def test_engine_params_yaml_api(client, base_url):
    """/api/benchs/{id}/params-yaml：每个引擎一套参数，互不干扰。"""
    from benchscope.benchs import load_engine_params

    r = client.get(f"{base_url}/api/benchs/benchscope/params-yaml", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["engine_id"] == "benchscope"
    assert data["params_key"] == "benchscope"
    assert data["content"], "Bench CLI 应有参数清单内容"

    keys = [l["key"] for l in data["lines"]]
    # Bench CLI 参数清单核心项（与 configs/benchscope-default.yaml 对应）
    for key in ("backend", "endpoint", "request-rate", "num-prompts", "num-warmups",
                "chars-per-token", "timeout", "temperature", "seed"):
        assert key in keys, f"Bench CLI 参数清单缺少 {key}: {keys}"

    # 原生引擎读取各自的参数文件，与 Bench CLI 不同
    vllm_params = load_engine_params(get_engine("vllm-0.23"))
    assert vllm_params["params_key"] == "vllm"
    assert vllm_params["content"] != data["content"], "各引擎参数清单应相互独立"


def test_engine_params_yaml_save(client, base_url):
    """/api/benchs/{id}/params-yaml 保存：去重后写回，且可再读回。"""
    from benchscope.benchs import get_engine, load_engine_params, save_engine_params

    engine = get_engine("benchscope")
    original = load_engine_params(engine)["content"]
    try:
        r = client.put(
            f"{base_url}/api/benchs/benchscope/params-yaml",
            json={"content": "version: test\nbackend: openai\nendpoint: /v1/completions\n"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        saved = {l["key"]: l["value"] for l in data["lines"]}
        assert saved["backend"] == "openai"
        assert saved["endpoint"] == "/v1/completions"
        assert data["version"] == "test"

        # 重复 key 去重（只保留最后一个）
        r = client.get(f"{base_url}/api/benchs/benchscope/params-yaml", timeout=10)
        keys = [l["key"] for l in r.json()["lines"]]
        assert keys.count("backend") == 1, f"重复 key 应去重: {keys}"
    finally:
        save_engine_params(engine, original)
        assert load_engine_params(engine)["content"] == original


def test_engine_params_yaml_404(client, base_url):
    """未知引擎请求参数清单 → 404。"""
    r = client.get(f"{base_url}/api/benchs/no-such-engine/params-yaml", timeout=10)
    assert r.status_code == 404


# ---------------- 引擎包上传（Upload Engine） ----------------


def _build_package(engine_yaml: str, param_yaml: str = "") -> bytes:
    import io
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, text in (("configs/benchs.yaml", engine_yaml), ("configs/bench-params.yaml", param_yaml)):
            if not text:
                continue
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


# 复用已有 params_key（vllm）的新版本引擎 —— 单独上传 .yaml 即可通过校验
VALID_ENGINE = (
    "engines:\n"
    "  - id: demo-1.0\n    kind: vllm\n    version: '1.0'\n    params_key: vllm\n"
    "    name: Demo Bench\n    description: 上传校验用示例引擎\n"
    "    requires:\n"
    "      - {name: torch, spec: '>=2.0'}\n"
    "      - {name: vllm, spec: '>=0.23,<0.24'}\n"
)
# 自带全新 params_key（demo）的引擎 —— 必须在包内同时提供参数说明段
VALID_ENGINE_NEW_PARAMS = (
    "engines:\n"
    "  - id: demo-1.0\n    kind: vllm\n    version: '1.0'\n    params_key: demo\n"
    "    name: Demo Bench\n    description: 上传校验用示例引擎\n"
    "    requires:\n"
    "      - {name: torch, spec: '>=2.0'}\n"
    "      - {name: vllm, spec: '>=0.23,<0.24'}\n"
)
VALID_PARAMS = (
    "demo:\n"
    "  backend:\n"
    "    label: 后端 Backend\n    help: 示例参数\n    type: select\n"
    "    options:\n"
    "      - value: openai-chat\n        label: openai-chat\n        description: 对话补全接口\n"
)


def test_upload_engine_package_tar(client, base_url):
    """/api/benchs/upload：.tar.gz 技能包 → 校验通过 → 引擎与参数段合并生效。

    技能包自带全新 params_key（demo）的参数说明段，故校验可通过。
    """
    from benchscope.bench_params import PARAMS_YAML
    from benchscope.benchs import BENCHS_YAML

    benchs_orig = BENCHS_YAML.read_text(encoding="utf-8")
    params_orig = PARAMS_YAML.read_text(encoding="utf-8")
    try:
        r = client.post(
            f"{base_url}/api/benchs/upload",
            files={"file": ("demo-engine-1.0.0.tar.gz",
                            _build_package(VALID_ENGINE_NEW_PARAMS, VALID_PARAMS),
                            "application/gzip")},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["added"] == ["demo-1.0"], data
        assert "demo" in data["param_sections"], "参数说明段应随包合并"
        assert "demo-1.0" in [e["id"] for e in data["engines"]]

        # 引擎清单 API 同步生效
        r = client.get(f"{base_url}/api/benchs", timeout=10)
        assert "demo-1.0" in [e["id"] for e in r.json()["engines"]]
    finally:
        BENCHS_YAML.write_text(benchs_orig, encoding="utf-8")
        PARAMS_YAML.write_text(params_orig, encoding="utf-8")


def test_upload_engine_package_yaml(client, base_url):
    """/api/benchs/upload：.yaml 引擎定义可直接上传。"""
    from benchscope.benchs import BENCHS_YAML

    benchs_orig = BENCHS_YAML.read_text(encoding="utf-8")
    try:
        r = client.post(
            f"{base_url}/api/benchs/upload",
            files={"file": ("engines.yaml", VALID_ENGINE.encode(), "application/x-yaml")},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.json()["added"] == ["demo-1.0"]
    finally:
        BENCHS_YAML.write_text(benchs_orig, encoding="utf-8")


def test_upload_engine_package_invalid(client, base_url):
    """/api/benchs/upload：非法包被拒绝（400），且不修改配置。"""
    from benchscope.benchs import BENCHS_YAML

    benchs_orig = BENCHS_YAML.read_text(encoding="utf-8")
    cases = [
        ("kind 非法", "engines:\n  - id: bad\n    kind: unknown\n    params_key: vllm\n", ".yaml"),
        ("缺 requires", "engines:\n  - id: bad\n    kind: vllm\n    params_key: vllm\n", ".yaml"),
        ("无 engines 段", "foo: bar\n", ".yaml"),
        ("空文件", "", ".yaml"),
        # 单独上传 .yaml 时引用了不存在的 params_key（未提供参数说明段）→ 拒绝
        ("未知 params_key", VALID_ENGINE_NEW_PARAMS, ".yaml"),
    ]
    try:
        for label, content, suffix in cases:
            r = client.post(
                f"{base_url}/api/benchs/upload",
                files={"file": (f"bad{suffix}", content.encode(), "application/octet-stream")},
                timeout=60,
            )
            assert r.status_code == 400, f"{label} 应被拒绝: {r.status_code} {r.text}"
            assert BENCHS_YAML.read_text(encoding="utf-8") == benchs_orig, f"{label} 不应写文件"

        # 不支持的文件类型
        r = client.post(
            f"{base_url}/api/benchs/upload",
            files={"file": ("engine.zip", b"PK\x03\x04", "application/zip")},
            timeout=60,
        )
        assert r.status_code == 400, "zip 不应被支持"
    finally:
        BENCHS_YAML.write_text(benchs_orig, encoding="utf-8")


def test_upload_engine_package_rejects_path_traversal():
    """引擎包含路径穿越条目 → 直接拒绝，不解压。"""
    import io
    import tarfile

    from benchscope.benchs import import_engine_package

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        payload = VALID_ENGINE.encode()
        info = tarfile.TarInfo("../../evil.yaml")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    with pytest.raises(ValueError, match="非法路径"):
        import_engine_package(buf.getvalue(), "evil.tar.gz")


# ---------------- 命令预览随引擎变化 ----------------


def test_preview_command_follows_engine(client, base_url):
    """同一 payload 下，切换引擎 → 预览命令随之变化（Bench CLI / vLLM 各自命令）。"""
    params = "version: Bench CLI stable\nbackend: openai-chat\nendpoint: /v1/chat/completions\n"
    payload = {
        "framework": "vllm",
        "engine_id": "benchscope",
        "model": "mock-model",
        "tokenizer": "",
        "dataset": {"type": "random", "length_pairs": [[1024, 1024, "1024x1024", 1]]},
        "concurrency_list": [8],
        "gpu": {},
        "request_rate": "inf",
        "mode": "concurrency",
        "engine_params_yaml": params,
        "params_yaml": {},
    }

    r = client.post(f"{base_url}/api/tasks/preview", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    builtin_cmd = r.json()["commands"][0]["cmd"]
    assert builtin_cmd.startswith("benchscope perf"), f"Bench CLI 应给出 benchscope perf 命令: {builtin_cmd}"
    for flag in ("--model mock-model", "--concurrency 8", "--input-len 1024", "--output-len 1024"):
        assert flag in builtin_cmd, f"Bench CLI 命令缺少 {flag}: {builtin_cmd}"

    # 切到原生引擎 → 命令为 vllm bench serve
    payload["engine_id"] = "vllm-0.23"
    r = client.post(f"{base_url}/api/tasks/preview", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    native_cmd = r.json()["commands"][0]["cmd"]
    assert "vllm bench serve" in native_cmd, f"原生引擎应给出 vllm bench serve 命令: {native_cmd}"
    assert native_cmd != builtin_cmd, "切换引擎后命令必须变化"


def test_builtin_options_from_engine_params():
    """Bench CLI 执行选项由「引擎参数清单」构造（参数随引擎，不再为空）。"""
    from benchscope.benches.builtin_bench import build_options, params_from_yaml

    params = params_from_yaml(
        "version: Bench CLI stable\nbackend: openai\nendpoint: /v1/completions\n"
        "request-rate: 10\nnum-prompts: 100\nnum-warmups: 3\ntimeout: 60\n"
        "chars-per-token: 2\ntemperature: 0.5\nseed: 42\n"
    )
    opts = build_options(params, base_url="http://x:8000", model="m",
                         dataset={"input_len": 128, "output_len": 256}, concurrency=8)

    assert opts.backend == "openai"
    assert opts.endpoint == "/v1/completions"
    assert opts.request_rate == 10.0
    assert opts.num_prompts == 100
    assert opts.warmups == 3
    assert opts.timeout == 60.0
    assert opts.chars_per_token == 2.0
    assert opts.seed == 42
    assert opts.extra_body["temperature"] == 0.5
    assert opts.concurrency == 8

    # 缺省：num-prompts=0 → 跟随并发数；request-rate=inf → 全速
    default_opts = build_options({}, base_url="http://x:8000", model="m",
                                 dataset={"input_len": 128, "output_len": 256}, concurrency=8)
    assert default_opts.num_prompts == 8, "num-prompts=0 应跟随并发数"
    assert default_opts.request_rate == float("inf")
    assert default_opts.backend == "openai-chat"
    assert default_opts.seed is None, "seed=0 表示不固定（None）"


def test_merge_extra_args_prefers_engine_params():
    """原生引擎命令：优先使用引擎参数清单（engine_params_yaml）。"""
    from benchscope.benches.base import merge_extra_args

    payload = {
        "framework": "vllm",
        "engine_params_yaml": "version: v\nmax-model-len: 4096\n",
        "params_yaml": {"vllm": "version: v\nmax-num-seqs: 128\n"},
        "extra_args": [],
    }
    extra = merge_extra_args(payload)
    assert "--max-model-len=4096" in extra, extra
    # 提供了 engine_params_yaml 时，旧字段不再生效（避免两套参数混用）
    assert "--max-num-seqs=128" not in extra, extra

    # 无引擎参数清单时回退旧字段（向后兼容）
    legacy = merge_extra_args({"framework": "vllm", "params_yaml": {"vllm": "version: v\nmax-num-seqs: 128\n"}})
    assert "--max-num-seqs=128" in legacy, legacy


def test_bench_cli_subcommand_parsing(capsys):
    """`benchscope perf` 子命令可解析（与 Step3 预览命令同构，可直接复制执行）。"""
    from benchscope.cli import main

    # 顶层 --help 与子命令均可用（argparse 打印后 SystemExit(0)）
    for argv in (["--help"], ["perf", "--help"], ["serve", "--help"]):
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 0, f"{argv} 解析失败"
        assert "benchscope" in capsys.readouterr().out

    # perf 子命令必填项校验：缺 --model 应报错退出（SystemExit(2)）
    with pytest.raises(SystemExit) as exc:
        main(["perf"])
    assert exc.value.code == 2, "缺少必填 --model 时应拒绝执行"


def test_authoring_prompt_generates_package():
    """Create Engine 提示词要求产出 tar.gz 引擎包（导入走 Upload Engine）。"""
    from benchscope.server.api_benchs import _authoring_prompt

    prompt = _authoring_prompt()
    assert "<framework>-<version>-engine.tar.gz" in prompt, "应指定压缩包命名"
    assert "tar -czf" in prompt, "应给出打包命令"
    assert "benchs.yaml" in prompt and "bench-params.yaml" in prompt, "应包含包内布局"
    assert "Upload Engine" in prompt, "应说明通过 Upload Engine 导入"
    assert "name_zh" in prompt, "应包含双语字段约定"
