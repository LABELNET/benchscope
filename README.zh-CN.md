# benchscope

[English](README.md) | **简体中文**

> 面向 **vLLM / SGLang** 及任意 **OpenAI 兼容**推理服务的单进程、pip 可直接安装的 Web 性能测试工具。

## 介绍

benchscope 是面向大模型推理服务的性能测试工具。连接 vLLM / SGLang（或任意 OpenAI 兼容）推理服务后，通过**管理台风格的 Web 界面**即可进行吞吐/时延压测。

- **执行方式** — bench 工具（`vllm bench serve` / `sglang.bench_serving`）在 benchscope 所在机器以子进程运行；推理服务端只需提供 OpenAI 兼容 API，**无需安装任何插件**。
- **实时反馈** — 每个并发结果实时流入表格与曲线。
- **单进程** — `pip install` 后一条命令同时启动后端与内置前端。

## 快速开始

```bash
# 从 PyPI 安装
pip install benchscope

# 启动（默认 http://127.0.0.1:8080，自动打开浏览器）
benchscope

# 可选参数
benchscope --port 8080 --no-browser
```

打开页面后，通过顶部 5 栏导航 **Dashboard / Performance / Accuracy / Sessions / Settings** 切换：

1. **Settings** →「推理服务 API」分区，填写 **Base URL**（任意 OpenAI 兼容地址），点击「测试连接」确认能拉到 `/v1/models`。
2. **Performance** → 点击「新建测试任务」打开任务表单（选择模型 + 框架、数据集、并发、高级参数、命令预览），创建后自动跳转任务详情页。
3. 任务详情页左侧为实时进度 + bench 终端，右侧为实时双语表格与六条曲线（顶部状态栏含开始/停止/重试/命令预览按钮）。
4. **Dashboard** 展示统计卡片（总测试次数 / 进行中任务 / 平均 TPOT / 最佳模型）与历史运行记录列表（内嵌均值/P99 分析面板）。
5. **Sessions** 与推理服务进行 SSE 流式对话（模型选择 + 系统提示词 + Markdown 渲染）。
6. 日志保存在 `logs/<月日-时分秒>/` 目录，并生成 `benchmark-*.xlsx` 汇总（均值 + P99 双 sheet）。

> UI 语言（中/英）与主题（亮色/暗色/跟随系统）可在 **Settings → 通用** 中切换。

## 功能特性

