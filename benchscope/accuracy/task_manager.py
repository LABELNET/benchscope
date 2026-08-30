"""精度任务管理器（EvalTaskManager）：与性能 TaskManager 完全独立的调度与落库。

- 独立状态机：pending → running → done | stopped | error（服务重启 running → stopped）。
- 落库三件套：evals/<task_id>/task.json（主表）/ result.json（结果）/ samples.jsonl（溯源）。
- 终端日志：logs/eval_<run_id>_<ts>.log（eval 前缀，沿用目录约定）。
- WS 推送：eval_task_started / log / progress / result / done / error（复用 WebSocketHub）。
- 评测核心：accuracy.executor.run_eval（与 `benchscope eval` CLI 共用）。
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from benchscope.accuracy import baselines as acc_baselines
from benchscope.accuracy import estimator as acc_estimator
from benchscope.accuracy import metrics as acc_metrics
from benchscope.accuracy.engines import eval_capability, get_eval_engine
from benchscope.accuracy.executor import run_eval

log = logging.getLogger("benchscope.accuracy.task_manager")

TASK_STATUSES = ("pending", "running", "done", "stopped", "error")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class EvalTask:
    """精度任务（主表 task.json 的内存态）。"""

    task_id: str
    task_dir: Path
    payload: dict
    mode: str = "serving"                # serving | native
    engine_id: str = ""
    model: str = ""
    name: str = ""
    dataset_id: str = ""
    dataset_name: str = ""
    lora_name: str = ""
    lora_path: str = ""
    status: str = "pending"
    error: Optional[str] = None
    progress: dict = field(default_factory=lambda: {"done": 0, "total": 0})
    estimate: Optional[dict] = None
    result: Optional[dict] = None
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    log_path: Optional[str] = None
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)

    def snapshot(self, include_result: bool = True) -> dict:
        data = {
            "task_id": self.task_id,
            "task_dir": str(self.task_dir),
            "name": self.name,
            "mode": self.mode,
            "engine_id": self.engine_id,
            "model": self.model,
            "lora_name": self.lora_name,
            "lora_path": self.lora_path,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "dataset": self.payload.get("dataset") or {},
            "limit": self.payload.get("limit") or 0,
            "seed": self.payload.get("seed") or 0,
            "temperature": self.payload.get("temperature") or 0.0,
            "top_p": self.payload.get("top_p") or 1.0,
            "max_tokens": self.payload.get("max_tokens") or 512,
            "concurrency": self.payload.get("concurrency") or 4,
            "judge_model": self.payload.get("judge_model") or "",
            "status": self.status,
            "error": self.error,
            "progress": self.progress,
            "estimate": self.estimate,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "log_path": self.log_path,
            "use_mock_env": bool(self.payload.get("use_mock_env", False)),
        }
        if include_result:
            data["result"] = self.result
        return data

    def persist(self):
        try:
            self.task_dir.mkdir(parents=True, exist_ok=True)
            (self.task_dir / "task.json").write_text(
                json.dumps(self.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            # run.json：接入既有 Datas/Logs 记录体系（list_runs 扫描 evals_dir 下含 run.json 的目录）
            run = dict(self.snapshot(include_result=False))
            run["run_id"] = self.task_id
            run["kind"] = "eval"
            result = self.result or {}
            run["summary"] = {
                "accuracy": result.get("accuracy"),
                "pass_rate": result.get("pass_rate"),
                "total_samples": result.get("total_samples"),
                "conclusion": result.get("conclusion"),
            }
            (self.task_dir / "run.json").write_text(
                json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            log.exception("EvalTask persist failed: %s", self.task_id)

    def persist_result(self):
        try:
            if self.result is not None:
                (self.task_dir / "result.json").write_text(
                    json.dumps(self.result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        except Exception:
            log.exception("EvalTask persist_result failed: %s", self.task_id)

    @classmethod
    def from_json(cls, task_dir: Path, data: dict) -> "EvalTask":
        payload = {k: v for k, v in data.items() if k not in ("result", "progress", "estimate", "status", "error")}
        payload["dataset"] = data.get("dataset") or {}
        task = cls(
            task_id=data.get("task_id") or task_dir.name,
            task_dir=task_dir,
            payload=payload,
            mode=data.get("mode") or "serving",
            engine_id=data.get("engine_id") or "",
            model=data.get("model") or "",
            name=data.get("name") or "",
            dataset_id=data.get("dataset_id") or "",
            dataset_name=data.get("dataset_name") or "",
            lora_name=data.get("lora_name") or "",
            lora_path=data.get("lora_path") or "",
            status=data.get("status") or "pending",
            error=data.get("error"),
            progress=data.get("progress") or {"done": 0, "total": 0},
            estimate=data.get("estimate"),
            result=data.get("result"),
            created_at=data.get("created_at") or "",
            started_at=data.get("started_at") or "",
            finished_at=data.get("finished_at") or "",
            log_path=data.get("log_path"),
        )
        return task


class EvalTaskManager:
    """精度任务管理器（独立于性能 TaskManager；线程执行 + 三件套落库 + WS 推送）。"""

    def __init__(self, config, hub, evals_dir: Path | None = None):
        self.config = config
        self.hub = hub
        self.evals_dir = evals_dir or config.evals_dir
        self.evals_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._tasks: dict[str, EvalTask] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._restore_tasks()

    # ------------------------------------------------------------------
    def _restore_tasks(self):
        """启动时扫描 evals/*/task.json 恢复任务（running → stopped：服务重启中断）。"""
        for task_dir in sorted(self.evals_dir.glob("eval-*")):
            task_file = task_dir / "task.json"
            if not task_file.exists():
                continue
            try:
                data = json.loads(task_file.read_text(encoding="utf-8"))
                if data.get("status") == "running":
                    data["status"] = "stopped"
                    data["error"] = "服务重启，任务中断"
                    if not data.get("finished_at"):
                        data["finished_at"] = _now()
                    task_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                task = EvalTask.from_json(task_dir, data)
                self._tasks[task.task_id] = task
            except Exception:
                log.exception("恢复精度任务失败: %s", task_dir)

    @property
    def running_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == "running")

    def list_tasks(self) -> list[dict]:
        with self._lock:
            items = [t.snapshot(include_result=False) for t in self._tasks.values()]
        return sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)

    def get_task(self, task_id: str) -> Optional[EvalTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def create_task(self, payload: dict) -> EvalTask:
        """创建精度任务（落库 task.json；启动经 start_task）。"""
        now = datetime.now()
        base = f"eval-{now.strftime('%m%d-%H%M%S')}"
        with self._lock:
            task_id = base
            suffix = 1
            while task_id in self._tasks or (self.evals_dir / task_id).exists():
                suffix += 1
                task_id = f"{base}-{suffix}"
            task_dir = self.evals_dir / task_id

            engine_id = payload.get("engine_id") or ""
            # 模式由引擎能力决定（native-hf → native；serving/mock → serving）
            engine = get_eval_engine(engine_id)
            capability = eval_capability(engine) if engine else ""
            mode = "native" if capability == "native" else "serving"
            dataset_ref = payload.get("dataset") or {}
            task = EvalTask(
                task_id=task_id,
                task_dir=task_dir,
                payload=payload,
                mode=mode,
                engine_id=engine_id,
                model=payload.get("model") or "",
                name=payload.get("name") or "",
                dataset_id=dataset_ref.get("id") or str(dataset_ref.get("path") or ""),
                dataset_name=dataset_ref.get("name") or dataset_ref.get("id") or dataset_ref.get("path") or "",
                lora_name=payload.get("lora_name") or "",
                lora_path=payload.get("lora_path") or "",
                created_at=_now(),
            )
            task.persist()
            self._tasks[task_id] = task
            return task

    def start_task(self, task_id: str) -> EvalTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError(f"精度任务不存在: {task_id}")
            if task.status == "running":
                raise RuntimeError("任务已在运行中")
            task.status = "running"
            task.started_at = _now()
            task.finished_at = ""
            task.error = None
            task.result = None
            task.progress = {"done": 0, "total": 0}
            task._stop.clear()
            # Serving 模式：前置 Token 预估（预估 vs 实际偏差对比的数据来源）
            if task.mode == "serving":
                try:
                    task.estimate = acc_estimator.estimate(
                        self.config, task.payload.get("dataset") or {},
                        limit=task.payload.get("limit") or 0, mode="serving",
                        max_tokens=int(task.payload.get("max_tokens") or 512))
                except Exception:
                    log.exception("Token 预估失败: %s", task_id)
                    task.estimate = None
            task.persist()

            thread = threading.Thread(target=self._execute, args=(task,),
                                      name=f"eval-task-{task_id}", daemon=True)
            self._threads[task_id] = thread
            thread.start()
            return task

    def stop_task(self, task_id: str):
        task = self.get_task(task_id)
        if task:
            task._stop.set()

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.pop(task_id, None)
        if not task:
            return False
        if task.status == "running":
            task._stop.set()
        import shutil

        shutil.rmtree(task.task_dir, ignore_errors=True)
        return True

    def stop(self):
        """停止全部运行中任务（服务退出时调用）。"""
        for task in list(self._tasks.values()):
            if task.status == "running":
                task._stop.set()

    # ------------------------------------------------------------------
    def _execute(self, task: EvalTask):
        run_id = task.task_id.replace("eval-", "")
        ts = datetime.now().strftime("%m%d%H%M%S")
        log_path = self.config.logs_dir / f"eval_{run_id}_{ts}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        task.log_path = str(log_path)

        samples_file = task.task_dir / "samples.jsonl"
        samples_fp = samples_file.open("a", encoding="utf-8")
        log_fp = open(log_path, "a", encoding="utf-8")

        def broadcast(payload: dict):
            payload.setdefault("task_id", task.task_id)
            self.hub.broadcast(payload)

        try:
            broadcast({"type": "eval_task_started", "task": task.snapshot()})

            def log_cb(line: str):
                log_fp.write(line)
                log_fp.flush()
                broadcast({"type": "eval_task_log", "line": line})

            def progress_cb(done: int, total: int):
                task.progress = {"done": done, "total": total}
                task.persist()
                broadcast({"type": "eval_task_progress", "progress": task.progress})

            def sample_cb(record: dict):
                try:
                    samples_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                    samples_fp.flush()
                except Exception:
                    log.exception("samples.jsonl 写入失败: %s", task.task_id)
                broadcast({"type": "eval_task_result", "sample": record})

            meta, _results, result, stopped = run_eval(
                self.config, task.payload,
                log_cb=log_cb, sample_cb=sample_cb,
                progress_cb=progress_cb, stop_flag=task._stop,
            )

            # 基线对标 + 结论 + 预估 vs 实际
            benchmark = acc_baselines.compute_benchmark(meta, result)
            if benchmark:
                result["benchmark"] = benchmark
            result["estimate_vs_actual"] = acc_estimator.estimate_vs_actual(task.estimate, result)
            result["conclusion"] = acc_metrics.conclusion(result, benchmark)

            task.dataset_id = meta.get("id") or task.dataset_id
            task.dataset_name = meta.get("name") or task.dataset_name
            task.result = result
            task.status = "stopped" if (stopped or task._stop.is_set()) else "done"
            task.finished_at = _now()
            task.progress = {"done": result.get("total_samples") or 0, "total": result.get("total_samples") or 0}
            task.persist()
            task.persist_result()
            broadcast({"type": "eval_task_done", "task": task.snapshot()})
        except Exception as e:  # noqa: BLE001
            log.exception("精度任务执行失败: %s", task.task_id)
            task.status = "error"
            task.error = str(e)
            task.finished_at = _now()
            task.persist()
            broadcast({"type": "eval_task_error", "error": str(e), "task": task.snapshot()})
        finally:
            try:
                samples_fp.close()
                log_fp.close()
            except Exception:
                pass
            self._threads.pop(task.task_id, None)
