# benchscope Settings 页面 — 功能与约束说明

> **版本**：v1.0.6  
> **最后更新**：2026-08-27  
> **文档状态**：Settings 页面五个侧边栏（General / Environment / Models / Datasets / Plugins）的功能与约束条件说明  
> **关联文档**：[Performance.md](./Performance.md) · [Dashboard.md](./Dashboard.md)

---

## 0. 总览

Settings 页面左侧 5 个侧边栏：

| 侧边栏 | 图标 | 内容 |
| --- | --- | --- |
| General | ⚙️ Setting | 2 个面板：Language、Cache Paths（9 目录配置，双语标签） |
| Environment | 🖥️ Desktop | 1 个运行环境面板（环境配置 + 状态 + 编辑/保存/测试连接） |
| Models | 🗄️ Database | 模型厂商目录（见 3）：按 国内/国外 分组的厂商列表 + 模型列表 + 详情抽屉 |
| Datasets | ☁️ CloudDownload | 内置数据集下载面板（见 4）：左侧分类 + 右侧行式列表 |
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
- **双语标签**（1.0.6）：目录项名称与描述使用双语字段（`label_zh/label_en`、`desc_zh/desc_en`），随界面语言实时切换（`GET /api/config/dirs` 返回，后端 `CACHE_DIR_INFO` 定义）。

---

## 2. Environment（环境配置面板）

- 面板标题：**Envs**；标题右侧显示**环境状态**徽标：🟢 在线（含模型数 `N models`）/ 🔴 离线（来自 `config.status`，`/api/config/status` 轮询 + WebSocket 广播）。
- 内容两行：**Base URL**（OpenAI 兼容接口，默认显示 `http://127.0.0.1:8000`）、**API Key**（**可不填**，placeholder 提示 optional）。
  > **1.0.7 变更：移除 Framework（vLLM / SGLang 单选）**。框架不再在此处选择，
  > 而是由「Performance → 创建任务」所选**测试引擎**决定（见 §5）：引擎的 `framework`
  > 字段用于生成对应原生命令，`PerfCreateView` 与 `test_manager.build_command_lines()`
  > 均优先取引擎的 `framework`。
- **编辑/保存模式**：
  - 显示状态：输入框**禁用**，footer 右侧显示 `Edit` 按钮
  - 点击 `Edit` → 进入编辑：输入框可编辑，按钮变为 `Save`
  - 点击 `Save` → 持久化 `api`（base_url / api_key / extra_headers）→ toast「配置已保存」→ 退出编辑 → 刷新状态徽标
- **Test Connection**：`POST /api/config/test-connection` 探测 `{base_url}/v1/models`；成功提示「连接成功」并刷新状态，失败提示错误信息。
- 约束：Base URL 无格式强校验；API Key 可为空；阈值等其余配置项不在此面板。

---

## 3. Models（模型厂商目录，1.0.6 新增）

- 标题：**内置模型**（Built-in Models），副标题说明「点击厂商查看其模型，点击模型名查看详情」。
- 数据源：`GET /api/config/model-catalog`（`benchscope/configs/models.yaml`，按 国内 / 国外 分组；数据参考 https://recipes.vllm.ai 的 Providers 菜单）。
- **左侧分组副侧边栏**（210px）：
  - 两个分组：**国内**（Domestic，18 厂商）/ **国外**（International，23 厂商），分组标题可点击折叠/展开（▸ 箭头旋转），标题右侧显示厂商数。
  - 分组内厂商列表：点击选中高亮；默认全部展开并选中第一个厂商。
- **右侧厂商模型列表**：
  - 顶部：厂商名 + **Homepage 链接**（新窗口，空则不显示）。
  - 模型列表：每行一个模型；**与内置模型目录 `web/src/data/modelCatalog.js` 匹配时**（名称/id 忽略大小写）显示蓝色「详情」标签且整行可点击。
  - 无模型的厂商显示 `a-empty`（暂无模型）；未选中厂商时提示「请选择厂商」。
- **详情抽屉**（`a-drawer` 440px，复用旧模型目录数据 `modelCatalog.js`）：
  - LOGO、名称、机构（org）、简介（双语 `intro.zh/en`）
  - **支持的数据精度**（precision tags：如 BF16 / FP8 / W8A8 / AWQ / GPTQ / INT4）
  - **访问链接**（homepage，新窗口打开）
  - **下载命令**（download，可复制 `a-typography-text copyable`）
  - footer 右侧 **部署按钮**：功能暂未实现，点击 toast「功能待实现」
- 约束：厂商目录为静态内置数据（models.yaml）；厂商明细模型（models 列表）与模型目录（modelCatalog.js）为两套数据，仅在名称匹配时打通详情；部署功能待实现。

