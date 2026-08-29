# benchscope Settings 页面 — 功能与约束说明

> **版本**：v1.0.7  
> **最后更新**：2026-08-30 23:00:00  
> **文档状态**：Settings 页面七个侧边栏（General / Providers / Models / Datasets / Bench Engines / Skills / Plugins）的功能与约束条件说明  
> **关联文档**：[Performance.md](./Performance.md) · [Dashboard.md](./Dashboard.md)

---

## 0. 总览

Settings 页面左侧 7 个侧边栏：

| 侧边栏 | 图标（1.0.7 更新） | 内容 |
| --- | --- | --- |
| General | Control | 2 个面板：Language、Cache Paths（9 目录配置，双语标签） |
| Providers | CloudServer | 多个推理服务提供方面板（Provider 配置 + 在线状态 + 模型 + 编辑/删除） |
| Models | Robot | 模型厂商目录（见 3）：按 国内/国外 分组的厂商列表 + 模型面板列表 |
| Datasets | Database | 内置数据集下载面板（见 4）：左侧分类 + 右侧数据集面板列表 |
| Bench Engines | Experiment | 测试引擎管理（见 5）：引擎面板列表 + 每引擎 Mock 开关 + 右上角文字按钮弹框 |
| Skills | Book | 内置技能清单（见 6）：技能面板（版本/描述/特性/使用/提示词） |
| Plugins | Api | 占位（v5.0 预留） |

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

## 2. Providers（推理服务提供方，1.0.7 去 Activate 改造）

- 菜单项与面板头均为 **Providers**（不再显示 Envs 字样）。
- **多 Provider**：可添加多个推理服务提供方（OpenAI 兼容接口）；**每个 Provider 一个面板**，
  面板 header 显示 **Provider Name** + **在线状态标记**（`.env-status ok` 绿 / `bad` 红，探测所得）。
  > **1.0.7 变更**：移除 Framework 单选——框架由「Performance → 创建任务」所选**测试引擎**决定。
- **Add Provider 弹窗**：`Provider Name` **必填**（为空时 Save 禁用），Base URL / API Key 选填。
- **每个 Provider 面板**：
  - 字段：Provider Name / Base URL / API Key（`Edit` → 编辑 → `Save`，逐面板独立编辑态）
  - **模型状态行**：探测该 Provider 的 `{base_url}/v1/models` → 展示在线状态（在线绿 `a-badge success` / 离线红 `error`）与模型数
  - **模型行**：列出该 Provider 可用模型（`a-tag .provider-model-tag`）；无模型显示「无模型」（`.no-model`）
  - **Delete**：删除该 Provider；新增 / 编辑 / 删除后自动重新探测状态与模型
  - 原 **Activate 按钮与 Active 标签已移除**（1.0.7）：不再需要激活
- **使用处自行选择 Provider（1.0.7）**：
  - 「Performance → 创建任务」Base 面板：选择 Provider（默认第一个）→ 联动模型与在线状态 → payload 携带 `provider_id` + `api`（该 Provider 的 base_url/api_key 内联），任务执行按 `payload.api` 优先（`task_manager._run_one`）
  - 「Sessions」会话输入栏：Provider 下拉（联动模型）→ chat 请求携带 `provider_id` → `session_manager.stream_chat` 按 Provider 解析 API 配置调用
- **接口**：`GET/POST /api/config/providers`、`PUT/DELETE /api/config/providers/{id}`；
  `POST /api/config/providers/{id}/activate` 后端保留（兼容旧客户端），前端不再调用。
- **迁移**：旧配置（仅 `api`）启动时自动生成名为 `Default` 的 Provider（`config.py::_migrate_providers`）。
- 约束：Provider Name 非空；Base URL 无格式强校验；API Key 可为空。

---

## 3. Models（模型厂商目录，1.0.6 新增 / 1.0.7 面板化 / 1.0.7 顶部分类）

