"""配置持久化：config.json 读写与运行时配置单例。"""
from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path

from benchscope.constants import DEFAULT_CONFIG

DEFAULT_CONFIG_PATH = Path.home() / ".benchscope" / "config.json"


class ConfigManager:
    """线程安全的配置管理。"""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        self._lock = threading.RLock()
        self._data: dict = deepcopy(DEFAULT_CONFIG)
        self.load()

    # ---------- 持久化 ----------
    def load(self) -> None:
        with self._lock:
            if self.path.exists():
                try:
                    loaded = json.loads(self.path.read_text(encoding="utf-8"))
                    self._merge(self._data, loaded)
                except Exception:
                    pass  # 配置损坏时使用默认配置

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    @staticmethod
    def _merge(base: dict, overlay: dict) -> None:
        for key, value in overlay.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                ConfigManager._merge(base[key], value)
            else:
                base[key] = value

    # ---------- 访问 ----------
    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
            self.save()

    def update(self, patch: dict) -> dict:
        with self._lock:
            self._merge(self._data, patch)
            self.save()
            return deepcopy(self._data)

    def snapshot(self) -> dict:
        with self._lock:
            return deepcopy(self._data)

    # ---------- 常用辅助 ----------
    @property
    def api(self) -> dict:
        return self.get("api", {})

    @property
    def logs_dir(self) -> Path:
        raw = self.get("logs_dir", "./logs")
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def datasets_dir(self) -> Path:
        raw = self.get("datasets_dir", "./datasets")
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def data_dir(self) -> Path:
        """服务端数据持久化目录（任务 / 会话等），默认 ~/.benchscope。"""
        raw = self.get("data_dir", "~/.benchscope")
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def models_dir(self) -> Path:
        """模型下载缓存目录，默认 ~/.benchscope/models。"""
        raw = self.get("models_dir", "~/.benchscope/models")
        return Path(os.path.expanduser(raw)).resolve()

    def set_api(self, patch: dict) -> dict:
        with self._lock:
            api = deepcopy(self._data.setdefault("api", {}))
            api.update(patch)
            self._data["api"] = api
            self.save()
            return deepcopy(api)
