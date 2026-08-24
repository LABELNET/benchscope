"""任务管理器：支持多任务并发执行、持久化、刷新恢复。"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from benchscope.benches.base import BenchOptions
from benchscope.benches.runner import BenchRunner, StopRequested
from benchscope.benches import sglang_bench, vllm_bench
from benchscope.constants import DATASET_RANDOM, DATASET_SHAREGPT, FRAMEWORK_NAMES
from benchscope.summary import write_summary_csv, write_xlsx

log = logging.getLogger("benchscope.task_manager")

TASKS_DIR_DEFAULT = Path.home() / ".benchscope" / "tasks"


def sanitize_name(name: str) -> str:
    return re.sub(r"[^\w.-]", "_", name).strip("_")


def build_cases(dataset: dict, model: str) -> list[dict]:
    ds_type = dataset.get("type", DATASET_RANDOM)
    cases: list[dict] = []
    if ds_type == DATASET_RANDOM:
        pairs = dataset.get("length_pairs") or []
        for il, ol, label in pairs:
            cases.append({"label": label, "input_len": il, "output_len": ol, "path": None})
    else:
        label = "ShareGPT" if ds_type == DATASET_SHAREGPT else "Custom"
        if ds_type == DATASET_SHAREGPT and dataset.get("label"):
            label = dataset["label"]
        cases.append({"label": label, "input_len": None, "output_len": None, "path": dataset.get("path")})
    return cases


def build_single_command(framework, model, tokenizer, api, dataset, concurrency, request_rate, curated, extra_args):
    opts = BenchOptions(
        framework=framework, model=model, api=api, dataset=dataset,
        concurrency=concurrency, request_rate=request_rate,
        curated=curated or {}, extra_args=extra_args or [],
    )
    opts.tokenizer = tokenizer or model
    if framework == "sglang":
        return sglang_bench.build_command(opts)
    return vllm_bench.build_command(opts)


@dataclass
class Task:
    task_id: str
    run_dir: Path
    payload: dict
    framework: str
    model: str
    gpu: dict
    cases: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    status: str = "pending"  # pending | running | done | stopped | error
    error: Optional[str] = None
    summary: Optional[dict] = None
    started_at: str = ""
    finished_at: str = ""
    precision: str = ""
    created_at: str = ""
    _persist_path: Optional[Path] = None

    def snapshot(self, include_rows: bool = True) -> dict:
        data = {
            "task_id": self.task_id,
            "run_dir": str(self.run_dir),
            "framework": self.framework,
            "framework_name": FRAMEWORK_NAMES.get(self.framework, self.framework),
            "model": self.model,
            "gpu": self.gpu,
            "cases": self.cases,
            "status": self.status,
            "error": self.error,
            "summary": self.summary,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "created_at": self.created_at,
            "precision": self.precision,
            "concurrency_list": self.payload.get("concurrency_list", []),
            "request_rate": self.payload.get("request_rate", "inf"),
            "tpot_threshold_ms": self.payload.get("tpot_threshold_ms"),
            "dataset": self.payload.get("dataset", {}),
        }
        if include_rows:
            data["rows"] = self.rows
        return data

    def persist(self):
        if self._persist_path:
            try:
                self._persist_path.write_text(
                    json.dumps(self.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except Exception:
                log.exception("Task persist failed: %s", self.task_id)


class TaskManager:
    def __init__(self, config, hub, tasks_dir: Path | None = None):
        self.config = config
        self.hub = hub
        self.tasks_dir = tasks_dir or TASKS_DIR_DEFAULT
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._tasks: dict[str, Task] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._runners: dict[str, BenchRunner] = {}
        self._restore_tasks()

    def _restore_tasks(self):
        """启动时扫描 tasks 目录，恢复 running 状态的任务。"""
        for p in self.tasks_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("status") == "running":
                    data["status"] = "stopped"
                    data["error"] = "服务重启，任务中断"
                    if not data.get("finished_at"):
                        data["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                task_id = data.get("task_id", p.stem)
                task = Task(
                    task_id=task_id,
                    run_dir=Path(data.get("run_dir", self.config.logs_dir / task_id)),
                    payload=data,
                    framework=data.get("framework", "vllm"),
                    model=data.get("model", ""),
                    gpu=data.get("gpu", {}),
                    cases=data.get("cases", []),
                    rows=data.get("rows", []),
                    status=data.get("status", "pending"),
                    error=data.get("error"),
                    summary=data.get("summary"),
                    started_at=data.get("started_at", ""),
                    finished_at=data.get("finished_at", ""),
                    precision=data.get("precision", ""),
                    created_at=data.get("created_at", ""),
                )
                task._persist_path = p
                self._tasks[task_id] = task
            except Exception:
                log.exception("Restore task failed: %s", p)

    @property
    def running_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == "running")

    def list_tasks(self) -> list[dict]:
        with self._lock:
            return [t.snapshot(include_rows=False) for t in sorted(self._tasks.values(), key=lambda x: x.created_at, reverse=True)]

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def create_task(self, payload: dict) -> Task:
        with self._lock:
            dataset = payload.get("dataset", {})
            if dataset.get("type") == DATASET_SHAREGPT and not dataset.get("path"):
                from benchscope.datasets import ensure_sharegpt
                path = str(ensure_sharegpt(self.config.datasets_dir))
                dataset = dict(dataset)
                dataset["path"] = path
                payload = dict(payload)
                payload["dataset"] = dataset

            framework = payload.get("framework", "vllm")
            model = payload.get("model", "")
            now = datetime.now()
            task_id = f"task-{now.strftime('%m%d-%H%M%S')}"
            run_dir = self.config.logs_dir / task_id.replace("task-", "")
            run_dir.mkdir(parents=True, exist_ok=True)

            task = Task(
                task_id=task_id,
                run_dir=run_dir,
                payload=payload,
                framework=framework,
                model=model,
                gpu=payload.get("gpu", {}),
                precision=payload.get("precision", ""),
                created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            )
            task.cases = build_cases(payload.get("dataset", {}), model)
            task._persist_path = self.tasks_dir / f"{task_id}.json"
            task.persist()
            self._tasks[task_id] = task
            return task

    def start_task(self, task_id: str) -> Task:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            if task.status == "running":
                raise RuntimeError("Task already running")

            task.status = "running"
            task.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task.rows = []
            task.error = None
            task.summary = None
            task.finished_at = ""
            task.persist()

            thread = threading.Thread(target=self._execute, args=(task,), name=f"task-{task_id}", daemon=True)
            self._threads[task_id] = thread
            thread.start()
            return task

    def stop_task(self, task_id: str):
        runner = self._runners.get(task_id)
        if runner:
            runner.kill()

    def delete_task(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == "running":
                self.stop_task(task_id)
            self._tasks.pop(task_id, None)
            persist_path = self.tasks_dir / f"{task_id}.json"
            if persist_path.exists():
                persist_path.unlink()

    # ------------------------------------------------------------------
    def _execute(self, task: Task):
        framework = task.framework
        tmpl = (self.config.get("bench_commands") or {}).get(framework, "")
        runner = BenchRunner(tmpl)
        self._runners[task.task_id] = runner

        model_name = sanitize_name(Path(task.model).name or task.model)
        gpu_count = task.gpu.get("count", "") if isinstance(task.gpu, dict) else task.gpu
        gpu_label = f"{gpu_count}" if gpu_count else ""
        if isinstance(task.gpu, dict) and task.gpu.get("name"):
            gpu_label = f"{task.gpu['name']}×{gpu_count}" if gpu_count else task.gpu["name"]

        meta = {
            "model": task.model, "model_name": model_name,
            "framework": FRAMEWORK_NAMES.get(framework, framework),
            "gpu": gpu_label, "precision": task.precision,
        }
        mean_csv = task.run_dir / f"{model_name}_X{gpu_count}.log"
        p99_csv = task.run_dir / f"{model_name}_X{gpu_count}_p99.log"

        try:
            self.hub.broadcast({"type": "task_started", "task_id": task.task_id, "task": task.snapshot()})
            cases_done = 0
            for case in task.cases:
                if runner._stop_flag.is_set():
                    break
                case_label = case["label"]
                detail_path = task.run_dir / f"{model_name}_{case_label}_X{gpu_count}.log"
                detail_fp = open(detail_path, "a", encoding="utf-8")
                concurrency_ok = 0
                for conc in task.payload.get("concurrency_list", []):
                    if runner._stop_flag.is_set():
                        break
                    if conc == "inf" or conc is None:
                        continue
                    conc = int(conc)
                    try:
                        row = self._run_one(runner, task, case, conc, detail_fp, meta)
                        task.rows.append(row)
                        concurrency_ok += 1
                        write_summary_csv(mean_csv, [row], p99=False, append=True, case_header=concurrency_ok == 1, case=case, meta=meta)
                        write_summary_csv(p99_csv, [row], p99=True, append=True, case_header=concurrency_ok == 1, case=case, meta=meta)
                        task.persist()
                        self.hub.broadcast({"type": "task_result", "task_id": task.task_id, "row": row})
                    except StopRequested:
                        break
                    except Exception as e:
                        log.exception("Concurrency %s failed", conc)
                        err_row = {"case": case_label, "label": case_label, "input_len": case.get("input_len"), "output_len": case.get("output_len"), "concurrency": conc, "error": str(e)[:500]}
                        task.rows.append(err_row)
                        task.persist()
                        self.hub.broadcast({"type": "task_result", "task_id": task.task_id, "row": err_row})
                detail_fp.close()
                cases_done += 1

            if task.rows:
                rows_for_xlsx = [r for r in task.rows if "metrics" in r]
                if rows_for_xlsx:
                    annotated = self._annotate_best(rows_for_xlsx, task.payload.get("tpot_threshold_ms"))
                    xlsx_path = task.run_dir / f"benchmark-{datetime.now().strftime('%d%m%y')}.xlsx"
                    write_xlsx(xlsx_path, annotated, meta)
                    task.summary = {"xlsx": str(xlsx_path), "rows": len(rows_for_xlsx)}

            task.status = "stopped" if runner._stop_flag.is_set() else "done"
            task.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task.persist()
            self.hub.broadcast({"type": "task_done", "task_id": task.task_id, "task": task.snapshot()})
        except StopRequested:
            task.status = "stopped"
            task.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task.persist()
            self.hub.broadcast({"type": "task_done", "task_id": task.task_id, "task": task.snapshot()})
        except Exception as e:
            log.exception("Task execution failed")
            task.status = "error"
            task.error = str(e)
            task.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task.persist()
            self.hub.broadcast({"type": "task_error", "task_id": task.task_id, "error": str(e), "task": task.snapshot()})
        finally:
            self._runners.pop(task.task_id, None)
            self._threads.pop(task.task_id, None)

    def _run_one(self, runner, task, case, concurrency, detail_fp, meta):
        ds = dict(task.payload.get("dataset", {}))
        ds.update({"input_len": case.get("input_len"), "output_len": case.get("output_len"), "path": case.get("path")})
        cmd = build_single_command(
            task.framework, task.model, task.payload.get("tokenizer", ""),
            dict(self.config.api), ds, concurrency,
            task.payload.get("request_rate", "inf"),
            task.payload.get("curated", {}), task.payload.get("extra_args", []),
        )

        def stream(line: str):
            detail_fp.write(line)
            self.hub.broadcast({"type": "task_log", "task_id": task.task_id, "case": case["label"], "concurrency": concurrency, "line": line})

        metrics = runner.run(cmd, stream_cb=stream)
        return {
            "case": case["label"], "label": case["label"],
            "input_len": case.get("input_len"), "output_len": case.get("output_len"),
            "concurrency": concurrency, "cmd": " ".join(cmd), "metrics": metrics,
        }

    def _annotate_best(self, rows, threshold):
        if threshold is None:
            return rows
        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            return rows
        by_case: dict = {}
        for r in rows:
            by_case.setdefault(r.get("label"), []).append(r)
        for label, items in by_case.items():
            valid = []
            for r in items:
                m = r.get("metrics", {})
                tpot = m.get("tpot_mean")
                if tpot is not None:
                    valid.append((float(tpot), r))
            if not valid:
                continue
            below = [(t, r) for t, r in valid if t < threshold]
            if below:
                best_t, best_r = max(below, key=lambda x: x[0])
            else:
                best_t, best_r = min(valid, key=lambda x: x[0])
            best_r["best"] = True
            best_r["best_tpot"] = best_t
        return rows

    def stop(self):
        """停止所有运行中的任务。"""
        with self._lock:
            for task_id, runner in list(self._runners.items()):
                runner.kill()
