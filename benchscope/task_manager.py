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

from benchscope.benches.base import BenchOptions, merge_extra_args
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
        for item in pairs:
            il, ol, label, *rest = item
            cases.append({
                "label": label,
                "case_id": rest[0] if rest else None,  # 唯一组 id，区分相同条件的多组
                "input_len": il, "output_len": ol, "path": None,
            })
    else:
        label = "ShareGPT" if ds_type == DATASET_SHAREGPT else "Custom"
        if ds_type == DATASET_SHAREGPT and dataset.get("label"):
            label = dataset["label"]
        cases.append({"label": label, "case_id": None, "input_len": None, "output_len": None, "path": dataset.get("path")})
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
    kind: str = "perf"  # perf（性能测试）| eval（精度测试）
    log_path: Optional[Path] = None  # 终端输出日志（logs_dir 下 perf/eval_runID_*.log）
    _persist_path: Optional[Path] = None

    def snapshot(self, include_rows: bool = True) -> dict:
        data = {
            "task_id": self.task_id,
            "run_dir": str(self.run_dir),
            "kind": self.kind,
            "log_path": str(self.log_path) if self.log_path else None,
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
            "mode": self.payload.get("mode", "concurrency"),
            "output_throughput_threshold": self.payload.get("output_throughput_threshold", 0),
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

    def persist_run_json(self):
        """将 snapshot() 写入 run_dir/run.json，供 Dashboard/Logs API 读取运行元数据。

        与 persist() 并行：persist() 写 tasks/<id>.json，
        本方法写 perfs|evals/<run_id>/run.json（按任务类型分目录）。失败时 log.exception 但不抛。
        """
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / "run.json").write_text(
                json.dumps(self.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            log.exception("persist_run_json failed: %s", self.task_id)


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
                kind = data.get("kind", "perf")
                default_run_dir = (
                    self.config.perfs_dir if kind == "perf" else self.config.evals_dir
                ) / task_id.replace("task-", "")
                task = Task(
                    task_id=task_id,
                    run_dir=Path(data.get("run_dir", str(default_run_dir))),
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
                    kind=kind,
                    log_path=Path(data["log_path"]) if data.get("log_path") else None,
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
            kind = payload.get("kind", "perf")
            now = datetime.now()
            task_id = f"task-{now.strftime('%m%d-%H%M%S')}"
            run_root = self.config.perfs_dir if kind == "perf" else self.config.evals_dir
            run_dir = run_root / task_id.replace("task-", "")
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
                kind=kind,
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
            try:
                if persist_path.exists():
                    persist_path.unlink()
            except OSError:
                # 权限/只读文件等:任务已从内存移除,持久化文件残留不影响功能
                log.warning("unlink persist failed: %s", persist_path)

    # ------------------------------------------------------------------
    def _execute(self, task: Task):
        framework = task.framework
        tmpl = (self.config.get("bench_commands") or {}).get(framework, "")
        runner = BenchRunner(command_template=tmpl)
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
        # 终端输出日志落盘到 logs 目录：perf|eval_runID_月日时分秒.log
        run_id = task.task_id.replace("task-", "")
        ts = datetime.now().strftime("%m%d%H%M%S")
        full_log_path = self.config.logs_dir / f"{task.kind}_{run_id}_{ts}.log"
        full_log_path.parent.mkdir(parents=True, exist_ok=True)
        task.log_path = full_log_path
        full_log_fp = open(full_log_path, "a", encoding="utf-8")

        try:
            self.hub.broadcast({"type": "task_started", "task_id": task.task_id, "task": task.snapshot()})
            task.persist_run_json()  # 任务开始：写 run.json（status=running）
            cases_done = 0
            mode = task.payload.get("mode", "concurrency")
            for case in task.cases:
                if runner._stop_flag.is_set():
                    break
                case_label = case["label"]
                detail_path = task.run_dir / f"{model_name}_{case_label}_X{gpu_count}.log"
                detail_fp = open(detail_path, "a", encoding="utf-8")
                if mode == "threshold":
                    self._execute_case_threshold(runner, task, case, detail_fp, full_log_fp, mean_csv, p99_csv, meta)
                else:
                    concurrency_ok = 0
                    for conc in task.payload.get("concurrency_list", []):
                        if runner._stop_flag.is_set():
                            break
                        if conc == "inf" or conc is None:
                            continue
                        conc = int(conc)
                        try:
                            row = self._run_one(runner, task, case, conc, detail_fp, full_log_fp, meta)
                            self._record_row(task, row, mean_csv, p99_csv, case, meta, concurrency_ok == 0)
                            concurrency_ok += 1
                        except StopRequested:
                            break
                        except Exception as e:
                            log.exception("Concurrency %s failed", conc)
                            err_row = {"case": case_label, "label": case_label, "case_id": case.get("case_id"), "input_len": case.get("input_len"), "output_len": case.get("output_len"), "concurrency": conc, "error": str(e)[:500]}
                            self._record_row(task, err_row, mean_csv, p99_csv, case, meta, concurrency_ok == 0)
                            concurrency_ok += 1
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
            task.persist_run_json()  # 任务结束：写 run.json（done/stopped）
            self.hub.broadcast({"type": "task_done", "task_id": task.task_id, "task": task.snapshot()})
        except StopRequested:
            task.status = "stopped"
            task.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task.persist()
            task.persist_run_json()  # 任务结束：写 run.json（stopped）
            self.hub.broadcast({"type": "task_done", "task_id": task.task_id, "task": task.snapshot()})
        except Exception as e:
            log.exception("Task execution failed")
            task.status = "error"
            task.error = str(e)
            task.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task.persist()
            task.persist_run_json()  # 任务结束：写 run.json（error）
            self.hub.broadcast({"type": "task_error", "task_id": task.task_id, "error": str(e), "task": task.snapshot()})
        finally:
            try:
                full_log_fp.close()
            except Exception:
                pass
            self._runners.pop(task.task_id, None)
            self._threads.pop(task.task_id, None)

    def _run_one(self, runner, task, case, concurrency, detail_fp, full_log_fp, meta):
        ds = dict(task.payload.get("dataset", {}))
        ds.update({"input_len": case.get("input_len"), "output_len": case.get("output_len"), "path": case.get("path")})
        cmd = build_single_command(
            task.framework, task.model, task.payload.get("tokenizer", ""),
            dict(self.config.api), ds, concurrency,
            task.payload.get("request_rate", "inf"),
            task.payload.get("curated", {}),
            merge_extra_args(task.payload, task.payload.get("extra_args", [])),
        )

        def stream(line: str):
            detail_fp.write(line)
            full_log_fp.write(line)
            full_log_fp.flush()
            self.hub.broadcast({"type": "task_log", "task_id": task.task_id, "case": case["label"], "case_id": case.get("case_id"), "concurrency": concurrency, "line": line})

        shell_init = (self.config.get("bench_shell_init") or "").strip()
        metrics = runner.run(cmd, stream_cb=stream, shell_init=shell_init)
        return {
            "case": case["label"], "label": case["label"], "case_id": case.get("case_id"),
            "input_len": case.get("input_len"), "output_len": case.get("output_len"),
            "concurrency": concurrency, "cmd": " ".join(cmd), "metrics": metrics,
        }

    def _record_row(self, task, row, mean_csv, p99_csv, case, meta, case_header):
        """记录一行结果：追加 rows、写 CSV、持久化、广播 task_result。"""
        task.rows.append(row)
        write_summary_csv(mean_csv, [row], p99=False, append=True, case_header=case_header, case=case, meta=meta)
        write_summary_csv(p99_csv, [row], p99=True, append=True, case_header=case_header, case=case, meta=meta)
        task.persist()
        task.persist_run_json()  # 每完成一个并发：刷新 run.json
        self.hub.broadcast({"type": "task_result", "task_id": task.task_id, "row": row})

    def _execute_case_threshold(self, runner, task, case, detail_fp, full_log_fp, mean_csv, p99_csv, meta):
        """阈值模式执行策略（对单个 case）：

        1. 从 1 并发开始执行，以 2 的次方递增（1,2,4,8,...）寻找超阈值点；
        2. 若 1 并发已超阈值 → 1 并发为最佳，结束（情景1）；
        3. 若执行到 hi=2^k 超阈值（lo=2^(k-1) 满足）→ 在 (lo, hi] 内二分，
           每次测试 (lo+hi)/2 取整，直到 lo+1 == hi，lo 即为满足阈值的最大并发；
        4. 若达到上限仍满足 → 上限并发为最佳。
        已测试的并发会动态追加到 payload.concurrency_list 并广播 task_snapshot，
        前端进度（done/total）随执行实时增长。
        """
        payload = task.payload
        try:
            tpot_thr = float(payload.get("tpot_threshold_ms")) if payload.get("tpot_threshold_ms") not in (None, "") else 0.0
        except (TypeError, ValueError):
            tpot_thr = 0.0
        try:
            out_thr = float(payload.get("output_throughput_threshold") or 0)
        except (TypeError, ValueError):
            out_thr = 0.0
        max_conc = int(payload.get("max_concurrency_search") or 4096)
        rows_in_case = 0

        def violated(row) -> bool:
            m = row.get("metrics") or {}
            if tpot_thr > 0 and m.get("tpot_mean") is not None:
                try:
                    if float(m["tpot_mean"]) > tpot_thr:
                        return True
                except (TypeError, ValueError):
                    pass
            if out_thr > 0 and m.get("output") is not None:
                try:
                    if float(m["output"]) > out_thr:
                        return True
                except (TypeError, ValueError):
                    pass
            return False

        def push_conc(conc):
            clist = payload.setdefault("concurrency_list", [])
            if conc not in clist:
                clist.append(conc)
                task.persist()
                task.persist_run_json()
                self.hub.broadcast({"type": "task_snapshot", "task_id": task.task_id, "task": task.snapshot()})

        def run_conc(conc):
            nonlocal rows_in_case
            conc = int(conc)
            push_conc(conc)
            try:
                row = self._run_one(runner, task, case, conc, detail_fp, full_log_fp, meta)
            except StopRequested:
                raise
            except Exception as e:
                log.exception("Threshold concurrency %s failed", conc)
                row = {"case": case["label"], "label": case["label"], "case_id": case.get("case_id"), "input_len": case.get("input_len"),
                       "output_len": case.get("output_len"), "concurrency": conc, "error": str(e)[:500]}
                self._record_row(task, row, mean_csv, p99_csv, case, meta, rows_in_case == 0)
                rows_in_case += 1
                return row  # 失败不视为违反阈值，继续向上探测
            self._record_row(task, row, mean_csv, p99_csv, case, meta, rows_in_case == 0)
            rows_in_case += 1
            return row

        # 从 1 并发开始
        if runner._stop_flag.is_set():
            return
        lo = 1
        row = run_conc(lo)
        if violated(row):
            return  # 情景1：1 并发已超阈值，最佳并发为 1
        # 2 的次方递增
        while not runner._stop_flag.is_set() and lo * 2 <= max_conc:
            hi = lo * 2
            row = run_conc(hi)
            if violated(row):
                # 二分 (lo, hi]：lo 满足阈值，hi 超阈值
                while not runner._stop_flag.is_set() and hi - lo > 1:
                    mid = (lo + hi) // 2
                    row = run_conc(mid)
                    if violated(row):
                        hi = mid
                    else:
                        lo = mid
                return
            lo = hi
        # 到达上限仍满足 → 上限为最佳

    def _annotate_best(self, rows, threshold):
        if threshold is None:
            return rows
        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            return rows
        by_case: dict = {}
        for r in rows:
            by_case.setdefault(r.get("case_id") or r.get("label"), []).append(r)
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