- 标题：**内置模型**（Built-in Models），副标题说明「点击厂商查看其模型」。
- 数据源：`GET /api/config/model-catalog`（`benchscope/configs/models.yaml`，按 国内 / 国外 分组；数据参考 https://recipes.vllm.ai 的 Providers 菜单）。
- **顶部分类信息**（1.0.7 布局调整：原左侧副侧边栏移除，分类上移到内容区顶部 `.cat-bar`）：
  - 两个厂商分组：**国内**（Domestic，18 厂商）/ **国外**（International，23 厂商）；组标签 + 组内厂商 **chip**（`.cat-chip`）横向排列、自动换行。
  - 厂商 chip 点击选中高亮（`.active`）；默认选中第一个厂商。
  - 分组折叠已移除（1.0.7，原 `collapsedGroups` / `toggleGroup` / `isCollapsed` 清理）。
  - **分类面板全宽（1.0.7）**：`.cat-bar` 宽度与右侧页面宽度一致（Models/Datasets 的 `tab-content` 移除 `narrow` 约束），下方内容列表**靠左显示**（卡片 720px 面板宽，`.panel-list` 用 `align-items: flex-start`），滚动条在页面最右侧。
- **模型面板列表**（1.0.7 面板化 + 三分区，`.model-panel-card`）：
  - 顶部：厂商名 + **Homepage 链接**（新窗口，空则不显示）。
  - 每个模型一个**面板**（`a-card size="small"`，宽度 = 面板宽度，与 General 面板一致）：
    - **Header**（`#title`/`#extra`）：左侧模型名称（`.pm-name`）+ 右侧**详情操作高亮链接**（`.mp-action`，蓝字，跳转 `modelCatalog.js::homepage`；**仅目录匹配时显示**）
    - **内容区** `.card-body`（`matchCatalog(m)` 命中时展示，未命中显示「暂无目录信息」灰字）：
      - 简介（`intro.zh/en`，随语言切换）
      - **支持的数据精度**（`.mp-tags` 蓝色 tags：BF16 / FP8 / W8A8 / AWQ / GPTQ / INT4）
      - **访问链接**（`.mp-link`，新窗口打开）
    - **footer 区** `.card-footer`（浅底色 + 上边框）：**下载命令**（`.mp-cmd`，可复制 `a-typography-text copyable`）
- 内容多时**面板列表内部滚动**（`.panel-list`，滚动条在页面最右侧）。
- 约束：厂商目录为静态内置数据（models.yaml）；厂商明细模型（models 列表）与模型目录（modelCatalog.js）为两套数据，仅在名称/id 匹配时展示完整内容；**详情抽屉已移除**（1.0.7，详情内容直接内联在面板中）。

---

## 4. Datasets（内置数据集面板，1.0.6 新增 / 1.0.7 面板化 / 1.0.7 顶部分类）

- 数据源：`GET /api/config/datasets`（`benchscope/configs/datasets.yaml` 定义 + 分类 + 缓存状态）
- **顶部分类信息**（1.0.7 布局调整：原左侧分类侧边栏移除，分类上移到内容区顶部 `.cat-bar`）：
  - **全部**（All，含全部数据集数）+ `datasets.yaml::categories` 定义的各分类（双语名称 `name_zh/name_en`，chip 右侧显示该分类数据集数）；chip 点击过滤下方列表。
  - **分类面板全宽（1.0.7）**：`.cat-bar` 宽度与右侧页面宽度一致（`tab-content` 移除 `narrow`），下方内容列表**靠左显示**（卡片 720px 面板宽，滚动条最右）。
- 每个数据集一个**面板**（`.ds-panel-card`，`a-card size="small"`，宽度 = 面板宽度，与 Models 面板一致）：
  - **Header**（`#title`/`#extra`）：左侧数据集名称（`.ds-name`）+ 缓存状态标签（绿色「已缓存」/ 默认「未缓存」）+ 右侧**下载按钮**（`.ant-card-head .ant-btn`，`POST /api/config/datasets/download` `{id}` → 缓存到 `datasets_dir/{id}/`，默认 `~/.benchscope/datasets`；下载中按钮 loading）
  - **内容区** `.card-body`：描述（`.ds-desc`）+ **访问链接**（`.ds-link`，新窗口）
  - **footer 区** `.card-footer`（浅底色 + 上边框）：**下载命令**（`.ds-cmd`，可复制 `a-typography-text code copyable`）
- 内容多时**面板列表内部滚动**（`.panel-list`）。
- 约束：huggingface 源在部分网络环境不可达时下载失败（返回 502）；下载为同步阻塞（大文件耗时较长）；下载成功后刷新列表以更新缓存状态。

---

