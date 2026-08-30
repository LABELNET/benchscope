# 软件方案 / 选型 / 依赖 — Software

> **文档状态**：benchscope 技术方案、技术选型与依赖说明  
> **关联**：[Architecture.md](./Architecture.md)（系统架构）

---

## 1. 总体方案

- **形态**：单进程、pip 可安装的 Web 性能测试工具（类 tensorflow-dashboard）。
- **执行方式**：
  - 原生引擎（vLLM / SGLang）：bench 工具（`vllm bench serve` / `sglang.bench_serving`）以**子进程**方式在本机执行，需本地安装 `torch` + 对应框架；
  - **自研引擎（benchscope，1.0.7）**：进程内异步压测（aiohttp + SSE），**不依赖本地框架环境**，pip 安装后即可远程测试任意 OpenAI 兼容服务；
  - 推理服务只需暴露 OpenAI 兼容 API，**无需安装服务端插件**。
- **联调**：无真实 vLLM/SGLang 环境时，`mocks/` 提供仿真 bench 输出 + mock OpenAI 兼容服务（含 SSE 流式）。

## 2. 技术栈

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 后端 | Python 3.9+（开发 3.12） | `benchscope` 包 |
| Web 框架 | FastAPI + uvicorn | REST + WebSocket 广播 |
| 前端 | Vue 3 + Vite 5 | 组合式 API（`<script setup>`） |
| UI 组件 | Ant Design Vue 4 | 组件库 |
| 状态管理 | Pinia | `store/config.js` / `store/test.js` |
| 路由 | Vue Router 4 | 6 栏主导航（TopBar 详见 [prds/TopBar.md](../prds/TopBar.md)） |
| 图表 | ECharts 5 | 12 图网格 + 联动 tooltip |
| 数据请求 | axios | 拦截器统一取 `data` / 错误 `detail` |
| 异步压测（自研引擎） | aiohttp（1.0.7） | SSE 流式采集 TTFT/ITL，高并发负载生成 |
| 构建 | Vite build → `benchscope/webui/` | 后端静态托管 |

## 3. 依赖清单

### Python（`pyproject.toml`）

`fastapi>=0.110` · `uvicorn[standard]>=0.29` · `requests>=2.31` · `openpyxl>=3.1`（Excel 导出）· `pydantic>=2` · `python-multipart>=0.0.9`（数据集上传、**1.0.7 新增：引擎包上传 `/api/benchs/upload`**）· `pyyaml>=6.0`（1.0.6：内置数据集 / 模型厂商目录 yaml 定义解析）· `aiohttp>=3.9`（**1.0.7：自研 bench 引擎异步 SSE 压测**）

可选：`modelscope>=1.15`（`pip install benchscope[modelscope]`，1.0.6：数据集 modelscope 源下载）；**1.0.8 新增 extras**：`accuracy-native`（`torch>=2.0` + `transformers>=4.40` + `peft>=0.10`，`pip install 'benchscope[accuracy-native]'`，Native 原生精度评测 / LoRA 增量模型加载，**不随 pip 必装**）

### 前端（`web/package.json`）

`vue ^3.5` · `vue-router ^4.5` · `pinia ^2.3` · `ant-design-vue ^4.2.6` · `@ant-design/icons-vue ^7` · `echarts ^5.6` · `axios ^1.7` · `dayjs ^1.11`；dev：`vite ^5.4` · `@vitejs/plugin-vue ^5.2`

## 4. 关键方案决策

| 决策点 | 方案 | 理由 |
| --- | --- | --- |
| 前端托管 | 后端托管构建产物（统一入口 8080） | 单进程部署，`pip install` 即用 |
| 双模式任务 | `mode` 字段 + 阈值快照 + 二分探测 | 阈值模式自动寻找满足条件最大并发 |
| 多组条件 | `length_pairs` 第 4 元素 `case_id` | 相同条件多组可区分（不叠加） |
| 进度计数 | 阈值模式按 case 数 | 并发点动态探测，不能作分母 |
| 状态推送 | WebSocket 广播（status/task_log/task_result） | 实时刷新，刷新页面可恢复 |
| bench 输出解析 | 正则双套（mean + P99），vLLM/SGLang 兼容 | 统一指标键（output/ttft/itl/tpot…） |
| 思考标签 | 通用标签对解析（ASCII + 全角） | 兼容多推理模型输出 |
| 环境信息 | `importlib.metadata` + 系统探测，缺失显示 `—` | 不强依赖 nvidia-smi 等 |
| **测试引擎（1.0.7）** | yaml 驱动注册表（`configs/benchs.yaml`）：`benchscope`（自研）/ `vllm-<ver>` / `sglang-<ver>` | 引擎与版本解耦，用户可扩展；原生引擎需环境校验 |
| **自研引擎口径（1.0.7）** | 严格对齐 vLLM bench（TPOT=(E2E-TTFT)/(tokens-1)、throughput=tokens/duration） | 自研与原生引擎结果可直接对比 |
| **输出 token 计数（1.0.7）** | 服务端 `usage.completion_tokens`（`stream_options.include_usage`），缺失回退 chunk 数 | 精确且不引入分词依赖 |
| **精度模块解耦（1.0.8）** | 独立包 `benchscope/accuracy/` + 独立 `EvalTaskManager` + 文件落库三件套（`evals/<task_id>/`）；引擎/数据集注册复用公共 yaml（`benchs.yaml` eval 能力字段 / `datasets.yaml` eval 元数据） | 与性能模块彻底解耦；保持 pip 即用与无数据库定位 |
| **精度引擎（1.0.8）** | serving（aiohttp OpenAI 兼容）/ native（transformers 本地权重，可选依赖 + CUDA 校验）/ mock（可控正确率伪输出） | 双模式独立运行；mock 环境无 GPU 全链路可测 |
| **判分器（1.0.8）** | 注册表按数据集绑定：choice（选项抽取）/ math（\boxed + 规范化等价）/ code（受限子进程沙箱 pass@1）/ judge（LLM-as-judge JSON 评分） | 各专项数据集口径对齐行业标准（accuracy / exact_match / pass@1 / mt_bench_score） |
| **LoRA 增量模型（1.0.8）** | 任务配置 `lora_path`（可选 `lora_name`）：Native peft 合并加载；Serving 请求服务端已注册 adapter（vLLM 需 `--enable-lora --lora-modules`） | 微调前后精度与性能均可量化对比 |

## 5. 数据流约定

- 前端 `api/index.js` 统一封装 HTTP；`wsUrl()` 提供 `/ws`。
- 任务结果行统一结构：`{case, label, case_id, input_len, output_len, concurrency, cmd, metrics|error}`。
- 指标键：`output_mean/peakoutput_mean/total_mean/ttft_mean|median|p99/tpot_mean|median|p99/itl_mean|median|p99/req_per_s/single_user`。
- 环境信息结构：`{hardware:{host,cpu,memory,gpu}, os:{name,version,kernel}, network:[{iface,ip}], versions:{python,pytorch,vllm,sglang,benchscope}}`。

## 6. 维护约定

- **依赖变更必须同步**：任何 Python 依赖（`pyproject.toml`）或前端依赖（`web/package.json`）的**新增 / 升级 / 移除**，必须同步更新本文档 §2 技术栈与 §3 依赖清单，并在 `docs/versions/VERSION_x_y_z.md` 迭代记录中说明；架构级变更同步 [Architecture.md](./Architecture.md)。
