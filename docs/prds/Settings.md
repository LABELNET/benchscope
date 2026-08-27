# benchscope Settings 页面 — 功能与约束说明

> **版本**：v1.0.6  
> **最后更新**：2026-08-27  
> **文档状态**：Settings 页面四个侧边栏（General / Envs / Models / Plugins）的功能与约束条件说明  
> **关联文档**：[Performance.md](./Performance.md) · [Dashboard.md](./Dashboard.md)

---

## 0. 总览

Settings 页面左侧 4 个侧边栏：

| 侧边栏 | 图标 | 内容 |
| --- | --- | --- |
| General | ⚙️ Setting | 2 个面板：Language、Cache Paths（9 目录配置） |
| Envs | 🖥️ Desktop | 1 个运行环境面板（环境配置 + 状态 + 编辑/保存/测试连接） |
| Datasets（1.0.6） | ☁️ CloudDownload | 内置数据集下载面板（见 2.5） |
| Models | 🗄️ Database | 内置模型下载宫格 + 右侧详情面板 |
| Plugins | 🔌 Api | 占位（v5.0 预留） |

所有配置持久化到服务端 `~/.benchscope/settings.json`（`ConfigManager`，旧版 `config.json` 首启自动迁移），默认配置见 `benchscope/constants.py::DEFAULT_CONFIG`。

---

## 1. General

### 1.1 Language 面板

- 语言选择：English / 中文（`a-select`，立即生效 + 持久化 `locale`）。
- 切换后全局文案实时切换（`setLocale`）。

### 1.2 Cache Paths 面板（缓存路径，1.0.6 重构为 9 目录体系）

数据根目录 `data_dir` + 8 个功能子目录，**子目录未自定义时跟随 `data_dir`**（联动解析）：

| 项 | 配置键 | 默认值 | 说明 |
| --- | --- | --- | --- |
| Data | `data_dir` | `~/.benchscope` | **数据根目录**（服务端数据持久化根），修改后需重启服务并可迁移数据 |
| Perf | `perfs_dir` | `~/.benchscope/perfs` | 性能测试任务目录（run_dir），有运行中任务时锁定 |
| Eval | `evals_dir` | `~/.benchscope/evals` | 精度测试任务目录（run_dir），有运行中任务时锁定 |
| Analysis | `analysis_dir` | `~/.benchscope/analysys` | 数据分析目录（联动 Datas / 缓存） |
| Logs | `logs_dir` | `~/.benchscope/logs` | 日志目录：`runtime_年月日.log` + 任务终端输出（`perf\|eval_runID_月日时分秒.log`） |
| Sessions | `sessions_dir` | `~/.benchscope/sessions` | 会话缓存目录 |
| Models | `models_dir` | `~/.benchscope/models` | 模型下载缓存目录（联动 Settings/Models） |
| Datasets | `datasets_dir` | `~/.benchscope/datasets` | 数据集下载缓存目录（联动 Settings/Datasets，内置数据集缓存到 `datasets_dir/{id}/`） |
| Plugins | `plugins_dir` | `~/.benchscope/plugins` | 插件安装加载目录（联动 Settings/Plugins，v5.0） |

**交互（行内编辑）**：
- 点击目录值 → 变为输入框 + 保存按钮；`Enter` 保存、失焦取消；保存成功**静默持久化**（无 toast）。
- 目录不存在显示红色「Missing」标签；后端 `ConfigManager` 对路径做 `expanduser` + `resolve`。
- **Perf / Eval 目录在存在运行中任务时锁定**（`locked`）：面板标题显示「运行中锁定」橙色标签，点击值弹警告通知（后端 409 兜底校验）。
- 修改 **Data 根目录** → 确认重启 → 确认是否迁移数据 → `POST /api/config/restart`（`migrate: true/false`）；迁移时 WebSocket 监听 `migration` 进度事件（进度 Modal + spinner）。

---

## 2.5 Datasets（内置数据集面板，1.0.6 新增）

