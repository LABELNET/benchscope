"""pytest 公共 fixtures：被测服务地址与 HTTP 客户端。"""

from __future__ import annotations

import os

import pytest
import requests

from tests.helpers import MOCK_URL
import tests.helpers as helpers

# 被测服务地址（由 run_tests.sh 注入，默认 http://127.0.0.1:18081）
BASE_URL = os.environ.get("BS_TEST_URL", "http://127.0.0.1:18081")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def mock_url() -> str:
    return MOCK_URL


@pytest.fixture(scope="session", autouse=True)
def point_to_mock(base_url: str):
    """会话级前置：将推理服务指向 mock（隔离测试环境）。

    autouse 且 session 级 —— WebUI 测试不依赖 client fixture，单独增量跑
    tests/webui 时也必须先把 base_url 指向 mock，否则创建任务页模型列表
    502、Step1 校验不通过（此前增量跑 WebUI 需靠 API 测试先跑才间接配置）。
    """
    s = requests.Session()

    def ready():
        try:
            return s.get(f"{base_url}/api/version", timeout=2).status_code == 200
        except Exception:
            return False

    helpers.wait_until(ready, timeout=60, msg="benchscope 服务未就绪（请先执行 ./tests/run_tests.sh）")

    r = s.post(f"{base_url}/api/config", json={"api": {"base_url": MOCK_URL}}, timeout=10)
    assert r.status_code == 200, f"设置 mock 推理地址失败: {r.status_code} {r.text}"


@pytest.fixture(scope="session")
def client(base_url: str) -> requests.Session:
    """就绪探活（mock 指向由 point_to_mock 完成）+ 返回 HTTP 会话。"""
    s = requests.Session()
    helpers.wait_until(
        lambda: s.get(f"{base_url}/api/version", timeout=2).status_code == 200,
        timeout=60,
        msg="benchscope 服务未就绪（请先执行 ./tests/run_tests.sh）",
    )
    return s
