# benchscope

[English](README.md) | **简体中文**

> 面向 **vLLM / SGLang** 及任意 **OpenAI 兼容**推理服务的单进程、pip 可直接安装的 Web 性能测试工具。

## 快速开始

```bash
pip install benchscope
benchscope                      # 默认 http://127.0.0.1:8080，自动打开浏览器
benchscope --port 8080 --no-browser
```

1. **Settings → 推理 API** — 填写 **Base URL**（任意 OpenAI 兼容地址），点击「测试连接」。
2. **Performance → 新建测试任务** — 选择模型 + 框架、数据集、并发数（或阈值）、参数，预览命令；创建后自动进入任务详情页。
3. **任务详情页** — 左侧实时进度 + bench 终端，右侧实时表格与六条曲线。

> UI 语言（中/英）与主题（亮色/暗色/跟随系统）在 **Settings → 通用** 中切换。

## 功能特性

**压测能力**
- 双框架 — vLLM（`vllm bench serve`）与 SGLang（`sglang.bench_serving`）；兼容任意 OpenAI API，推理服务端无需安装插件。
- 数据集 — `random`（多组输入/输出长度）、`sharegpt`（自动从 ModelScope 下载）、`custom`（上传 jsonl 或指定本地路径）。
- 可配置压测 — 并发数列表可编辑、`inf` 限速选项、框架参数表单 + 自由参数编辑器、命令预览。
- 双执行模式 — **并发模式**（多档并发压测）与 **阈值模式**（TPOT / Output 吞吐阈值探测）。

**实时结果**
- 实时表格按 case 分组，组内按并发数升序；组内唯一 **Best / BestPerf** 阈值高亮（0 值阈值不参与，全 0 不标记）。
- 六条曲线 — Output / Total 吞吐，TTFT / TPOT mean & P99。
- 本地阈值试算 — 调整 TPOT（默认 100）/ Output（默认 0）即时重算高亮，不写回任务。
- 成功率整数展示。

**分析、日志与导出**
- 均值 / P99 双分析面板 + 最佳并发高亮。
- 每次运行 `logs/<月日-时分秒>/` 目录 + `benchmark-*.xlsx` 汇总（mean + P99 双 sheet，含单用户 `1000/tpot`）。
- 实时表格一键 **导出 Excel**（写入任务记录缓存目录）。

**任务与状态**
- 任务化执行 — 每任务独立线程运行，持久化到 `~/.benchscope/tasks/`，刷新页面不丢。
- 服务 / 环境在线离线状态监控。

**UI 与体验**
- 管理台 UI — 顶部 5 栏导航（Dashboard / Performance / Accuracy / Sessions / Settings）。
- Dashboard — 统计卡片（总测试次数 / 进行中任务 / 平均 TPOT / 最佳模型）+ 运行记录列表。
- Sessions — SSE 流式对话，持久化到 `~/.benchscope/sessions/`。
- i18n（中英双语）与亮色 / 暗色 / 跟随系统主题。

## 目录结构

```
benchscope/
├── benchscope/       # Python 后端 — CLI、任务执行、bench 编排、FastAPI + WebSocket
│   └── server/       #   api_config / api_tasks / api_sessions / api_dashboard / api_logs / ws
├── web/              # Vue 3 + Ant Design Vue 前端
├── mocks/            # 模拟推理服务与 FAKE bench 仿真输出
└── tests/            # mock OpenAI 服务与 UI 冒烟测试
```

## 开发调试

- **开发模式（FAKE 仿真，无需真实推理环境）** — `./scripts/dev.sh` 一键启动 mock OpenAI（:8001）+ FAKE bench 后端（:8080）+ Vite 前端（:5173）；或 `BENCHSCOPE_FAKE_BENCH=1 python -m benchscope.cli`。
- **验证模式（真实推理环境）** — 不带 FAKE 环境变量启动后端（如 `--port 8081`），Base URL 指向真实服务（如 vLLM :8000），用于并发 / 阈值双模式回归验证。
- **前端热更新** — `cd web && npm install && npm run dev`（http://127.0.0.1:5173，代理 `/api` 与 `/ws` 到 :8080）。

## 开源信息

- **许可证** — [Apache License 2.0](LICENSE) · **发布平台** — [PyPI: benchscope](https://pypi.org/project/benchscope/) · **源码仓库** — <https://github.com/LABELNET/benchscope>

版本规划与迭代记录：[VERSION_README.md](VERSION_README.md) · 产品需求：[PROJECTS-README.md](PROJECTS-README.md)
