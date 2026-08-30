"""判分器注册表：按数据集 eval.scorer 绑定对应判分器。"""
from __future__ import annotations

from .base import Scorer, STATUS_CORRECT, STATUS_INVALID, STATUS_WRONG
from .choice import ChoiceScorer, extract_choice
from .code import CodeScorer, build_program, compiles, extract_code, run_program
from .judge import JudgeScorer, judge_turn, parse_judge_output
from .math import MathScorer, exact_match, extract_answer, normalize_answer, normalize_number

_SCORERS: dict[str, Scorer] = {
    "choice": ChoiceScorer(),
    "math": MathScorer(),
    "code": CodeScorer(),
    "judge": JudgeScorer(),
}


def get_scorer(name: str) -> Scorer:
    """按名称取判分器（未知名称回退 math——自定义数据集默认答案精确匹配）。"""
    return _SCORERS.get(name) or _SCORERS["math"]


def scorer_names() -> list[str]:
    return list(_SCORERS.keys())