## 5. Bench Engines（测试引擎管理，1.0.6 新增 / 1.0.7 重构）

> 数据源：`GET /api/benchs`（`benchscope/configs/benchs.yaml`，yaml 驱动、用户可扩展）

### 5.1 界面布局（1.0.7 重构）

- **整页即引擎列表**：左侧菜单切换后，右侧内容区为引擎卡片列表（`.bench-card`），
  **列表区独立可滑动**（`.bench-list-scroll`），顶部操作栏固定不随滚动
- **顶部操作栏全宽（1.0.7）**：`.bench-tab` 不再受 `narrow`（720px）约束，标题 + 三个文字按钮宽度与右侧页面宽度一致；
  **引擎卡片列表靠左为面板宽度**（`.bench-list { max-width: 720px; margin: 0 auto 20px 0 }`，**靠左**），
  **滚动条保持在页面最右侧**（列表滚动容器全宽，内部内容靠左）。
- **引擎卡片面板化（1.0.7，header + footer）**：`.bench-card` 为面板形式（圆角 + 溢出裁剪）：
  - **header**（`.bench-head`）：引擎名 + 标识（默认/kind/环境状态 tag）+ 版本号
  - **body**：描述（`.bench-desc`）+ 亮点列表（`.bench-highlights`）
  - **footer**（`.bench-foot`，浅底色 + 上边框）：环境要求与校验结果（`requires` 明细 / `bench-env-none`）
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

- **面板宽度统一**（1.0.7）：引擎卡片为 `a-card size="small"`，宽度与 General / Models / Datasets 面板一致（`.bench-list { max-width: 720px; margin: 0 auto }`）
- **Header 左右分栏**（1.0.7，`justify-content: space-between`）：
  - **左侧 title**：引擎名称（Bench CLI / vLLM 0.23 / SGLang 0.5.10）+ 标识（默认标记 + kind 标签 `builtin` 紫 / `vllm`、`sglang` 青）
  - **右侧**：版本号（`.bench-version`，如 `v0.23`）
- 内容区：环境状态标签（`Ready` / `Not Satisfied`）、介绍文案、亮点列表（`highlights`）
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

## 6. Skills（内置技能清单，1.0.7 新增）

- 数据源：`GET /api/skills`（`benchscope/server/api_skills.py`，扫描 `skills/*/SKILL.md` 的 front-matter），
  字段：`name / version / description / features(≥2) / usage(≥2) / prompt / download({path,name})`。
- **页面可滚动（1.0.7）**：`.tab-content` 移除 `narrow`，`.skill-list` 为全宽滚动容器（`flex:1 + overflow-y:auto`，滚动条在页面最右侧），技能卡片**靠左**显示（`align-items:flex-start`，`max-width:720px`）。`.settings-content.content-fill > .tab-content` 为 flex column（`display:flex`），确保 `.fill-spin` 高度链打通、`.skill-list` 正确限高滚动。
- 每个技能一个**面板**（`.skill-card`，`a-card size="small"`，样式与 Bench Engines 面板一致）：
  - **Header 左侧**：技能名称（`.skill-name`）+ id 标签（紫色 `a-tag`）；**header 无高亮颜色**（`.ant-card-head` 背景 `transparent`）
  - **Header 右侧**：版本号（`.skill-version`，如 `v1.0.0`）
  - **内容区**（描述/特性/使用/提示词**均随语言切换**：`description_zh`/`features_zh`/`usage_zh`/`prompt_zh` 或英文）：
    - 功能描述（`.skill-desc`）
    - **功能特性**（`.skill-ul` 无序列表，来自 `features`）
    - **使用说明**（`.skill-ol` 有序列表，来自 `usage`；1.0.7 优化第一项为「下载技能：下载技能包（.tar.gz），导入其他支持 skills 的 agents 平台即可使用」）
    - **提示词**（`.skill-prompt`，`pre` 预格式化，`max-height: 220px` 超长滚动，可全选复制；1.0.7 为**精简操作提示词**——引导用户输入框架/版本/阈值等参数，如「你正在使用 bs-engine-create 技能…请让用户输入框架及其版本后继续」，不再展示 SKILL.md 全文）
  - **footer**：**仅两个文字按钮**（`.skill-footer` 内 `a-button type="link"`，右对齐）：
    - **Download**（`.skillDownload`，随语言切换：en=Download / zh=下载技能 → 优先下载 `download_url` 技能包 tar.gz，回退下载 SKILL.md）
    - **Copy Prompt**（`.skillCopyPrompt`，随语言切换：en=Copy Prompt / zh=复制提示词 → 复制 `prompt` 到剪贴板，成功/失败 toast）
