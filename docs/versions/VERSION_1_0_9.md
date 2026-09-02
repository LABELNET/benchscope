# VERSION 1.0.9 — 版本修订记录

> **版本**：1.0.9  
> **状态**：开发中（In Development）  
> **发布时间**：待定  
> **文档状态**：当前开发版本——**未特别说明版本号时，项目内容所有变更均迭代在此版本**（显示 `v1.0.9-dev`），按时间顺序追加到本文档；仅当明确「迭代下一个版本」才切换  
> **目录**：页面级行为细则见 `docs/prds/`；版本路线见 `docs/Roadmap.md`

---

## 1. 版本概述

1.0.9 为 1.0.8（独立精度测试模块 + 性能页增强）发布后的**迭代开发版本**，目标范围待规划，后续按需求/用户确认补充并在此按时间顺序记录迭代明细。

规划功能见 [docs/Roadmap.md](../Roadmap.md) 1.0.9 小节。

---

## 2. 版本规划目标（用户确认版）

（待规划）

---

## 3. 迭代记录（按时间顺序）

### 迭代 1（2026-09-01 18:47:00）：开启 1.0.9 开发

**功能概述**：

- 1.0.8 发布完成后开启下一迭代版本：版本号升至 `1.0.9.dev0`（`pyproject.toml` / `benchscope/__init__.py` / `web/package.json` 三处单一来源同步），新建本文档。
- 目标范围待规划，后续按时间顺序追加迭代明细。

**TODO 状态**：

- [x] 版本 — 升版本号至 `1.0.9.dev0`（三处统一）
- [x] 文档 — 新建 `VERSION_1_0_9.md`；`docs/Readme.md` 版本表 + `docs/Roadmap.md` 增 1.0.9
- [ ] 规划 — 1.0.9 目标范围与 TODO 清单（待补充）

---

### 迭代 2（2026-09-01 18:56:23）：开发模式分环境约定

**功能概述**：

- 新增项目级强制约定：**沙箱环境启动「沙箱开发模式」，主机环境启动「主机开发模式」**；涉及代码更新的任务执行完毕须重启对应环境开发模式。

**变更内容**：

1. **约定落地**（`agents/Memory.md` / `agents/Readme.md` / `docs/rules/Development.md`）：
   - `Memory.md` 强制约定速查表新增 **#11 开发模式分环境** + 新增 **§10 开发模式**（主机 `dev.sh` / 沙箱自起 mock+后端的两套启动、数据目录、端口与验证步骤）
   - `agents/Readme.md` §4.5 新增「开发模式（分环境启动）」约定
   - `docs/rules/Development.md` §1 头部新增分环境启动强约束
2. **背景**：沙箱为 `bwrap --unshare-pid`，看不到主进程 PID（无法 stop/kill 主环境服务）、连不上主环境 mock，故沙箱内需自起一套开发环境；两套环境独立数据目录、端口占位互不干扰。

**TODO 状态**：

- [x] 约定 — `Memory.md` #11 + §10（分环境启动、各自步骤、重启规则）
- [x] 约定 — `agents/Readme.md` §4.5 同步
- [x] 规范 — `docs/rules/Development.md` §1 分环境强约束
- [x] 迭代记录 — 本文件追加

---

### 迭代 3（2026-09-01 19:35:50）：Settings/Cache Paths 改版 —— Root Dir 即时生效 + 子目录只读

**功能概述**：

- Cache Paths 面板：**Data → Root Dir（根目录）**；改 Root Dir **无需重启服务**，以环境变量形式透传子进程；失焦即创建子目录；8 个子目录只读高亮；去掉重启/迁移流程。

**变更内容**：

1. **后端 — config.py**：
   - `update()` 的 data_dir 联动改为**全部子目录重置为新根下的默认子目录**（不再只联动"未自定义"项）
   - 启动与更新时把数据根目录同步到 `os.environ['BENCHSCOPE_DATA_DIR']`（以环境变量形式使用）
