# VERSION 1.0.5 — 版本修订记录

> **版本**：1.0.5  
> **发布日期**：迭代中  
> **文档状态**：1.0.5 版本的功能主要概述、迭代 PRD 汇总与 TODO 清单  
> **目录**：本文档汇总 `docs/versions/PRD_*.md` 全部迭代需求；页面级行为细则见 `docs/prds/`

---

## 1. 版本概述

v1.0.5 为 **v2.0 UI 大改 + 性能页双模式增强** 版本，核心范围：

1. **v2.0 UI 大改** — 5 栏导航（Dashboard / Performance / Accuracy / Sessions / Settings）、任务化 Performance（多任务持久化 `~/.benchscope/tasks/`）、Sessions SSE 对话（持久化 `~/.benchscope/sessions/`）、Accuracy 占位页、Settings 分区设置、i18n（EN / 简体中文）+ 亮 / 暗 / 跟随系统主题。
2. **任务双模式** — `concurrency`（多档并发压测）/ `threshold`（阈值探测：`concurrency_list=[1]`，逐级倍增 + 二分寻找满足阈值的最大并发）。
3. **创建任务三步表单** — 独立创建页（`/performance/create`），Step1 条件 / Step2 参数 / Step3 命令预览，`?mode=` 区分模式；多组条件带唯一 `case_id`。
4. **Realtime 分组表格** — 按 case 分组（`caseKey = label#g{case_id}`）、组内并发升序、每组独立 Best/BestPerf 唯一高亮、本地阈值试算（TPOT 默认 100 / Output 默认 0）。
5. **Progress 按 case 计数**（阈值模式）— 与 Cases 数量严格一致（1/1、2/2、N/N），不随动态并发点增长。
6. **Excel 导出** — `POST /api/tasks/{task_id}/export` → `task.run_dir/realtime_{task_id}.xlsx`（含分组标题行、Best/BestPerf 标记）。
7. **Dashboard 重构** — Overview（2×3 六宫格统计）+ Envs info（硬件/OS/网络/框架版本，缺失显示 `—`）+ Perf Records / Eval Records（最多 8 条、不分页、纯文本表格）。
8. **Settings 四栏** — General（Language + Cache Paths）/ Envs（环境配置 + Edit/Save + Test Connection）/ Models（内置模型下载宫格 + 详情抽屉 + 部署待实现）/ Plugins（占位）。
9. **mock 环境** — `mocks/` 包（vLLM/SGLang bench 仿真输出 + OpenAI 兼容服务 + SSE 流式）、`scripts/dev.sh` 统一入口（后端托管前端构建产物）。

---

## 2. 迭代 PRD 汇总（按时间顺序：260824 → 260825 → 260826-1 → 260826-2）

### 2.1 PRD_260824（产品需求文档 — 基线）

**功能概述**：产品定位（LLM 推理服务性能测试工具，单进程 pip 安装，无需服务端插件）。

**功能模块总览**（5 页导航）：

| 模块 | 路由 | 说明 |
| --- | --- | --- |
| Dashboard | `/dashboard` | 统计卡片（总测试次数 / 进行中任务 / 平均 TPOT / 最佳模型）+ 历史运行记录 |
| Performance | `/performance` `/performance/create` `/performance/:taskId` | 任务列表 + 新建表单 + 详情页（进度 + 终端 + 实时表格 + 曲线） |
| Accuracy | `/accuracy` | 占位页（v5.0 预留） |
| Sessions | `/sessions` | SSE 流式对话 + 会话持久化 |
| Settings | `/settings` | 通用 / 推理服务 API / GPU；Plugins 占位 |

**webclient 功能定义**：
- 基本：配置 OpenAI 兼容 API；支持 vLLM/SGLang bench 参数搜索与选择；数据集 random / sharegpt（自动下载）/ custom；模型以 API `/v1/models` 为准；服务状态监控（web 就绪/离线、推理就绪/离线）；UI 全宽 + 顶部导航（服务状态 + 服务设置）
- 测试：random 支持多组输入/输出长度（默认 3K/1K、1K/1K、256/256，可自定义）；请求数默认 1,4,8,16,32,40,64,128（可编辑）；`--max-concurrency` 与 `--num-prompts` 保持一致、提供 inf；GPU 数量自动获取或手动；vLLM/SGLang 其他参数可自由添加
- 日志：`logs/<MMDD-HHMMSS>/` 目录、预览与下载、`benchmark-*.xlsx` 汇总（模型/精度/GPU/框架/输入输出长度/并发/output/peakoutput/total/ttft/itl/tpot/单用户=1000/tpot）；mean 与 P99 双面板
- 分析：实时表格与六条曲线（output/peakoutput/total/ttft/itl/tpot，横轴并发）；自定义最佳并发（TPOT 阈值高亮最接近 <100ms 的记录）

