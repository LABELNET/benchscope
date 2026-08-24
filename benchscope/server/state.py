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
        self.monitor = StatusMonitor(self.config, self.hub)
        self.tasks = TaskManager(self.config, self.hub)
        self.sessions = SessionManager(self.config)


state = AppState()