2. **后端 — benches/runner.py**：`minimal_env` 显式透传 `BENCHSCOPE_DATA_DIR` 给 bench 子进程（vllm / sglang / bench CLI）
3. **后端 — server/api_config.py**：
   - `update_cache_dirs` 去掉 `requires_restart`（改 Root Dir 不再要求重启），移除 `state.migration_source`
   - `get_cache_dirs` 子目录项加 `readonly: True`（data_dir 可编辑）；`CACHE_DIR_INFO` `data_dir` 命名 `Root Dir / 根目录`，子目录 desc 更新
4. **前端 — SettingsView.vue**：
   - Cache Paths：Root Dir 失焦（blur）/回车即保存并创建子目录，**静默无提醒**；8 个子目录只读高亮展示（`.dir-value.readonly`）
   - 移除"运行中锁定"标签、重启/迁移 Modal、`notifyLocked`/`askMigrate`/`restartWithMigrate`/迁移 WS 逻辑与相关 import/样式

**验证（增量）**：

- 后端：`tests/api/test_config.py` 全量 22 项通过，新增 3 项 —— `test_cache_dirs_root_readonly_contract`（Root Dir 可编辑、子目录 readonly、命名 Root Dir/根目录）、`test_update_data_dir_no_restart_and_subdirs_reset`（requires_restart=False + 子目录重置新根）、`test_config_update_creates_subdirs_and_sync_env`（同进程创建子目录 + 环境变量同步）
- 前端 `npm run build` 成功；`check-i18n` OK
- 实测量：改 Root Dir → `requires_restart=false`、8 子目录重置为新根、共享磁盘上子目录真实创建

**TODO 状态**：

- [x] 后端 — Root Dir 改名 / 子目录重置 / 去重启 / env 注入 + runner 透传
- [x] 前端 — Root Dir 失焦保存 + 子目录只读高亮 + 去迁移弹窗
- [x] 测试 — test_config（契约 / 重置 / 创建 / env）+ 构建
- [x] 文档 — Settings / Architecture / VERSION 同步

---

### 迭代 4（2026-09-01 22:30:44）：Settings 四类 UI 细化

**功能概述**：

- Settings 页四类细节优化：侧边栏字号缩小、Root Dir 变更加确认弹窗、子目录只读改灰字无框、Provider 模型列表化加复制图标。

**变更内容**：

1. **前端 — SettingsView.vue**
   - **侧边栏字号**：`.menu-item` 14px→**13px**、`.menu-icon` 18px→**16px**，区别于顶部主导航（14px）
   - **Cache Paths / Root Dir 变更确认**：编辑框后附加小 **Save 按钮**（`.dir-save-btn`，不使用失焦/回车自动保存）；点击 Save 或按回车时若值有变更，弹出确认弹窗（`.dir-confirm-modal`）——**确定**保存新空白路径（原数据不迁移）；**取消**不保存、恢复原路径；新增 `confirmSaveDir/doSaveDir/cancelSaveDir` 与 `dirConfirmOpen/dirConfirmTarget`
   - **Cache Paths / 子目录**：`.dir-value.readonly` 由浅蓝底+描边改**纯灰色文字、无框**
   - **Providers / 模型**：模型由横排 `a-tag` 改**纵向内部列表**（`.provider-models-list`，`panel-row column`）——一行一个、左对齐、文字 12px、每行带复制图标（`.pm-copy`，`CopyOutlined`，点击复制模型名，新增 `copyModel`）
2. **i18n — en.js / zh.js**：新增 `rootDirChangeTitle` / `rootDirChangeContent` / `copyModel`（en/zh 双语，`check-i18n` 通过）
3. **测试 — tests/webui/test_ui.py**：更新 `test_settings_providers_no_activate_with_status`（模型标签 `.provider-model-tag` → 模型列表 `.pm-item` / `.pm-copy`）；新增 `test_settings_root_dir_confirm_cancel`（取消恢复原路径）、`test_settings_root_dir_confirm_ok_saves`（确定保存，结束后恢复原根目录防污染）
4. **文档**：`docs/prds/Settings.md` §1.2 / §2 / §9 同步更新

