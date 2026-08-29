"""内置 bench 引擎 API：引擎清单 / 详情 / 环境校验。

环境校验约定（强制）：
  - 原生引擎（kind = vllm / sglang）：必须校验 torch 与 vllm / sglang 安装版本，
    环境不满足时 ok=False，前端禁止进入下一步（参数选择）。
  - 自研引擎（kind = builtin）：无框架环境依赖，恒 ok=True，可对远程 OpenAI 兼容服务测试。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from benchscope.benchs import (
    check_env,
    engine_summary,
    get_engine,
    import_engine_package,
    list_engines,
    load_benchs_yaml_text,
    load_engine_params,
    save_benchs_yaml_text,
    save_engine_params,
    validate_benchs_yaml,
)

# 自定义引擎的上游参考链接（按版本 tag 固定，供前端「添加自定义版本」展示）
UPSTREAM_LINKS = {
    "vllm": {
        "repo": "https://github.com/vllm-project/vllm",
        "bench_entry": "vllm/benchmarks/serve.py",
        "link_template": "https://github.com/vllm-project/vllm/blob/v{version}/vllm/benchmarks/serve.py",
        "command": "vllm bench serve",
    },
    "sglang": {
        "repo": "https://github.com/sgl-project/sglang",
        "bench_entry": "python/sglang/bench_serving.py",
        "link_template": "https://github.com/sgl-project/sglang/blob/v{version}/python/sglang/bench_serving.py",
        "command": "python -m sglang.bench_serving",
    },
}

AUTHORING_SKILL = {
    "name": "bench-engine-authoring",
    "path": "skills/bench-engine-authoring/SKILL.md",
    "readme": "skills/bench-engine-authoring/README.md",
    "description": "自定义 bench 引擎（vllm/sglang/其他版本）配置与代码生成、导入校验技能",
}
from benchscope.bench_params import get_option_description, param_specs_for_engine

log = logging.getLogger("benchscope.api_benchs")

router = APIRouter(prefix="/api/benchs", tags=["benchs"])


@router.get("")
def list_bench_engines():
    """全部内置引擎（含介绍 / 对比表 / 环境校验结果）+ 默认引擎 id。"""
    return list_engines(with_env=True)


@router.get("/authoring")
def get_authoring_guide():
    """自定义引擎开发指引：skills 技能信息与上游参考链接（按版本 tag 固定）。

    前端「添加自定义版本」据此展示：可复制的 AI 提示词 + 目标版本 GitHub 链接。
    """
    return {
        "skill": AUTHORING_SKILL,
        "upstream": UPSTREAM_LINKS,
        "prompt": _authoring_prompt(),
    }


@router.post("/upload")
async def upload_engine_package(file: UploadFile = File(...)):
    """上传引擎包并合并进引擎列表（校验通过才写入）。

    支持两类文件：
      - `.yaml` / `.yml`：引擎定义原文（含 engines 段）
      - `.tar.gz` / `.tgz`：技能包（bench-engine-authoring 打包产物），
        自动提取其中的引擎定义与参数说明

    返回 {ok, checks, added, updated, param_sections, engines}。
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="引擎包过大（上限 20MB）")
    try:
        return import_engine_package(data, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("导入引擎包失败: %s", file.filename)
        raise HTTPException(status_code=400, detail=f"导入引擎包失败: {e}")


@router.post("/import")
def import_benchs(payload: dict):
    """导入自定义引擎定义（校验成功方可导入）。

    请求体：{content: <benchs.yaml 内容>, mock_output?: <mock 输出文本>, dry_run?: bool, apply?: bool}
      - dry_run=true  → 只校验，不写文件（默认）
      - apply=true    → 校验通过后写入 configs/benchs.yaml
    响应：{ok, checks: [{item, ok, message}], engines, applied}
    """
    content = payload.get("content") or ""
    mock_output = payload.get("mock_output") or ""
    dry_run = bool(payload.get("dry_run", True))
    apply_change = bool(payload.get("apply", False))

    result = validate_benchs_yaml(content, mock_output)
    if not result["ok"] or dry_run or not apply_change:
        return {**result, "engines": [], "applied": False}

    try:
        save_benchs_yaml_text(content, mock_output)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e), "checks": result["checks"]})
    return {**result, "engines": list_engines(with_env=False)["engines"], "applied": True}


# ⚠️ 静态路径（/authoring / /import / /config/yaml）必须注册在 /{engine_id} 之前，
#    否则会被 /{engine_id} 优先匹配导致 404。
@router.get("/{engine_id}")
def get_bench_engine(engine_id: str):
    """单个引擎详情（含环境校验结果）。"""
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"未知引擎: {engine_id}")
    return engine_summary(engine, with_env=True)


