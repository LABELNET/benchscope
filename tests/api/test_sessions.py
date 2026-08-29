"""API 测试：会话（/api/sessions*），含 SSE 流式对话（走 mock 推理服务）。"""

from __future__ import annotations

import pytest

import tests.helpers as helpers
from tests.helpers import MOCK_URL


@pytest.fixture(scope="module")
def created_session(client, base_url):
    r = client.post(f"{base_url}/api/sessions", json={"title": "测试会话", "model": ""}, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()["session"]


def test_create_list_get(created_session, client, base_url):
    sid = created_session["session_id"]
    r = client.get(f"{base_url}/api/sessions", timeout=10)
    assert r.status_code == 200, r.text
    sessions = r.json()["sessions"]
    assert any(s["session_id"] == sid for s in sessions)

    r = client.get(f"{base_url}/api/sessions/{sid}", timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["session_id"] == sid
    assert "messages" in r.json()


def test_update_perf(created_session, client, base_url):
    sid = created_session["session_id"]
    r = client.patch(f"{base_url}/api/sessions/{sid}/perf", json={"perf": {"note": "hello"}}, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_chat_sse(created_session, client, base_url):
    """SSE 流式对话：mock 推理服务应流式返回内容并结束。"""
    sid = created_session["session_id"]
    r = client.post(
        f"{base_url}/api/sessions/{sid}/chat",
        json={"message": "你好", "model": "", "enable_thinking": False},
        timeout=30,
        stream=True,
    )
    assert r.status_code == 200, r.text
    assert "text/event-stream" in r.headers.get("content-type", "")

    events = []
    for raw in r.iter_lines(decode_unicode=True):
        if not raw:
            continue
        assert raw.startswith("data: "), f"非 SSE 行: {raw!r}"
        events.append(raw)
    assert len(events) > 0

    # 最后一个事件应为结束标记（[DONE] 或 done 字段）
    last = events[-1]
    assert "DONE" in last or '"done"' in last or '"done":' in last


def test_delete_session(created_session, client, base_url):
    sid = created_session["session_id"]
    r = client.delete(f"{base_url}/api/sessions/{sid}", timeout=10)
    assert r.status_code == 200 and r.json()["ok"] is True
    r = client.get(f"{base_url}/api/sessions/{sid}", timeout=10)
    assert r.status_code == 404


def test_unknown_session_404(client, base_url):
    r = client.get(f"{base_url}/api/sessions/nope", timeout=10)
    assert r.status_code == 404
    r = client.post(f"{base_url}/api/sessions/nope/chat", json={"message": "hi"}, timeout=10)
    assert r.status_code == 404


def test_clear_sessions(client, base_url):
    r = client.delete(f"{base_url}/api/sessions", timeout=10)
    assert r.status_code == 200 and r.json()["ok"] is True
    r = client.get(f"{base_url}/api/sessions", timeout=10)
    assert r.json()["sessions"] == []


def _chat_events(client, base_url, sid, body):
    r = client.post(
        f"{base_url}/api/sessions/{sid}/chat",
        json=body,
        timeout=30,
        stream=True,
    )
    assert r.status_code == 200, r.text
    assert "text/event-stream" in r.headers.get("content-type", "")
    events = []
    for raw in r.iter_lines(decode_unicode=True):
        if not raw:
            continue
        assert raw.startswith("data: "), f"非 SSE 行: {raw!r}"
        events.append(raw)
    assert events, "应至少有一个 SSE 事件"
    return events


def test_chat_with_provider_id(client, base_url):
    """会话 Provider 链路：chat 请求带 provider_id 时使用对应 Provider 的 API 配置（指向 mock），
    并将 provider_id 持久化到会话。"""
    r = client.post(
        f"{base_url}/api/config/providers",
        json={"name": "Sess Mock", "base_url": MOCK_URL, "endpoint": "/v1/chat/completions"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["provider"]["id"]
    try:
        r = client.post(f"{base_url}/api/sessions", json={"title": "Provider 会话", "model": ""}, timeout=10)
        assert r.status_code == 200, r.text
        sid = r.json()["session"]["session_id"]

        events = _chat_events(client, base_url, sid, {"message": "你好", "model": "test-model", "provider_id": pid})
        assert not any('"error"' in ev for ev in events), f"Provider 对话不应报错: {events}"
        last = events[-1]
        assert "DONE" in last or '"done"' in last or '"done":' in last

        # provider_id 持久化到会话
        r = client.get(f"{base_url}/api/sessions/{sid}", timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("provider_id") == pid
    finally:
        client.delete(f"{base_url}/api/config/providers/{pid}", timeout=10)


def test_chat_invalid_provider_uses_own_config(client, base_url):
    """Provider 配置真实生效：指向不可达地址的 Provider 对话应失败（而非回退全局 mock）。"""
    r = client.post(
        f"{base_url}/api/config/providers",
        json={"name": "Sess Bad", "base_url": "http://127.0.0.1:9", "endpoint": "/v1/chat/completions"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["provider"]["id"]
    try:
        r = client.post(f"{base_url}/api/sessions", json={"title": "Bad 会话", "model": ""}, timeout=10)
        assert r.status_code == 200, r.text
        sid = r.json()["session"]["session_id"]

        events = _chat_events(client, base_url, sid, {"message": "hi", "provider_id": pid})
        assert any('"error"' in ev for ev in events), f"指向不可达地址应报错: {events}"
    finally:
        client.delete(f"{base_url}/api/config/providers/{pid}", timeout=10)
