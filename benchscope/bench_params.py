"""引擎参数定义加载（描述信息 + 下拉选项）。

数据源：benchscope/configs/bench-params.yaml（yaml 驱动，用户可扩展）。

每个参数可包含：
  - label / help：参数名与说明
  - type：str | int | float | bool | select
  - options：可选值列表，每项含 value / label / description（选中后展示描述信息）

前端在创建页 Step2 参数面板中据此渲染下拉控件，并在选中后展示选项级描述。

注意：模块名不能为 `benchs`（与 `benchscope/benchs.py` 引擎注册表模块同名会冲突），
故命名为 `bench_params`。
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

log = logging.getLogger("benchscope.bench_params")

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
PARAMS_YAML = CONFIGS_DIR / "bench-params.yaml"


def load_all_param_specs() -> dict:
    """全部参数定义：{params_key: {yaml_key: spec}}。"""
    if not PARAMS_YAML.exists():
        log.warning("bench-params.yaml 不存在: %s", PARAMS_YAML)
        return {}
    try:
        data = yaml.safe_load(PARAMS_YAML.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        log.exception("解析 bench-params.yaml 失败")
        return {}


def load_param_specs(params_key: str) -> dict:
    """按 params_key（vllm / sglang / benchscope）加载参数定义。"""
    return load_all_param_specs().get(params_key, {}) or {}


def normalize_key(yaml_key: str) -> str:
    """归一化参数 key（去空格）。"""
    return (yaml_key or "").strip()


def param_specs_for_engine(engine: dict) -> dict:
    """按引擎定义取参数集：优先 params_key，缺省回退 kind。"""
    key = engine.get("params_key") or engine.get("kind") or ""
    return load_param_specs(key)


def get_param_spec(params_key: str, yaml_key: str) -> dict:
    """单个参数的定义（无定义时返回空 dict）。"""
    return load_param_specs(params_key).get(normalize_key(yaml_key), {}) or {}


def get_option_description(params_key: str, yaml_key: str, value: str) -> str:
    """取某个参数取值的描述信息（选中后展示）。"""
    spec = get_param_spec(params_key, yaml_key)
    for opt in spec.get("options") or []:
        if isinstance(opt, dict) and str(opt.get("value")) == str(value):
            return opt.get("description") or ""
    return ""
