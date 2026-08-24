"""会话管理器：支持多会话、消息持久化、SSE 流式对话。"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("benchscope.session_manager")

SESSIONS_DIR_DEFAULT = Path.home() / ".benchscope" / "sessions"


@dataclass
class Message:
    role: str  # user | assistant | system
    content: str
    timestamp: str = ""
    model: str = ""

    def to_dict(self):
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp, "model": self.model}


@dataclass
class Session:
    session_id: str
    title: str = ""
    model: str = ""
    system_prompt: str = ""
    messages: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "title": self.title,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "messages": [m.to_dict() if isinstance(m, Message) else m for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def persist(self, path: Path):
        try:
            path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            log.exception("Session persist failed: %s", self.session_id)


class SessionManager:
    def __init__(self, config, sessions_dir: Path | None = None):
        self.config = config
        self.sessions_dir = sessions_dir or SESSIONS_DIR_DEFAULT
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._sessions: dict[str, Session] = {}
        self._restore_sessions()

    def _restore_sessions(self):
        for p in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                session = Session(
                    session_id=data.get("session_id", p.stem),
                    title=data.get("title", ""),
                    model=data.get("model", ""),
                    system_prompt=data.get("system_prompt", ""),
                    messages=[Message(**m) if isinstance(m, dict) else m for m in data.get("messages", [])],
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                )
                self._sessions[session.session_id] = session
            except Exception:
                log.exception("Restore session failed: %s", p)

    def list_sessions(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in sorted(self._sessions.values(), key=lambda x: x.updated_at, reverse=True)]

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(session_id)

    def create_session(self, title: str = "", model: str = "", system_prompt: str = "") -> Session:
        with self._lock:
            now = datetime.now()
            session_id = f"sess-{now.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
            session = Session(
                session_id=session_id,
                title=title or f"会话 {now.strftime('%m/%d %H:%M')}",
                model=model,
                system_prompt=system_prompt,
                created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
                updated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._sessions[session_id] = session
            session.persist(self.sessions_dir / f"{session_id}.json")
            return session

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            p = self.sessions_dir / f"{session_id}.json"
            if p.exists():
                p.unlink()

    def clear_all(self):
        with self._lock:
            for p in self.sessions_dir.glob("*.json"):
                p.unlink()
            self._sessions.clear()

    def add_message(self, session_id: str, role: str, content: str, model: str = "") -> Optional[Message]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            msg = Message(
                role=role,
                content=content,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                model=model,
            )
            session.messages.append(msg)
            session.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if role == "user" and not session.title.startswith("会话"):
                pass  # keep custom title
            elif role == "user" and len(session.messages) == 1:
                session.title = content[:50] + ("..." if len(content) > 50 else "")
            session.persist(self.sessions_dir / f"{session_id}.json")
            return msg

    def stream_chat(self, session_id: str, user_message: str):
        """生成器：通过 OpenAI 兼容 API 流式转发对话。"""
        session = self.get_session(session_id)
        if not session:
            yield json.dumps({"error": "Session not found"}, ensure_ascii=False)
            return

        self.add_message(session_id, "user", user_message, model=session.model)

        api_config = self.config.api or {}
        base_url = api_config.get("base_url", "http://localhost:8000")
        api_key = api_config.get("api_key", "")
        endpoint = api_config.get("endpoint", "/v1/chat/completions")
        headers_extra = api_config.get("extra_headers", {})

        url = f"{base_url.rstrip('/')}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        headers.update(headers_extra)

        messages = []
        if session.system_prompt:
            messages.append({"role": "system", "content": session.system_prompt})
        for m in session.messages:
            if isinstance(m, Message):
                messages.append({"role": m.role, "content": m.content})
            elif isinstance(m, dict):
                messages.append({"role": m["role"], "content": m["content"]})

        import requests as req

        payload = {
            "model": session.model or "default",
            "messages": messages,
            "stream": True,
            "max_tokens": 4096,
        }

        assistant_content = ""
        try:
            resp = req.post(url, json=payload, headers=headers, stream=True, timeout=120)
            if resp.status_code != 200:
                err_msg = f"API 返回错误: {resp.status_code} {resp.text[:500]}"
                self.add_message(session_id, "assistant", err_msg, model=session.model)
                yield json.dumps({"error": err_msg}, ensure_ascii=False)
                return

            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        assistant_content += token
                        yield json.dumps({"token": token}, ensure_ascii=False)
                except json.JSONDecodeError:
                    continue

            if assistant_content:
                self.add_message(session_id, "assistant", assistant_content, model=session.model)
            yield json.dumps({"done": True}, ensure_ascii=False)

        except Exception as e:
            log.exception("Stream chat failed")
            err_msg = f"请求失败: {e}"
            if assistant_content:
                self.add_message(session_id, "assistant", assistant_content, model=session.model)
            self.add_message(session_id, "assistant", err_msg, model=session.model)
            yield json.dumps({"error": err_msg}, ensure_ascii=False)
