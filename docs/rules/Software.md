# 软件方案 / 选型 / 依赖 — Software

> **文档状态**：benchscope 技术方案、技术选型与依赖说明  
> **关联**：[Architecture.md](./Architecture.md)（系统架构）

---

## 1. 总体方案

- **形态**：单进程、pip 可安装的 Web 性能测试工具（类 tensorflow-dashboard）。
- **执行方式**：bench 工具（`vllm bench serve` / `sglang.bench_serving`）以**子进程**方式在本机执行；推理服务只需暴露 OpenAI 兼容 API，**无需安装服务端插件**。
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
| 构建 | Vite build → `benchscope/webui/` | 后端静态托管 |

## 3. 依赖清单

### Python（`pyproject.toml`）

`fastapi>=0.110` · `uvicorn[standard]>=0.29` · `requests>=2.31` · `openpyxl>=3.1`（Excel 导出）· `pydantic>=2` · `python-multipart>=0.0.9`（数据集上传）· `pyyaml>=6.0`（1.0.6：内置数据集 / 模型厂商目录 yaml 定义解析）

可选：`modelscope>=1.15`（`pip install benchscope[modelscope]`，1.0.6：数据集 modelscope 源下载）

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

## 5. 数据流约定

- 前端 `api/index.js` 统一封装 HTTP；`wsUrl()` 提供 `/ws`。
- 任务结果行统一结构：`{case, label, case_id, input_len, output_len, concurrency, cmd, metrics|error}`。
- 指标键：`output_mean/peakoutput_mean/total_mean/ttft_mean|median|p99/tpot_mean|median|p99/itl_mean|median|p99/req_per_s/single_user`。
- 环境信息结构：`{hardware:{host,cpu,memory,gpu}, os:{name,version,kernel}, network:[{iface,ip}], versions:{python,pytorch,vllm,sglang,benchscope}}`。

## 6. 维护约定

- **依赖变更必须同步**：任何 Python 依赖（`pyproject.toml`）或前端依赖（`web/package.json`）的**新增 / 升级 / 移除**，必须同步更新本文档 §2 技术栈与 §3 依赖清单，并在 `docs/versions/VERSION_x_y_z.md` 迭代记录中说明；架构级变更同步 [Architecture.md](./Architecture.md)。
