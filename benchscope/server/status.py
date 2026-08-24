"""推理服务状态监控：心跳探测 /v1/models，广播状态变化。"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests

from benchscope.constants import STATUS_OFFLINE, STATUS_READY

log = logging.getLogger("benchscope.status")


class StatusMonitor:
    INTERVAL = 5.0

    def __init__(self, config, hub):
        self.config = config
        self.hub = hub
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.status = {
            "web": STATUS_READY,
            "inference": STATUS_OFFLINE,
            "last_check": None,
            "models": [],
            "error": None,
        }

    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="status-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    # ------------------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.check_once(broadcast=True)
            except Exception:
                log.exception("状态探测异常")
            self._stop.wait(self.INTERVAL)

    def check_once(self, broadcast: bool = False) -> dict:
        api = self.config.api
        base = (api.get("base_url") or "").rstrip("/")
        headers = {}
        if api.get("api_key"):
            headers["Authorization"] = f"Bearer {api['api_key']}"
        headers.update(api.get("extra_headers") or {})

        models: list[str] = []
        error = None
        inference = STATUS_READY
        if not base:
            inference, error = STATUS_OFFLINE, "未配置 API 地址"
        else:
            try:
                resp = requests.get(f"{base}/v1/models", headers=headers, timeout=4)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("data", []):
                    mid = item.get("id")
                    if mid and mid not in models:
                        models.append(mid)
            except Exception as e:
                inference = STATUS_OFFLINE
                error = str(e)[:300]

        changed = False
        with self._lock:
            old = self.status["inference"]
            self.status.update(
                inference=inference, last_check=time.strftime("%H:%M:%S"),
                models=models, error=error,
            )
            changed = old != inference or bool(self.status["models"]) != bool(models)
            snapshot = dict(self.status)

        if broadcast and changed:
            self.hub.broadcast({"type": "status", "status": snapshot})
        return snapshot

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.status)
