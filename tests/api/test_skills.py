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

    # 参考文档齐全
    refs = d / "references"
    for f in ("engine-schema.md", "mock-core.md", "import-checklist.md"):
        assert (refs / f).is_file(), f"缺少参考文档 {f}"

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


def test_skills_readme_lists_all_skills():
    """skills/Readme.md 必须列出所有技能。"""
    readme = (SKILLS_DIR / "Readme.md").read_text(encoding="utf-8")
    for name in EXPECTED_SKILLS:
        assert name in readme, f"Readme.md 未列出技能 {name}"
