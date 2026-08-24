# benchscope 产品需求文档 (PRD)

> **版本**：v1.0.4  
> **最后更新**：2026-08-24  
> **文档状态**：基于现有代码整理  

---

## 1. 产品概述

### 1.1 产品定位

benchscope 是一款面向大语言模型（LLM）推理服务的**性能测试工具**，为 vLLM、SGLang 及任意 OpenAI 兼容推理服务提供单进程、pip 可直接安装的 Web 性能测试能力。

### 1.2 目标用户

- LLM 推理服务开发者与运维人员
- 模型性能评估与选型人员
- AI 基础设施团队

### 1.3 核心价值

| 价值点 | 说明 |
| --- | --- |
| **零侵入** | bench 工具在客户端本地以子进程运行，推理服务端只需提供 OpenAI 兼容 API，无需安装任何插件 |
| **实时反馈** | 每个并发结果实时流入表格与曲线，无需等待全部测试完成 |
| **一键启动** | `pip install` + 一条命令同时启动后端与内置前端，单进程设计 |
| **双框架** | 同时支持 vLLM（`vllm bench serve`）与 SGLang（`sglang.bench_serving`）|

### 1.4 产品形态

- **安装方式**：`pip install benchscope`
- **启动命令**：`benchscope`（默认 `http://127.0.0.1:8080`，自动打开浏览器）
- **可选参数**：`--host`、`--port`、`--no-browser`、`--debug`
- **开源协议**：Apache License 2.0
- **发布平台**：PyPI

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    浏览器（前端）                      │
│           Vue 3 + Ant Design Vue + ECharts           │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP REST / WebSocket
┌──────────────────────┴──────────────────────────────┐
│                  benchscope 后端                      │
│                 FastAPI + Uvicorn                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ API 路由  │ │WebSocket │ │ 状态监控  │ │测试管理 │ │
│  │(config/  │ │  Hub     │ │ Monitor  │ │ Manager│ │
│  │ test/    │ │          │ │          │ │        │ │
│  │ logs)    │ │          │ │          │ │        │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ 配置管理  │ │ 数据集   │ │ 输出解析  │            │
│  │ Config   │ │ 管理     │ │ Parser   │            │
│  └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────┬──────────────────────────────┘
                       │ 子进程调用
         ┌─────────────┴─────────────┐
         │                           │
   ┌─────┴─────┐             ┌──────┴──────┐
   │ vLLM CLI  │             │ SGLang CLI  │
   │ bench serve│            │ bench_serving│
   └───────────┘             └─────────────┘
         │                           │
         └─────────┬─────────────────┘
                   │ OpenAI Compatible API
         ┌─────────┴─────────┐
         │   推理服务（远程）   │
         │  vLLM / SGLang /   │
         │  其他兼容服务       │
         └───────────────────┘
```

### 2.2 技术栈

| 层级 | 技术选型 |
| --- | --- |
| **前端** | Vue 3（`<script setup>`）、Ant Design Vue、ECharts、Pinia、Vue Router、Vite、Axios |
| **后端** | Python 3.9+、FastAPI、Uvicorn、Pydantic、openpyxl |
| **通信** | HTTP REST API + WebSocket（实时推送测试结果与状态） |
| **构建** | setuptools + wheel（后端）、Vite（前端） |
| **推理框架** | vLLM（`vllm bench serve`）、SGLang（`python -m sglang.bench_serving`） |

### 2.3 单进程设计

benchscope 采用单进程设计，`pip install` 后一条命令即可启动：

- 后端 FastAPI 服务同时托管前端构建产物（`benchscope/webui/`）
- 前端构建后的静态资源作为包数据打包在 Python 包内
- 开发时支持前后端分离：后端 `python -m benchscope.cli`，前端 `npm run dev`（Vite 代理 `/api` 和 `/ws`）

---

## 3. 功能需求

### 3.1 功能模块总览

| 模块 | 路由 | 说明 |
| --- | --- | --- |
| vLLM 测试页 | `/vllm` | vLLM 框架性能测试（环境→配置→进度→结果） |
| SGLang 测试页 | `/sglang` | SGLang 框架性能测试（与 vLLM 共用 TestView 组件） |
| 日志管理页 | `/logs` | 历史测试记录浏览、日志预览/下载、数据分析 |
| 设置页 | `/settings` | 推理服务 API 配置、GPU 配置、阈值/目录等全局设置 |

---

### 3.2 服务设置（Settings）

#### 3.2.1 推理服务 API 配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| 默认框架 | vLLM / SGLang | vLLM |
| Base URL | OpenAI 兼容 API 地址 | `http://192.168.1.67:8000` |
| Endpoint | 推理接口路径 | `/v1/chat/completions` |
| API Key | 可选的 Bearer Token | 空 |
| 额外请求头 | JSON 格式的自定义请求头 | `{}` |

