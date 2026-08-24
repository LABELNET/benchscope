# benchscope UI 重构实现方案

> 基于现有 v1.0.4 代码，重构主导航与页面体系，引入任务化性能测试、Dashboard、会话等新功能。

---

## 一、整体变更概览

### 1.1 导航结构变更

| 现有导航 | 新导航 | 说明 |
| --- | --- | --- |
| vLLM / SGLang / 日志管理 / 设置 | **Dashboard** / **Performance** / **Accuracy** / **Sessions** / **Settings** | 5 大模块 |

### 1.2 页面清单

| 路由 | 页面 | 状态 | 核心功能 |
| --- | --- | --- | --- |
| `/` → `/dashboard` | Dashboard | 重构 | 统计卡片 + 测试记录列表 + 详情/日志分析 |
| `/performance` | Performance | 重构 | 任务列表 + 新建任务 + 任务详情（实时结果） |
| `/performance/:taskId` | 任务详情 | 新增 | 任务状态/控制 + 左侧进度终端 + 右侧实时结果 |
| `/accuracy` | Accuracy | 新增 | 占位页「规划中」 |
| `/sessions` | Sessions | 新增 | 会话列表 + 对话界面 + 模型选择 |
| `/settings` | Settings | 重构 | 通用设置（主题/语言） + 模型管理 |

### 1.3 后端 API 变更

| API | 说明 | 新增/修改 |
| --- | --- | --- |
| `GET /api/tasks` | 获取所有任务列表 | 新增 |
| `GET /api/tasks/:id` | 获取单个任务详情 | 新增 |
| `POST /api/tasks` | 创建新任务 | 新增 |
| `POST /api/tasks/:id/start` | 启动任务 | 修改（原 `/api/test/start`） |
| `POST /api/tasks/:id/stop` | 停止任务 | 修改（原 `/api/test/stop`） |
| `GET /api/tasks/:id/summary` | 获取任务分析数据 | 修改（原 `/api/logs/runs/:id/summary`） |
| `GET /api/dashboard/stats` | Dashboard 统计数据 | 新增 |
| `POST /api/chat` | 会话对话接口（流式） | 新增 |
| `GET /api/models` | 模型列表（独立管理） | 新增 |
| `POST /api/models` | 添加/编辑模型 | 新增 |
| `DELETE /api/models/:id` | 删除模型 | 新增 |

---

## 二、各页面详细设计

### 2.1 Dashboard（仪表盘）

**路由**：`/dashboard`（默认首页）  
**文件**：`web/src/views/DashboardView.vue`

