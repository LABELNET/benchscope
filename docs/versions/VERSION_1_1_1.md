# VERSION 1.1.1 — 版本修订记录

> **版本**：1.1.1  
> **状态**：已发布（Released）  
> **发布时间**：2026-09-05  
> **文档状态**：1.1.1 修复发布版本（发布规则虽为补丁 Z 变更，按用户指示特殊处理推送 PyPI）。后续开发内容迭代到下一版本  
> **目录**：页面级行为细则见 `docs/prds/`；版本路线见 `docs/Roadmap.md`

---

## 1. 版本概述

1.1.1 为 1.1.0（性能实时面板 / 单请求快照 / Dashboard Overview 重构 / Sessions 体验）发布后的**迭代开发版本**，目标范围待规划，后续按需求/用户确认补充并在此按时间顺序记录迭代明细。

规划功能见 [docs/Roadmap.md](../Roadmap.md) 1.1.1 小节。

---

## 2. 版本规划目标（用户确认版）

（待规划）

---

## 3. 迭代记录（按时间顺序）

### 迭代 1（2026-09-05 19:02:58）：Provider 缺失 id 修复（回归：未知 Provider: undefined）

**功能概述**：

- 历史遗留的 Provider（如旧版「Default」，仅 `api` 时迁移而来）可能缺少 `id` 字段，导致性能创建任务无法选择该 Provider、Settings 编辑报「未知 Provider: undefined」。本次在配置加载时的 Provider 迁移中**自动补齐缺失的稳定 id**。

**变更内容**：

1. `benchscope/config.py` `_migrate_providers()`：已有 providers 时不再直接返回，而是**遍历回填缺失的 `id`**（由名称 slug 生成稳定 id，如 Default → `provider_default`，冲突追加数字后缀保证唯一），并随后持久化；`active_provider` 缺失/失效时回退到首个有效 id。
2. 新增 `_provider_id_from_name(name)` 静态方法生成稳定 id。

**影响**：

- Performance 创建任务 Provider 下拉可正常选择 Default（前端以 `p.id` 作选项 value）。
- Settings/Provider 编辑 Default 不再报「未知 Provider: undefined」（`update_provider` 能命中回填后的 id）。

**验证**：

- 手动构造含无 id Default 的旧 settings.json → `ConfigManager.load()` 后 `list_providers()` 返回 `id=provider_default` 且已持久化；`update_provider("provider_default", ...)` 编辑成功。
- 新增回归测试 `tests/api/test_config.py::test_providers_backfill_missing_id`；`py_compile` OK。

**TODO 状态**：

- [x] 配置文件加载补齐历史 Provider 缺失 id
- [x] 回归测试
- [x] 重启 dev 验证当前数据已回填

---

### 迭代 2（2026-09-05 19:20:00）：发布包补齐 configs 与 skills（修复 Settings 空内容）

**功能概述**：

- 修复 `pip install` 的正式包中 Settings 的 Models / Datasets / Bench Engines / Skills 均为空的问题：此前 wheel/sdist 只打包了 `webui/**/*`，未包含 `benchscope/configs/*.yaml` 与技能包，导致安装后的运行环境读不到配置与技能。

**变更内容**：

1. `pyproject.toml` `[tool.setuptools.package-data]`：`"benchscope"` 新增 `configs/*.yaml` 与 `skills/**/*`（连同原 `webui/**/*`）。
2. 技能目录由仓库根 `skills/` **迁入包内 `benchscope/skills/`**（`git mv`），随包分发。
3. `benchscope/server/api_skills.py`：`_SKILLS_DIR` 由 `parents[2]/"skills"`（仓库根）改为 `parents[1]/"skills"`（包内），开发与安装后路径一致。
4. `tests/api/test_skills.py`：`SKILLS_DIR` 同步为 `REPO_ROOT/"benchscope"/"skills"`。
5. 文档同步：`docs/Readme.md`、`docs/skills/Readme.md`、`docs/rules/BenchEngine.md` 中 `skills/...` 路径更新为 `benchscope/skills/...`。

**验证**：