**功能要求**：
- 提供「测试连接」按钮，调用 `/v1/models` 验证连通性并返回模型列表
- 配置持久化到 `~/.benchscope/config.json`

#### 3.2.2 GPU 配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| 自动检测 | 通过 `nvidia-smi` 自动获取 GPU 型号与数量 | 开启 |
| GPU 型号（回退） | 自动检测失败时手动填写 | 空 |
| GPU 数量 | 部署使用的 GPU 卡数 | 8 |

#### 3.2.3 其他配置

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| TPOT 阈值 (ms) | 用于高亮最佳并发行 | 100 |
| 日志目录 | 测试日志保存路径 | `./logs` |
| 数据集缓存目录 | ShareGPT 等数据集缓存路径 | `./datasets` |
| 请求速率 | `inf`（不限速）或自定义数值 | `inf` |
| vLLM bench 命令模板 | 可自定义 bench 执行命令 | `vllm bench serve` |
| SGLang bench 命令模板 | 可自定义 bench 执行命令 | `python -m sglang.bench_serving` |

---

### 3.3 测试页面（vLLM / SGLang）

测试页面采用管理台风格布局：左侧固定导航（测试流程）+ 右侧内容区（内部滚动），内容区顶部固定副导航（数据集类型切换）。

#### 3.3.1 测试环境面板

- 显示推理服务在线/离线状态（实时指示灯）
- 展示当前可用的模型列表（通过 `/v1/models` 获取）
- 多模型时提供下拉选择
- GPU 信息展示（自动检测或手动配置）

#### 3.3.2 测试配置面板

**数据集配置**（副导航切换三种类型）：

| 数据集类型 | 配置方式 |
| --- | --- |
| **Random** | 支持多组输入/输出长度组合，默认 `3K/1K`、`1K/1K`、`256/256`；可勾选/取消/自定义 |
| **ShareGPT** | 自动从 ModelScope 下载（`gliang1001/ShareGPT_V3_unfiltered_cleaned_split`），无需指定输入/输出长度 |
| **Custom** | 上传 JSONL 文件或指定服务器本地路径，功能与 ShareGPT 一致 |

**并发数配置**：
- 默认并发列表：`1, 4, 8, 16, 32, 40, 64, 128`
- 支持编辑、添加、删除并发数
- `--max-concurrency` 与 `--num-prompts` 保持一致
- 支持 `inf` 请求速率选项

**框架参数表单**：
- 根据所选框架（vLLM / SGLang）动态渲染可配置参数表单
- 参数分为基础参数和高级参数（折叠区）
- 支持自由参数编辑器（flag + value 形式添加任意额外参数）
- 提供命令预览功能（预览将要执行的完整命令）

**vLLM 可配置参数**：

