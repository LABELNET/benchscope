"""配置持久化：settings.json 读写与运行时配置单例。"""
from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from pathlib import Path

from benchscope.constants import DEFAULT_CONFIG

log = logging.getLogger("benchscope.config")


def _data_root() -> Path:
    """数据根目录：默认 ~/.benchscope；可通过环境变量 BENCHSCOPE_DATA_DIR 覆盖（测试隔离）。"""
    env = os.environ.get("BENCHSCOPE_DATA_DIR")
    if env:
        return Path(os.path.expanduser(env)).resolve()
    return Path.home() / ".benchscope"


DATA_ROOT = _data_root()

# 设置持久化文件：~/.benchscope/settings.json
DEFAULT_CONFIG_PATH = DATA_ROOT / "settings.json"
# 旧版配置（兼容迁移）
LEGACY_CONFIG_PATH = DATA_ROOT / "config.json"
# 旧版默认路径 -> 新目录体系（迁移归一化）
LEGACY_DEFAULT_PATHS = {
    "./logs": str(DATA_ROOT / "logs"),
    "./datasets": str(DATA_ROOT / "datasets"),
}

# data_dir 下的默认子目录映射：配置 key -> 子目录名
DATA_SUBDIRS = {
    "perfs_dir": "perfs",
    "evals_dir": "evals",
    "analysis_dir": "analysys",
    "logs_dir": "logs",
    "sessions_dir": "sessions",
    "models_dir": "models",
    "datasets_dir": "datasets",
    "plugins_dir": "plugins",
}


class ConfigManager:
    """线程安全的配置管理。"""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        # 旧版 config.json 与 settings.json 同目录（默认均为 ~/.benchscope）
        self.legacy_path = self.path.parent / "config.json"
        self._lock = threading.RLock()
        self._data: dict = deepcopy(DEFAULT_CONFIG)
        self._redirect_default_dirs()
        self.load()

    def _redirect_default_dirs(self) -> None:
        """测试隔离：设置 BENCHSCOPE_DATA_DIR 时，把默认缓存目录重定向到该根目录下。

        仅作用于默认值；settings.json 中已持久化的自定义目录仍以持久化值为准。
        """
        env = os.environ.get("BENCHSCOPE_DATA_DIR")
        if not env:
            return
        root = Path(os.path.expanduser(env)).resolve()
        self._data["data_dir"] = str(root)
        for key, sub in DATA_SUBDIRS.items():
            self._data[key] = str(root / sub)

    # ---------- 持久化 ----------
    def load(self) -> None:
        with self._lock:
            # 优先读 settings.json；若不存在则尝试旧版 config.json（兼容迁移）
            source = self.path if self.path.exists() else self.legacy_path
            if source and source.exists():
                try:
                    loaded = json.loads(source.read_text(encoding="utf-8"))
                    self._merge(self._data, loaded)
                    self._normalize_legacy_defaults()
                except Exception:
                    log.exception("配置加载失败，使用默认配置: %s", source)
                # 若读取的是旧版 config.json，则一次性落盘 settings.json 完成迁移
                if source != self.path:
                    self.save()
            else:
                # 首次启动：落盘默认配置，确保 settings.json 存在
                self.save()
            # 启动时检查目录是否齐全（缺失则创建）
            self.ensure_dirs()

    def _normalize_legacy_defaults(self) -> None:
        """旧版默认相对路径（./logs、./datasets）归一化为新目录体系默认值。"""
        for old, new in LEGACY_DEFAULT_PATHS.items():
            for key in ("logs_dir", "datasets_dir"):
                if self._data.get(key) == old:
                    self._data[key] = new

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
            # data_dir 联动：当数据根目录变化时，未自定义的子目录跟随新 data_dir
            new_data = patch.get("data_dir")
            if new_data:
                old_data = self._data.get("data_dir", DEFAULT_CONFIG["data_dir"])
                old_root = str(Path(os.path.expanduser(old_data)).resolve())
                new_root = str(Path(os.path.expanduser(new_data)).resolve())
                for key, sub in DATA_SUBDIRS.items():
                    if key in patch:  # 本次显式指定，不联动
                        continue
                    cur = self._data.get(key)
                    if cur:
                        cur_resolved = str(Path(os.path.expanduser(cur)).resolve())
                        if cur_resolved == str(Path(old_root) / sub):
                            patch[key] = str(Path(new_root) / sub)
            self._merge(self._data, patch)
            self.save()
            self.ensure_dirs()
            return deepcopy(self._data)

    def snapshot(self) -> dict:
        with self._lock:
            return deepcopy(self._data)

    def resolve_dir(self, key: str) -> Path:
        """解析配置中的目录（展开 ~ 并 resolve）。"""
        raw = self._data.get(key) or DEFAULT_CONFIG.get(key, "")
        return Path(os.path.expanduser(raw)).resolve()

    def ensure_dirs(self) -> None:
        """检查并创建所有缓存目录（启动时调用）。"""
        with self._lock:
            for key in ("data_dir", "perfs_dir", "evals_dir", "analysis_dir",
                        "logs_dir", "sessions_dir", "models_dir", "datasets_dir", "plugins_dir"):
                raw = self._data.get(key, DEFAULT_CONFIG.get(key, ""))
                try:
                    Path(os.path.expanduser(raw)).mkdir(parents=True, exist_ok=True)
                except Exception:
                    log.exception("目录创建失败: %s=%s", key, raw)

    # ---------- 常用辅助 ----------
    @property
    def api(self) -> dict:
        return self.get("api", {})

    @property
    def data_dir(self) -> Path:
        """数据根目录，默认 ~/.benchscope。"""
        raw = self.get("data_dir", DEFAULT_CONFIG["data_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def perfs_dir(self) -> Path:
        """性能测试任务目录，默认 ~/.benchscope/perfs。"""
        raw = self.get("perfs_dir", DEFAULT_CONFIG["perfs_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def evals_dir(self) -> Path:
        """精度测试任务目录，默认 ~/.benchscope/evals。"""
        raw = self.get("evals_dir", DEFAULT_CONFIG["evals_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def analysis_dir(self) -> Path:
        """数据分析目录，默认 ~/.benchscope/analysys（联动 Datas）。"""
        raw = self.get("analysis_dir", DEFAULT_CONFIG["analysis_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def logs_dir(self) -> Path:
        """日志目录（runtime 日志 + 任务终端输出），默认 ~/.benchscope/logs。"""
        raw = self.get("logs_dir", DEFAULT_CONFIG["logs_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def sessions_dir(self) -> Path:
        """会话缓存目录，默认 ~/.benchscope/sessions。"""
        raw = self.get("sessions_dir", DEFAULT_CONFIG["sessions_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def datasets_dir(self) -> Path:
        """数据集下载目录，默认 ~/.benchscope/datasets。"""
        raw = self.get("datasets_dir", DEFAULT_CONFIG["datasets_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def models_dir(self) -> Path:
        """模型下载缓存目录，默认 ~/.benchscope/models。"""
        raw = self.get("models_dir", DEFAULT_CONFIG["models_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    @property
    def plugins_dir(self) -> Path:
        """插件安装加载目录，默认 ~/.benchscope/plugins。"""
        raw = self.get("plugins_dir", DEFAULT_CONFIG["plugins_dir"])
        return Path(os.path.expanduser(raw)).resolve()

    def set_api(self, patch: dict) -> dict:
        with self._lock:
            api = deepcopy(self._data.setdefault("api", {}))
            api.update(patch)
            self._data["api"] = api
            self.save()
            return deepcopy(api)
