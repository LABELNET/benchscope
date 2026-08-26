# benchscope Dashboard 页面 — 面板结构与数据说明

> **版本**：v1.0.5  
> **最后更新**：2026-08-26  
> **文档状态**：Dashboard 页面各面板的布局、内容、数据来源与交互规则说明  
> **关联文档**：[Performance.md](./Performance.md)（Performance 双模式核心逻辑）

---

## 0. 总览

Dashboard 页面自上而下共三块内容：

1. **第一行**：左 2 列「Overview 统计概览」+ 右 2 列「Envs info 环境信息」（等高卡片）
2. **Perf Records**：性能测试记录（最多 8 条，不分页）
3. **Eval Records**：精度/评估测试记录（v5.0 预留，当前为空）

页面加载时并行拉取：运行记录（`/api/logs/runs`）、统计（`/api/dashboard/stats`）、环境信息（`/api/dashboard/env`），并刷新推理服务状态（`config.refreshStatus()`）。

---

## 1. Overview 面板（左 2 列，2 列 × 3 行 6 宫格）

| 位置 | 内容 | 数据来源 | 显示规则 |
| --- | --- | --- | --- |
| 1 | Total Perf Records | `stats.total_runs` | 性能测试总次数 |
| 2 | Total Acc Records | `stats.total_acc_runs` | 精度测试总次数（v5.0 预留，当前恒为 0） |
| 3 | Max Perf Records (RUN ID) | — | 显示 `—`（逻辑未实现） |
| 4 | Max Acc Records (RUN ID) | — | 显示 `—`（逻辑未实现） |
| 5 | Running Tasks | `stats.running_tasks` | 运行中任务数；>0 时数字绿色 |
| 6 | 测试环境状态 | `config.status.inference` | 🟢 在线（含模型数 `N models`）/ 🔴 离线 |

- 数值样式：数字 26px/700 主色，标签 12px 次级色；占位 `—` 灰色。
- `loadStats` 失败时回退：`total_runs` 取记录条数、`running_tasks` 取运行中记录数。

---

## 2. Envs info 面板（右 2 列，2 列 × 2 行 4 宫格）

数据来源：`GET /api/dashboard/env`（后端 `benchscope/env_info.py::collect_env_info` 采集），**缺失项一律显示 `—`**。

| 宫格 | 字段 | 说明 |
| --- | --- | --- |
| 硬件环境 | 主机 / CPU / 内存 / GPU | 主机名 `platform.node()`；CPU 型号×核数；内存总量（GB）；GPU 来自 `nvidia-smi` 探测（`detect_gpu`），无则 `—` |
| 操作系统 | 操作系统 / 系统版本 / 内核版本 | Darwin / Linux 等；macOS 取 `mac_ver`，Linux 取 `/etc/os-release`；内核 `platform.release()` |
| 网络环境 | 网口 - IP | 列出网口与其 IPv4，**过滤 docker / 虚拟网卡**（`docker*`、`veth*`、`br-*`、`virbr*`、`cni*`、`flannel*`、`lo`、`tun*`、`utun*`）；无网口显示 `—` |
| 框架版本 | Python / Pytorch / vLLM / SGLang / benchscope | `sys.version` 与 `importlib.metadata.version` 读取；未安装的框架显示 `—` |

- 采集函数：`collect_env_info()` 返回 `{hardware, os, network, versions}`，全部字段缺失时为 `None`。
- 网络探测：Linux 优先 `ip -o -4 addr`，macOS/回退 `ifconfig` 解析。

---

## 3. Perf Records 面板

### 3.1 标题与操作区

- 标题：**Perf Records**；header 右侧仅保留两个文字按钮（link 按钮）：
  - **刷新**：重新拉取运行记录并刷新统计
  - **更多**：暂未实现，点击提示 toast「功能待实现」

### 3.2 数据与分页

- 展示**最多 8 条最新记录**（`runs.slice(0, 8)`），**不分页**（`pagination: false`）。
- 记录来源：`GET /api/logs/runs`（`resp.runs`）。

### 3.3 表格样式（纯文本，无按钮/边框）

| 规则 | 说明 |
| --- | --- |
| 字体 | 表头/表体统一 12px |
| 单元格 | 纯文本，无 `a-tag` / 按钮边框；Run ID 不加粗 |
| 颜色 | 仅**状态列**（done 绿 / error 红 / stopped 橙 / running 蓝 / pending 灰）与**操作列**（详情蓝、删除红）着色；其余列统一默认文字色 |
| 操作 | 「详情」文字点击 → 弹出运行详情（`RunDetailPanel`，含均值/P99 分析）；「删除」文字点击 → `popconfirm` 确认后删除记录及关联文件 |

---

## 4. Eval Records 面板

- 标题：**Eval Records**（原 Acc Records，v5.0 精度/评估测试预留）。
- 结构与 Perf Records 一致：最多 8 条、不分页、header 右侧「刷新 / 更多」文字按钮。
- 当前无数据：`loadAccRuns` 恒返回空数组，表格空态显示「精度测试功能规划中,待 v5.0」。

---

## 5. 接口与数据流

| 接口 | 用途 |
| --- | --- |
| `GET /api/logs/runs` | 运行记录列表（Perf Records 数据源） |
| `GET /api/logs/runs/{run_id}` | 单条运行详情（详情弹窗） |
| `DELETE /api/logs/runs/{run_id}` | 删除运行记录 |
| `GET /api/dashboard/stats` | 统计卡片：`total_runs` / `total_acc_runs` / `running_tasks` / `avg_tpot` / `best_model` |
| `GET /api/dashboard/env` | 环境信息：`hardware` / `os` / `network` / `versions` |
| `GET /api/config/status`（`config.refreshStatus`） | 推理服务状态：`inference` / `models`（测试环境状态徽标） |

---

## 6. 交互与边界

| 场景 | 行为 |
| --- | --- |
| 记录超过 8 条 | 仅显示最新 8 条（按列表返回顺序，后端已按时间倒序） |
| 删除记录 | popconfirm 确认 → 调 `DELETE` → 本地移除该行并刷新统计 |
| 更多按钮 | toast「功能待实现」，无跳转 |
| 环境信息接口失败 | 面板保持为空，不报错 |
| 统计接口失败 | 回退用记录列表本地计算 |
| Max Perf / Max Acc Records | 显示 `—`，逻辑未实现 |
| 测试环境状态 | 在线显示模型数量（`N models`）；离线显示红色「离线」 |