| 参数 | CLI Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| Backend | `--backend` | select | `openai-chat` | openai-chat / openai |
| Endpoint | `--endpoint` | str | `/v1/chat/completions` | 接口路径 |
| trust-remote-code | `--trust-remote-code` | bool | true | 信任远程代码 |
| ignore-eos | `--ignore-eos` | bool | true | 忽略 EOS |
| Burstiness | `--burstiness` | float | 1.0 | 突发因子 |
| Seed | `--seed` | int | 0 | 随机种子 |
| Warmups | `--num-warmups` | int | 0 | 预热请求数 |
| Percentiles | `--metric-percentiles` | str | `99` | 百分位 |
| Temperature | `--temperature` | float | 0.0 | 采样温度 |
| top-p | `--top-p` | float | 1.0 | Top-p 采样 |
| top-k | `--top-k` | int | -1 | Top-k 采样 |
| min-p | `--min-p` | float | 0.0 | Min-p 采样 |
| frequency-penalty | `--frequency-penalty` | float | 0.0 | 频率惩罚 |
| presence-penalty | `--presence-penalty` | float | 0.0 | 存在惩罚 |
| ShareGPT 输出长度 | `--sharegpt-output-len` | int | 128 | 高级参数 |
| no-stream | `--no-stream` | bool | false | 高级参数 |
| disable-tqdm | `--disable-tqdm` | bool | false | 高级参数 |
| save-result | `--save-result` | bool | false | 高级参数 |
| profile | `--profile` | bool | false | 高级参数 |

**SGLang 可配置参数**：

| 参数 | CLI Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| Backend | `--backend` | select | `openai` | openai / sglang |
| 应用聊天模板 | `--apply-chat-template` | bool | true | ShareGPT/自定义数据集时启用 |
| 不忽略 EOS | `--disable-ignore-eos` | bool | false | 开启后不忽略 EOS |
| Seed | `--seed` | int | 0 | 随机种子 |
| 预热请求数 | `--warmup-requests` | int | 0 | 预热请求数 |
| 预分词 | `--tokenize-prompt` | bool | true | 预分词 |
| 刷新缓存 | `--flush-cache` | bool | false | 高级参数 |
| 打印请求 | `--print-requests` | bool | false | 高级参数 |
| disable-tqdm | `--disable-tqdm` | bool | false | 高级参数 |
| ShareGPT 输出长度 | `--sharegpt-output-len` | int | 128 | 高级参数 |
| ShareGPT 上下文长度 | `--sharegpt-context-len` | int | - | 高级参数 |

#### 3.3.3 测试进度面板

- 「开始测试」按钮启动测试
- 「停止测试」按钮终止正在执行的测试（发送 kill 信号到子进程）
- 测试执行期间显示当前状态（运行中/已完成/已停止/错误）

**测试执行流程**：
1. 根据数据集配置生成用例列表（Random 按长度组合拆分，ShareGPT/Custom 为单用例）
2. 遍历每个用例 × 每个并发数，依次执行 bench 命令
3. bench 命令以子进程方式运行，实时流式读取输出
4. 解析每个并发度的输出，提取性能指标
5. 每完成一个并发度，实时推送到前端并增量写入汇总 CSV
6. 全部完成后生成 xlsx 汇总报告

#### 3.3.4 实时结果面板

**双语表格**（中英双语标题），展示以下指标：

| 指标 | 英文 | 单位 | 说明 |
| --- | --- | --- | --- |
| 用例 | Case/Label | - | 数据集条件标签（如 3K1K、ShareGPT） |
| 并发数 | Concurrency | - | 当前并发度 |
| Output 吞吐 | Output Throughput | tok/s | 输出 token 吞吐量 |
| Peak Output 吞吐 | Peak Output Throughput | tok/s | 峰值输出 token 吞吐量 |
| Total 吞吐 | Total Throughput | tok/s | 总 token 吞吐量（输入+输出） |
| TTFT Mean | Mean TTFT | ms | 首 token 平均延迟 |
| TTFT P99 | P99 TTFT | ms | 首 token P99 延迟 |
| TPOT Mean | Mean TPOT | ms | 每 token 平均耗时 |
| TPOT P99 | P99 TPOT | ms | 每 token P99 耗时 |
| ITL Mean | Mean ITL | ms | token 间平均延迟 |
| ITL P99 | P99 ITL | ms | token 间 P99 延迟 |
| 单用户 QPS | Single-user QPS | req/s | `1000 / tpot_mean` 自动计算 |

**六条实时曲线**（ECharts），横轴为并发数，纵轴为对应指标值：
1. Output 吞吐量
2. Total 吞吐量
3. TTFT Mean
4. TPOT Mean
5. TTFT P99
6. TPOT P99

