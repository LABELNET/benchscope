# benchscope 项目总览 / Project Overview

> **文档状态**：基于现有功能重新生成的项目功能说明（替代原 PROJECTS-README.md）  
> **关联**：[Roadmap.md](./Roadmap.md)（版本路线）· [README.md](../README.md)（根 README）· [docs/README.md](./README.md)（文档目录）

---

## 1. 产品定位 / Positioning

benchscope 是一款面向大语言模型（LLM）推理服务的**性能测试工具**，为 vLLM、SGLang 及任意 OpenAI 兼容推理服务提供**单进程、pip 可直接安装**的 Web 性能测试能力。执行 bench 无需在推理服务端安装任何插件。

## 2. 功能总览 / Features

### 2.1 Dashboard（仪表盘）

- **Overview**（2×3 六宫格）：Total Perf Records、Total Acc Records、Max Perf Records (RUN ID)、Max Acc Records (RUN ID)（后两者逻辑待实现，显示 `—`）、Running Tasks、测试环境状态（在线/离线 + 模型数）
- **Envs info**（2×2 四宫格）：硬件环境（主机/CPU/内存/GPU）、操作系统（OS/版本/内核）、网络环境（网口-IP，docker 虚拟网卡过滤）、框架版本（Python/Pytorch/vLLM/SGLang/benchscope）；缺失项显示 `—`
- **Perf Records / Eval Records**：最多 8 条最新记录、不分页、纯文本表格（状态/操作列着色）；刷新 / 更多（更多待实现）

### 2.2 Performance（性能测试）

- **双模式任务**：`concurrency`（多档并发压测）/ `threshold`（阈值探测，二分寻找满足 TPOT/Output 阈值的最大并发）
- **创建任务三步表单**（`/performance/create`）：条件组（多组条件带唯一 `case_id`，相同条件不叠加）/ 参数 YAML / 命令预览
- **任务执行页三行布局**：Perf（进度按 case 计数 1/1、2/2、N/N）/ Cases（阈值条件只读 + 每组独立请求状态）/ Console（终端 + 日志下载）
- **Realtime 分组表格**：按 case 分组（`label#g{case_id}`）、组内并发升序、Best/BestPerf 唯一高亮、本地阈值控件、列设置、Excel 导出
- **Statistics**：4×3 共 12 张统计图（吞吐 / TTFT / TPOT / ITL 各 Mean/Median/P99），多组独立成线

### 2.3 Accuracy（精度测试）

- 占位页（v5.0 预留）：规划提示 + 3 张功能预览卡（数据集精度评估 / ModelScope 模型对比 / 多维度质量分析）

### 2.4 Sessions（会话）

- SSE 流式对话（OpenAI 兼容端点）：思考（reasoning_content / `<think>` 标签解析）与正文分离、Markdown 渲染
- 会话持久化（`data_dir/sessions`）、实时推理性能栏（TTFT/TPOT/ITL）、模型/质量/思考开关偏好记忆

### 2.5 Settings（设置）

- **General**：Language（中英）+ Cache Paths（logs_dir / datasets_dir / data_dir 服务端持久化目录）
- **Envs**：环境配置（Framework / Base URL 默认 `http://127.0.0.1:8000` / API Key 可选）+ 状态徽标 + Edit/Save + Test Connection
- **Models**：内置模型下载宫格（DeepSeek/Qwen/Llama/GLM/InternLM 等 6 款）+ 详情抽屉（精度/访问链接/下载命令）+ 部署按钮（待实现）
- **Plugins**：占位

### 2.6 基础能力

- 双框架命令构建与子进程执行（`vllm bench serve` / `sglang.bench_serving`）、FAKE 模式（无真实环境可联调）
- 三数据集（random / ShareGPT 自动下载 / custom 上传）
- bench 输出解析（mean + P99 双套指标）、CSV / xlsx 汇总、日志预览与下载
- i18n（中英）+ 亮 / 暗 / 跟随系统主题
- mock 调试环境（`mocks/`：仿真 bench 输出 + OpenAI 兼容服务含 SSE）

## 3. 技术栈 / Tech Stack

Python 3.9+ · FastAPI + uvicorn · Vue 3 + Vite 5 · Ant Design Vue 4 · Pinia · Vue Router 4 · ECharts 5 · axios · openpyxl

## 4. 项目结构 / Project Structure

```
benchscope/
├── benchscope/          # Python 后端：CLI、任务执行、bench 编排、FastAPI + WebSocket
│   ├── benches/         #   vllm/sglang 命令构建与执行（FAKE 模式）
│   ├── server/          #   api_config / api_tasks / api_sessions / api_dashboard / api_logs / ws
│   └── env_info.py      #   系统环境信息采集
├── web/                 # Vue 3 + Ant Design Vue 前端（构建产物 → benchscope/webui/）
├── mocks/               # mock 推理服务与 FAKE bench 输出
├── scripts/             # dev.sh / maca.sh / release 脚本
├── tests/               # mock OpenAI server & UI smoke tests
├── asserts/             # 截图与示例产物
└── docs/                # 文档体系（README 目录 · Roadmap · Projects · prds/ · versions/ · rules/）
```

## 5. 开发与验证 / Development & Validation

```bash
# 开发模式（FAKE，无需真实推理环境）
./scripts/dev.sh start      # mock OpenAI :8001 + 统一入口 :8080（自动重建前端，FAKE bench）
./scripts/dev.sh stop       # 停止全部

# 前端热更新
cd web && npm run dev       # http://127.0.0.1:5173（proxy /api、/ws 到 :8080）

# 验证模式（真实推理）：不设置 BENCHSCOPE_FAKE_BENCH
python -m benchscope.cli --port 8081 --no-browser
```

- mock 联调：Settings → Envs 的 Base URL 填 `http://127.0.0.1:8001`。
- 文档同步：设计/界面修改、逻辑与策略及 UI 调整需同步更新对应文档（见 [README.md](./README.md) 维护约定）。

## 6. 版本路线 / Roadmap

v1.0.0 纯文本性能测试 → v1.0.5 v2.0 UI 大改 + 双模式（当前）→ v2.0 多模态 → v3.0 全模态 → v4.0 世界模型 → v5.0 精度测试 → v6.0 ModelScope 对比 → v7.0 内置 GPU 适配模型下载。详见 [Roadmap.md](./Roadmap.md)。
