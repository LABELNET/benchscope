"""MT-Bench 判分器（LLM-as-judge）：评审模型打分（1–10 + 分项）。

流程（与执行器协作，两轮对话已由 executor 生成）：
  1. 第 1 轮问题直接提问；第 2 轮携带第 1 轮问答作为上下文；
  2. 对每轮回答调用评审模型（judge_model，走同一 Serving 调用底座）；
  3. 评审 prompt 要求输出 JSON：{"score": 1-10, "helpfulness": 1-10,
     "truthfulness": 1-10, "harmlessness": 1-10}；
  4. JSON 解析失败回退正则抽取首个 1–10 数值；再失败该轮重评一次，
     仍失败标记 judge 异常（invalid）。
指标：单轮得分、多轮平均分 mt_bench_score（0–10 行业口径）、分项得分均值。
"""
from __future__ import annotations

import json
import re

from .base import (
    STATUS_CORRECT,
    STATUS_INVALID,
    STATUS_WRONG,
    TAG_JUDGE,
    Scorer,
    scorer_result,
)

JUDGE_PROMPT = """You are a helpful and strict assistant for evaluating the quality of AI assistant responses.
Please rate the quality of the AI assistant's answer to the user question on a scale of 1 to 10
(10 = excellent, 1 = poor), considering helpfulness, truthfulness and harmlessness.

[User Question]
{question}

[Assistant Answer]
{answer}

Respond with a single JSON object only, in the format:
{{"score": <1-10>, "helpfulness": <1-10>, "truthfulness": <1-10>, "harmlessness": <1-10>}}"""

_SCORE_JSON_RE = re.compile(r"\{[^{}]*\"score\"[^{}]*\}", re.DOTALL)
_SCORE_NUM_RE = re.compile(r"\b(\d+)\b")


def parse_judge_output(output: str) -> dict | None:
    """解析评审输出：优先 JSON 对象，回退首个 1–10 数值（仅 score）。"""
    text = (output or "").strip()
    m = _SCORE_JSON_RE.search(text)
    if m:
        try:
            data = json.loads(m.group(0))
            score = float(data.get("score"))
            if 0 < score <= 10:
                return {
                    "score": score,
                    "helpfulness": _sub(data.get("helpfulness"), score),
                    "truthfulness": _sub(data.get("truthfulness"), score),
                    "harmlessness": _sub(data.get("harmlessness"), score),
                }
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    nums = [float(n) for n in _SCORE_NUM_RE.findall(text) if 0 < float(n) <= 10]
    if nums:
        return {"score": nums[0], "helpfulness": nums[0], "truthfulness": nums[0], "harmlessness": nums[0]}
    return None


def _sub(value, fallback: float) -> float:
    try:
        v = float(value)
        return v if 0 < v <= 10 else fallback
    except (TypeError, ValueError):
        return fallback


def judge_turn(infer_fn, question: str, answer: str, retries: int = 1) -> dict | None:
    """调用评审模型评单一轮（解析失败重评一次），失败返回 None。"""
    prompt = JUDGE_PROMPT.format(question=question, answer=answer)
    for _ in range(retries + 1):
        out = infer_fn(prompt)
        parsed = parse_judge_output(out or "")
        if parsed:
            return parsed
    return None


class JudgeScorer(Scorer):
    """MT-Bench 判分：单轮 / 多轮 / 分项得分（sample["judge_result"] 由执行器填充）。"""

    name = "judge"

    def score(self, sample: dict, output: str) -> dict:
        # judge 数据集的实际判分在执行器两轮生成后完成（见 executor.run_eval）；
        # 此接口兼容直接调用：从 sample.judge_result 读取评审结果。
        detail = sample.get("judge_result") or {}
        scores = detail.get("scores") or []
        if not scores:
            return scorer_result(None, STATUS_INVALID, TAG_JUDGE, "缺少评审结果")
        valid = [s for s in scores if s]
        if not valid:
            return scorer_result(None, STATUS_INVALID, TAG_JUDGE, "评审模型评分全部失败")
        avg = sum(s["score"] for s in valid) / len(valid)
        status = STATUS_CORRECT if avg >= 6 else STATUS_WRONG
        if len(valid) < len(scores):
            return scorer_result(round(avg, 2), STATUS_INVALID, TAG_JUDGE, "部分轮次评审失败")
        return scorer_result(
            round(avg, 2), status, "", json.dumps(detail, ensure_ascii=False)
        )
