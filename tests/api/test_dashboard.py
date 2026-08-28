"""API 测试：Dashboard 首页（/api/dashboard/*）。"""

from __future__ import annotations


def test_dashboard_stats(client, base_url):
    r = client.get(f"{base_url}/api/dashboard/stats", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in ("total_runs", "running_tasks", "avg_tpot", "best_model"):
        assert key in data


def test_dashboard_env(client, base_url):
    r = client.get(f"{base_url}/api/dashboard/env", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, dict)
