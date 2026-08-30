"""服务端全局状态单例。"""
from __future__ import annotations

from benchscope.config import ConfigManager
from benchscope.server.status import StatusMonitor
from benchscope.server.test_manager import TestManager
from benchscope.task_manager import TaskManager
from benchscope.session_manager import SessionManager
from benchscope.accuracy.task_manager import EvalTaskManager
from benchscope.server.ws import WebSocketHub


class AppState:
    def __init__(self):
        self.config = ConfigManager()
        self.hub = WebSocketHub()
        self.migration_source = str(self.config.data_dir)  # data_dir 迁移来源（默认当前数据根目录）
        self.monitor = StatusMonitor(self.config, self.hub)
        self.tasks = TaskManager(self.config, self.hub, tasks_dir=self.config.perfs_dir / "tasks")
        self.tests = TestManager(self.config, self.hub)  # 精度测试（Accuracy，/api/test*）
        # 独立精度测试模块（1.0.8，/api/accuracy*）：EvalTaskManager 独立调度与落库
        self.evals = EvalTaskManager(self.config, self.hub)
        self.sessions = SessionManager(self.config, sessions_dir=self.config.sessions_dir)


state = AppState()
