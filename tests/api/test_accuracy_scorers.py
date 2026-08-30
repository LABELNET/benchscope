"""精度判分器单元测试：客观题 / 数学 / 代码沙箱 / MT-Bench judge 解析（纯函数级）。"""

from __future__ import annotations

from benchscope.accuracy.scorers import get_scorer
from benchscope.accuracy.scorers.base import STATUS_CORRECT, STATUS_INVALID, STATUS_WRONG
from benchscope.accuracy.scorers.choice import extract_choice
from benchscope.accuracy.scorers.code import compiles, extract_code, run_program
from benchscope.accuracy.scorers.judge import parse_judge_output
from benchscope.accuracy.scorers.math import exact_match, extract_answer, normalize_number

# ---------------------------------------------------------------------------
# 客观题：选项抽取
# ---------------------------------------------------------------------------


def test_extract_choice_explicit_markers():
    assert extract_choice("分析如下……最终答案是 B") == "B"
    assert extract_choice("答案为：C") == "C"
    assert extract_choice("答案是 A。") == "A"
    assert extract_choice("The answer is D") == "D"
    assert extract_choice("Answer: (B)") == "B"
    assert extract_choice("正确选项 A") == "A"


def test_extract_choice_bare_letter_line():
    assert extract_choice("第一行\nB") == "B"
    assert extract_choice("第一行\nB.") == "B"
    assert extract_choice("A\nB\nC") == "C"  # 末行优先


def test_extract_choice_invalid_outputs():
    assert extract_choice("") is None
    assert extract_choice("我不会回答这道题") is None
    assert extract_choice("答案是 E", n_choices=4) is None  # 越界选项


def test_extract_choice_think_tags_stripped():
    assert extract_choice("<think>先分析选项 A 再看 B</think>答案是 B") == "B"


def test_choice_scorer_statuses_and_tags():
    scorer = get_scorer("choice")
    sample = {"choices": ["甲", "乙", "丙", "丁"], "answer": "B"}
    assert scorer.score(sample, "答案是 B")["status"] == STATUS_CORRECT
    wrong = scorer.score(sample, "答案是 C")
    assert wrong["status"] == STATUS_WRONG and wrong["error_tag"] == "知识错误"
    invalid = scorer.score(sample, "我不知道")
    assert invalid["status"] == STATUS_INVALID and invalid["error_tag"] == "输出格式错误"
    no_answer = scorer.score({"choices": [], "answer": ""}, "答案是 A")
    assert no_answer["status"] == STATUS_INVALID


# ---------------------------------------------------------------------------
# 数学：答案抽取 + 规范化等价
# ---------------------------------------------------------------------------


def test_extract_answer_boxed_and_markers():
    assert extract_answer(r"推理……$\boxed{42}$") == "42"
    assert extract_answer("推理……\n答案是 72") == "72"
    assert extract_answer("The answer is 3.5") == "3.5"
    assert extract_answer("毫无答案信息") is None


def test_normalize_number_variants():
    assert normalize_number("1,234") == 1234.0
    assert normalize_number("$50%") == 50.0
    assert normalize_number("3/4") == 0.75
    assert normalize_number(r"\sqrt{16}") == 4.0
    assert normalize_number("abc") is None


def test_exact_match_equivalences():
    assert exact_match("答案是 42", "42") is True
    assert exact_match("答案是 0.5", "1/2") is True
    assert exact_match(r"答案是 \boxed{1,234}", "1234") is True
    assert exact_match("答案是 41", "42") is False
    assert exact_match("无法解析", "42") is None


def test_math_scorer_statuses():
    scorer = get_scorer("math")
    sample = {"question": "1+1=?", "answer": "2"}
    assert scorer.score(sample, "推理……\n答案是 2")["status"] == STATUS_CORRECT
    wrong = scorer.score(sample, "推理……\n答案是 3")
    assert wrong["status"] == STATUS_WRONG and wrong["error_tag"] == "推理错误"
    invalid = scorer.score(sample, "完全跑题")
    assert invalid["status"] == STATUS_INVALID and invalid["error_tag"] == "输出格式错误"


# ---------------------------------------------------------------------------
# 代码：抽取 + 沙箱执行
# ---------------------------------------------------------------------------


def test_extract_code_variants():
    assert extract_code("```python\ndef f():\n    return 1\n```") == "def f():\n    return 1"
    assert extract_code("说明\n```python\ncode1\n```\n中间\n```python\ncode2\n```") == "code2"
    assert extract_code("def g():\n    pass") == "def g():\n    pass"


def test_compiles_check():
    assert compiles("def f():\n    return 1")
    assert not compiles("def f(:\n    bad")
    assert not compiles("")


def test_run_program_pass_and_fail():
    ok, err = run_program("print('hi')")
    assert ok and err == ""
    ok, err = run_program("raise ValueError('boom')")
    assert not ok and "boom" in err
    ok, err = run_program("", timeout=5)
    assert not ok


def test_run_program_timeout():
    ok, err = run_program("while True:\n    pass\n", timeout=2)
    assert not ok and "超时" in err


def test_code_scorer_humaneval_and_mbpp():
    scorer = get_scorer("code")
    humaneval = {
        "prompt": "def add(a, b):\n    \"\"\"Return a + b\"\"\"\n",
        "test": "def check(candidate):\n    assert candidate(1, 2) == 3\n    assert candidate(-1, 1) == 0\n",
        "entry_point": "add",
    }
    good = scorer.score(humaneval, "```python\ndef add(a, b):\n    return a + b\n```")
    assert good["status"] == STATUS_CORRECT
    wrong = scorer.score(humaneval, "```python\ndef add(a, b):\n    return a - b\n```")
    assert wrong["status"] == STATUS_WRONG and wrong["error_tag"] == "执行错误"

    mbpp = {"text": "max of two", "test_list": ["assert f(1, 2) == 2", "assert f(5, 3) == 5"], "entry_point": "f"}
    ok = scorer.score(mbpp, "```python\ndef f(a, b):\n    return max(a, b)\n```")
    assert ok["status"] == STATUS_CORRECT
    syntax = scorer.score(mbpp, "```python\ndef f(a, b)\n    return\n```")
    assert syntax["status"] == STATUS_WRONG and "语法" in syntax["detail"]


# ---------------------------------------------------------------------------
# judge：评审输出解析
# ---------------------------------------------------------------------------


def test_parse_judge_output_json_and_fallback():
    parsed = parse_judge_output('{"score": 8, "helpfulness": 8, "truthfulness": 7, "harmlessness": 9}')
    assert parsed and parsed["score"] == 8.0 and parsed["harmlessness"] == 9.0
    fallback = parse_judge_output("我认为得分为 7/10")
    assert fallback and fallback["score"] == 7.0
    assert parse_judge_output("无法评分") is None