**最佳并发高亮**：
- 根据 TPOT 阈值（默认 100ms），找到最接近且低于阈值的并发行
- 该行在表格中以高亮颜色标记
- 若无低于阈值的记录，则取 TPOT 最小的行

---

### 3.4 日志管理

#### 3.4.1 日志目录结构

每次测试运行生成一个以 `MMDD-HHMMSS` 命名的目录：

```
logs/
└── 0824-103412/                     # 一次运行目录
    ├── Qwen3.5-4B_256X256_X8.log    # 用例级详细 bench 日志
    ├── Qwen3.5-4B_X8.log            # Mean 汇总 CSV
    ├── Qwen3.5-4B_X8_p99.log        # P99 汇总 CSV
    ├── benchmark-240826.xlsx         # Excel 汇总报告（均值 + P99 双 sheet）
    └── run.json                      # 运行元数据（含完整结果行）
```

#### 3.4.2 日志管理页

- **左侧**：运行记录列表（按时间倒序），显示运行 ID、框架、模型、状态、时间
- **右侧**：选中运行的详情面板
  - 文件列表（支持预览与下载）
  - 测试日志表格（合并 mean / P99 指标）
  - 分析曲线（Output / PeakOutput / Total / TTFT / ITL / TPOT）

#### 3.4.3 Excel 汇总报告

生成 `benchmark-*.xlsx`，包含两个 sheet：

**Sheet 1：均值 Mean**

| 列 | 说明 |
| --- | --- |
| GPU | GPU 型号×数量 |
| 模型 | 模型名称 |
| 精度 | 模型精度（可选） |
| 推理框架 | vLLM 或 SGLang |
| 输入长度 | 输入 token 数 |
| 输出长度 | 输出 token 数 |
| 并发数 | 并发度 |
| Output | Output token 吞吐（mean） |
| Peak Output | Peak Output token 吞吐（mean） |
| Total | Total token 吞吐（mean） |
| TTFT | Mean TTFT |
| ITL | Mean ITL |
| TPOT | Mean TPOT |
| 单用户 | `1000 / tpot_mean` |

**Sheet 2：P99**

与均值 sheet 结构相同，但取 P99 指标。最佳行（TPOT 最接近且低于阈值）以黄色高亮。

---

### 3.5 状态监控

#### 3.5.1 状态指示

顶部导航栏右侧显示两个状态指示灯：

| 状态 | 含义 | 检测方式 |
| --- | --- | --- |
| **服务**（Service） | benchscope 应用自身状态 | 始终在线（应用启动即就绪） |
| **环境**（Environment） | 推理服务连接状态 | 每 5 秒探测 `/v1/models` |

#### 3.5.2 状态推送

- 后端 `StatusMonitor` 每 5 秒轮询推理服务 `/v1/models`
- 状态变化时通过 WebSocket 广播到所有已连接的前端客户端
- WebSocket 连接建立时立即推送一次当前状态
- 同时返回可用模型列表

---

### 3.6 数据集管理

#### 3.6.1 Random 数据集

- 无需下载，由 bench 工具根据指定的输入/输出长度自动生成
- 支持多组长度组合，默认三组：
  - `3072 / 1024`（3K1K）
  - `1024 / 1024`（1K1K）
  - `256 / 256`（256X256）
- 用户可自定义添加新的长度组合

#### 3.6.2 ShareGPT 数据集

- 自动从 ModelScope 下载（数据集 ID：`gliang1001/ShareGPT_V3_unfiltered_cleaned_split`）
- 下载方式优先级：modelscope SDK → HTTP API
- 下载后自动将 JSON 数组格式转换为 JSONL（流式转换，低内存占用）
- 缓存到 `datasets/sharegpt/` 目录，避免重复下载
- 支持手动触发重新下载

#### 3.6.3 Custom 数据集

- 支持通过 Web 界面上传 JSONL 文件
- 支持指定服务器本地文件路径
- 上传文件存储在 `datasets/uploads/` 目录
- 功能与 ShareGPT 一致（无需指定输入/输出长度）
- 提供已上传数据集的列表、删除管理

