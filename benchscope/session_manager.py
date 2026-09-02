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
    thinking: str = ""

    def to_dict(self):
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp, "model": self.model, "thinking": self.thinking}


# 支持的推理标签对列表（通用化）
# 支持: 标准 ASCII 标签 <think>, 全角标签 ＜think＞, 以及其他常见变体
REASONING_TAGS = [
    # 标准 ASCII 标签
    ("think", "<think>", "</think>"),
    ("reasoning", "<reasoning>", "</reasoning>"),
    ("thinking", "<thinking>", "</thinking>"),
    ("reflection", "<reflection>", "</reflection>"),
    ("analysis", "<analysis>", "</analysis>"),
    # 全角标签（中文输入法常见）
    ("think-full", "＜think＞", "＜/think＞"),
    ("reasoning-full", "＜reasoning＞", "＜/reasoning＞"),
    ("thinking-full", "＜thinking＞", "＜/thinking＞"),
]

# 预编译所有标签的 open/close 查找表
_TAG_OPENS = {tag[1]: (tag[0], tag[2]) for tag in REASONING_TAGS}
_TAG_CLOSES = {tag[2]: tag[1] for tag in REASONING_TAGS}
_TAG_NAMES = [tag[0] for tag in REASONING_TAGS]


def parse_think_tags(raw: str):
    """通用推理标签解析:从 raw 中分离所有已知推理标签对的内容,返回 (thinking, content)。
    支持多段推理块、嵌套不严格、标签未闭合时剩余内容归为 thinking。
    """
    thinking_parts = []
    content_parts = []
    i = 0
    n = len(raw)
    # 当前打开的标签栈:存 open_tag 字符串
    open_stack = []
    while i < n:
        # 检查是否命中任一 open 标签
        matched_open = None
        for _, open_tag, close_tag in REASONING_TAGS:
            if raw[i:].startswith(open_tag):
                matched_open = open_tag
                break
        if matched_open:
            # 找到 open 标签
            if open_stack:
                # 已有打开的标签，把之前累积的 content 保留
                pass  # 继续推入 thinking
            open_stack.append(matched_open)
            i += len(matched_open)
            # 查找对应 close
            tag_name, close_tag = _TAG_OPENS[matched_open]
            end = raw.find(close_tag, i)
            if end == -1:
                # 标签未闭合,剩余内容全部归为 thinking
                thinking_parts.append(raw[i:])
                i = n
                break
            else:
                thinking_parts.append(raw[i:end])
                i = end + len(close_tag)
                open_stack.pop()
            continue
        # 检查是否命中任一 close 标签（可能存在未匹配的 close，忽略）
        matched_close = None
        for _, open_tag, close_tag in REASONING_TAGS:
            if raw[i:].startswith(close_tag):
                matched_close = close_tag
                break
        if matched_close:
            # 有打开的标签才视为闭合;否则作为普通文本
            if open_stack:
                expected_open = _TAG_CLOSES[matched_close]
                # 弹出匹配的 open（栈顶查找）
                if expected_open in open_stack:
                    open_stack.remove(expected_open)
                i += len(matched_close)
                continue
            # 无打开标签,作为普通 content
            content_parts.append(raw[i])
            i += 1
            continue
        # 普通字符
        if open_stack:
            # 在推理块内部
            thinking_parts.append(raw[i])
        else:
            content_parts.append(raw[i])
        i += 1
    thinking = "".join(thinking_parts).strip()
    content = "".join(content_parts).strip()
    return thinking, content