```
┌──────────────────────────────────────────────────────────────┐
│  统计卡片（一行四个）                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 总测试次数 │ │ 进行中任务 │ │ 平均 TPOT  │ │ 最佳模型   │        │
│  │    42     │ │    2     │ │  23.5ms  │ │ Qwen3.5  │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                              │
│  测试记录                                                     │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 筛选：[全部框架 ▼] [全部状态 ▼] [搜索模型...]              ││
│  │──────────────────────────────────────────────────────────││
│  │ 时间      │ 模型       │ 框架  │ 状态 │ 并发  │ 操作     ││
│  │ 08-24 10:3│ Qwen3.5-4B│ vLLM │ ✅  │ 128  │ [详情]   ││
│  │ 08-24 09:1│ Llama-3-8B│SGLang│ ✅  │ 64   │ [详情]   ││
│  │ 08-23 16:0│ Qwen3.5-4B│ vLLM │ ⏹  │ 32   │ [详情]   ││
│  │ ...                                                      ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**统计卡片数据源**：`GET /api/dashboard/stats`
- `total_runs`：总测试次数
- `running_tasks`：当前进行中任务数
- `avg_tpot`：最近一次完成的测试的平均 TPOT
- `best_model`：TPOT 最低的模型名

**测试记录**：复用现有 `GET /api/logs/runs` API，前端以表格形式展示。

**点击「详情」**：弹出 Modal 或展开内嵌面板，内容复用现有 `RunDetailPanel.vue` 组件（指标汇总 / 均值分析 / P99 分析 / 日志文件四个 Tab）。

**实现要点**：
- 统计卡片用 `a-statistic` 组件
- 表格用 `a-table`，支持排序、筛选、分页
- 详情弹窗内嵌 `RunDetailPanel`，传入 `runId`

---

### 2.2 Performance（性能测试）

**路由**：`/performance`（任务列表）+ `/performance/:taskId`（任务详情）  
**文件**：`web/src/views/PerformanceView.vue` + `web/src/views/TaskDetailView.vue`

#### 2.2.1 任务列表页 `/performance`

```
┌──────────────────────────────────────────────────────────────┐
│  [+ 新建测试任务]                              [刷新] [筛选▼] │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 任务卡片列表（网格或列表视图）                              ││
│  │                                                          ││
│  │ ┌─────────────────┐  ┌─────────────────┐                ││
│  │ │ 🟢 task-0824-1  │  │ 🔵 task-0824-2  │                ││
│  │ │ Qwen3.5-4B      │  │ Llama-3-8B      │                ││
│  │ │ vLLM · Random   │  │ SGLang · ShareGPT│                ││
│  │ │ 进度: 12/24     │  │ 状态: 已完成     │                ││
│  │ │ [进入] [停止]    │  │ [进入] [查看]    │                ││
│  │ └─────────────────┘  └─────────────────┘                ││
│  │                                                          ││
│  │ ┌─────────────────┐  ┌─────────────────┐                ││
│  │ │ ⚪ task-0824-3   │  │ 🔴 task-0823-1  │                ││
│  │ │ Qwen3.5-4B      │  │ Qwen3.5-4B      │                ││
│  │ │ vLLM · Custom   │  │ vLLM · Random   │                ││
│  │ │ 状态: 待开始     │  │ 状态: 执行出错   │                ││
│  │ │ [进入] [删除]    │  │ [进入] [重试]    │                ││
│  │ └─────────────────┘  └─────────────────┘                ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**任务状态**：`pending`（待开始）→ `running`（进行中）→ `done`（完成）/ `stopped`（已停止）/ `error`（出错）

**任务卡片信息**：
- 任务 ID / 模型名 / 框架 / 数据集类型
- 状态指示灯 + 进度（进行中时）
- 操作按钮：进入 / 开始 / 停止 / 删除 / 重试

#### 2.2.2 新建任务流程

点击「新建测试任务」弹出分步表单（Modal 或 Drawer）：

```
┌──────────────────────────────────────────────┐
│  新建测试任务                    步骤 1/3     │
│──────────────────────────────────────────────│
│                                              │
│  Step 1: 选择模型与框架                       │
│  ┌────────────────────────────────────────┐  │
│  │ 模型：[下拉选择 / 从模型库选择]         │  │
│  │ 模型状态：🟢 在线 (Qwen3.5-4B)         │  │
│  │ 框架：(●vLLM  ○SGLang)                │  │
│  │ 精度：[W8A8____]（可选）               │  │
│  └────────────────────────────────────────┘  │
│                                              │
│              [上一步]  [下一步]               │
└──────────────────────────────────────────────┘

│  Step 2: 配置测试参数                       │
│  ┌────────────────────────────────────────┐  │
│  │ 数据集类型：[Random ▼]                  │  │
│  │ (Random) 输入/输出长度组合：             │  │
│  │   [3K1K ✓] [1K1K ✓] [256X256 ✓]      │  │
│  │   自定义: [1024] / [512] [+添加]       │  │
│  │                                        │  │
│  │ 并发数：[1][4][8][16][32][40][64][128] │  │
│  │ 请求速率：[inf ▼]                      │  │
│  │                                        │  │
│  │ ▸ 高级参数（折叠）                      │  │
│  │   GPU / TPOT阈值 / 框架参数 / 自由参数  │  │
│  └────────────────────────────────────────┘  │

│  Step 3: 确认与预览                         │
│  ┌────────────────────────────────────────┐  │
│  │ 任务摘要：                              │  │
│  │   模型: Qwen3.5-4B                     │  │
│  │   框架: vLLM                           │  │
│  │   数据集: Random (3K1K, 1K1K, 256X256) │  │
│  │   并发: 1,4,8,16,32,40,64,128          │  │
│  │                                        │  │
│  │ 命令预览：                              │  │
│  │ ┌──────────────────────────────────┐   │  │
│  │ │ [3K1K | 并发=1]                  │   │  │
│  │ │ vllm bench serve --model ...     │   │  │
│  │ │                                  │   │  │
│  │ │ [3K1K | 并发=4]                  │   │  │
│  │ │ vllm bench serve --model ...     │   │  │
│  │ └──────────────────────────────────┘   │  │
│  │                                        │  │
│  │ ☐ 创建后立即开始测试                    │  │
│  └────────────────────────────────────────┘  │
```

