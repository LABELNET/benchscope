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

## 4. TODO 清单

（1.0.9 待办，按规划补充后逐项勾选）

---

## 5. 相关文档

- 页面级功能与约束：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings / Datas / TopBar）
- 架构 / 方案 / 设计 / 开发规范：`docs/rules/`（Architecture / Software / Design / Development / BenchEngine / BenchCore / BenchUpstream / AccuracyEngine）
- 版本路线：`docs/Roadmap.md`
