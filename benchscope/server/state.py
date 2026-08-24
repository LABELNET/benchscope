"""服务端全局状态单例。"""
from __future__ import annotations

from benchscope.config import ConfigManager
from benchscope.server.status import StatusMonitor
from benchscope.server.test_manager import TestManager
from benchscope.server.ws import WebSocketHub


class AppState:
    def __init__(self):
        self.config = ConfigManager()
        self.hub = WebSocketHub()
        self.monitor = StatusMonitor(self.config, self.hub)
        self.tests = TestManager(self.config, self.hub)


state = AppState()
