"""内置 bench 引擎 API：引擎清单 / 详情 / 环境校验。

环境校验约定（强制）：
  - 原生引擎（kind = vllm / sglang）：必须校验 torch 与 vllm / sglang 安装版本，
    环境不满足时 ok=False，前端禁止进入下一步（参数选择）。
  - 自研引擎（kind = builtin）：无框架环境依赖，恒 ok=True，可对远程 OpenAI 兼容服务测试。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from benchscope.benchs import (
    check_env,
    engine_summary,
    get_engine,
    list_engines,
    load_benchs_yaml_text,
    save_benchs_yaml_text,
)
from benchscope.bench_params import get_option_description, param_specs_for_engine

log = logging.getLogger("benchscope.api_benchs")

router = APIRouter(prefix="/api/benchs", tags=["benchs"])


@router.get("")
def list_bench_engines():
    """全部内置引擎（含介绍 / 对比表 / 环境校验结果）+ 默认引擎 id。"""
    return list_engines(with_env=True)


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
    """保存引擎定义（用户自定义新增引擎 / 版本）。

    校验失败（YAML 非法 / 缺 engines / 引擎缺 id / kind 不合法）返回 400，文件不被修改。
    """
    content = payload.get("content") or ""
    try:
        save_benchs_yaml_text(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "engines": list_engines(with_env=False)["engines"]}


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