---

## 4. Datasets（内置数据集面板，1.0.6 新增）

- 数据源：`GET /api/config/datasets`（`benchscope/configs/datasets.yaml` 定义 + 分类 + 缓存状态）
- 布局：**左侧分类侧边栏 + 右侧行式列表**（与 Models 相同的 `catalog-layout` 结构）
  - 左侧分类：**全部**（All，含全部数据集数）+ `datasets.yaml::categories` 定义的各分类（双语名称 `name_zh/name_en`，右侧显示该分类数据集数）；点击过滤右侧列表。
- 右侧行式列表：每行一个数据集，包含：
  - 名称 + 缓存状态标签（绿色「已缓存」/ 默认「未缓存」）
  - 描述（description）
  - **访问链接**（新窗口）+ **下载命令**（可复制 `a-typography-text code copyable`）
  - 右侧**下载按钮**（`POST /api/config/datasets/download` `{id}` → 缓存到 `datasets_dir/{id}/`，默认 `~/.benchscope/datasets`）
- 约束：huggingface 源在部分网络环境不可达时下载失败（返回 502）；下载为同步阻塞（大文件耗时较长）；下载成功后刷新列表以更新缓存状态。

---

## 5. Bench Engines（测试引擎管理，1.0.6 新增 / 1.0.7 重构）

> 数据源：`GET /api/benchs`（`benchscope/configs/benchs.yaml`，yaml 驱动、用户可扩展）

### 5.1 界面布局（1.0.7 重构）

- **整页即引擎列表**：左侧菜单切换后，右侧内容区为引擎卡片列表（`.bench-card`），
  **列表区独立可滑动**（`.bench-list-scroll`），顶部操作栏固定不随滚动
- **右上角三个文字按钮**（`.bench-actions .bench-text-btn`），点击后在**中间弹框**展示内容：

| 按钮 | 弹框内容 | 说明 |
| --- | --- | --- |
| **Create Engine** | 制作教程 + 上游链接 + 可复制 AI 提示词 | 纯教程与提示词，**不再展示 Engine Definition（引擎定义原文）** |
| **Upload Engine** | 拖拽/点选上传区 + 校验结果 | 上传 `.yaml` / `.yml` 引擎定义，或 `.tar.gz` / `.tgz` 技能包 |
| **Engine Comparison** | 引擎对比表（维度 × 引擎） | 原内联对比表移入弹框 |

**弹框规范（1.0.7）**：

| 项 | 规范 |
| --- | --- |
| 宽度 | 统一为 **1/3 浏览器宽度**（`.bench-modal { width: 33.33vw !important; min-width: 420px; max-width: 720px }`）；不再使用各弹框的内联 `width` 属性 |
| Header | **标题 + 提示文案**（`#title` 插槽 → `.bench-modal-title` + `.bench-modal-hint`） |
| Footer | **文字操作按钮**（`type="link"`，右对齐于 `.bench-modal-footer`） |
| 底部间距 | 所有页面（`.app-content-layout`）底部统一保留 **18px** |

各弹框 footer 操作：Create → 复制提示词 / 取消；Upload → 校验并导入 / 取消；Comparison → 取消。

> 注意：ant-design-vue 的 `<a-modal class="bench-modal">` 会把 class 落在 **`.ant-modal` 本身**（不是外层包裹），
> 因此宽度选择器为 `.bench-modal` 而非 `.bench-modal .ant-modal`。

**列表可滚动（1.0.7 修复）**：`.bench-list-scroll` 的父级是 `a-spin` 的
`.ant-spin-nested-loading` / `.ant-spin-container`，必须为其补充
`flex: 1; min-height: 0; display: flex; flex-direction: column`，否则滚动容器拿不到限高而无法滚动。
⚠️ 两个容器都是 `a-spin` 的**内部元素（非根元素）**，在 `<style scoped>` 下不带本组件 data-v 属性，
规则必须写成 **`:deep(.ant-spin-nested-loading)`** —— 普通后代选择器编译后带 `[data-v-xxx]`
匹配不到，样式等于没写（这正是首次修复无效的原因）。

**弹框样式作用域（1.0.7）**：Modal 被 Teleport 到 body，`.bench-modal` 等弹框元素同样
不带 data-v 属性，**弹框相关规则一律用 `:global()`**（`:deep()` 对插槽内容同样拿不到 scopeId）；
相关测试容差须收紧（宽度 ±20px）并限定 `:visible`（关闭后的 Modal 仍留在 DOM）。

### 5.2 引擎卡片内容

