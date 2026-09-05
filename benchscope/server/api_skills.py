"""内置技能清单（Settings → Skills）。

技能本体位于 benchscope/skills/<skill-id>/SKILL.md（frontmatter: name/description/version），
随包分发（package-data `skills/**/*`），接口返回每个技能的元数据与提示词全文，
供前端技能面板展示、复制与下载。
"""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

log = logging.getLogger("benchscope.api_skills")

router = APIRouter(prefix="/api/skills", tags=["skills"])

_SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

# 内置技能补充元数据（SKILL.md frontmatter 之外的展示字段；features/prompt/description 均为中英双语）
_SKILL_EXTRA = {
    "bs-engine-create": {
        "name": "bs-engine-create",
        "description_zh": "创建自定义 Bench Engine（vLLM/SGLang 等）压缩包：导入时校验 + Mock 数据验证 + 功能动态注册",
        "features": [
            "Define a custom bench engine (vllm / sglang or any version) from yaml",
            "Produce an engine package (engine def + params + mock logic); validate + mock-check on import",
            "Dynamically register the engine (usable in task creation right after import)",
        ],
        "features_zh": [
            "基于 yaml 定义自定义 bench 引擎（vllm / sglang 及任意版本）",
            "生成引擎压缩包（含引擎定义 + 参数说明 + mock 逻辑），导入时校验与 mock 数据验证",
            "引擎功能动态注册（导入成功后即可在创建任务中选择使用）",
        ],
        # 操作提示词：引导用户输入框架及其版本，生成对应的 bench engine 压缩包
        "prompt": (
            "You are using the bs-engine-create skill: create a Bench Engine.\n"
            "Follow these steps:\n"
            "1. Ask the user which inference framework and version to build the bench engine for "
            "(e.g. vllm, sglang, with a concrete version like vllm 0.28 / sglang 0.5.10; any version or built-in benchscope is OK).\n"
            "2. Based on the framework & version, generate the engine package: engine definition (benchs.yaml entry), "
            "parameter specs (bench-params.yaml), and mock logic (mocks/).\n"
            "3. On import, run validation and Mock data verification (mock output matches metric regex); after passing, the engine is dynamically registered.\n"
            "Ask the user to input the framework and its version, then continue."
        ),
        "prompt_zh": (
            "你正在使用 bs-engine-create 技能：创建 Bench Engine。\n"
            "请按以下步骤操作：\n"
            "1. 询问用户要创建哪个推理框架的 bench 引擎及其版本（例如：vllm、sglang，"
            "并输入具体版本号，如 vllm 0.28 / sglang 0.5.10；也支持任意版本或自研 benchscope）。\n"
            "2. 根据所选框架与版本，生成引擎压缩包：包含引擎定义（benchs.yaml 条目）、"
            "参数说明（bench-params.yaml）、以及 mock 逻辑（mocks/）。\n"
            "3. 压缩包导入时做校验与 Mock 数据验证（mock 输出命中指标正则），通过后引擎功能动态注册。\n"
            "请让用户输入框架及其版本后继续。"
        ),
    },
    "bs-perfs-concurrency": {
        "name": "bs-perfs-concurrency",
        "description_zh": "安装 benchscope，用 benchscope perf 进行并发（concurrency）压测：内置表单 + 保存任务/日志 + 生成可导入 Datas/perfs 的压缩包",
        "features": [
            "Install benchscope and run concurrency benchmark via the benchscope perf command",
            "Built-in simple form to configure parameters for a quick test",
            "Save task & log data into a package importable in the Datas/perfs page",
        ],
        "features_zh": [
            "安装 benchscope 并用 benchscope perf 命令进行并发（concurrency）压测",
            "内置简单表单参数配置页面，填写参数即可快速测试",
            "保存任务与日志数据，生成压缩包产物，可在网页 Datas/perfs 导入",
        ],
        "prompt": (
            "You are using the bs-perfs-concurrency skill: concurrency benchmark.\n"
            "Follow these steps:\n"
            "1. Install benchscope (pip install benchscope).\n"
            "2. Show the built-in simple form and ask the user for parameters: model (--model), base URL (--base-url), "
            "concurrency (--concurrency), num prompts (--num-prompts), input/output length, request rate, timeout, etc.\n"
            "3. Run `benchscope perf` for the concurrency benchmark based on the form.\n"
            "4. Save the task & log data (run.json + perf_<run_id>_*.log) into a zip package.\n"
            "5. Guide the user to import the package in the Datas/perfs page.\n"
            "Ask the user to input the model and base URL, then continue."
        ),
        "prompt_zh": (
            "你正在使用 bs-perfs-concurrency 技能：并发压测。\n"
            "请按以下步骤操作：\n"
            "1. 安装 benchscope（pip install benchscope）。\n"
            "2. 展示内置简单表单，询问用户填写参数：被测模型（--model）、服务地址（--base-url）、"
            "并发数（--concurrency）、请求总数（--num-prompts）、输入/输出长度、请求速率、超时等。\n"
            "3. 依据表单执行 `benchscope perf` 命令进行 concurrency 压测。\n"
            "4. 保存任务与日志数据（run.json + perf_<run_id>_*.log），生成压缩包（zip）。\n"
            "5. 指导用户在网页 Datas/perfs 导入该压缩包。\n"
            "请让用户输入模型与服务地址后继续。"
        ),
    },
    "bs-perfs-threshold": {
        "name": "bs-perfs-threshold",
        "description_zh": "安装 benchscope，用 benchscope perf --mode threshold 进行阈值搜索压测：内置表单 + 保存任务/日志 + 生成可导入 Datas/perfs 的压缩包",
        "features": [
            "Install benchscope and run threshold (best-concurrency search) benchmark via benchscope perf --mode threshold",
            "Built-in simple form to configure parameters for a quick test",
            "Save task & log data into a package importable in the Datas/perfs page",
        ],
        "features_zh": [
            "安装 benchscope 并用 benchscope perf 命令进行阈值（threshold）搜索压测",
            "内置简单表单参数配置页面，填写参数即可快速测试",
            "保存任务与日志数据，生成压缩包产物，可在网页 Datas/perfs 导入",
        ],
        "prompt": (
            "You are using the bs-perfs-threshold skill: threshold benchmark.\n"
            "Follow these steps:\n"
            "1. Install benchscope (pip install benchscope).\n"
            "2. Show the built-in simple form and ask the user for parameters: model (--model), base URL (--base-url), "
            "TTFT/TPOT/throughput thresholds, search cap, max requests, etc.\n"
            "3. Run `benchscope perf --mode threshold` to search the max concurrency that still meets the thresholds (best_concurrency).\n"
            "4. Save the task & log data (run.json + perf_<run_id>_*.log) into a zip package.\n"
            "5. Guide the user to import the package in the Datas/perfs page.\n"
            "Ask the user to input the model and threshold parameters, then continue."
        ),
        "prompt_zh": (
            "你正在使用 bs-perfs-threshold 技能：阈值搜索压测。\n"
            "请按以下步骤操作：\n"
            "1. 安装 benchscope（pip install benchscope）。\n"
            "2. 展示内置简单表单，询问用户填写参数：被测模型（--model）、服务地址（--base-url）、"
            "TTFT/TPOT/吞吐阈值、搜索上限、最大请求数等。\n"
            "3. 依据表单执行 `benchscope perf --mode threshold` 命令，搜索满足阈值的最大并发（best_concurrency）。\n"
            "4. 保存任务与日志数据（run.json + perf_<run_id>_*.log），生成压缩包（zip）。\n"
            "5. 指导用户在网页 Datas/perfs 导入该压缩包。\n"
            "请让用户输入模型与阈值参数后继续。"
        ),
    },
}