**验证（增量）**：

- 前端 `npm run build` 成功；`check-i18n` OK；`py_compile test_ui.py` 通过
- （本沙箱缺 pytest/playwright/Chromium，WebUI 测试未在本机执行；API 后端不受前端改动影响，构建产物已在开发环境 8080 验证可达）
- **沙箱 500 根因与修复**：沙箱内 `~/.benchscope`（Home 目录）不可写，Root Dir 确认保存触发 `save()` 写 `settings.json` 时 `PermissionError` → 500。已按沙箱开发模式约定将后端以 `BENCHSCOPE_DATA_DIR=<workspace>/.dev-data` 重启（数据根落在可写工作区内），`POST /api/config/dirs` 实测返回 200 + 8 子目录重置新根，500 消除。

**TODO 状态**：

- [x] 前端 — 侧边栏字号 / Root Dir 确认弹窗 / 子目录灰字 / Provider 模型列表 + 复制
- [x] i18n — 新增 rootDirChange* / copyModel（en/zh）
- [x] 测试 — test_ui 更新与新增
- [x] 文档 — Settings / VERSION 同步

---

### 迭代 5（2026-09-01 23:37:30）：Bench Engines 卡片边框按来源标色

**功能概述**：

- Settings → Bench Engines 每个引擎卡片边框加色：**内置引擎蓝色、用户上传自定义引擎紫色**。

**变更内容**：

1. **后端 — benchs.py**：`engine_summary` 新增 `origin` 字段（`builtin` / `custom`），依 `BUILTIN_ENGINE_IDS`（随包内置引擎 id 集：benchscope / vllm-0.23 / sglang-0.5.10 / native-hf / mock）判定；上传新增的引擎 id 不在集内 → `custom`
2. **前端 — SettingsView.vue**：`.bench-card` 依 `eng.origin` 附加 `.bench-origin-builtin`（蓝，`--ant-color-primary`）/ `.bench-origin-custom`（紫，`--ant-color-purple`）边框类
3. **文档**：`docs/prds/Settings.md` §5.2 同步

**验证（增量）**：

- `py_compile benchs.py` 通过；`npm run build` 成功
- 实测 `GET /api/benchs`：现有 5 引擎均返回 `origin=builtin`（定制引擎经 Upload 导入后为 `custom`）
- 前端构建产物已含两条边框规则，dev 后端（重启加载新代码）8080 可达

**TODO 状态**：

- [x] 后端 — engine_summary 加 origin（builtin/custom）
- [x] 前端 — 引擎卡片边框蓝/紫
- [x] 文档 — Settings / VERSION 同步

---

### 迭代 6（2026-09-01 23:45:12）：Performance 默认卡片对齐 Accuracy + Provider 模型改回绿色标签

**功能概述**：

- Performance 默认页三张介绍卡片样式与 Accuracy 默认页一致，图标补充渐变背景色；
- Settings → Providers 卡片模型由「一行一个列表」改回「绿色标签框 + 复制小图标」。

**变更内容**：

1. **前端 — PerformanceView.vue**：`feature-card` 图标按序号附加 `fi-${idx % 4}` 渐变底色类（蓝/绿/橙/紫，对齐 Accuracy 的 `.fi-0..3`）；卡片标题/描述样式同步 Accuracy（标题 14px/600、描述次级色 2 行截断）
2. **前端 — SettingsView.vue**：Provider 模型行改回**绿色标签框**（`a-tag color="green"` `.provider-model-tag`，可换行），标签内带**复制小图标**（`.tag-copy`，点击复制模型名）；移除上一版的 `.provider-models-list` / `.pm-item` / `.pm-copy` 列表样式
3. **测试 — tests/webui/test_ui.py**：`test_settings_providers_no_activate_with_status` 改回断言 `.provider-model-tag` / `.tag-copy`
4. **文档**：`docs/prds/Settings.md` §2、`docs/prds/Performance.md` §0.1 同步

