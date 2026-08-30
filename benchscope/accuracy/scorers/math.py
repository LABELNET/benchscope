"""数学判分器（GSM8K / MATH）：最终答案抽取 + 规范化等价 + exact_match。

抽取优先级：
  1. \\boxed{...}（MATH 官方口径）
  2. 显式标记：答案是 X / 答案为 X / answer is X / The answer is X / 最终答案 X
  3. 最后一行中的最后一个数值（GSM8K 常见 "#### 42" 已在数据集适配层处理）
规范化：去千分位逗号 / 货币符号 / 单位 / 百分号、分数 a/b、负号统一；
数值以 1e-6 容差比较，非数值做字符串规范化比较（小写、去空白与标点）。
"""
from __future__ import annotations

import re
from fractions import Fraction

from .base import (
    STATUS_CORRECT,
    STATUS_INVALID,
    STATUS_WRONG,
    TAG_FORMAT,
    TAG_REASON,
    Scorer,
    clean_output,
    scorer_result,
)

_BOXED_RE = re.compile(r"\\boxed\{([^{}]+)\}")
_MARK_RES = [
    re.compile(r"最终答案\s*[是为:：]?\s*(.+)"),
    re.compile(r"答案\s*[是为:：]\s*(.+)"),
    re.compile(r"answer\s*(?:is|:|：)\s*(.+)", re.IGNORECASE),
]
_NUMBER_RE = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?")


def extract_answer(output: str) -> str | None:
    """抽取最终答案文本；无法定位返回 None。"""
    text = clean_output(output)
    if not text:
        return None
    boxed = _BOXED_RE.findall(text)
    if boxed:
        return boxed[-1].strip()
    for pat in _MARK_RES:
        matches = pat.findall(text)
        if matches:
            tail = matches[-1].strip()
            tail = re.sub(r"^[\"'（(\[【\s]+|[\"'）)\]】\s.。]+$", "", tail)
            if tail:
                return tail
    # 末行最后一个数值
    for line in reversed(text.splitlines()):
        nums = _NUMBER_RE.findall(line.replace("####", ""))
        if nums:
            return nums[-1].replace(",", "")
    return None


_NUM_CLEAN_RE = re.compile(r"[$,，%％\s]|(元|美元|个|人|只|条|米|千米|公里|克|千克|小时|分钟|秒|度)$")


def normalize_number(text: str) -> float | None:
    r"""答案规范化为数值（分数 a/b、根式 \sqrt{n} 简单展开；失败返回 None）。"""
    s = (text or "").strip()
    if not s:
        return None
    s = s.replace("\\$", "$")
    sqrt_m = re.fullmatch(r"\\?sqrt\{?(-?\d+(?:\.\d+)?)\}?", s)
    if sqrt_m:
        v = float(sqrt_m.group(1))
        return v ** 0.5
    s = _NUM_CLEAN_RE.sub("", s)
    if not s or s in {"+", "-", "."}:
        return None
    if re.fullmatch(r"-?\d+/\d+", s):
        try:
            return float(Fraction(s))
        except (ZeroDivisionError, ValueError):
            return None
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        try:
            return float(s)
        except ValueError:
            return None
    return None


_TEXT_CLEAN_RE = re.compile(r"[\s.。,，、;；:：'\"!！?？]+")


def normalize_answer(text: str) -> str:
    """非数值答案的规范化（小写、去空白与常见标点、统一 π/pi）。"""
    s = (text or "").strip().lower().replace("\\pi", "pi").replace("π", "pi")
    return _TEXT_CLEAN_RE.sub("", s)


def exact_match(output: str, answer: str) -> bool | None:
    """exact_match：数值等价或规范化字符串相等；无法解析输出返回 None。"""
    extracted = extract_answer(output)
    if extracted is None:
        return None
    if normalize_answer(extracted) == normalize_answer(answer):
        return True
    a, b = normalize_number(extracted), normalize_number(answer)
    if a is not None and b is not None:
        return abs(a - b) < 1e-6
    return False


class MathScorer(Scorer):
    """数学判分：exact_match / math_accuracy，错因区分推理错误 / 输出格式错误。"""

    name = "math"

    def score(self, sample: dict, output: str) -> dict:
        answer = str(sample.get("answer") or "").strip()
        if not answer:
            return scorer_result(None, STATUS_INVALID, TAG_FORMAT, "样本缺少标准答案")
        extracted = extract_answer(output)
        if extracted is None:
            return scorer_result(None, STATUS_INVALID, TAG_FORMAT, "无法从输出解析出最终答案")
        if exact_match(output, answer):
            return scorer_result(extracted, STATUS_CORRECT, "", "")
        return scorer_result(extracted, STATUS_WRONG, TAG_REASON, f"标准答案 {answer}")
