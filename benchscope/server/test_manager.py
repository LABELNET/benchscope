"""测试执行管理器：编排用例×并发，流式执行、实时推送、日志落盘、xlsx 汇总。"""
from __future__ import annotations

import json
import logging
import os
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
from benchscope.constants import (
    DATASET_RANDOM, DATASET_SHAREGPT, FRAMEWORK_NAMES,
)
from benchscope.summary import write_summary_csv, write_xlsx

log = logging.getLogger("benchscope.test")


def sanitize_name(name: str) -> str:
    """把模型名/路径转成安全的文件名片段。"""
    return re.sub(r"[^\w.-]", "_", name).strip("_")


def build_cases(dataset: dict, model: str) -> list[dict]:
    """根据数据集配置生成用例列表。"""
    ds_type = dataset.get("type", DATASET_RANDOM)
    cases: list[dict] = []
    if ds_type == DATASET_RANDOM:
        pairs = dataset.get("length_pairs") or []
        for item in pairs:
            il, ol, label, *rest = item
            cases.append({
                "label": label,
                "case_id": rest[0] if rest else None,  # 唯一组 id，区分相同条件的多组
                "input_len": il,
                "output_len": ol,
                "path": None,
            })
    else:
        label = "ShareGPT" if ds_type == DATASET_SHAREGPT else "Custom"
        if ds_type == DATASET_SHAREGPT and dataset.get("label"):
            label = dataset["label"]
        cases.append({
            "label": label,
            "case_id": None,
            "input_len": None,
            "output_len": None,
            "path": dataset.get("path"),
        })
    return cases


@dataclass
class TestRun:
    run_id: str
    run_dir: Path
    payload: dict
    framework: str
    model: str
    gpu: dict
    cases: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    status: str = "running"          # running | done | stopped | error
    error: Optional[str] = None
    summary: Optional[dict] = None
    started_at: str = ""
    finished_at: str = ""
    precision: str = ""

    def snapshot(self, include_rows: bool = True) -> dict:
        data = {
            "run_id": self.run_id,
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
            "precision": self.precision,
            "concurrency_list": self.payload.get("concurrency_list", []),
            "request_rate": self.payload.get("request_rate", "inf"),
            "tpot_threshold_ms": self.payload.get("tpot_threshold_ms"),
            "ttft_threshold_ms": self.payload.get("ttft_threshold_ms", 0),
            "ttft_statistic": self.payload.get("ttft_statistic", "mean"),
            "tpot_statistic": self.payload.get("tpot_statistic", "mean"),
            "output_throughput_threshold": self.payload.get("output_throughput_threshold", 0),
            "mode": self.payload.get("mode", "concurrency"),
            "dataset": self.payload.get("dataset", {}),
        }
        if include_rows:
            data["rows"] = self.rows
        return data


def build_single_command(
    framework: str, model: str, tokenizer: str, api: dict, dataset: dict,
    concurrency: int, request_rate, curated: dict, extra_args: list,
) -> list[str]:
    """构建单条 bench 命令（供执行与预览共用）。"""
    opts = BenchOptions(
        framework=framework,
        model=model,
        api=api,
        dataset=dataset,
        concurrency=concurrency,
        request_rate=request_rate,
        curated=curated or {},
        extra_args=extra_args or [],
    )
    opts.tokenizer = tokenizer or model
    if framework == "sglang":
        return sglang_bench.build_command(opts)
    return vllm_bench.build_command(opts)


def build_command_lines(payload: dict, config) -> list[dict]:
    """为 payload 中的所有用例×并发构建命令列表（预览用）。

    阈值模式（mode=threshold）下并发由策略动态决定，预览仅给出从 1 并发开始的
    首条命令；Step2「性能参数」编辑的 yaml 参数会以 --key=value 形式附加到命令。
    """
    framework = payload.get("framework", "vllm")
    model = payload.get("model", "")
    tokenizer = payload.get("tokenizer", "")
    dataset = dict(payload.get("dataset", {}))
    cases = build_cases(dataset, model)
    mode = payload.get("mode", "concurrency")
    conc_list = payload.get("concurrency_list", [])
    if mode == "threshold":
        conc_list = conc_list[:1] or [1]  # 阈值模式：预览从 1 并发开始
    lines = []
    for case in cases:
        ds = dict(dataset)
        ds.update({
            "input_len": case.get("input_len"),
            "output_len": case.get("output_len"),
            "path": case.get("path"),
        })
        for conc in conc_list:
            if conc == "inf" or conc is None:
                continue
            cmd = build_single_command(
                framework, model, tokenizer, dict(config.api), ds,
                int(conc), payload.get("request_rate", "inf"),
                payload.get("curated", {}),
                merge_extra_args(payload, payload.get("extra_args", [])),
            )
            lines.append({"case": case["label"], "concurrency": int(conc), "cmd": " ".join(cmd)})
    return lines


