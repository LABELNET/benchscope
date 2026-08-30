"""客观题判分器（MMLU / CMMLU / C-Eval / GAOKAO-Bench）：选项抽取 + 分学科。

答案抽取多策略（按置信顺序）：
  1. 显式标记：答案是 X / 答案为 X / 答案：X / answer is X / Answer: X / 正确选项 X / 选 X
  2. 独立字母行：`A` / `A.` / `A、`
  3. 括号/方括号包裹：(A) / 【A】
  4. 末行首个孤立的选项字母
解析失败 → invalid（输出格式错误）；解析成功但不符 → wrong（知识错误）。
"""
from __future__ import annotations

import re

from .base import (
    STATUS_CORRECT,
    STATUS_INVALID,
    STATUS_WRONG,
    TAG_FORMAT,
    TAG_KNOWLEDGE,
    Scorer,
    clean_output,
    scorer_result,
)

_LETTERS = "ABCDEFGH"

# 显式答案标记（中英）
_MARK_PATTERNS = [
    re.compile(r"答案\s*[是为]?\s*[:：]?\s*\**([A-H])\**"),
    re.compile(r"answer\s*(?:is|:|：)\s*\**([A-H])\**", re.IGNORECASE),
    re.compile(r"正确(?:选项|答案)\s*[是为:：]?\s*\**([A-H])\**"),
    re.compile(r"选\s*\**([A-H])\**"),
    re.compile(r"^\s*\**([A-H])\**\s*[.。、:：]?\s*$", re.MULTILINE),
    re.compile(r"[（(【\[]\s*([A-H])\s*[)）】\]]"),
]


def extract_choice(output: str, n_choices: int = 4) -> str | None:
    """从模型输出中抽取选项字母（A-H），失败返回 None。"""
    text = clean_output(output)
    if not text:
        return None
    allowed = _LETTERS[: max(1, min(n_choices, len(_LETTERS)))]
    # ① 显式标记
    for pat in _MARK_PATTERNS[:4]:
        matches = pat.findall(text)
        if matches:
            candidate = matches[-1].upper()
            if candidate in allowed:
                return candidate
    # ② 独立字母行
    for line in reversed(text.splitlines()):
        m = re.fullmatch(r"\s*\**([A-H])\**\s*[.。、:：]?\s*", line.strip())
        if m and m.group(1) in allowed:
            return m.group(1)
    # ③ 括号包裹
    m = _MARK_PATTERNS[5].search(text)
    if m and m.group(1) in allowed:
        return m.group(1)
    # ④ 末行行首孤立字母（如 "A 是正确答案"）
    for line in reversed(text.splitlines()):
        m = re.match(r"\s*\**([A-H])\**(\s|$)", line.strip())
        if m and m.group(1) in allowed:
            return m.group(1)
    return None


class ChoiceScorer(Scorer):
    """客观题判分：accuracy 主指标，错因区分知识错误 / 输出格式错误。"""

    name = "choice"

    def score(self, sample: dict, output: str) -> dict:
        n_choices = len(sample.get("choices") or []) or 4
        extracted = extract_choice(output, n_choices)
        answer = str(sample.get("answer") or "").strip().upper()
        if not answer:
            return scorer_result(extracted, STATUS_INVALID, TAG_FORMAT, "样本缺少标准答案")
        if extracted is None:
            return scorer_result(None, STATUS_INVALID, TAG_FORMAT, "无法从输出解析出选项字母")
        if extracted == answer:
            return scorer_result(extracted, STATUS_CORRECT, "", "")
        return scorer_result(extracted, STATUS_WRONG, TAG_KNOWLEDGE, f"标准答案 {answer}")