**验证（增量）**：

- `npm run build` 成功；`check-i18n` OK；`py_compile test_ui.py` 通过
- 实测 dev 8080：Performance 构建产物含 `.fi-0..3` 渐变类、Settings 构建产物含 `.tag-copy` 样式，均 HTTP 200 可达

**TODO 状态**：

- [x] 前端 — Performance 三卡图标背景色 + 卡片样式对齐 Accuracy
- [x] 前端 — Provider 模型改回绿色标签 + 复制图标
- [x] 测试 — test_ui 更新
- [x] 文档 — Settings / Performance / VERSION 同步

---

### 迭代 7（2026-09-02 17:07:47）：Sessions 对话采样参数 + Markdown 渲染升级

**功能概述**：

- Sessions 顶部性能栏新增**对话采样参数** top_k / temperature / top_p（随发送请求携带，覆盖 quality 映射）；
- 前端 Markdown 渲染由自实现解析升级为 **marked + DOMPurify**（支持 GFM 表格 / 标题 / 引用等，XSS 净化）；
- 配套 UI 细化：输入栏下拉统一样式、发送/停止改圆形图标按钮、会话气泡与侧栏样式优化。

**变更内容**：

1. **后端**：
   - `benchscope/server/api_sessions.py`：`ChatRequest` 新增可选 `top_k` / `temperature` / `top_p`
   - `benchscope/session_manager.py`：`stream_chat` 透传三参数到 payload；显式 `temperature` 优先于 quality 映射（high 0.9 / medium 0.5 / low 0.2），`top_k>0` / `top_p` 非空时写入（扩展字段，缺失/不支持忽略）
2. **前端 — web/src/views/SessionsView.vue**：
   - 顶部性能栏新增三个 `a-input-number` 采样参数输入（top_k 1–200 / temp 0–2 / top_p 0–1），localStorage 记忆（`benchscope_chat_top_k` / `benchscope_chat_temperature` / `benchscope_chat_top_p`），随发送请求体携带
   - `renderMarkdown` 改用 `marked.parse` + `DOMPurify.sanitize`；代码块经 `wrapCodeBlocks` 包装（语言标签 + Copy 按钮），Copy 用事件委托 `onDocClick`（v-html 动态插入，避免内联 onclick 被净化），`onBeforeUnmount` 移除监听
   - UI：输入栏 Provider/Model/Quality 下拉统一灰色小字样式；发送/停止改圆形小图标按钮（蓝圆白箭头 / 白色方块）；会话气泡渐变、侧栏浅色化等
   - 依赖新增：`marked ^18` + `dompurify ^3.4`（`web/package.json` + `package-lock.json`）
3. **测试**：`tests/api/test_sessions.py` 新增 `test_chat_with_sampling_params`（携带三参数走 SSE 流式并通过 mock）

**验证（增量）**：

- 后端 `tests/api/test_sessions.py` 增量运行通过（SSE 对话 + 采样参数；mock 流式约 16KB 回复、逐块 0.015s，单次对话约 45s 完成）
- 前端 `npm run build` 成功；`check:i18n` OK（采样参数名 top_k/temp/top_p 为技术参数，不新增 i18n 键）
- `npm run build` 刷新 `benchscope/webui` 构建产物（含 marked/dompurify）

**TODO 状态**：

- [x] 后端 — ChatRequest + stream_chat 透传采样参数
- [x] 前端 — 采样参数输入 + 持久化 + 随请求携带
- [x] 前端 — Markdown 渲染升级（marked + DOMPurify + 代码块 Copy 事件委托）
- [x] 测试 — test_chat_with_sampling_params
- [x] 文档 — Sessions / Software / VERSION 同步

---

### 迭代 8（2026-09-02 18:16:21）：Sessions 侧栏与会话项体验细化

**功能概述**：

- Sessions 侧栏会话项升级：每项显示**标题 + 修改时间**，末尾新增**三点菜单**（重命名 / 删除）；新建按钮图标改为**加号**；
- 会话项前置小图标在该会话**通讯中**切换为**三个点滚动动画**（表示正在沟通）；
- 代码块**统一黑底白字、绿色高亮**样式。