_USAGE = [
    "Download the skill: download the skill package (.tar.gz) and import it into any agents platform that supports skills.",
    "Copy the prompt: send the prompt below to an AI assistant to run the workflow.",
]
_USAGE_ZH = [
    "下载技能：下载技能包（.tar.gz），导入其他可使用 skills 的 agents 平台即可使用",
    "复制提示词：将下方提示词发送给 AI 助手，按流程完成对应测试",
]


def _parse_frontmatter(text: str) -> dict:
    """解析 SKILL.md 的 YAML frontmatter（--- 分隔），支持 >- 折叠描述。"""
    meta: dict = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return meta
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.lstrip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.startswith(">-"):
            parts = [value[2:].strip()]
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].strip() == ""):
                if lines[i].strip():
                    parts.append(lines[i].strip())
                i += 1
            meta[key] = " ".join(parts).strip()
            continue
        meta[key] = value
        i += 1
    return meta


def _collect_skills() -> list:
    if not _SKILLS_DIR.is_dir():
        return []
    skills = []
    for child in sorted(_SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        skill_file = child / "SKILL.md"
        if not skill_file.is_file():
            continue
        try:
            text = skill_file.read_text(encoding="utf-8")
        except OSError:
            log.warning("read SKILL.md failed: %s", skill_file)
            continue
        meta = _parse_frontmatter(text)
        skill_id = meta.get("name") or child.name
        extra = _SKILL_EXTRA.get(child.name, {})
        # 默认 language 字段（英文，用于 option-desc 等兼容）；另附 *_zh 中文，前端按 locale 选择
        prompt_text = extra.get("prompt") or text
        features_en = extra.get("features") or []
        features_zh = extra.get("features_zh") or features_en
        usage_en = list(_USAGE)
        usage_zh = list(_USAGE_ZH)
        skills.append(
            {
                "id": skill_id,
                "name": extra.get("name") or skill_id.replace("-", " ").title(),
                "version": meta.get("version", "1.0.0"),
                "description": meta.get("description", ""),
                "description_zh": extra.get("description_zh") or meta.get("description", ""),
                "features": features_en,
                "features_zh": features_zh,
                "usage": usage_en,
                "usage_zh": usage_zh,
                # 优先用精简操作提示词（引导用户输入参数）；无则回退 SKILL.md 全文
                "prompt": prompt_text,
                "prompt_zh": extra.get("prompt_zh") or prompt_text,
                "download": {
                    "name": "SKILL.md",
                    "path": f"skills/{child.name}/SKILL.md",
                },
                "download_url": f"/api/skills/{child.name}/download",
                "package": {
                    "name": f"{child.name}-{meta.get('version', '1.0.0')}.tar.gz",
                    "path": f"skills/{child.name}/dist/{child.name}-{meta.get('version', '1.0.0')}.tar.gz",
                },
            }
        )
    return skills


@router.get("")
def get_skills():
    return {"skills": _collect_skills()}


def _skill_dir(skill_id: str) -> Path:
    """按技能 id（目录名）定位技能目录。"""
    d = _SKILLS_DIR / skill_id
    if not d.is_dir() or not (d / "SKILL.md").is_file():
        return Path()
    return d


@router.get("/{skill_id}/download")
def download_skill(skill_id: str):
    """下载技能版本包（tar.gz）。

    优先返回 skills/<skill_id>/dist/<skill_id>-<version>.tar.gz（已发版的本地产物）；
    若未发版，则实时按 package.sh 打包一次返回。版本号取自 SKILL.md frontmatter。
    """
    from fastapi.responses import FileResponse

    d = _skill_dir(skill_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"未知技能: {skill_id}")

    # 从 SKILL.md 读取版本号
    version = ""
    try:
        meta = _parse_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        version = meta.get("version", "")
    except OSError:
        pass

    dist = d / "dist"
    archive = dist / f"{skill_id}-{version}.tar.gz" if version else None
    if archive and archive.is_file():
        return FileResponse(
            archive,
            media_type="application/gzip",
            filename=archive.name,
        )

    # 未发版：实时打包一次返回
    pkg = d / "scripts" / "package.sh"
    if not pkg.is_file():
        raise HTTPException(status_code=404, detail=f"技能 {skill_id} 无打包脚本")
    import tempfile
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["bash", str(pkg), tmp], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise HTTPException(status_code=500, detail=f"技能打包失败: {r.stderr or r.stdout}")
        files = [p for p in Path(tmp).glob("*.tar.gz")]
        if not files:
            raise HTTPException(status_code=500, detail=f"技能打包未产出 tar.gz")
        return FileResponse(
            files[0],
            media_type="application/gzip",
            filename=files[0].name,
        )