**技术方案**：Vue 前端 + Ant Design UI 组件；执行 vLLM/sglang bench 无需在其环境安装插件；本地调试地址 `http://192.168.1.67:8000`（后改为默认 `127.0.0.1:8000`）。

**TODO 清单**：
- [x] 双框架（vLLM / SGLang）性能测试
- [x] 三数据集（random / ShareGPT / custom）
- [x] 实时结果 + 六条曲线 + 日志与 `benchmark-*.xlsx` 汇总（mean + P99）
- [x] 分析面板与最佳并发高亮
- [x] 管理台 UI + 服务 / 推理环境状态监控
- [ ] v2.0 多模态模型性能测试（规划）
- [ ] v5.0 常见数据集精度测试
- [ ] v6.0 ModelScope 官方模型对比
- [ ] v7.0 内置 GPU 适配模型一键下载 / 部署

### 2.2 PRD_260825（Performance 单任务 + Sessions 会话重构）

**功能概述**：围绕 Performance 与 Sessions 的大量交互/展示迭代。

**Performance 单任务模式**：
- 页面有且仅保留一个任务：store 新增 `theTask` getter（最新任务），路由收敛到 `/performance`
- 默认界面：功能介绍 + 开启测试按钮（a-result + 功能卡网格，与 Accuracy 同构）
- 点击「开启测试」弹出创建面板（复用 TaskCreateForm），创建+启动后自动切详情；Close 后 `deleteTask` 恢复默认界面

**四块式详情布局**：
- 任务详情面板：标题栏左侧（模型名 | Progress 已完成/总数 | Elapsed | Perf Status），右侧（开始/停止/关闭按钮按状态显隐）；内容（框架/精度/数据集/并发/请求率/Service Status/URL/测试 Case×并发网格）；状态高亮 running=蓝+转圈、done=绿、error=红
- 实时数据面板：TPOT 阈值就地编辑（失焦保存）；表格无分页、最佳行深绿 `#d9f7be`、阈值附近浅绿 `#f6ffed`、错误行红；Case/并发固定左、状态固定右
- 数据分析面板：3×2 网格（吞吐蓝 / TTFT 金 / TPOT 绿）；`echarts.connect('perf-charts')` 曲线联动；最大点 `markPoint pin` 标记
- 控制台：终端日志 + 自动滚动（用户向上阅读不打扰）+ 历史加载 + 下载
- 刷新恢复：状态来自后台，刷新即恢复（任务快照 + 日志）

**Sessions 重构**：
- 会话持久化（`~/.benchscope/sessions/`）、思考折叠显示、通用推理标签解析器（`<think>` 等 6 种 + 全角变体，`parse_think_tags`）
- 实时性能数据栏（turns/steps/LLM Time/TTFT/Output tok/s/TPOT/ITL）、底部操作栏（模型/质量/思考开关/发送）
- 后端：full.log 持久化、会话配置与思考字段持久化

**TODO 清单**：
- [x] Performance 单任务模式与四块式详情布局
- [x] 曲线联动与 markPoint 最大点标记
- [x] Sessions SSE 流式对话 + 思考/正文分离
- [x] 通用推理标签解析（多标签 + 全角兼容）
- [x] 会话与性能数据持久化

### 2.3 PRD_260826-1（三行布局 + 表格/统计图重构 + mocks 重命名）

**功能概述**：在 1.0.5 基础上继续迭代 Performance 与 mock 仿真包。

- **mock → mocks 重命名**：目录/包重命名 + 外部引用更新 + 验证（9 文件）
- **Performance 三行布局**：第一行 Perf + Cases + Console（各占 1/3 等高）；第二行 Realtime Data；第三行 Statistics
  - Perf 面板：标题 `Perf | 模型名`（14px/600）；右侧 Progress/Elapsed/Perf Status（12px 灰）；内容 info-row 两端对齐、Framework 无边框纯文本、详情值 12px/400；footer Start/Stop/Close
  - Cases 面板（新增）：按 case 显示并发标签，多组条件独立
  - Console 面板：终端日志 + 下载按钮