**变更内容**：

1. **后端 — 会话重命名 API**：
   - `benchscope/session_manager.py`：新增 `SessionManager.update_title`（更新标题 + 刷新 `updated_at` + 持久化）
   - `benchscope/server/api_sessions.py`：新增 `RenameRequest` 与 `PATCH /api/sessions/{session_id}/title`（未知会话 404，返回 `{ok, session}`）
2. **前端 — web/src/views/SessionsView.vue**：
   - 新建会话按钮图标 `SmileOutlined` → **`PlusOutlined`（加号）**
   - 会话项布局改为：前置小图标 + `session-main`（标题 `session-name` + 修改时间 `session-time`，`formatModTime` 格式化）+ 末尾三点 `MoreOutlined`（`a-dropdown` → 重命名 / 删除菜单）
   - 重命名弹框 `a-modal`（`renameOpen/renameValue/renaming/renameTargetId`，`confirmRename` 调 `api.renameSession` 后刷新列表）
   - 通讯动画：新增 `streamingId`（`sendMessage` 置为当前会话、`finally` 清空）；会话项图标 `streamingId === s.session_id` 时渲染 `.session-typing` 三个点并 `@keyframes sessionDotRoll` 起伏滚动
   - 代码块样式改**黑底白字绿高亮**：`.code-block` 背景 `#0d1117`、正文 `#e6edf3`、语言标签 / Copy hover 用绿 `#3fb950`、`.inline-code` 黑底绿字
   - 移除旧的 hover `CloseOutlined` 删除图标（删除改入三点菜单）
3. **前端 API — web/src/api/index.js**：新增 `renameSession(id, title)`
4. **i18n — en.js / zh.js**：新增 `sessionRename` / `sessionRenamePlaceholder`（双语，`check-i18n` 通过）
5. **测试**：
   - `tests/api/test_sessions.py`：新增 `test_rename_session`（创建 → 重命名 → 列表读取新标题 → 未知会话 404）
   - `tests/webui/test_ui.py`：新增 `test_sessions_rename_modal`（三点菜单 → 重命名弹框 → 保存后列表标题更新）

**验证（增量）**：

- 后端 `tests/api/test_sessions.py` 增量运行（含新 rename 用例，SSE 对话用例因 mock 默认 16KB 回复、逐块 0.015s 较慢）
- 实测 `PATCH /api/sessions/{id}/title`：返回新标题 + 刷新 `updated_at`；未知会话 404
- 前端 `npm run build` 成功；`check:i18n` OK；`py_compile test_ui.py` 通过
- （本沙箱缺 playwright/Chromium，WebUI 测试未本机执行；API 后端不受前端改动影响）

**TODO 状态**：

- [x] 后端 — update_title + PATCH title API
- [x] 前端 — 加号按钮 / 会话项时间 + 三点菜单（重命名 / 删除）/ 通讯三点滚动 / 代码黑底绿字
- [x] i18n — sessionRename*（en/zh）
- [x] 测试 — test_rename_session + test_sessions_rename_modal
- [x] 文档 — Sessions / VERSION 同步

---

### 迭代 9（2026-09-02 19:00:36）：Sessions 会话日志落盘 + 清空居中弹窗 + 采样参数右对齐

**功能概述**：

- Sessions 对话记录**落盘为日志文件**到 `logs_dir/sessions/<id>.log`（此前只在 `sessions/*.json` 缓存，日志目录无文件）；
- 「清空会话」由 popconfirm 改为**页面居中确认弹窗**；
- 顶部采样参数 top_k / temperature / top_p：宽度足够时**右对齐**，宽度不足时**换行**。

**变更内容**：

