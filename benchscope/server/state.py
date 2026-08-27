"""服务端全局状态单例。"""
from __future__ import annotations

from benchscope.config import ConfigManager
from benchscope.server.status import StatusMonitor
from benchscope.task_manager import TaskManager
from benchscope.session_manager import SessionManager
from benchscope.server.ws import WebSocketHub


class AppState:
    def __init__(self):
        self.config = ConfigManager()
        self.hub = WebSocketHub()
        self.migration_source = str(self.config.data_dir)  # data_dir 迁移来源（默认当前数据根目录）
        self.monitor = StatusMonitor(self.config, self.hub)
        self.tasks = TaskManager(self.config, self.hub, tasks_dir=self.config.perfs_dir / "tasks")
        self.sessions = SessionManager(self.config, sessions_dir=self.config.sessions_dir)


state = AppState()