- **双框架** — vLLM（`vllm bench serve`）与 SGLang（`sglang.bench_serving`）。
- **数据集**
  - `random` — 多组输入/输出长度组合（默认 `3K/1K`、`1K/1K`、`256/256`，可自定义）。
  - `sharegpt` — 自动从 [ModelScope](https://www.modelscope.cn/datasets/gliang1001/ShareGPT_V3_unfiltered_cleaned_split) 下载。
  - `custom` — 上传 jsonl 或指定服务器本地路径（与 ShareGPT 功能一致）。
- **可配置压测** — 并发数列表可编辑（默认 `1,4,8,16,32,40,64,128`）、`--max-concurrency` = `--num-prompts`、`inf` 限速选项、框架参数表单 + 自由参数编辑器、命令预览。
- **GPU 自动检测**（`nvidia-smi`）并提供手动回退；可设 **TPOT 阈值**以高亮最佳/最接近行。
- **实时结果** — 双语表格 + 六条曲线（Output/Total 吞吐，TTFT/TPOT mean & P99）随并发数变化。
- **日志** — 每次运行一个 `月日-时分秒` 目录，含原始 bench 日志、mean/P99 汇总 CSV 与 `benchmark-*.xlsx`（双 sheet，含单用户 = `1000/tpot` 列）；界面内支持预览与下载。
- **分析** — 均值 / P99 两大块，含 output/peakoutput/total/ttft/itl/tpot 曲线与**最佳并发高亮**（最接近且低于 TPOT 阈值的记录）。
- **任务化 Performance（v1.0.5）** — 在 Performance 页创建测试任务，每任务独立线程运行并持久化到 `~/.benchscope/tasks/`，刷新页面不丢任务。任务详情页左侧实时进度 + bench 终端，右侧实时双语表格 + 六条曲线。
- **Dashboard（v1.0.5）** — 统计卡片（总测试次数 / 进行中任务 / 平均 TPOT / 最佳模型）+ 历史运行记录列表（内嵌均值/P99 分析面板）。
- **Sessions（v1.0.5）** — 与 OpenAI 兼容 API 的 SSE 流式对话；会话持久化到 `~/.benchscope/sessions/`。
- **Accuracy（v1.0.5）** — 占位页，为 v5.0 精度测试版本预留。
- **i18n 与主题（v1.0.5）** — 中英双语 UI 与亮色/暗色/跟随系统主题切换，均在 Settings 配置。
- **管理台 UI** — 固定顶栏 5 项导航（Dashboard / Performance / Accuracy / Sessions / Settings）+ 每页副导航；内容区内部滚动。旧路由 `/vllm`、`/sglang`、`/logs` 已重定向到新页面。
- **状态监控** — 「服务」与「环境」在线/离线指示灯实时刷新。

## 规划

| 版本 | 状态 | 范围 |
| --- | --- | --- |
| 1.0.0 | 🚀 已发布 | 纯文本性能测试 — 双框架、三种数据集、实时结果、日志与 xlsx 汇总、分析、管理台 UI |
| 1.0.5 | 🚀 已发布 | v2.0 UI 大改：5 栏导航（Dashboard / Performance / Accuracy / Sessions / Settings）、任务化 Performance（持久化）、Sessions 会话、i18n（中英）、亮/暗/跟随系统主题 |
| 2.0 | 🔜 规划中 | 多模态模型性能测试 |
| 3.0 | 规划中 | 全模态（音频/视频等）模型性能测试 |
| 4.0 | 规划中 | 世界模型性能测试 |
| 5.0 | 规划中 | 常见数据集精度测试 |
| 6.0 | 规划中 | ModelScope 官方模型链接与对比结论 |

> 完整版本计划：[ROADMAP.md](ROADMAP.md) · 产品需求：[PROJECTS-README.md](PROJECTS-README.md)

## 目录结构

```
benchscope/
├── benchscope/
│   ├── cli.py            # `benchscope` 命令入口
│   ├── config.py         # 配置持久化 (~/.benchscope/config.json)
│   ├── task_manager.py   # 任务化性能测试执行器 + 持久化
│   ├── session_manager.py # 会话存储 + SSE 流式对话
│   ├── datasets.py       # sharegpt 下载/转换、自定义数据集
│   ├── gpu.py            # GPU 自动检测
│   ├── parser.py         # bench 输出解析（mean + P99）
│   ├── summary.py        # CSV 与 xlsx 汇总生成
│   ├── benches/          # vllm/sglang 命令构建与执行
│   └── server/           # FastAPI + WebSocket + 测试编排
│       ├── api_config.py     # 配置 / 模型 / GPU / 状态 API
│       ├── api_test.py       # 旧版单测试启停 API
│       ├── api_tasks.py      # 任务 CRUD + 启停/预览
│       ├── api_sessions.py   # 会话 CRUD + SSE 对话
│       ├── api_dashboard.py  # Dashboard 统计（总测试次数 / 平均 TPOT / 最佳模型）
│       ├── api_logs.py       # 运行记录与数据集管理 API
│       ├── test_manager.py   # 旧版单测试管理器（api_test 使用）
│       └── ws.py             # WebSocket 广播 Hub
├── web/                  # Vue 3 + Ant Design Vue 前端源码
│   └── src/views/        # DashboardView / PerformanceView / TaskDetailView /
│                          CreateTaskView / AccuracyView / SessionsView / SettingsView
└── tests/                # 模拟 OpenAI 服务与 UI 冒烟测试
```

## 开发调试

```bash
# 后端
python -m benchscope.cli --port 8080 --no-browser

# 前端（热更新，代理 /api 与 /ws 到 :8080）
cd web && npm install && npm run dev    # http://127.0.0.1:5173
```

- 无 vLLM/SGLang 环境联调：`BENCHSCOPE_FAKE_BENCH=1 python -m benchscope`，以仿真数据执行。
- 本地模拟推理服务：`python tests/mock_openai_server.py`（端口 8001），并在「设置」中把 Base URL 指向 `http://127.0.0.1:8001`。

## 开源信息

- **许可证** — [Apache License 2.0](LICENSE)
- **发布平台** — [PyPI: benchscope](https://pypi.org/project/benchscope/)
- **源码仓库** — <https://github.com/LABELNET/benchscope>
- **贡献** — 欢迎在源码仓库提交 Issue 或 Pull Request。