1. **后端 — session_manager.py（会话日志落盘）**：
   - 新增 `SessionManager.persist_log(session)`：把会话以可读 transcript 写到 `logs_dir/sessions/<id>.log`（标题 / ID / 模型 / Provider / 创建 / 更新时间 + 逐条 `[时间戳] role` + `[thinking]` + 正文）
   - 在 `create_session`、`add_message`、`update_perf`、`update_title` 处调用 `persist_log`
   - `delete_session` 同步删除对应 `.log`；`clear_all` 清空 `logs_dir/sessions/*.log`
2. **前端 — web/src/views/SessionsView.vue**：
   - **清空居中弹窗**：`clear-all` 按钮改为 `@click="clearOpen = true"` 打开居中 `a-modal`（`centered`、`ok-danger`，内容含 `WarningOutlined` 警告图标 + `clearConfirm` 文案），去掉原 `a-popconfirm`；`clearAllSessions` 成功后关闭弹窗
   - **采样参数布局**：`.chat-header` 改 `display:flex; flex-wrap:wrap; align-items:center`；`.perf-bar` `flex:1 1 auto`；`.chat-params` `margin-left:auto; justify-content:flex-end` —— 宽度足够参数右对齐同排，宽度不足换行仍靠右
   - 新增 `clearOpen` ref；新增 i18n 键 `clear`
   - 弹窗/菜单类为 teleport 到 body 的样式用 `:global()`（`.clear-modal-content` / `.clear-warn-icon` / `.menu-icon` / `.menu-danger`）
3. **i18n — en.js / zh.js**：新增 `clear`（Clear / 清空，双语，`check-i18n` 通过）

**验证（增量）**：

- 前置单测（同一进程、同命名空间）：`create_session` → `add_message` → `persist_log` 生成 `logs/sessions/<id>.log`；`update_title` 刷新；`delete_session` 删除日志，均符合预期
- 沙箱后端实际 HTTP 走查（创建会话/重命名/删除）：日志随会话增删同步
- 前端 `npm run build` 成功；`check:i18n` OK
- 后端 `tests/api/test_sessions.py` 增量运行（含 rename 用例；SSE 对话用例因 mock 16KB 回复较慢）

**TODO 状态**：

- [x] 后端 — persist_log + delete/clear 同步日志
- [x] 前端 — 清空居中弹窗 / 采样参数右对齐换行
- [x] i18n — clear（en/zh）
- [x] 验证 — 日志落盘单测 + 构建 + 会话 API 测试
- [x] 文档 — Sessions / VERSION 同步

---

### 迭代 10（2026-09-02 19:35:41）：Sessions 代码块语法高亮（highlight.js + 主题）

**功能概述**：

- 对话区 Markdown 代码块由「纯黑底」升级为 **highlight.js 语法着色 + 暗色主题**，按语言高亮关键字 / 字符串 / 注释等。

**变更内容**：

1. **依赖 — web/package.json + package-lock.json**：新增 `highlight.js ^11.12.0`
2. **前端 — web/src/views/SessionsView.vue**：
   - 按需引入 `highlight.js/lib/core` 并注册常用语言（javascript / typescript / python / json / bash / xml / css / sql / java / c / cpp / go / rust / yaml / markdown / plaintext）+ 引入暗色主题 `highlight.js/styles/atom-one-dark.css`
   - 自定义 `marked.Renderer().code`（marked v18 现为单 token 参数 `{text, lang, escaped}`）：`highlightCode(code, lang)` 按语言高亮，未识别自动 `highlightAuto`，失败回退 `escapePlain`；输出 `<pre><code class="language-x hljs">…</code></pre>`
   - `wrapCodeBlocks` 正则改为 `<pre><code([^>]*)>…`，从开标签提取 `language-(\w+)` 作语言标签（兼容 `language-x hljs` 与仅 `hljs`）
   - CSS：`.code-block pre code.hljs` 去掉主题自带底色/内边距、沿用黑底 `#0d1117`，保留语法配色；`SessionsView` 分块含主题 CSS
   - 高亮 `span class="hljs-*"` 经 `DOMPurify.sanitize` 保留（默认允许 span/class）
