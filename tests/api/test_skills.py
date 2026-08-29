"""测试：skills 项目规范合规性（结构 / frontmatter / 打包 / 校验脚本）。

规范见 skills/Readme.md：每个技能必须含 SKILL.md / README.md / scripts/package.sh。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

EXPECTED_SKILLS = {"bench-engine-authoring", "vllm-bench-testing", "sglang-bench-testing"}


def _skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def test_skills_directory_layout():
    """每个技能目录必须含 SKILL.md / README.md / scripts/package.sh。"""
    dirs = _skill_dirs()
    names = {p.name for p in dirs}
    assert EXPECTED_SKILLS.issubset(names), f"缺少技能: {EXPECTED_SKILLS - names}"

    for d in dirs:
        assert (d / "SKILL.md").is_file(), f"{d.name} 缺少 SKILL.md"
        assert (d / "README.md").is_file(), f"{d.name} 缺少 README.md"
        assert (d / "scripts" / "package.sh").is_file(), f"{d.name} 缺少 scripts/package.sh"


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_skill_frontmatter(skill_dir: Path):
    """SKILL.md 必须有 YAML frontmatter，且含 name / description / version。"""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---"), f"{skill_dir.name} frontmatter 必须以 --- 开头"

    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{skill_dir.name} frontmatter 未闭合"

    fm = m.group(1)
    for key in ("name:", "description:", "version:"):
        assert re.search(rf"^{key}", fm, re.M), f"{skill_dir.name} frontmatter 缺少 {key}"

    # name 必须与目录名一致
    name = re.search(r"^name:\s*(\S+)", fm, re.M).group(1)
    assert name == skill_dir.name, f"{skill_dir.name} 的 name({name}) 与目录名不一致"

    # version 必须是语义化版本
    version = re.search(r"^version:\s*(\S+)", fm, re.M).group(1)
    assert re.match(r"^\d+\.\d+\.\d+$", version), f"{skill_dir.name} version 非语义化: {version}"

    # description 不能为空且应描述用途
    desc_block = re.search(r"^description:\s*>-\n((?:[ \t]+.*\n?)+)", fm, re.M)
    assert desc_block, f"{skill_dir.name} description 应描述触发场景"
    assert len(desc_block.group(1).strip()) > 30, f"{skill_dir.name} description 过短"


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_skill_package(skill_dir: Path):
    """scripts/package.sh 可打包，产物可解压且含必需文件；版本号取自 frontmatter。"""
    pkg = skill_dir / "scripts" / "package.sh"
    out_dir = Path(tempfile.mkdtemp(prefix=f"skill-pkg-{skill_dir.name}-"))
    try:
        r = subprocess.run(
            ["bash", str(pkg), str(out_dir)],
            capture_output=True, text=True, timeout=120,
        )
        assert r.returncode == 0, f"{skill_dir.name} 打包失败: {r.stderr or r.stdout}"

        version = re.search(
            r"^version:\s*(\S+)",
            (skill_dir / "SKILL.md").read_text(encoding="utf-8"), re.M,
        ).group(1)
        archive = out_dir / f"{skill_dir.name}-{version}.tar.gz"
        assert archive.is_file(), f"产物命名应为 <name>-<version>.tar.gz: {list(out_dir.iterdir())}"

        with tarfile.open(archive, "r:gz") as tf:
            names = tf.getnames()
            for required in ("SKILL.md", "README.md", "scripts/package.sh"):
                assert any(n.endswith(f"{skill_dir.name}/{required}") for n in names), \
                    f"产物缺少 {required}"
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_bench_engine_authoring_contents():
    """自定义引擎技能必须包含：mock 核心方法说明、上游链接、提示词、导入校验清单。"""
    d = SKILLS_DIR / "bench-engine-authoring"
    skill = (d / "SKILL.md").read_text(encoding="utf-8")

    # mock 核心逻辑方法与介绍
    assert "Mock" in skill or "mock" in skill, "SKILL.md 应说明 mock"
    assert "mocks/" in skill, "应说明 mock 代码唯一归属 mocks/"
    for method in ("generate_vllm_output", "generate_sglang_output", "_scale_stats", "_sse_stream"):
        assert method in skill, f"应描述 mock 核心方法 {method}"

    # 上游 github 链接（vllm / sglang）
    assert "github.com/vllm-project/vllm" in skill, "缺少 vLLM 上游链接"
    assert "github.com/sgl-project/sglang" in skill, "缺少 SGLang 上游链接"

    # 可复制提示词
    assert "Task: create a BenchScope custom bench engine" in skill, "缺少可复制提示词"

    # 导入校验
    assert "validation" in skill.lower() or "校验" in skill, "应描述导入校验"

    # 参考文档齐全（含上游源码分析）
    refs = d / "references"
    for f in ("engine-schema.md", "mock-core.md", "import-checklist.md", "upstream-analysis.md"):
        assert (refs / f).is_file(), f"缺少参考文档 {f}"

    # 上游分析必须提供：版本 / git 链接 / zip 链接 / 核心逻辑
    up = (refs / "upstream-analysis.md").read_text(encoding="utf-8")
    assert "v0.23.0" in up, "应记录 vLLM 分析版本"
    assert "v0.5.10" in up, "应记录 SGLang 分析版本"
    assert "github.com/vllm-project/vllm" in up, "缺 vLLM git 链接"
    assert "github.com/sgl-project/sglang" in up, "缺 SGLang git 链接"
    assert "archive/refs/tags" in up and up.count(".zip") >= 2, "应提供 zip 下载链接"
    # 核心逻辑要点：TPOT 公式分母、时间线、并发、usage 计数
    assert "output_len - 1" in up, "应记录 TPOT 分母为 output_len - 1"
    assert "most_recent_timestamp" in up or "t_first" in up, "应记录时间线采集"
    assert "Semaphore" in up, "应记录并发模型"
    assert "completion_tokens" in up, "应记录 token 计数方式"
    # 契约适配（入口/出口/mock）
    for kw in ("Input", "Core", "Output", "Mock"):
        assert kw in up, f"应描述 {kw} 契约"

    # 模板
    for f in ("benchs-engine-entry.yaml", "bench-params-section.yaml"):
        assert (d / "templates" / f).is_file(), f"缺少模板 {f}"


def test_validate_script_checks_definition():
    """validate.sh：合法配置通过；非法配置（kind 错误）返回非 0。"""
    script = SKILLS_DIR / "bench-engine-authoring" / "scripts" / "validate.sh"
    assert script.is_file()

    # 合法：仓库默认配置
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"默认配置应校验通过: {r.stdout}{r.stderr}"
    assert "校验通过" in r.stdout

    # 非法：kind 错误
    bad = Path(tempfile.mkdtemp(prefix="bad-benchs-")) / "benchs.yaml"
    bad.write_text("engines:\n  - id: x\n    kind: not-a-kind\n", encoding="utf-8")
    try:
        r = subprocess.run(
            ["bash", str(script), str(bad)],
            capture_output=True, text=True, timeout=120,
        )
        assert r.returncode != 0, "非法 kind 应校验失败"
        assert "kind" in r.stdout, f"应提示 kind 错误: {r.stdout}"
    finally:
        shutil.rmtree(bad.parent, ignore_errors=True)


def test_upstream_analysis_doc():
    """docs/rules/BenchUpstream.md：上游核心逻辑存档，须含版本/链接/公式/对齐表。"""
    doc = REPO_ROOT / "docs" / "rules" / "BenchUpstream.md"
    assert doc.is_file(), "缺少上游核心逻辑分析文档"

    text = doc.read_text(encoding="utf-8")

    # 版本与链接（必须具体、可验证）
    assert "v0.23.0" in text and "v0.5.10" in text, "应记录具体分析版本"
    assert "0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665" in text, "应记录 vLLM commit"
    assert "1519acf37c23f2189adb93f57ca9cd2db1bebf18" in text, "应记录 SGLang commit"
    assert "archive/refs/tags/v0.23.0.zip" in text, "缺 vLLM zip 链接"
    assert "archive/refs/tags/v0.5.10.zip" in text, "缺 SGLang zip 链接"

    # 核心逻辑：TPOT 公式、duration 定义、时间线
    assert "(output_len - 1)" in text or "output_len - 1" in text, "应记录 TPOT 分母"
    assert "time.perf_counter() - benchmark_start_time" in text, "应记录 duration 定义"
    assert "most_recent_timestamp" in text, "应记录时间线采集"

    # 对齐表与优化项
    assert "对齐" in text, "应给出与自研引擎的对齐情况"
    assert "优化" in text, "应给出基于上游分析的后续优化项"

    # 实现方法（复制上游 + 契约适配）
    assert "Mock" in text and "入口" in text, "应描述入口/出口/mock 契约"


def test_skills_readme_lists_all_skills():
    """skills/Readme.md 必须列出所有技能。"""
    readme = (SKILLS_DIR / "Readme.md").read_text(encoding="utf-8")
    for name in EXPECTED_SKILLS:
        assert name in readme, f"Readme.md 未列出技能 {name}"


def test_skills_docs_directory():
    """docs/skills/：skills 说明文档归口，须含三份文档并列全所有技能。"""
    docs = REPO_ROOT / "docs" / "skills"

    for f in ("Readme.md", "BenchEngineAuthoring.md", "BenchTesting.md"):
        assert (docs / f).is_file(), f"缺少技能文档 docs/skills/{f}"

    # 总入口：列出全部技能 + 规范章节（打包 / SKILL.md / 维护约定）
    index = (docs / "Readme.md").read_text(encoding="utf-8")
    for name in EXPECTED_SKILLS:
        assert name in index, f"docs/skills/Readme.md 未列出技能 {name}"
    for kw in ("SKILL.md", "package.sh", "frontmatter", "维护约定"):
        assert kw in index, f"docs/skills/Readme.md 缺少规范章节关键字 {kw}"


def test_bench_engine_authoring_doc():
    """docs/skills/BenchEngineAuthoring.md：自定义引擎技能详解（工作流/上游/契约/校验/提示词）。"""
    doc = REPO_ROOT / "docs" / "skills" / "BenchEngineAuthoring.md"
    assert doc.is_file(), "缺少 docs/skills/BenchEngineAuthoring.md"

    text = doc.read_text(encoding="utf-8")

    # 上游来源必须具体可验证（git + zip + commit）
    assert "github.com/vllm-project/vllm" in text, "缺 vLLM 上游链接"
    assert "github.com/sgl-project/sglang" in text, "缺 SGLang 上游链接"
    assert "archive/refs/tags/v0.23.0.zip" in text, "缺 vLLM zip 链接"
    assert "archive/refs/tags/v0.5.10.zip" in text, "缺 SGLang zip 链接"
    assert "0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665" in text, "应记录 vLLM commit"
    assert "1519acf37c23f2189adb93f57ca9cd2db1bebf18" in text, "应记录 SGLang commit"

    # 四段契约（入口 / 处理 / 出口 / Mock）
    for kw in ("Input", "Core", "Output", "Mock"):
        assert kw in text, f"应描述 {kw} 契约"

    # mock 核心方法与硬规则（parser 正则、mocks/ 归属）
    for method in ("generate_vllm_output", "generate_sglang_output", "_scale_stats"):
        assert method in text, f"应描述 mock 核心方法 {method}"
    assert "mocks/" in text and "parser.py" in text, "应说明 mock 归属与 parser 正则匹配"

    # 导入校验与可复制提示词
    assert "params_key" in text and "description" in text, "应描述导入校验项"
    assert "Task: create a BenchScope custom bench engine" in text, "缺少可复制提示词"


def test_bench_testing_doc():
    """docs/skills/BenchTesting.md：vLLM / SGLang 性能测试技能说明。"""
    doc = REPO_ROOT / "docs" / "skills" / "BenchTesting.md"
    assert doc.is_file(), "缺少 docs/skills/BenchTesting.md"

    text = doc.read_text(encoding="utf-8")

    # 两个技能均须覆盖
    assert "vllm-bench-testing" in text, "未覆盖 vLLM 技能"
    assert "sglang-bench-testing" in text, "未覆盖 SGLang 技能"

    # 引擎选择与环境校验（1.0.7 新增能力）
    assert "Ready" in text and "Not Satisfied" in text, "应说明环境校验状态"
    assert "benchscope" in text and "vllm-0.23" in text and "sglang-0.5.10" in text, "应列出内置引擎"

    # 流程与产物
    for kw in ("并发", "数据集", "benchmark-*.xlsx", "TPOT"):
        assert kw in text, f"应说明 {kw}"


def test_docs_index_links_skills_section():
    """docs/Readme.md 索引须登记 skills 文档章节。"""
    text = (REPO_ROOT / "docs" / "Readme.md").read_text(encoding="utf-8")
    for f in ("skills/Readme.md", "skills/BenchEngineAuthoring.md", "skills/BenchTesting.md"):
        assert f in text, f"docs/Readme.md 未登记 {f}"