---

## 4. API 设计

### 4.1 配置 API（`/api/config`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/config` | 获取当前完整配置 |
| POST | `/api/config` | 更新配置（增量合并） |
| GET | `/api/config/status` | 获取服务/推理环境状态 |
| GET | `/api/config/models` | 获取推理服务模型列表 |
| POST | `/api/config/test-connection` | 测试推理服务连接 |
| GET | `/api/config/gpu` | 获取 GPU 信息（自动检测 + 配置） |
| GET | `/api/config/params/{framework}` | 获取框架可配置参数定义 |

### 4.2 测试 API（`/api/test`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/test/start` | 启动测试 |
| POST | `/api/test/stop` | 停止测试 |
| GET | `/api/test/status` | 获取当前测试状态 |
| POST | `/api/test/preview` | 预览将要执行的命令（不运行） |

### 4.3 日志 API（`/api/logs`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/logs/runs` | 获取运行记录列表 |
| GET | `/api/logs/runs/{run_id}` | 获取单次运行详情 |
| GET | `/api/logs/runs/{run_id}/preview` | 预览日志文件内容 |
| GET | `/api/logs/runs/{run_id}/download` | 下载日志文件 |
| GET | `/api/logs/runs/{run_id}/summary` | 获取 mean/P99 分析数据 |
| GET | `/api/logs/datasets` | 获取已上传自定义数据集列表 |
| POST | `/api/logs/datasets/upload` | 上传自定义数据集 |
| DELETE | `/api/logs/datasets/{name}` | 删除自定义数据集 |
| GET | `/api/logs/datasets/sharegpt` | 获取 ShareGPT 下载状态 |
| POST | `/api/logs/datasets/sharegpt/download` | 触发 ShareGPT 下载 |

### 4.4 WebSocket（`/ws`）

客户端连接后，服务端推送以下消息类型：

| 消息类型 | 说明 | 数据结构 |
| --- | --- | --- |
| `status` | 状态变更推送 | `{ type, status: { web, inference, models, error } }` |
| `run_started` | 测试开始 | `{ type, run: TestRun }` |
| `run_snapshot` | 测试快照（连接时/恢复时） | `{ type, run: TestRun }` |
| `result` | 单个并发结果 | `{ type, run_id, row }` |
| `log_line` | 实时日志行 | `{ type, run_id, case, concurrency, line }` |
| `run_done` | 测试完成 | `{ type, run_id, run: TestRun }` |
| `run_error` | 测试出错 | `{ type, run_id, error, run: TestRun }` |

---

## 5. 数据模型

### 5.1 配置结构（config.json）

```json
{
  "framework": "vllm",
  "api": {
    "base_url": "http://192.168.1.67:8000",
    "endpoint": "/v1/chat/completions",
    "api_key": "",
    "extra_headers": {}
  },
  "gpu": {
    "auto": true,
    "name": "",
    "count": 8
  },
  "logs_dir": "./logs",
  "datasets_dir": "./datasets",
  "tpot_threshold_ms": 100,
  "request_rate": "inf",
  "bench_commands": {
    "vllm": "vllm bench serve",
    "sglang": "python -m sglang.bench_serving"
  }
}
```

### 5.2 性能指标（解析自 bench 输出）

| 指标键 | 说明 |
| --- | --- |
| `output_mean` | Output token 吞吐（mean） |
| `output_p99` | Output token 吞吐（P99，当前取 mean） |
| `peakoutput_mean` | Peak Output token 吞吐 |
| `total_mean` | Total token 吞吐（mean） |
| `ttft_mean` | Mean TTFT (ms) |
| `ttft_p99` | P99 TTFT (ms) |
| `tpot_mean` | Mean TPOT (ms) |
| `tpot_p99` | P99 TPOT (ms) |
| `itl_mean` | Mean ITL (ms) |
| `itl_p99` | P99 ITL (ms) |
| `req_per_s` | 请求吞吐 (req/s) |
| `single_user` | 单用户 QPS = 1000 / tpot_mean |
| `concurrency` | 实际并发数 |
| `raw` | 完整原始 bench 输出 |