3. **文档**：`docs/rules/Software.md` §3 前端依赖 + `docs/prds/Sessions.md` §2 代码高亮小节

**验证（增量）**：

- node 端到端模拟（marked + hljs + wrapCodeBlocks）：python/js 代码块输出 `hljs-keyword` / `hljs-string` / `hljs-number` span 且语言标签正确，无语言代码块降级为 `code`，行内代码不受影响，`<` 等正常转义
- 构建产物：`SessionsView-*.js` 分块体积约 177kB（含 hljs core + 语言 + 主题），`SessionsView-*.css` 含 `.hljs-*` 主题规则
- 前端 `npm run build` 成功；`check:i18n` OK（无新增 i18n 键）
- host 8080 已服务最新构建（最新 `index-*.js` + `SessionsView-*.js` 分块 HTTP 200）

**TODO 状态**：

- [x] 依赖 — highlight.js 引入 + 注册常用语言 + 暗色主题
- [x] 前端 — marked 自定义 code renderer 高亮 + wrapCodeBlocks 适配 + CSS 主题覆盖
- [x] 验证 — node 端到端 + 构建
- [x] 文档 — Software / Sessions / VERSION 同步

---

### 迭代 11（2026-09-02 22:49:28）：Sessions 代码块黑底 + 行号 + 字体优化

**功能概述**：

- 代码块改用**纯黑背景**，**增加行号侧栏**，并整体优化代码等宽字体（字号/行高/缩进）。

**变更内容**：

1. **前端 — web/src/views/SessionsView.vue**：
   - **行号**：`wrapCodeBlocks` 新增 `.code-body`（flex：左侧 `.code-gutter` + 右侧 `<pre>`）；按 hljs 高亮输出中换行数（1:1 保留源码换行）统计总行数，为每行生成 `<span>n</span>` 行号；横向滚动仅作用于代码区，行号侧栏固定
   - **纯黑背景**：`.code-block` 背景 `#0a0a0a`、header `#151515`、gutter `#0d0d0d` + 右侧分隔线 `#262626`；行号置灰 `#555`
   - **字体优化**：代码统一 `JetBrains Mono / Fira Code / SF Mono / SFMono-Regular / Cascadia Code / Consolas / Liberty Mono / monospace`（无则回退系统等宽），`font-size 13px`、`line-height 1.6`、`tab-size 4`、`font-variant-ligatures:none`；`.code-lang` / `.copy-btn` 同步小字号加字距；行内 `.inline-code` 同一字体栈
2. **文档**：`docs/prds/Sessions.md` §2 代码样式/语法高亮小节同步（黑底、行号、字体）

**验证（增量）**：

- node 端到端：3 行 python 块 → `.code-gutter` 生成 `<span>1</span><span>2</span><span>3</span>`，`code-body` 结构 + hljs 高亮 span 均保留
- 构建产物 `SessionsView-*.css` 含 `code-gutter` / `code-body` / `#0a0a0a` / `JetBrains Mono` 规则
- 前端 `npm run build` 成功；`check:i18n` OK；host 8080 已服务最新构建

**TODO 状态**：

- [x] 前端 — 行号侧栏 + 纯黑底 + 代码字体优化
- [x] 验证 — node 端到端 + 构建 + host 8080
- [x] 文档 — Sessions / VERSION 同步

---

### 迭代 12（2026-09-02 23:29:03）：Sessions 代码块行号逐行对齐 + 弱化 Header

**功能概述**：

- 修复「行号不在每行」：从「独立行号侧栏」改为**每行一个 flex 行（行号 + 代码）**，保证行号与代码严格逐行对齐（多行字符串跨行 span 亦正确）。
- 弱化「Copy 按钮 / 语言提示突兀」：Header 极简、语言标签置灰小字、Copy 默认隐藏仅悬停显示。

**变更内容**：