- 名称 + 默认标记 + kind 标签（`builtin` 紫 / `vllm`、`sglang` 青）+ 环境状态标签（`Ready` / `Not Satisfied`）
- 版本、介绍文案、亮点列表（`highlights`）
- 环境要求明细（`requires`）：要求版本 / 已安装 / OK-FAIL；不满足时展示安装提示
- **Bench CLI（自研引擎）无 `requires`**，展示「无框架环境依赖，安装即用」

### 5.3 Create Engine 弹框

- 制作步骤教程（4 步）：确认目标版本 → 拉取上游源码核实参数 → 复制提示词给 AI → 用 Upload Engine 导入
- 上游仓库链接（vLLM / SGLang，含 bench 入口与命令）
- 可复制 AI 提示词（内容由 `GET /api/benchs/authoring` 生成）

### 5.4 Upload Engine 弹框

- 支持 `.yaml` / `.yml`（引擎定义原文）与 `.tar.gz` / `.tgz`（技能包），单文件上限 20MB
- 技能包内自动识别：引擎定义（含 `engines` 段）、参数说明（`bench-params.yaml`）
- 合并策略：引擎 `id` 已存在 → 更新，不存在 → 追加；对比表按 `dimension` 去重合并；参数段按 `params_key` 覆盖合并
- **校验通过才写入**（与手动导入同一套校验）；未选择文件时「校验并导入」按钮禁用
- 结果展示：新增引擎 / 更新引擎 / 逐项校验结果
- 接口：`POST /api/benchs/upload`（multipart）
- 安全：解压时拒绝 `../` 路径穿越与绝对路径条目

### 5.5 引擎命名与文案（1.0.7）

**命名**：自研引擎名称统一为 **Bench CLI**（原「BenchScope Bench（自研）」），界面、文档、对比表保持一致。
其**实际命令**为 **`benchscope perf`**（原 `benchscope bench`），即界面显示「Bench CLI」、
执行的是 `benchscope perf` 子命令。

**文案双语**：引擎定义（`configs/benchs.yaml`）的文案**默认为英文**，中文放在 `*_zh` 字段
（沿用仓库既有的 `name_zh` / `label_zh` / `desc_zh` 约定），界面按当前语言选择，缺失回退英文：

| 字段 | 中文字段 | 说明 |
| --- | --- | --- |
| `name` | `name_zh` | 引擎名（Bench CLI 等名称语言中立，可只写一次） |
| `description` | `description_zh` | 引擎介绍 |
| `highlights` | `highlights_zh` | 亮点列表 |
| `comparison[].dimension` | `dimension_zh` | 对比表维度名 |
| `comparison[].values` | `values_zh` | 对比表各引擎取值 |

后端 `engine_summary()` 透传 `name_zh` / `description_zh` / `highlights_zh`（`name_zh` 缺失时回退 `name`）；
前端由 `benchName()` / `benchDesc()` / `benchHighlights()` / `compTitle()` / `compValue()` 按语言取值。

**Highlights 规范**：只列「**简洁特性**」与「**版本支持情况**」，**不描述实现方式**；
条目 ≤6 条、每条 ≤80 字符，最后一条以 `Version support: ...` 说明版本支持范围。

> ⚠️ **YAML 陷阱**：列表项若含半角 `: `（如 `Version support: vLLM 0.23.x only`）会被解析为
> **mapping 而非字符串**，必须加引号；中文全角「：」无此问题。

---

## 6. Plugins

- 占位页：标题「插件」+ 描述「插件系统即将推出」+ 空状态（`a-empty`）。
- v5.0 预留，无功能逻辑。

---

## 7. 全局约束

| 项 | 约束 |
| --- | --- |
| 配置持久化 | 目录变更经 `GET/POST /api/config/dirs` 写入 `settings.json`（旧版 `config.json` 首启自动迁移）；其余配置经 `PATCH/POST /api/config`；路径类支持 `~` 展开 |
| i18n | 全量中英双语键（`check-i18n` 保证 en/zh 键集合一致、无重复键） |
| 主题 | 使用 antd 变量（`var(--ant-color-*)`），亮/暗主题自适应 |
| 面板样式 | 均为 `size="small"` 卡片，标签 12px，与 Dashboard 面板字体保持一致 |
| 语言切换 | 立即生效并持久化；默认英文 |
| 布局 | 左侧一级菜单（General/Environment/Models/Datasets/Plugins/Bench Engines）+ 右侧内容区；Models/Datasets 在内容区内再嵌「副侧边栏 + 内容」结构 |
| Bench Engines 布局 | 整页为可滑动引擎列表 + 右上角文字按钮（操作入口）；对比表与上传/教程均为弹框，不内联占用页面 |

## 8. 相关文档约定

> **约定**：后续对 Settings 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。
