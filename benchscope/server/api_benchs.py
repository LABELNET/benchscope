"""内置 bench 引擎 API：引擎清单 / 详情 / 环境校验。

环境校验约定（强制）：
  - 原生引擎（kind = vllm / sglang）：必须校验 torch 与 vllm / sglang 安装版本，
    环境不满足时 ok=False，前端禁止进入下一步（参数选择）。
  - 自研引擎（kind = builtin）：无框架环境依赖，恒 ok=True，可对远程 OpenAI 兼容服务测试。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from benchscope.benchs import check_env, engine_summary, get_engine, list_engines

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