- 重建 wheel/sdist：均包含 `benchscope/configs/*.yaml`（9 个，含 models / datasets / benchs）与 `benchscope/skills/**/*`（30 个文件）。
- dev 重启后 Settings 各接口返回数据：Models `GET /api/config/model-catalog`=2 组、Datasets `/api/config/datasets`=12、Bench Engines `/api/benchs`=5（benchscope / vllm-0.23 / sglang-0.5.10 / native-hf / mock）、Skills `/api/skills`=3。

**TODO 状态**：

- [x] package-data 增加 configs / skills
- [x] 技能目录迁入包内 + `_SKILLS_DIR` 指向包内
- [x] 测试与文档路径同步
- [x] 重建产物验证 configs/skills 已打包 + 各接口返回数据

---

### 迭代 3（2026-09-05 19:33:39）：README 图示更换 + PyPI 图片显示修复

**功能概述**：

- README 主截图由 `main-performance.png` 更换为 **`benchscope-performance.png`**；并将图片引用改为 **GitHub raw 绝对 URL**，使 PyPI 上也能正常渲染图片（此前相对路径 `asserts/*.png` 在 PyPI 无法解析显示）。

**变更内容**：

1. `README.md` / `README.zh-CN.md`：主截图改为 `benchscope-performance.png`；logo 与主截图 `<img src>` 均改为 `https://raw.githubusercontent.com/LABELNET/benchscope/main/asserts/*.png`。
2. `asserts/benchscope-performance.png`（用户提供的新截图，2838×1440）纳入版本管理（`git add`）。

**生效说明**：

- PyPI 使用上传包内 METADATA 的 long_description（即 README 内容）渲染页面；图片需为**可公开访问的 URL**。本变更后需 **commit + push**（raw.githubusercontent 由 `main` 分支提供）并**下次发布**才会在 PyPI 上刷新显示。

**验证**：

- `file` 校验新 png 为合法 PNG（2838×1440）；两个 README 均已指向 `benchscope-performance.png` + raw 绝对 URL。

**TODO 状态**：

- [x] README 主截图换为 benchscope-performance.png
- [x] 图片改用 raw 绝对 URL（PyPI 可显示）
- [x] 新 png 纳入 git

---

## 版本功能清单（Release Notes）

### Feature Highlights

- **Fix: Settings empty tabs in installed package**: the published package now ships `benchscope/configs/*.yaml` (models / datasets / benchs) and the bundled skills — Models / Datasets / Bench Engines / Skills tabs are populated after `pip install` (no repo checkout required)
- **Fix: Provider missing `id`**: legacy providers (e.g. the old "Default") without an `id` are auto-backfilled with a stable id on config load, so creating perf tasks can select Default and Settings can edit it without the "未知 Provider: undefined" error
- **Fix: PyPI images**: README switched to `benchscope-performance.png` with absolute GitHub raw URLs so screenshots and logo render on PyPI
- **Skills relocated into the package** (`benchscope/skills/`) and shipped as package data; path resolution now consistent in dev and installed environments

### 功能清单

- **修复安装包 Settings 空内容**：发布包现随包分发 `benchscope/configs/*.yaml`（models / datasets / benchs）与内置技能——`pip install` 后 Models / Datasets / Bench Engines / Skills 各栏均有条目（不再依赖源码目录）
- **修复 Provider 缺失 id**：历史无 `id` 的 Provider（如旧版 Default）在配置加载时自动回填稳定 id，性能创建任务可选 Default、Settings 可正常编辑，不再报「未知 Provider: undefined」
- **修复 PyPI 图片显示**：README 主截图换为 `benchscope-performance.png`，图片改用 GitHub raw 绝对 URL，PyPI 页面可正常渲染截图与 logo
- **技能迁入包内**（`benchscope/skills/`）并作为 package-data 分发；开发与安装后路径解析一致

---

## 4. TODO 清单

（1.1.1 待办，按规划补充后逐项勾选）

---

## 5. 相关文档

- 页面级功能与约束：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings / Datas / TopBar）
- 架构 / 方案 / 设计 / 开发规范：`docs/rules/`（Architecture / Software / Design / Development / BenchEngine / BenchCore / BenchUpstream / AccuracyEngine）
- 版本路线：`docs/Roadmap.md`