class TestManager:
    def __init__(self, config, hub):
        self.config = config
        self.hub = hub
        self._lock = threading.RLock()
        self.current: Optional[TestRun] = None
        self._thread: Optional[threading.Thread] = None
        self._runner: Optional[BenchRunner] = None

    # ------------------------------------------------------------------
    @property
    def running(self) -> bool:
        with self._lock:
            return self.current is not None and self.current.status == "running"

    def start(self, payload: dict) -> TestRun:
        with self._lock:
            if self.running:
                raise RuntimeError("已有测试正在运行，请先停止。")
            # sharegpt 数据集：未指定路径时自动从 modelscope 下载
            dataset = payload.get("dataset", {})
            if dataset.get("type") == DATASET_SHAREGPT and not dataset.get("path"):
                from benchscope.datasets import ensure_sharegpt

                path = str(ensure_sharegpt(self.config.datasets_dir))
                dataset = dict(dataset)
                dataset["path"] = path
                payload = dict(payload)
                payload["dataset"] = dataset
            run = self._create_run(payload)
            self.current = run
            self._thread = threading.Thread(
                target=self._execute, args=(run,), name="bench-run", daemon=True
            )
            self._thread.start()
            return run

    def stop(self) -> None:
        runner = self._runner
        if runner:
            runner.kill()

    def _create_run(self, payload: dict) -> TestRun:
        framework = payload.get("framework", "vllm")
        model = payload.get("model", "")
        gpu = payload.get("gpu", {})
        run_id = datetime.now().strftime("%m%d-%H%M%S")
        run_dir = self.config.perfs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        run = TestRun(
            run_id=run_id,
            run_dir=run_dir,
            payload=payload,
            framework=framework,
            model=model,
            gpu=gpu,
            precision=payload.get("precision", ""),
            started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        run.cases = build_cases(payload.get("dataset", {}), model)
        return run

    # ------------------------------------------------------------------
    def _execute(self, run: TestRun) -> None:
        framework = run.framework
        tmpl = (self.config.get("bench_commands") or {}).get(framework, "")
        runner = BenchRunner(command_template=tmpl)
        self._runner = runner

        model_name = sanitize_name(Path(run.model).name or run.model)
        gpu_count = run.gpu.get("count", "") if isinstance(run.gpu, dict) else run.gpu
        gpu_label = f"{gpu_count}" if gpu_count else ""
        if isinstance(run.gpu, dict) and run.gpu.get("name"):
            gpu_label = f"{run.gpu['name']}×{gpu_count}" if gpu_count else run.gpu["name"]

        meta = {
            "model": run.model,
            "model_name": model_name,
            "framework": FRAMEWORK_NAMES.get(framework, framework),
            "gpu": gpu_label,
            "precision": run.precision,
        }
        mean_csv = run.run_dir / f"{model_name}_X{gpu_count}.log"
        p99_csv = run.run_dir / f"{model_name}_X{gpu_count}_p99.log"

        try:
            self.hub.broadcast({"type": "run_started", "run": run.snapshot()})
            cases_done = 0
            for case in run.cases:
                if runner._stop_flag.is_set():
                    break
                case_label = case["label"]
                detail_path = run.run_dir / f"{model_name}_{case_label}_X{gpu_count}.log"
                detail_fp = open(detail_path, "a", encoding="utf-8")
                concurrency_ok = 0
                for conc in run.payload.get("concurrency_list", []):
                    if runner._stop_flag.is_set():
                        break
                    if conc == "inf" or conc is None:
                        continue
                    conc = int(conc)
                    try:
                        row = self._run_one(runner, run, case, conc, detail_fp, meta)
                        run.rows.append(row)
                        concurrency_ok += 1
                        # 增量写汇总 CSV
                        write_summary_csv(
                            mean_csv, [row], p99=False, append=True, case_header=concurrency_ok == 1, case=case, meta=meta
                        )
                        write_summary_csv(
                            p99_csv, [row], p99=True, append=True, case_header=concurrency_ok == 1, case=case, meta=meta
                        )
                        self.hub.broadcast({"type": "result", "run_id": run.run_id, "row": row})
                    except StopRequested:
                        break
                    except Exception as e:
                        log.exception("并发 %s 执行失败", conc)
                        err_row = {
                            "case": case_label, "label": case_label,
                            "input_len": case.get("input_len"), "output_len": case.get("output_len"),
                            "concurrency": conc, "error": str(e)[:500],
                        }
                        run.rows.append(err_row)
                        self.hub.broadcast({"type": "result", "run_id": run.run_id, "row": err_row})
                detail_fp.close()
                cases_done += 1

            # 汇总 xlsx
            if run.rows:
                rows_for_xlsx = [r for r in run.rows if "metrics" in r]
                if rows_for_xlsx:
                    annotated = self._annotate_best(rows_for_xlsx, run.payload.get("tpot_threshold_ms"))
                    xlsx_path = run.run_dir / f"benchmark-{datetime.now().strftime('%d%m%y')}.xlsx"
                    write_xlsx(xlsx_path, annotated, meta)
                    run.summary = {"xlsx": str(xlsx_path), "rows": len(rows_for_xlsx)}

            run.status = "stopped" if runner._stop_flag.is_set() else "done"
            run.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_run_json(run)
            self.hub.broadcast({"type": "run_done", "run_id": run.run_id, "run": run.snapshot()})
        except StopRequested:
            run.status = "stopped"
            run.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_run_json(run)
            self.hub.broadcast({"type": "run_done", "run_id": run.run_id, "run": run.snapshot()})
        except Exception as e:
            log.exception("测试执行失败")
            run.status = "error"
            run.error = str(e)
            run.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_run_json(run)
            self.hub.broadcast({"type": "run_error", "run_id": run.run_id, "error": str(e), "run": run.snapshot()})
        finally:
            self._runner = None

    def _run_one(self, runner: BenchRunner, run: TestRun, case: dict,
                 concurrency: int, detail_fp, meta: dict) -> dict:
        ds = dict(run.payload.get("dataset", {}))
        ds.update({
            "input_len": case.get("input_len"),
            "output_len": case.get("output_len"),
            "path": case.get("path"),
        })
        cmd = build_single_command(
            run.framework, run.model, run.payload.get("tokenizer", ""),
            dict(self.config.api), ds, concurrency,
            run.payload.get("request_rate", "inf"),
            run.payload.get("curated", {}), run.payload.get("extra_args", []),
        )

        def stream(line: str):
            detail_fp.write(line)
            self.hub.broadcast({
                "type": "log_line", "run_id": run.run_id,
                "case": case["label"], "concurrency": concurrency, "line": line,
            })

        shell_init = (self.config.get("bench_shell_init") or "").strip()
        metrics = runner.run(cmd, stream_cb=stream, shell_init=shell_init)
        return {
            "case": case["label"], "label": case["label"],
            "input_len": case.get("input_len"), "output_len": case.get("output_len"),
            "concurrency": concurrency,
            "cmd": " ".join(cmd),
            "metrics": metrics,
        }

    def _annotate_best(self, rows: list[dict], threshold) -> list[dict]:
        """为每个用例标记最接近且低于阈值的 TPOT 行为最佳行。"""
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
                best_t, best_r = max(below, key=lambda x: x[0])  # 最接近阈值（从下方）
            else:
                best_t, best_r = min(valid, key=lambda x: x[0])  # 无低于阈值则取最小
            best_r["best"] = True
            best_r["best_tpot"] = best_t
        return rows

    def _save_run_json(self, run: TestRun) -> None:
        try:
            (run.run_dir / "run.json").write_text(
                json.dumps(run.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            log.exception("保存 run.json 失败")
