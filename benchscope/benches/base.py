"""bench 命令构建的公共定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParamDef:
    """UI 表单中一个可配置参数的定义。"""

    key: str          # 表单字段名
    flag: str         # 实际 CLI flag，如 "--temperature"
    label: str        # 中文标签
    help: str = ""
    type: str = "str"  # str | int | float | bool | select
    default: Any = None
    options: list = field(default_factory=list)
    advanced: bool = False  # 是否归入“高级参数”折叠区


@dataclass
class BenchOptions:
    """一次 bench 执行所需的全部选项。"""

    framework: str
    model: str
    api: dict            # {host, port, base_url, endpoint, api_key, extra_headers}
    dataset: dict        # {type, path, input_len, output_len, sharegpt_output_len}
    concurrency: int
    request_rate: str | float = "inf"
    curated: dict = field(default_factory=dict)   # 表单参数 key -> value
    extra_args: list = field(default_factory=list)  # [{"flag": "--x", "value": "y"}]


def build_arg_list(flags: list[list]) -> list[str]:
    """将 [["--flag","value"], ["--bool",""]] 展开为命令行列表。"""
    out: list[str] = []
    for item in flags:
        flag, value = item[0], item[1] if len(item) > 1 else ""
        if isinstance(value, bool):
            if value:
                out.append(flag)
            continue
        if value is None or value == "":
            out.append(flag)
        else:
            out.extend([flag, str(value)])
    return out


def flag_value(flag: str, value: Any) -> list[str]:
    """单个 flag 的展开（供参数校验后使用）。"""
    return build_arg_list([[flag, value]])
