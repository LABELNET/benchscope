"""精度判分器基类与公共工具。

判分器接口（scorers 注册表按数据集 eval.scorer 绑定）：

    class Scorer:
        def score(self, sample: dict, output: str) -> dict:
            return {"extracted": ..., "status": "correct|wrong|invalid",
                    "error_tag": ..., "detail": ...}

错因标签约定：
  - 输出格式错误：输出为空 / 截断 / 无法解析出答案
  - 知识错误：客观题解析成功但选项不符
  - 推理错误：数学答案解析成功但不匹配
  - 执行错误：代码沙箱执行异常 / 超时
  - judge 异常：评审模型评分解析失败
"""
from __future__ import annotations

STATUS_CORRECT = "correct"
STATUS_WRONG = "wrong"
STATUS_INVALID = "invalid"

TAG_FORMAT = "输出格式错误"
TAG_KNOWLEDGE = "知识错误"
TAG_REASON = "推理错误"
TAG_EXEC = "执行错误"
TAG_JUDGE = "judge 异常"


def scorer_result(extracted, status: str, error_tag: str = "", detail: str = "") -> dict:
    return {"extracted": extracted, "status": status, "error_tag": error_tag, "detail": detail}


class Scorer:
    """判分器接口。"""

    name = "base"

    def score(self, sample: dict, output: str) -> dict:  # pragma: no cover - 接口
        raise NotImplementedError


def strip_think(output: str) -> str:
    """剥离 <think>...</think> 思考内容（对齐 Sessions 的思考/正文分离语义）。"""
    import re

    return re.sub(r"<think>.*?</think>", "", output or "", flags=re.DOTALL).strip()


def clean_output(output: str) -> str:
    """判分前清理：剥思考标签、去首尾空白。"""
    return strip_think(output or "").strip()