- 前端 `web/src/api/index.js::getSkills()/downloadSkill()`；i18n 键：`skills/skillsDesc/skillFeatures/skillUsage/skillPrompt/skillDownload/skillCopyPrompt/skillCopySuccess/skillCopyFail/skillDownloaded/modelNoCatalog`。
- 约束：技能清单为内置只读数据（skills 目录）；下载优先取服务端发版版本包（`GET /api/skills/{id}/download`）。

---

## 7. 引擎 Mock 开关（Settings → Bench Engines，1.0.7 替代 Debug）

> Debug 开发模式面板（1.0.7 已移除）；mock 环境和数据**跟随 engine**，改为在 Bench Engines
> 每个引擎卡片上的独立 **Mock 开关**（默认关闭）。

- **开关位置**：每个引擎卡片 footer（`.bench-foot`）底部 `.bench-mock`，一行 `a-switch`，
  默认关闭；开启后该引擎用**仿真数据与运行环境**（FAKE 模式），关闭后走真实环境校验。
- **状态标记**：卡片 Header 与创建任务 Step1 均显示 **Mock / Real** 状态 tag：
  - **Mock（橙色）**：开关开启，环境校验**直接判定通过**（跳过真实框架依赖），创建任务走 mocks/ 仿真；
  - **Real（默认）**：开关关闭，正常环境校验与真实运行。
- **配置存储**：`config.engine_mocks`（`{engine_id: bool}`，`benchscope/constants.py::DEFAULT_CONFIG`），
  `POST /api/benchs/{engine_id}/mock` 切换（整体 `set`，支持移除 key），`POST /api/config` 亦可整体写入。
- **后端执行**（`task_manager._run_one`）：`runner.fake = payload.use_mock_env OR config.engine_mocks[engine_id]`
  ——按 **engine_id** 判定（动态注册的自定义引擎同样支持独立 mock 开关）。
- **创建页联动**（1.0.7）：「Performance → 创建任务」选择引擎时调用 `/env-check`，mock 开启的引擎
  显示 **Mock** 状态并环境通过（进入 Step2）；**不显示** Use Mock Environment 勾选。
- 测试：`tests/api/test_benchs.py::test_engine_mock_switch`、`test_benchs_yaml`（mock 状态）、
  `tests/api/test_tasks.py::test_native_engine_engine_mocks_config`（engine_mocks 触发 FAKE）、
  `tests/webui/test_ui.py::test_settings_benches_mock_switch`、`test_config.py::test_engine_mocks_config_update`。

---

## 8. Plugins

- 占位页：标题「插件」+ 描述「插件系统即将推出」+ 空状态（`a-empty`）。
- v5.0 预留，无功能逻辑。

---

## 9. 全局约束

| 项 | 约束 |
| --- | --- |
| 配置持久化 | 目录变更经 `GET/POST /api/config/dirs` 写入 `settings.json`（旧版 `config.json` 首启自动迁移）；其余配置经 `PATCH/POST /api/config`；路径类支持 `~` 展开 |
| i18n | 全量中英双语键（`check-i18n` 保证 en/zh 键集合一致、无重复键） |
| 主题 | 使用 antd 变量（`var(--ant-color-*)`），亮/暗主题自适应 |
| 面板样式 | 均为 `size="small"` 卡片，标签 12px，与 Dashboard 面板字体保持一致 |
| 语言切换 | 立即生效并持久化；默认英文 |
| 布局 | 左侧一级菜单（General/Providers/Models/Datasets/Bench Engines/Skills/Plugins）+ 右侧内容区；Models/Datasets/Bench Engines/Skills 四个栏位均用 `.content-fill`（副侧边栏贴右主导航 + 内容区内部滚动，padding `22px 16px 18px`） |
| Bench Engines 布局 | 整页为可滑动引擎列表 + 右上角文字按钮（操作入口）；对比表与上传/教程均为弹框，不内联占用页面 |

## 10. 相关文档约定

> **约定**：后续对 Settings 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。