1. **前端 — web/src/views/SessionsView.vue**：
   - 新增 `splitCodeLines(html)`：把 hljs 高亮 HTML 按 `\n` 拆行，遇跨行 span 在本行末 `</span>` 闭合、下一行重开，保证每行标签闭合且高亮不丢
   - `mdRenderer.code` 直接在 renderer 内生成完整 `.code-block`（不再经 `wrapCodeBlocks`）：按行输出 `<div class="code-line"><span class="code-ln">N</span><span class="code-lc">…高亮…</span></div>`；`wrapCodeBlocks` 移除、`renderMarkdown` 不再二次包装
   - `onDocClick` 复制改为拼接各 `.code-lc` 的 `textContent`（浏览器自动解码实体，含多行 span），不包含行号
   - CSS：`.code-line` flex 行（`.code-ln` 定宽 44px 右对齐置灰 `/ `.code-lc` `white-space:pre`）；`.code-body` `overflow-x:auto` 横向滚动；Header 极简（官方背景 `#0e0e0e`、`code-lang` 置灰 `#6b6b6b` 小字、`.copy-btn` `opacity:0` 悬停 `.code-block:hover` 显示）
2. **文档**：`docs/prds/Sessions.md` §2 代码样式/语法高亮小节同步

**验证（增量）**：

- node 端到端：6 行 python（含 `"""` 多行字符串跨行高亮 span）→ 生成 6 行 `.code-line`，每行行号+代码齐全、跨行 span 闭合/重开；拼接 `.code-lc` textContent 还原 === 源码
- 构建产物 `SessionsView-*.css` 含 `code-line` / `code-ln` / `code-lc` / `copy-btn` 规则；`npm run build` 成功；`check:i18n` OK
- host 8080 已服务最新构建

**TODO 状态**：

- [x] 前端 — splitCodeLines 逐行结构 + renderer 内生成 + onDocClick 改拼接 + CSS 逐行 flex / Header 弱化
- [x] 验证 — node 端到端（含多行 span）+ 构建 + host 8080
- [x] 文档 — Sessions / VERSION 同步

---

### 迭代 13（2026-09-02 23:43:48）：Sessions 代码块去行号 + 更小更紧凑字体

**功能概述**：

- 对话代码块**移除行号**，只展示代码；代码字体调**比正文更小、更紧凑**。

**变更内容**：

1. **前端 — web/src/views/SessionsView.vue**：
   - 移除 `splitCodeLines` 与逐行 `.code-line` 结构；`mdRenderer.code` 简化为直接输出 `<div class="code-block"><header><pre><code>高亮 HTML</code></pre></div>`（无行号）
   - `onDocClick` 复制改回读取 `<pre>` 的 `textContent`
   - CSS：删除 `.code-line/.code-ln/.code-lc/.code-lines/.code-body` 规则；`.code-block pre/code` 代码字体定为 **12.5px / line-height 1.4 / tab-size 4**（正文为 14px/1.75，代码更小更紧凑），代码区 `padding 8px 14px`
2. **文档**：`docs/prds/Sessions.md` §2 代码样式/语法高亮小节同步（无行号、紧凑小号字体）

**验证（增量）**：

- node 端到端：python 块输出简洁 `<pre><code>`（含 hljs span、无行号、无 code-line 结构），行内代码不受影响
- 构建产物 `SessionsView-*.css` 含 `.code-block` / `12.5px` / `line-height:1.4`，不含 `code-line/code-ln/code-gutter`
- `npm run build` 成功；`check:i18n` OK；host 8080 已服务最新构建

**TODO 状态**：

- [x] 前端 — 去行号 + renderer 简化 + onDocClick 改回 pre + 紧凑字体 CSS
- [x] 验证 — node + 构建 + host 8080
- [x] 文档 — Sessions / VERSION 同步

---

## 4. TODO 清单

（1.0.9 待办，按规划补充后逐项勾选）

---

## 5. 相关文档

- 页面级功能与约束：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings / Datas / TopBar）
- 架构 / 方案 / 设计 / 开发规范：`docs/rules/`（Architecture / Software / Design / Development / BenchEngine / BenchCore / BenchUpstream / AccuracyEngine）
- 版本路线：`docs/Roadmap.md`