- **Realtime Data 表格**：后端 parser 扩展（successful/failed/duration/tokens/median 等 10+ 字段）、API 序列化扩展（`_to_merged_rows`）、列设置（下拉勾选）、默认列紧凑不换行、Best 高亮
- **Statistics**：4×3 共 12 张图（吞吐 / TTFT / TPOT / ITL 各 mean / median / p99），每列 8 色调色板、单位轴（tok/s / ms）、图例滚动、tooltip 联动

**TODO 清单**：
- [x] mocks 包重命名与引用更新
- [x] Performance 三行布局、三面板等高
- [x] Realtime 表格新增列与列设置
- [x] Statistics 12 图网格与单位轴

### 2.4 PRD_260826-2（任务双模式 + 分组高亮 + Excel 导出）

**功能概述**：围绕「任务双模式（并发 / 阈值）」端到端增强 + 表格分组高亮 + Excel 导出。

- **任务双模式**：任务新增 `mode`（`concurrency` / `threshold`）；阈值模式携带 `tpot_threshold_ms`、`output_throughput_threshold` 快照；阈值策略：1→2→4→8… 倍增 + 二分寻找满足阈值最大并发
- **创建任务三步表单**：独立创建页（`?mode=` 区分），Step1 条件 / Step2 参数 / Step3 命令预览
- **Cases 面板（阈值模式）**：只读显示阈值条件；按 case 独立展示请求状态（完整测试列表 / Pending），各 case 互不联动
- **Realtime 分组表格**：按 case 分组，组内按并发数升序，每组独立阈值高亮
- **Best / BestPerf 唯一高亮**：满足阈值条件的行中标记并发最大的一行；0 值条件不参与；两阈值全 0 不处理
- **本地阈值控件**：TPOT Threshold 默认 100、Output Token Threshold 默认 0；即时重算本地高亮，不写回任务
- **Perf 面板调整**：Framework 下新增 Mode 行；移除 Requests 行；Successful 成功率按整数百分比显示
- **Excel 导出**：Realtime 表格底部 Download → `POST /api/tasks/{task_id}/export` → `task.run_dir/realtime_{task_id}.xlsx`（含分组标题行加粗 + 浅蓝底色）+ 浏览器下载
- **footer 布局**：Columns → Download 固定右下角

**文件变更清单**：`benchscope/task_manager.py`（双模式执行 + 阈值二分 + run.json）、`benchscope/server/api_tasks.py`（export/preview/阈值接口）、`benchscope/parser.py`（字段扩展）、`web/src/views/PerfCreateView.vue`（新建）、`web/src/components/performance/ConditionPanel.vue` 等（新建）、`web/src/views/PerformanceView.vue`（三行布局 + 分组表格 + 导出）。

**TODO 清单**：
- [x] 任务双模式端到端（并发 / 阈值）
- [x] 创建页三步表单
- [x] 分组表格 + 唯一高亮
- [x] 本地阈值控件（不写回任务）
- [x] Excel 导出
- [x] case_id 唯一组 id（多组相同条件不叠加）
- [x] 阈值模式 Progress 按 case 计数

---

## 3. 后续版本 TODO（规划）

| 版本 | 范围 | 状态 |
| --- | --- | --- |
| 2.0 | 多模态模型性能测试（图像/视频输入） | 规划 |
| 3.0 | 全模态模型性能测试（音频/视频/多模态） | 规划 |
| 4.0 | 世界模型性能测试 | 规划 |
| 5.0 | 常见数据集精度测试（Accuracy 页落地，Dashboard Eval Records 接入） | 规划 |
| 6.0 | ModelScope 官方模型对比（链接 + 结论） | 规划 |
| 7.0 | 内置 GPU 适配模型一键下载 / 部署（Settings → Models 部署按钮落地） | 规划 |

---

## 4. 相关文档

- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings）
- 上一版本归档：`docs/versions/VERSION_1_0_4.md`（1.0.4 规划与收口，原 `.trae/` 内容）
- **维护约定**：`docs/versions/` 下内容更新均以**时间顺序**进行——新版本创建 `VERSION_x_y_z.md`；同版本迭代内容按时间先后追加到对应版本文档。
