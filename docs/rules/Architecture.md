# 系统架构 — Architecture

> **文档状态**：benchscope 系统架构、核心模块与操作模块说明  
> **关联**：[Software.md](./Software.md)（技术选型与依赖）· [Development.md](./Development.md)（开发/验证/部署）

---

## 1. 整体架构

单进程 Web 应用：**Python 后端（FastAPI + WebSocket）** 内置托管 **Vue 3 前端构建产物**，`pip install` 后一条命令启动，无需外部服务。

```text
┌─────────────────────────── 单进程 (benchscope) ───────────────────────────┐
│                                                                           │
│  Web 前端 (Vue3 + AntDV，构建产物 webui/)                                  │
│  └─ Dashboard / Performance / Accuracy / Sessions / Settings              │
│        │  HTTP /api/*          │  WS /ws（状态广播、任务日志、结果流）       │
│        ▼                       ▼                                          │
│  FastAPI server（api_config / api_tasks / api_sessions /                  │
│                  api_dashboard / api_logs / ws）                          │
│        │                                                                  │
│        ├─ TaskManager ── BenchRunner ── bash -lic ── vllm bench / sglang  │
│        │                     （子进程执行，实时回传日志与结果）               │
│        ├─ StatusMonitor ── 探测 {base_url}/v1/models（每 5s）              │
│        └─ SessionManager ── OpenAI 兼容端点 SSE 流式转发                    │
└────────────────────────────────────────────────────────────────────────────┘
         │ 调用
         ▼
   vLLM / SGLang / 任意 OpenAI 兼容推理服务（仅需暴露 API，无需装插件）
```

## 2. 核心模块

| 模块 | 职责 |
| --- | --- |
| `benchscope/cli.py` | 命令行入口（`benchscope` / `python -m benchscope.cli`） |
| `benchscope/config.py` + `constants.py` | 配置持久化（`~/.benchscope/settings.json`，旧版 `config.json` 兼容迁移）与默认值（9 目录体系） |
| `benchscope/task_manager.py` | 任务生命周期（创建/执行/停止/持久化），双模式执行策略（并发/阈值 + 二分探测），结果行携带 `case_id` |
| `benchscope/session_manager.py` | 会话存储 + SSE 流式对话 + 思考标签解析（`parse_think_tags`） |
| `benchscope/parser.py` | bench 输出解析（mean + P99 双套指标，vLLM/SGLang 格式兼容） |
| `benchscope/summary.py` | CSV / xlsx 汇总（mean + P99 双 sheet） |
| `benchscope/env_info.py` | 系统环境信息采集（硬件/OS/网络/框架版本，虚拟网卡过滤） |
| `benchscope/benches/` | vLLM / SGLang 命令构建 + 子进程流式执行器（FAKE 模式） |
| `benchscope/server/` | FastAPI 路由（config/tasks/sessions/dashboard/logs/test）+ WebSocket 广播 + 状态监控 |
| `mocks/` | mock 调试环境：vLLM/SGLang 仿真输出生成器、mock OpenAI 兼容服务（SSE） |
| `web/` | Vue 3 + Ant Design Vue 前端源码 |

## 3. 操作模块（用户操作流）

| 操作 | 入口 → 链路 |
| --- | --- |
| 配置推理服务 | Settings → Envs → Edit/Save + Test Connection → `config.api`（base_url / api_key） |
| 创建性能任务 | Performance → 并发/阈值入口 → `/performance/create` 三步表单 → `POST /api/tasks` + `start` |
| 任务执行监控 | WS 广播：`task_log`（终端行 + 当前 case/concurrency 位置）、`task_result`（结果行）、`task_snapshot`、`task_done` |
| 阈值高亮 | 前端 computed 按组（`caseKey`）标记 Best/BestPerf（本地阈值与任务阈值） |
| 导出 Excel | Realtime 表格 Download → `POST /api/tasks/{id}/export` → run_dir 缓存 + 下载 |
| 精度/评估 | Accuracy 占位；Dashboard Eval Records 空态（v5.0） |
| 对话 | Sessions → `POST /api/sessions/{id}/chat` SSE 流式（思考 + 正文） |
| 模型下载 | Settings → Models → 宫格 → 详情抽屉（精度/链接/下载命令）；部署按钮待实现 |
| mock 联调 | `./scripts/dev.sh`（mock OpenAI :8001 + 统一入口 :8080，FAKE bench） |

## 4. 关键设计约束

- **单进程**：前端构建产物由后端静态托管，无独立前端服务（dev 脚本亦然）。静态资源 `/assets` 挂载目录；`bs-logo.png` 与 `blue_logo.png`（网站 LOGO）单独注册路由，避免被 SPA fallback 拦截。
- **子进程执行 bench**：`bash -lic` + 最小环境变量，自动 source 平台脚本（maca 等），支持用户自定义 `bench_shell_init`。
- **无服务端插件**：仅需推理服务暴露 OpenAI 兼容 API。
- **持久化**：配置 `~/.benchscope/settings.json`（旧版 `config.json` 首启自动迁移）。**9 目录体系**：`data_dir` 根（默认 `~/.benchscope`）+ 8 功能子目录（perfs / evals / analysis / logs / sessions / models / datasets / plugins），子目录未自定义时跟随 `data_dir`；任务 run_dir 按 `kind` 落 `perfs_dir` / `evals_dir`；终端输出日志 `logs_dir/perf|eval_runID_*.log`；会话 `sessions_dir`；内置数据集缓存 `datasets_dir/{id}/`。