### 5.3 测试运行（TestRun）

```python
@dataclass
class TestRun:
    run_id: str           # 运行 ID（MMDD-HHMMSS）
    run_dir: Path         # 运行目录
    framework: str        # vllm / sglang
    model: str            # 模型名称
    gpu: dict             # GPU 信息
    cases: list           # 用例列表
    rows: list            # 结果行
    status: str           # running / done / stopped / error
    error: str            # 错误信息
    summary: dict         # xlsx 汇总信息
    started_at: str       # 开始时间
    finished_at: str      # 结束时间
    precision: str        # 模型精度
```

---

## 6. 前端页面结构

### 6.1 全局布局

```
┌──────────────────────────────────────────────────────────┐
│  TopBar：品牌 + 导航（vLLM / SGLang / 日志管理） + 状态 + 设置 │
├──────────┬───────────────────────────────────────────────┤
│ 左侧导航  │               内容区                          │
│（固定）    │  ┌─────────────────────────────────────────┐ │
│           │  │  副导航（数据集 Tab：Random/ShareGPT/Custom）│ │
│ 测试流程   │  ├─────────────────────────────────────────┤ │
│ · 测试环境  │  │                                         │ │
│ · 测试配置  │  │  各面板内容（内部滚动）                    │ │
│ · 测试进度  │  │                                         │ │
│ · 测试结果  │  │                                         │ │
│           │  │                                         │ │
└──────────┴──┴─────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 6.2 页面组件

| 页面 | 核心组件 | 说明 |
| --- | --- | --- |
| **TestView** | EnvPanel | 测试环境：推理服务状态、模型选择、GPU 信息 |
| | TestConfigPanel | 测试配置：数据集、并发数、框架参数、命令预览 |
| | TestProgressPanel | 测试进度：开始/停止按钮、状态显示 |
| | RealtimeResultPanel | 实时结果：双语表格 + MetricsCharts 曲线 |
| | SubTabBar | 数据集类型切换（Random / ShareGPT / Custom） |
| | ConcurrencyEditor | 并发数列表编辑 |
| | FreeArgsEditor | 自由参数编辑器 |
| **LogView** | RunRecordList | 运行记录列表 |
| | RunDetailPanel | 运行详情：文件列表、日志预览、分析曲线 |
| | MetricsTable | 指标表格 |
| | MetricsCharts | 指标曲线图 |
| | AnalysisBlock | 分析面板（mean / P99） |
| **SettingsView** | 完整表单 | API 配置、GPU、阈值、目录、命令模板 |
| **通用** | TopBar | 顶部导航栏 |
| | StatusBadge | 状态指示灯组件 |

---

## 7. 非功能需求

### 7.1 性能要求

- 状态监控轮询间隔：5 秒
- WebSocket 消息实时推送，延迟 < 100ms
- 前端日志行缓存上限：8000 行
- ShareGPT 数据集转换采用流式处理，支持大文件低内存转换

### 7.2 兼容性

- Python 版本：>= 3.9
- 浏览器：现代浏览器（Chrome、Firefox、Edge、Safari）
- 操作系统：Linux（主要目标）、macOS、Windows
- 推理服务：任意 OpenAI 兼容 API

### 7.3 容错与降级

- 配置损坏时自动回退到默认配置
- GPU 自动检测失败时提供手动配置回退
- 推理服务不可达时状态显示离线，不影响前端操作
- bench 命令执行失败时记录错误并继续后续并发
- 测试被中断时保存已完成的结果
- 无 vLLM/SGLang 环境时可通过 `BENCHSCOPE_FAKE_BENCH=1` 启用仿真模式

### 7.4 安全性

- CORS 全开放（当前设计为本地/内网工具）
- API Key 存储在本地配置文件中
- 文件下载/预览接口做路径穿越校验

---

## 8. 版本规划

| 版本 | 状态 | 范围 |
| --- | --- | --- |
| **v1.0.0** | ✅ 已发布 | 纯文本性能测试：双框架、三数据集、实时结果、日志与 xlsx 汇总、分析、管理台 UI |
| **v1.0.1 ~ v1.0.4** | ✅ 已发布 | 补丁版本：README 双语化、打包元数据、源码链接更新 |
| **v2.0** | 🔜 规划中 | 多模态模型性能测试（图像/视频输入） |
| **v3.0** | 规划中 | 全模态模型性能测试（音频/视频等） |
| **v4.0** | 规划中 | 世界模型性能测试 |
| **v5.0** | 规划中 | 常见数据集精度测试 |
| **v6.0** | 规划中 | ModelScope 官方模型链接与对比结论 |

---

## 9. 术语表

| 术语 | 说明 |
| --- | --- |
| **vLLM** | 高性能 LLM 推理框架 |
| **SGLang** | LLM 推理框架（SGLang） |
| **OpenAI 兼容 API** | 遵循 OpenAI API 接口规范的推理服务接口 |
| **TTFT** | Time to First Token，首 token 延迟 |
| **TPOT** | Time per Output Token，每输出 token 耗时 |
| **ITL** | Inter-token Latency，token 间延迟 |
| **P99** | 第 99 百分位（衡量长尾延迟） |
| **Throughput** | 吞吐量（tok/s） |
| **ShareGPT** | 开源对话数据集 |
| **JSONL** | 每行一个 JSON 对象的文本格式 |
| **ModelScope** | 模型/数据集托管平台 |
| **bench** | 性能测试/基准测试 |
| **并发数** | 同时发起的请求数（`--max-concurrency`） |
| **请求速率** | 请求发送速率（`inf` 表示不限速） |

---

## 10. 附录

### 10.1 项目目录结构

```
benchscope/
├── benchscope/                   # Python 后端包
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # 命令行入口
│   ├── config.py                 # 配置持久化（~/.benchscope/config.json）
│   ├── constants.py              # 全局常量与默认值
│   ├── datasets.py               # ShareGPT 下载/转换、自定义数据集
│   ├── gpu.py                    # GPU 自动检测（nvidia-smi）
│   ├── parser.py                 # bench 输出解析（mean + P99）
│   ├── summary.py                # CSV 与 xlsx 汇总生成
│   ├── benches/                  # bench 命令构建与执行
│   │   ├── base.py               # 公共定义（ParamDef, BenchOptions）
│   │   ├── runner.py             # 子进程流式执行器
│   │   ├── vllm_bench.py         # vLLM 命令构建
│   │   └── sglang_bench.py       # SGLang 命令构建
│   ├── server/                   # FastAPI 服务
│   │   ├── app.py                # 应用装配（路由 + WebSocket + 静态托管）
│   │   ├── state.py              # 全局状态单例
│   │   ├── status.py             # 推理服务状态监控
│   │   ├── ws.py                 # WebSocket 广播 Hub
│   │   ├── api_config.py         # 配置/模型/GPU/状态 API
│   │   ├── api_test.py           # 测试启停与进度 API
│   │   ├── api_logs.py           # 日志管理 API
│   │   └── test_manager.py       # 测试执行管理器
│   └── webui/                    # 前端构建产物（打包分发）
├── web/                          # 前端源码
│   ├── src/
│   │   ├── api/index.js          # API 请求封装
│   │   ├── router/index.js       # 路由配置
│   │   ├── store/                # Pinia 状态管理
│   │   ├── components/           # Vue 组件
│   │   ├── views/                # 页面视图
│   │   ├── App.vue               # 根组件
│   │   └── main.js               # 入口
│   └── vite.config.js            # Vite 配置
├── tests/                        # 测试
├── datasets/                     # 数据集存储
├── logs/                         # 测试日志
├── docs/                         # 文档
├── pyproject.toml                # Python 包配置
└── scripts/                      # 构建/发布脚本
```

### 10.2 配置持久化路径

- 配置文件：`~/.benchscope/config.json`
- 日志目录：`./logs/`（可配置）
- 数据集目录：`./datasets/`（可配置）
  - ShareGPT 缓存：`datasets/sharegpt/`
  - 自定义上传：`datasets/uploads/`
