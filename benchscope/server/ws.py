"""WebSocket 客户端广播。"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from fastapi import WebSocket

log = logging.getLogger("benchscope.ws")


class WebSocketHub:
    """向所有已连接的前端客户端广播 JSON 消息（线程安全，可在后台线程调用）。"""

    def __init__(self):
        self._clients: set[tuple[WebSocket, asyncio.AbstractEventLoop]] = set()
        self._lock = threading.Lock()

    def register(self, ws: WebSocket, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._clients.add((ws, loop))

    def unregister(self, ws: WebSocket) -> None:
        with self._lock:
            self._clients = {(w, l) for w, l in self._clients if w is not ws}

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._clients)

    def broadcast(self, payload: dict[str, Any]) -> None:
        try:
            msg = json.dumps(payload, ensure_ascii=False, default=str)
        except TypeError:
            log.exception("WS 广播序列化失败")
            return
        with self._lock:
            clients = list(self._clients)
        for ws, loop in clients:
            try:
                fut = asyncio.run_coroutine_threadsafe(ws.send_text(msg), loop)
                fut.add_done_callback(self._on_sent(ws))
            except Exception:
                self.unregister(ws)

    def _on_sent(self, ws: WebSocket):
        def _cb(fut: asyncio.Future):
            try:
                fut.result()
            except Exception:
                self.unregister(ws)
        return _cb