@router.get("/config/yaml")
def get_benchs_yaml():
    """读取引擎定义原文（benchs.yaml），供 Settings 面板查看 / 编辑。"""
    return {"content": load_benchs_yaml_text()}


@router.put("/config/yaml")
def update_benchs_yaml(payload: dict):
    """保存引擎定义（用户自定义新增引擎 / 版本），保存前逐项校验。

    校验项：yaml / engines / id / kind / requires / params_key / option_desc / mock。
    任一项失败返回 400（含全部检查明细），**文件不被修改**。
    """
    content = payload.get("content") or ""
    mock_output = payload.get("mock_output") or ""
    try:
        result = save_benchs_yaml_text(content, mock_output)
    except ValueError as e:
        # 附带逐项检查结果，便于前端展示失败原因
        checks = validate_benchs_yaml(content, mock_output).get("checks", [])
        raise HTTPException(status_code=400, detail={"message": str(e), "checks": checks})
    return {
        "ok": True,
        "checks": result.get("checks", []),
        "engines": list_engines(with_env=False)["engines"],
    }


def _authoring_prompt() -> str:
    """生成「让 AI 生成自定义引擎」的提示词（前端可一键复制）。"""
    return """Task: create a BenchScope custom bench engine definition for <FRAMEWORK> version <VERSION>.

Steps:
1) Read the upstream bench entrypoint at the pinned tag and enumerate the REAL
   parameters at that version:
   - vLLM:   https://github.com/vllm-project/vllm/blob/v<VERSION>/vllm/benchmarks/serve.py
   - SGLang: https://github.com/sgl-project/sglang/blob/v<VERSION>/python/sglang/bench_serving.py
   Do NOT reuse parameters from another version.
2) Emit TWO yaml artifacts:
   a) an engine entry for configs/benchs.yaml:
      - id: <framework>-<version>   kind: vllm|sglang|builtin   params_key: <key>
      - name / description / highlights / requires (torch + framework, with version spec)
   b) a parameter section for configs/bench-params.yaml under key <params_key>:
      for each parameter: label, help, type, and options — EVERY option MUST have a
      non-empty description explaining what that value does.
3) If the engine needs mock/simulation output, generate it following the mock core
   contract (mocks/ only), scaling throughput/latency with concurrency and matching
   the parser regexes exactly.
4) Validate against the import checklist (yaml / engines / id / kind / requires /
   params_key exists / option descriptions / mock output) and fix all failures
   before presenting the result.
5) Output the final, importable yaml in one code block."""


@router.get("/{engine_id}/params")
def get_engine_params(engine_id: str):
    """引擎参数定义（说明文案 + 下拉选项 + 选项级描述）。

    返回 {engine_id, params_key, params: {<yaml_key>: {label, help, type, options:[{value,label,description}]}}}；
    前端据此渲染下拉控件，并在选中某选项后展示该选项的 description。
    """
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"未知引擎: {engine_id}")
    params_key = engine.get("params_key") or engine.get("kind") or ""
    return {
        "engine_id": engine_id,
        "params_key": params_key,
        "params": param_specs_for_engine(engine),
    }


@router.get("/{engine_id}/params-yaml")
def get_engine_params_yaml(engine_id: str):
    """引擎参数清单（随引擎切换，互不干扰）。

    返回 {engine_id, params_key, version, content, lines: [{key, value}]}；
    创建任务页 Step2 据此渲染「当前引擎」的参数，Step3 命令预览使用同一份参数。
    """
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"未知引擎: {engine_id}")
    return load_engine_params(engine)


class ParamsYamlUpdateRequest(BaseModel):
    content: str


@router.put("/{engine_id}/params-yaml")
def update_engine_params_yaml(engine_id: str, req: ParamsYamlUpdateRequest):
    """保存引擎参数清单（去重后写回），返回最新解析结果。"""
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"未知引擎: {engine_id}")
    return save_engine_params(engine, req.content or "")


@router.get("/{engine_id}/params/{param_key}/option-desc")
def get_param_option_desc(engine_id: str, param_key: str, value: str = ""):
    """单个参数取值的描述信息（选中后展示）。"""
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"未知引擎: {engine_id}")
    params_key = engine.get("params_key") or engine.get("kind") or ""
    return {
        "engine_id": engine_id,
        "param_key": param_key,
        "value": value,
        "description": get_option_description(params_key, param_key, value),
    }


@router.get("/{engine_id}/env-check")
def check_engine_env(engine_id: str):
    """引擎环境校验：{ok, checks: [{name, required, installed, ok, hint}]}。

    ok=False 表示环境不满足（原生引擎缺 torch / vllm / sglang 或命令不可用），
    前端应禁止进入下一步参数配置并展示 hint 安装提示。
    """
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"未知引擎: {engine_id}")
    result = check_env(engine)
    result["engine_id"] = engine_id
    result["kind"] = engine.get("kind")
    return result