#### 2.2.3 任务详情页 `/performance/:taskId`

**核心布局**（用户明确要求：上方状态栏 + 下方左 1/4 右 3/4）：

```
┌──────────────────────────────────────────────────────────────┐
│  ← 返回任务列表                                               │
│──────────────────────────────────────────────────────────────│
│  上方：状态栏（全宽）                                          │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 任务: task-0824-1  │ 模型: Qwen3.5-4B  │ 框架: vLLM    ││
│  │ 状态: 🟢 运行中     │ 进度: 12/24 (50%) │ 耗时: 3分22秒  ││
│  │                                                          ││
│  │ 服务状态: 🟢 推理服务在线 (2个模型)                        ││
│  │                                                          ││
│  │ [▶ 开始]  [⏹ 停止]  [🔄 重试]  [👁 命令预览]  [⚙ 编辑配置]││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  下方：左右分栏                                               │
│  ┌──────────────┬───────────────────────────────────────────┐│
│  │ 左侧 (1/4)   │  右侧 (3/4)                               ││
│  │              │                                           ││
│  │ ┌──────────┐ │  ┌─────────────────────────────────────┐ ││
│  │ │ 测试进度  │ │  │  实时结果表格                        │ ││
│  │ │          │ │  │  (双语表格，实时更新)                 │ ││
│  │ │ 当前:    │ │  │  Output/Total吞吐, TTFT/TPOT...     │ ││
│  │ │ 3K1K     │ │  │                                     │ ││
│  │ │ @并发 16 │ │  │  [分页]                              │ ││
│  │ │ 12/24    │ │  └─────────────────────────────────────┘ ││
│  │ │          │ │                                           ││
│  │ ├──────────┤ │  ┌─────────────────────────────────────┐ ││
│  │ │ 终端输出  │ │  │  实时曲线（6条）                     │ ││
│  │ │          │ │  │  Output吞吐 / Total吞吐              │ ││
│  │ │ $ vllm   │ │  │  TTFT mean / TPOT mean              │ ││
│  │ │ bench... │ │  │  TTFT P99  / TPOT P99               │ ││
│  │ │ Serving  │ │  │  (ECharts, 实时更新)                 │ ││
│  │ │ Benchmark│ │  │                                     │ ││
│  │ │ Result...│ │  │                                     │ ││
│  │ │          │ │  └─────────────────────────────────────┘ ││
│  │ └──────────┘ │                                           ││
│  └──────────────┴───────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**左侧 1/4 区域**：
- **测试进度**（上半部分）：圆形进度条 + 当前用例/并发信息 + 状态标签
- **终端输出**（下半部分）：深色终端风格，实时流式显示 bench 命令输出，自动滚动

**右侧 3/4 区域**：
- **实时结果表格**（上半部分）：复用 `MetricsTable.vue`，双语表头，实时更新
- **实时曲线**（下半部分）：复用 `MetricsCharts.vue`，6 条曲线

**关键交互**：
- 任务进行中：左侧终端实时滚动，右侧表格/曲线实时更新
- 任务完成后：左侧终端保留最终输出，右侧显示完整结果 + 分析 Tab（均值/P99）
- 任务待开始：右侧显示空状态「点击开始测试」

---

### 2.3 Accuracy（精度测试）

**路由**：`/accuracy`  
**文件**：`web/src/views/AccuracyView.vue`

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                      🔬 精度测试                              │
│                                                              │
│              ┌──────────────────────┐                        │
│              │   🚧 功能规划中       │                        │
│              │                      │                        │
│              │  计划支持：           │                        │
│              │  · 常见数据集精度评估  │                        │
│              │  · ModelScope 模型对比│                        │
│              │  · 多维度质量分析     │                        │
│              │                      │                        │
│              │  预计版本：v5.0       │                        │
│              └──────────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

纯展示页，使用 `a-result` 或自定义卡片展示规划信息。

---

### 2.4 Sessions（会话）

**路由**：`/sessions`  
**文件**：`web/src/views/SessionsView.vue`

```
┌──────────┬───────────────────────────────────────────────────┐
│ 会话列表  │  当前会话                                          │
│ (260px)  │                                                   │
│          │  ┌───────────────────────────────────────────────┐│
│ [+新建]  │  │ 模型: [Qwen3.5-4B ▼]  系统提示词: [可选...]   ││
│ [清空]   │  ├───────────────────────────────────────────────┤│
│          │  │                                               ││
│ ● 会话1  │  │  👤 User:                                    ││
│   刚才    │  │  请解释一下 vLLM 的 PagedAttention 原理       ││
│          │  │                                               ││
│ ○ 会话2  │  │  🤖 Assistant:                                ││
│   10:30  │  │  PagedAttention 是 vLLM 的核心创新...         ││
│          │  │  它将 KV cache 分成固定大小的块...              ││
│ ○ 会话3  │  │                                               ││
│   昨天    │  │  👤 User:                                    ││
│          │  │  与传统方案相比有什么优势？                     ││
│          │  │                                               ││
│          │  │  🤖 Assistant:                                ││
│          │  │  主要优势有三点...                              ││
│          │  │                                               ││
│          │  ├───────────────────────────────────────────────┤│
│          │  │ [输入消息...                           ] [发送]││
│          │  └───────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────┘
```

**左侧会话列表**：
- 「+ 新建会话」按钮：创建新对话，清空右侧
- 「清空」按钮：确认后删除全部会话
- 会话项：显示首条消息摘要 + 时间
- 点击切换右侧内容
- 当前选中会话高亮

**右侧对话区**：
- 顶部：模型选择下拉（从 `/v1/models` 获取）+ 可选系统提示词
- 中间：消息列表（用户 / 助手交替显示），支持 Markdown 渲染
- 底部：输入框 + 发送按钮，支持 Enter 发送、Shift+Enter 换行

**后端实现**：
- 会话数据存储在 `~/.benchscope/sessions/` 目录，每个会话一个 JSON 文件
- 对话接口 `POST /api/chat` 调用 OpenAI 兼容 API（`/v1/chat/completions`），流式返回（SSE）
- 前端通过 EventSource 或 fetch + ReadableStream 接收流式响应，逐字显示

**API 设计**：

```
GET    /api/sessions              → 会话列表
POST   /api/sessions              → 新建会话 { title?, model?, system_prompt? }
GET    /api/sessions/:id          → 获取会话详情（含消息历史）
DELETE /api/sessions/:id          → 删除会话
DELETE /api/sessions              → 清空全部会话
POST   /api/sessions/:id/chat     → 发送消息并获取流式回复
         body: { content: string }
         response: SSE stream (text/event-stream)