- 数据源：`GET /api/config/datasets`（`benchscope/configs/datasets.yaml` 定义 + 缓存状态）
- 内置数据集：ShareGPT（ModelScope）/ Alpaca / GSM8K / Dolly（HF）
- 卡片内容：名称 + 缓存状态（已缓存/未缓存）、描述、**访问链接**（新窗口）、**下载命令**（可复制）、**下载按钮**
- 下载：`POST /api/config/datasets/download`（`{id}`）→ 缓存到 `datasets_dir/{id}/`（默认 `~/.benchscope/datasets`）；modelscope 源按文件大小降序选数据文件（排除 `dataset_infos.json` 元数据）
- 约束：huggingface 源在部分网络环境不可达时下载失败（返回 502）；下载为同步阻塞（大文件耗时较长）

---

## 2. Envs（环境配置面板）

- 面板标题：**Envs**；标题右侧显示**环境状态**徽标：🟢 在线（含模型数 `N models`）/ 🔴 离线（来自 `config.status`，`/api/config/status` 轮询 + WebSocket 广播）。
- 内容三行：**Framework**（vLLM / SGLang 单选）、**Base URL**（默认显示 `http://127.0.0.1:8000`）、**API Key**（**可不填**，placeholder 提示 optional）。
- **编辑/保存模式**：
  - 显示状态：输入框**禁用**，footer 右侧显示 `Edit` 按钮
  - 点击 `Edit` → 进入编辑：输入框可编辑，按钮变为 `Save`
  - 点击 `Save` → 持久化 `framework` + `api`（base_url / api_key / extra_headers）→ toast「配置已保存」→ 退出编辑 → 刷新状态徽标
- **Test Connection**：`POST /api/config/test-connection` 探测 `{base_url}/v1/models`；成功提示「连接成功」并刷新状态，失败提示错误信息。
- 约束：Framework 单选必选其一；Base URL 无格式强校验；API Key 可为空；阈值等其余配置项不在此面板。

---

## 3. Models（内置模型下载宫格）

- 标题：**内置模型**（Built-in Models），提示「点击模型卡片查看详情」。
- **宫格**：6 个内置模型卡片（数据源 `web/src/data/modelCatalog.js`）：
  - DeepSeek-V3 / DeepSeek-R1 / Qwen2.5-72B-Instruct / Llama-3.1-70B-Instruct / GLM-4-9B / InternLM2.5-7B
  - 卡片内容：品牌色字母 LOGO（`short`）、模型名称、双语简介（随界面语言切换，`intro.zh/en`）
- **详情面板**（右侧 `a-drawer`，440px）：
  - LOGO、名称、机构（org）、简介
  - **支持的数据精度**（precision tags：如 BF16 / FP8 / W8A8 / AWQ / GPTQ / INT4）
  - **访问链接**（homepage，新窗口打开）
  - **下载命令**（download，可复制 `a-typography-text copyable`）
  - footer 右侧 **部署按钮**：功能暂未实现，点击 toast「功能待实现」
- 约束：模型目录为静态内置数据；部署功能待实现。

---

## 4. Plugins

- 占位页：标题「插件」+ 描述「插件系统即将推出」+ 空状态（`a-empty`）。
- v5.0 预留，无功能逻辑。

---

## 5. 全局约束

| 项 | 约束 |
| --- | --- |
| 配置持久化 | 目录变更经 `GET/POST /api/config/dirs` 写入 `settings.json`（旧版 `config.json` 首启自动迁移）；其余配置经 `PATCH/POST /api/config`；路径类支持 `~` 展开 |
| i18n | 全量中英双语键（`check-i18n` 保证 en/zh 键集合一致、无重复键） |
| 主题 | 使用 antd 变量（`var(--ant-color-*)`），亮/暗主题自适应 |
| 面板样式 | 均为 `size="small"` 卡片，标签 12px，与 Dashboard 面板字体保持一致 |
| 语言切换 | 立即生效并持久化；默认英文 |

## 6. 相关文档约定

> **约定**：后续对 Settings 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。
