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

打开页面后：

1. 确认顶部导航「服务」（应用）与「环境」（推理服务）显示为在线。
2. 进入右上角「设置」，配置推理服务 **Base URL**（任意 OpenAI 兼容地址）。
3. 打开 **vLLM / SGLang** 页面，选择模型（来自 `/v1/models`）、数据集（Random / ShareGPT / Custom）与并发数。
4. 在「测试进度 → 开始测试」执行。**测试结果**面板实时更新双语表格与六条曲线。
5. 日志保存在 `logs/<月日-时分秒>/` 目录，并生成 `benchmark-*.xlsx` 汇总（均值 + P99 双 sheet）。

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
- **管理台 UI** — 固定顶栏、固定左侧导航（测试流程 / 测试记录）、固定副导航；内容区内部滚动。
- **状态监控** — 「服务」与「环境」在线/离线指示灯实时刷新。

## 规划

| 版本 | 状态 | 范围 |
| --- | --- | --- |
| 1.0.0 | 🚀 已发布 | 纯文本性能测试 — 双框架、三种数据集、实时结果、日志与 xlsx 汇总、分析、管理台 UI |
| 2.0 | 🔜 规划中 | 多模态模型性能测试 |
| 3.0 | 规划中 | 全模态（音频/视频等）模型性能测试 |
| 4.0 | 规划中 | 世界模型性能测试 |
| 5.0 | 规划中 | 常见数据集精度测试 |
| 6.0 | 规划中 | ModelScope 官方模型链接与对比结论 |

## 目录结构

```
benchscope/
├── benchscope/
│   ├── cli.py            # `benchscope` 命令入口
│   ├── config.py         # 配置持久化 (~/.benchscope/config.json)
│   ├── datasets.py       # sharegpt 下载/转换、自定义数据集
│   ├── gpu.py            # GPU 自动检测
│   ├── parser.py         # bench 输出解析（mean + P99）
│   ├── summary.py        # CSV 与 xlsx 汇总生成
│   ├── benches/          # vllm/sglang 命令构建与执行
│   └── server/           # FastAPI + WebSocket + 测试编排
├── web/                  # Vue 3 + Ant Design Vue 前端源码
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