@dataclass
class Session:
    session_id: str
    title: str = ""
    model: str = ""
    system_prompt: str = ""
    messages: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    quality: str = ""
    enable_thinking: bool = True
    provider_id: str = ""
    perf: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "title": self.title,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "messages": [m.to_dict() if isinstance(m, Message) else m for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "quality": self.quality,
            "enable_thinking": self.enable_thinking,
            "provider_id": self.provider_id,
            "perf": self.perf,
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
                restored_msgs = []
                for m in data.get("messages", []):
                    if isinstance(m, dict):
                        raw_content = m.get("content", "")
                        existing_thinking = m.get("thinking", "")
                        # 检测是否包含任一已知推理标签（兼容旧消息）
                        has_tag = any(close_tag in raw_content for _, _, close_tag in REASONING_TAGS)
                        if has_tag and not existing_thinking:
                            t, c = parse_think_tags(raw_content)
                            restored_msgs.append(Message(
                                role=m.get("role", ""),
                                content=c,
                                timestamp=m.get("timestamp", ""),
                                model=m.get("model", ""),
                                thinking=t,
                            ))
                        else:
                            restored_msgs.append(Message(
                                role=m.get("role", ""),
                                content=raw_content,
                                timestamp=m.get("timestamp", ""),
                                model=m.get("model", ""),
                                thinking=existing_thinking,
                            ))
                    else:
                        restored_msgs.append(m)
                session = Session(
                    session_id=data.get("session_id", p.stem),
                    title=data.get("title", ""),
                    model=data.get("model", ""),
                    system_prompt=data.get("system_prompt", ""),
                    messages=restored_msgs,
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    quality=data.get("quality", ""),
                    enable_thinking=data.get("enable_thinking", True),
                    provider_id=data.get("provider_id", ""),
                    perf=data.get("perf", {}) if isinstance(data.get("perf"), dict) else {},
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

    def create_session(self, title: str = "", model: str = "", system_prompt: str = "", provider_id: str = "") -> Session:
        with self._lock:
            now = datetime.now()
            session_id = f"sess-{now.strftime('%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
            session = Session(
                session_id=session_id,
                title=title or f"会话 {now.strftime('%m/%d %H:%M')}",
                model=model,
                system_prompt=system_prompt,
                provider_id=provider_id,
                created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
                updated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._sessions[session_id] = session
            session.persist(self.sessions_dir / f"{session_id}.json")
            self.persist_log(session)
            return session

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            p = self.sessions_dir / f"{session_id}.json"
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    log.warning("unlink failed: %s", p)
            # 同步删除对应会话日志
            try:
                lp = Path(self.config.logs_dir) / "sessions" / f"{session_id}.log"
                if lp.exists():
                    lp.unlink()
            except Exception:
                log.warning("session log unlink failed: %s", session_id)

    def clear_all(self):
        with self._lock:
            for p in self.sessions_dir.glob("*.json"):
                try:
                    p.unlink()
                except Exception:
                    log.warning("unlink failed: %s", p)
            # 清空会话日志目录
            try:
                slog_dir = Path(self.config.logs_dir) / "sessions"
                for lp in slog_dir.glob("*.log"):
                    try:
                        lp.unlink()
                    except Exception:
                        log.warning("session log unlink failed: %s", lp)
            except Exception:
                log.warning("session log clear failed")
            self._sessions.clear()

    def add_message(self, session_id: str, role: str, content: str, model: str = "", thinking: str = "") -> Optional[Message]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            msg = Message(
                role=role,
                content=content,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                model=model,
                thinking=thinking,
            )
            session.messages.append(msg)
            session.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if role == "user" and not session.title.startswith("会话"):
                pass  # keep custom title
            elif role == "user" and len(session.messages) == 1:
                session.title = content[:50] + ("..." if len(content) > 50 else "")
            session.persist(self.sessions_dir / f"{session_id}.json")
            self.persist_log(session)
            return msg

    def persist_log(self, session: Session):
        """将会话对话记录以可读日志落盘到 logs 目录（logs_dir/sessions/<id>.log）。

        每次消息变更后刷新，作为会话「日志」对外可见（区别于 sessions/*.json 缓存）。
        """
        try:
            logs_dir = Path(self.config.logs_dir) / "sessions"
            logs_dir.mkdir(parents=True, exist_ok=True)
            lines = []
            lines.append(f"# Session: {session.title}")
            lines.append(f"# ID: {session.session_id}")
            lines.append(f"# Model: {session.model or '-'}")
            if session.provider_id:
                lines.append(f"# Provider: {session.provider_id}")
            lines.append(f"# Created: {session.created_at}")
            lines.append(f"# Updated: {session.updated_at}")
            lines.append("-" * 60)
            for m in session.messages:
                if isinstance(m, dict):
                    role, content, thinking, ts = m.get("role", "?"), m.get("content", ""), m.get("thinking", ""), m.get("timestamp", "")
                else:
                    role, content, thinking, ts = m.role, m.content, m.thinking, m.timestamp
                lines.append(f"[{ts}] {role}")
                if thinking:
                    lines.append(f"[thinking] {thinking}")
                lines.append(content or "")
                lines.append("")
            (logs_dir / f"{session.session_id}.log").write_text(
                "\n".join(lines), encoding="utf-8"
            )
        except Exception:
            log.exception("Session log persist failed: %s", session.session_id)

    def update_perf(self, session_id: str, perf: dict):
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            session.perf = perf if isinstance(perf, dict) else {}
            session.persist(self.sessions_dir / f"{session_id}.json")
            self.persist_log(session)

    def update_title(self, session_id: str, title: str):
        """重命名会话：更新标题并刷新 updated_at，持久化。"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            session.title = (title or "").strip()
            session.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session.persist(self.sessions_dir / f"{session_id}.json")
            self.persist_log(session)
            return session

    def _provider_api_config(self, provider_id: str) -> Optional[dict]:
        """按 provider_id 解析 Provider 的 API 配置（base_url/endpoint/api_key/extra_headers）。"""
        if not provider_id:
            return None
        try:
            # list_providers() 返回 {"providers": [...], "active_provider": "..."}
            providers = (self.config.list_providers() or {}).get("providers") or []
        except Exception:
            log.exception("list_providers failed")
            return None
        for p in providers:
            if p.get("id") == provider_id:
                return {
                    "base_url": p.get("base_url", ""),
                    "endpoint": p.get("endpoint", "/v1/chat/completions"),
                    "api_key": p.get("api_key", ""),
                    "extra_headers": p.get("extra_headers", {}) or {},
                }
        return None

    def stream_chat(self, session_id: str, user_message: str, model: str = "", quality: str = "", enable_thinking: bool = True, provider_id: str = "", top_k: int | None = None, temperature: float | None = None, top_p: float | None = None):
        """生成器：通过 OpenAI 兼容 API 流式转发对话。"""
        session = self.get_session(session_id)
        if not session:
            yield json.dumps({"error": "Session not found"}, ensure_ascii=False)
            return

        # 使用请求中的 model，否则回退到 session 的 model
        chat_model = model or session.model or "default"
        # 持久化对话配置到会话
        session.model = chat_model
        session.provider_id = provider_id or session.provider_id
        if quality:
            session.quality = quality
        session.enable_thinking = enable_thinking
        self.add_message(session_id, "user", user_message, model=chat_model)

        # api 配置：优先所选 Provider，否则回退全局配置
        api_config = self._provider_api_config(session.provider_id) or (self.config.api or {})
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
            "model": chat_model,
            "messages": messages,
            "stream": True,
            "max_tokens": 4096,
        }
        # 对话采样参数（顶部性能栏配置）：显式 temperature 优先于 quality 映射
        if temperature is not None:
            payload["temperature"] = temperature
        else:
            temp = {"high": 0.9, "medium": 0.5, "low": 0.2}.get(quality)
            if temp is not None:
                payload["temperature"] = temp
        if top_k is not None and top_k > 0:
            payload["top_k"] = top_k
        if top_p is not None:
            payload["top_p"] = top_p
        # 思考开关(vLLM/SGLang 通过 chat_template_kwargs 控制)
        payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}

        assistant_content = ""
        assistant_thinking = ""
        raw_content = ""
        prev_thinking = ""
        prev_content = ""
        try:
            resp = req.post(url, json=payload, headers=headers, stream=True, timeout=120)
            if resp.status_code != 200:
                err_msg = f"API error: {resp.status_code} {resp.text[:500]}"
                self.add_message(session_id, "assistant", err_msg, model=chat_model)
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
                    thinking = delta.get("reasoning_content", "")
                    if thinking:
                        assistant_thinking += thinking
                        yield json.dumps({"thinking": thinking}, ensure_ascii=False)
                    if token:
                        raw_content += token
                        # 解析 ndl...GGUF 标签,分离思考与回复
                        new_thinking, new_content = parse_think_tags(raw_content)
                        if len(new_thinking) > len(prev_thinking):
                            dt = new_thinking[len(prev_thinking):]
                            assistant_thinking += dt
                            yield json.dumps({"thinking": dt}, ensure_ascii=False)
                        if len(new_content) > len(prev_content):
                            dc = new_content[len(prev_content):]
                            assistant_content += dc
                            yield json.dumps({"token": dc}, ensure_ascii=False)
                        prev_thinking = new_thinking
                        prev_content = new_content
                except json.JSONDecodeError:
                    continue

            if assistant_content or assistant_thinking:
                log.info("stream_chat parsed: thinking=%d chars, content=%d chars", len(assistant_thinking), len(assistant_content))
                self.add_message(session_id, "assistant", assistant_content, model=chat_model, thinking=assistant_thinking)
            yield json.dumps({"done": True}, ensure_ascii=False)

        except Exception as e:
            log.exception("Stream chat failed")
            err_msg = f"Request failed: {e}"
            if assistant_content or assistant_thinking:
                self.add_message(session_id, "assistant", assistant_content, model=chat_model, thinking=assistant_thinking)
            self.add_message(session_id, "assistant", err_msg, model=chat_model)
            yield json.dumps({"error": err_msg}, ensure_ascii=False)