```

---

### 2.5 Settings（设置）

**路由**：`/settings`  
**文件**：`web/src/views/SettingsView.vue`

重构为分区设置页面：

```
┌──────────────────────────────────────────────────────────────┐
│  设置                                                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 通用 General                                             ││
│  │──────────────────────────────────────────────────────────││
│  │ 主题：(●亮色  ○暗色  ○跟随系统)                           ││
│  │ 语言：(●中文  ○English)                                  ││
│  │ 默认框架：(●vLLM  ○SGLang)                               ││
│  │ TPOT 阈值：[100] ms                                     ││
│  │ 日志目录：[./logs________]                               ││
│  │ 数据集目录：[./datasets______]                           ││
│  │ bench 命令：                                             ││
│  │   vLLM：[vllm bench serve________]                      ││
│  │   SGLang：[python -m sglang.bench_serving__]            ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 推理服务 API                                             │
│  │──────────────────────────────────────────────────────────││
│  │ Base URL：[http://192.168.1.67:8000___]                 ││
│  │ Endpoint：[/v1/chat/completions______]                  ││
│  │ API Key：[••••••••]                                      ││
│  │ 额外请求头：[{}____________________]                     ││
│  │ [测试连接]                                               ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 模型管理 Models                                          ││
│  │──────────────────────────────────────────────────────────││
│  │ [+ 添加模型]                                             ││
│  │                                                          ││
│  │ 名称              │ 地址              │ 框架  │ 操作      ││
│  │ Qwen3.5-4B       │ http://...:8000   │ vLLM │ [编辑][删]││
│  │ Llama-3-8B       │ http://...:8001   │SGLang│ [编辑][删]││
│  │                                                          ││
│  │ GPU：🟢 自动检测 (NVIDIA A100 × 8)  [刷新]              ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  [保存配置]                                                   │
└──────────────────────────────────────────────────────────────┘
```

**三大分区**：
1. **通用**：主题（亮/暗/跟随系统）、语言（中/英）、默认框架、TPOT 阈值、目录配置、bench 命令
2. **推理服务 API**：Base URL / Endpoint / API Key / 额外请求头 / 测试连接
3. **模型管理**：模型列表表格，支持添加/编辑/删除；GPU 信息展示

**模型管理说明**：
- 模型信息持久化到 `~/.benchscope/models.json`
- 每个模型记录：`{ id, name, base_url, framework, precision, gpu_count, notes }`
- 在 Performance 新建任务时，可从模型库快速选择
- 同时保留从 `/v1/models` 动态获取模型的能力

---

## 三、任务持久化方案（核心后端改造）

### 3.1 问题

当前测试执行状态仅保存在内存（`TestManager.current`），刷新页面即丢失。需要实现任务持久化，使：
- 切换页面不影响进行中的任务
- 刷新页面后可恢复任务状态

### 3.2 方案

**任务存储**：`~/.benchscope/tasks/` 目录，每个任务一个 JSON 文件。

```
~/.benchscope/
├── config.json           # 全局配置
├── models.json           # 模型库（新增）
├── tasks/                # 任务持久化（新增）
│   ├── task-0824-103412.json
│   ├── task-0824-110530.json
│   └── ...
└── sessions/             # 会话存储（新增）
    ├── session-001.json
    └── ...
```

**任务 JSON 结构**：

```json
{
  "task_id": "task-0824-103412",
  "created_at": "2026-08-24 10:34:12",
  "status": "running",
  "framework": "vllm",
  "model": "Qwen3.5-4B",
  "precision": "W8A8",
  "dataset": { "type": "random", "length_pairs": [...] },
  "concurrency_list": [1, 4, 8, 16, 32, 40, 64, 128],
  "gpu": { "name": "NVIDIA A100", "count": 8 },
  "request_rate": "inf",
  "tpot_threshold_ms": 100,
  "curated": {},
  "extra_args": [],
  "rows": [...],
  "run_dir": "./logs/0824-103412",
  "started_at": "2026-08-24 10:34:15",
  "finished_at": null,
  "error": null
}
```

**后端改造要点**：

1. **`TaskManager`**（替代现有 `TestManager`）：
   - 管理多个并发任务（不再限制同时只能有一个测试）
   - 每个任务独立线程执行
   - 任务创建时立即持久化
   - 每完成一个并发度，增量更新持久化文件
   - 服务启动时扫描 `tasks/` 目录，恢复 `running` 状态的任务

2. **`Task` 数据类**：
   - 包含完整的任务配置与执行状态
   - `snapshot()` 方法返回可序列化字典
   - 状态变更自动触发持久化写入

3. **WebSocket 消息扩展**：
   - 所有消息增加 `task_id` 字段
   - 前端根据 `task_id` 路由消息到对应的任务详情页

---

## 四、主题与国际化方案

### 4.1 主题

**实现方式**：Ant Design Vue 内置主题切换能力。

```javascript
// store/config.js 扩展
state: () => ({
  theme: 'light',  // 'light' | 'dark' | 'system'
  // ...
})

// App.vue
const themeConfig = computed(() => {
  const isDark = resolvedTheme.value === 'dark'
  return {
    token: {
      colorPrimary: '#1677ff',
      borderRadius: 6,
      ...(isDark ? {
        colorBgContainer: '#141414',
        colorText: 'rgba(255,255,255,0.85)',
      } : {}),
    },
    algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
  }
})
```

- 亮色/暗色/跟随系统三选一
- CSS 变量方案：在 `body` 上添加 `data-theme="dark"` 属性，配合 CSS 变量覆盖

### 4.2 国际化（i18n）

**方案**：引入 `vue-i18n`（或轻量级自建方案）。

考虑到项目体量，建议**轻量自建方案**，避免引入额外依赖：

```javascript
// src/i18n/index.js
const messages = {
  zh: {
    dashboard: '仪表盘',
    performance: '性能测试',
    accuracy: '精度测试',
    sessions: '会话',
    settings: '设置',
    newTask: '新建测试任务',
    // ...
  },
  en: {
    dashboard: 'Dashboard',
    performance: 'Performance',
    accuracy: 'Accuracy',
    sessions: 'Sessions',
    settings: 'Settings',
    newTask: 'New Test Task',
    // ...
  }
}
```

- 配置存储在 `config.json` 的 `locale` 字段
- 组件内通过 `t('dashboard')` 函数获取翻译
- 默认中文，可切换英文

---

## 五、前端文件结构（重构后）

```
web/src/
├── api/index.js                # API 请求（扩展任务/会话/模型接口）
├── i18n/                       # 国际化（新增）
│   ├── index.js
│   ├── zh.js
│   └── en.js
├── router/index.js             # 路由（重构）
├── store/
│   ├── config.js               # 配置（扩展主题/语言）
│   ├── test.js → tasks.js      # 任务状态管理（重命名+扩展）
│   ├── form.js                 # 测试表单（保留）
│   └── sessions.js             # 会话状态（新增）
├── components/
│   ├── TopBar.vue              # 顶部导航（重构为5项）
│   ├── StatusBadge.vue         # 状态指示灯（保留）
│   │
│   │── dashboard/              # Dashboard 组件（新增）
│   │   ├── StatsCards.vue
│   │   └── RunTable.vue
│   │
│   ├── performance/            # Performance 组件（新增）
│   │   ├── TaskCard.vue
│   │   ├── TaskCreateDrawer.vue
│   │   ├── TaskStatusBar.vue
│   │   ├── TaskTerminal.vue
│   │   └── TaskResults.vue
│   │
│   ├── sessions/               # Sessions 组件（新增）
│   │   ├── SessionList.vue
│   │   ├── ChatPanel.vue
│   │   └── MessageBubble.vue
│   │
│   ├── settings/               # Settings 组件（新增）
│   │   ├── GeneralSettings.vue
│   │   ├── ApiSettings.vue
│   │   └── ModelManager.vue
│   │
│   │── common/                 # 通用组件（从现有组件提取）
│   │   ├── MetricsTable.vue    # 复用
│   │   ├── MetricsCharts.vue   # 复用
│   │   ├── ConcurrencyEditor.vue # 复用
│   │   ├── FreeArgsEditor.vue  # 复用
│   │   ├── AnalysisBlock.vue   # 复用
│   │   └── RunDetailPanel.vue  # 复用
│   │
│   └── legacy/                 # 旧组件归档（逐步迁移后可删除）
│       ├── EnvPanel.vue
│       ├── TestConfigPanel.vue
│       ├── TestProgressPanel.vue
│       ├── RealtimeResultPanel.vue
│       ├── SubTabBar.vue
│       ├── RunRecordList.vue
│       └── RunSummaryBlock.vue
├── views/
│   ├── DashboardView.vue       # 新增
│   ├── PerformanceView.vue     # 新增（任务列表）
│   ├── TaskDetailView.vue      # 新增（任务详情）
│   ├── AccuracyView.vue        # 新增
│   ├── SessionsView.vue        # 新增
│   ├── SettingsView.vue        # 重构
│   └── (TestView.vue)          # 删除（拆分为 Performance + TaskDetail）
├── App.vue                     # 重构（新导航 + 主题）
└── main.js                     # 扩展（i18n 注入）
```

---

## 六、路由设计

```javascript
const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/performance', name: 'performance', component: PerformanceView },
  { path: '/performance/:taskId', name: 'taskDetail', component: TaskDetailView },
  { path: '/accuracy', name: 'accuracy', component: AccuracyView },
  { path: '/sessions', name: 'sessions', component: SessionsView },
  { path: '/settings', name: 'settings', component: SettingsView },
]
```

---

## 七、后端文件结构（重构后）

```
benchscope/
├── server/
│   ├── app.py                  # 路由注册（扩展新路由）
│   ├── state.py                # 全局状态（扩展 TaskManager）
│   ├── status.py               # 状态监控（保留）
│   ├── ws.py                   # WebSocket（扩展 task_id 路由）
│   ├── api_config.py           # 配置 API（保留，扩展主题/语言）
│   ├── api_test.py             # → api_tasks.py（重命名+重构）
│   ├── api_logs.py             # 日志 API（保留，Dashboard 复用）
│   ├── api_dashboard.py        # Dashboard 统计 API（新增）
│   ├── api_models.py           # 模型管理 API（新增）
│   ├── api_sessions.py         # 会话 API（新增）
│   └── test_manager.py         # → task_manager.py（重命名+重构）
├── task_manager.py             # 任务管理器（替代 TestManager）
├── session_manager.py          # 会话管理器（新增）
├── model_manager.py            # 模型管理器（新增）
└── (其余文件保留)
```

---

## 八、实施分期

### Phase 1：基础框架重构（优先级最高）

| 任务 | 文件 | 说明 |
| --- | --- | --- |
| 重构路由与导航 | `router/index.js`, `TopBar.vue`, `App.vue` | 5 项导航，新路由 |
| 新建 Dashboard 页 | `DashboardView.vue`, `StatsCards.vue`, `RunTable.vue` | 统计 + 记录列表 |
| 新建 Accuracy 占位页 | `AccuracyView.vue` | 简单 |
| 重构 Settings 页 | `SettingsView.vue` → 分区 | 通用/API/模型三段 |
| 后端 Dashboard API | `api_dashboard.py` | 统计数据 |

### Phase 2：任务化 Performance

| 任务 | 文件 | 说明 |
| --- | --- | --- |
| 后端 TaskManager | `task_manager.py`, `api_tasks.py` | 多任务、持久化 |
| WebSocket 扩展 | `ws.py` | task_id 路由 |
| 任务列表页 | `PerformanceView.vue`, `TaskCard.vue` | 卡片网格 |
| 新建任务抽屉 | `TaskCreateDrawer.vue` | 分步表单 |
| 任务详情页 | `TaskDetailView.vue`, `TaskStatusBar.vue`, `TaskTerminal.vue`, `TaskResults.vue` | 左 1/4 右 3/4 布局 |
| 服务启动恢复 | `task_manager.py` | 扫描 tasks/ 恢复 running |

### Phase 3：Sessions 会话

| 任务 | 文件 | 说明 |
| --- | --- | --- |
| 后端会话管理 | `session_manager.py`, `api_sessions.py` | 存储 + CRUD |
| 流式对话接口 | `api_sessions.py` | SSE 转发 OpenAI API |
| 前端会话界面 | `SessionsView.vue`, `SessionList.vue`, `ChatPanel.vue`, `MessageBubble.vue` | 左右分栏 |
| 会话状态管理 | `store/sessions.js` | Pinia store |

### Phase 4：主题 + 国际化 + 模型管理

| 任务 | 文件 | 说明 |
| --- | --- | --- |
| 暗色主题 | `App.vue`, CSS 变量 | Ant Design 主题算法 |
| 国际化框架 | `i18n/`, `main.js` | 轻量自建 |
| 翻译文件 | `zh.js`, `en.js` | 全量文案 |
| 模型管理后端 | `model_manager.py`, `api_models.py` | CRUD + 持久化 |
| 模型管理前端 | `ModelManager.vue` | Settings 内嵌 |

---

## 九、关键技术决策

| 决策点 | 方案 | 理由 |
| --- | --- | --- |
| 任务持久化 | JSON 文件（`~/.benchscope/tasks/`） | 与现有 config.json 一致，无需引入数据库 |
| 会话流式响应 | SSE（Server-Sent Events） | 单向推送，比 WebSocket 更简单，兼容性好 |
| 主题切换 | Ant Design Vue 主题算法 + CSS 变量 | 框架原生支持，维护成本低 |
| 国际化 | 轻量自建（`$t` 函数） | 避免引入 vue-i18n 依赖，项目体量够用 |
| 多任务并发 | 每任务独立线程 | 与现有单任务模型兼容，改动最小 |
| 前端组件复用 | 现有 MetricsTable/Charts/Analysis 直接复用 | 减少重复开发 |

---

## 十、风险与注意事项

1. **向后兼容**：现有 `benchscope` CLI 启动方式不变，`pip install` 后直接可用
2. **旧路由迁移**：`/vllm` 和 `/sglang` 路由需重定向到 `/performance`（或保留为兼容路由）
3. **WebSocket 消息格式**：新增 `task_id` 字段，旧前端不识别时可忽略
4. **Sessions 依赖**：会话功能依赖推理服务支持 `/v1/chat/completions`，需在 UI 中提示
5. **前端构建产物**：重构后需重新 `npm run build`，产物打包到 `benchscope/webui/`
6. **数据迁移**：现有 `logs/` 目录结构不变，Dashboard 直接复用
