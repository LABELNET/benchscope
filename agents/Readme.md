# 项目 Harness 约定 — benchscope

> **文档状态**：本项目（benchscope）的**项目级 harness 约定**——AI / 开发者在项目中应如何工作
> **定位**：`agents/` 目录下的文档用于**减小切换 agents（AI 助手）与模型带来的项目影响**——
> 换任何模型接手，都按同一套约定产出一致、可追溯的结果。
> **关联**：[agents/Harness.md](./Harness.md)（通用 harness 规范）· [docs/Readme.md](../docs/Readme.md)（文档体系 + 文档更新约定）· [docs/rules/](../docs/rules/)（架构/开发/设计/软件）

---

## 1. 本目录职责

| 文档 | 职责 |
| --- | --- |
| [agents/Readme.md](./Readme.md)（本文件） | **项目 harness 约定**：benchscope 特有的工作方式、维护约定、入口总纲 |
| [agents/Harness.md](./Harness.md) | **通用 harness 规范**：Harness Coding 方法论（有规划、有测试、有反馈），模型/项目无关 |
| [agents/Memory.md](./Memory.md) | **项目记忆**：项目速查 + 全部强制约定 + 恢复上下文清单；切换模型时优先读 |

**为什么需要**：模型（AI 助手）会切换，模型能力/风格不同。把"怎么在这个项目里干活"固化为约定，
使切换模型后产出**风格一致、约束一致、可追溯**，避免每个模型各写各的。

---

## 2. 通用规范入口

动手前**先读通用 harness 规范**：[agents/Harness.md](./Harness.md)——
**有规划（Plan）→ 有测试（Test）→ 有反馈（Feedback）** 的闭环工作法。
本文件是该项目规范在 **benchscope 的具体落地**（项目特有约定）。

---

## 3. 项目强制约定（切换任何模型都须遵守）

### 3.1 动手前

1. **读规范**：先读 `agents/Harness.md`、`docs/rules/`（Development / Architecture / Software / Design）、对应页面 `docs/prds/<页面>.md`。
2. **定位影响面**：确认改动涉及哪些文件、页面、文档、测试。
3. **列计划**：多步任务先建 todo（todo_write），按步骤推进。

### 3.2 写代码时

4. **最小改动**：只改与需求相关部分，不顺手重构无关代码；优先精准编辑（`replace_in_file`），避免整文件重写。
5. **命名规范**：技能 `bs-<模块>-<目标>`；技能说明文档 `<BsXxxYyy>.md`；版本 `x.y.z`（见 [skills/Readme.md](../skills/Readme.md)）。
6. **i18n 双语**：任何面向用户的文案，中英（`web/src/i18n/en.js` / `zh.js`）必须同步新增，禁止只加一种语言。

### 3.3 改完后

7. **文档同步（强制）**：按 [docs/Readme.md](../docs/Readme.md) 的「文档更新约定」同步对应文档（页面→prds、版本→versions、架构/依赖→rules、技能→docs/skills）。
8. **测试（强制）**：后端改 → `tests/api/`；前端页面改 → `tests/webui/`；跑**增量测试**（见 §4.1）。
9. **不自动 commit / push（强制）**：每个任务默认只改动 + 汇报，提交与推送需**用户明确指令**。
10. **git 提交规范（强制）**：提交描述一律**英文、简短**（Conventional Commits：`feat:`/`fix:`/`docs:`/`refactor:`/`test:` 前缀），禁止中文或冗长。

---

## 4. 项目工程约定

### 4.1 测试约定

- mock / 仿真代码唯一归属 `mocks/`，`tests/` 不携带 mock。
- **增量测试**（推荐）：只跑涉及变更功能的测试。
  - 前端页面：`BS_TEST_URL=http://127.0.0.1:18081 BS_MOCK_URL=http://127.0.0.1:8001 PYTHONPATH=$PWD python3 -m pytest tests/webui/test_ui.py -k "<功能关键词>"`
  - 后端：`pytest tests/api/test_<模块>.py`
- 仅大规模重构 / 发版前才全量 `./tests/run_tests.sh`。

### 4.2 版本与迭代

- 当前版本单一来源：`benchscope/__init__.py __version__`。
- 未特别说明版本号时，变更默认归当前版本，追加到 `docs/versions/VERSION_x_y_z.md` 迭代记录；仅明确「迭代下一个版本」才新建版本文档并升版本号。

### 4.3 发布规则

- **补丁（仅 Z 更新）** → 不推 PyPI，只推 GitHub tag + release；
- **主/次（X.Y 更新）** → 推 PyPI + GitHub tag + release。
- Release 说明 = **AI 总结的功能清单**（先英文后中文），**不搬迭代记录**；发布前写入 `VERSION_x_y_z.md` 的「版本功能清单（Release Notes）」区块。
- 发布后须同步 docs 状态（VERSION 置「已发布」+ Readme 版本表 + Roadmap）并提交。

### 4.4 技能约定

- 技能有版本，每次更新自动递增；更新内容多建议加大版本号，并发版本包到本地 `dist/`。
- 技能开发完须同步 `docs/skills/<BsXxxYyy>.md` 说明与变更内容。
- 服务提供 `GET /api/skills/{id}/download` 下载技能版本包。

---

## 5. 切换模型的「交接清单」

换一个 AI 助手 / 新开发者接手时，按此确认上下文就绪：

- [ ] 已读 `agents/Memory.md`（项目记忆：速查 + 全部强制约定）——**优先读**
- [ ] 已读 `agents/Harness.md`（通用规范）+ `agents/Readme.md`（本约定）
- [ ] 已读 `docs/rules/` 全套（Development / Architecture / Software / Design）
- [ ] 已读当前版本 `docs/versions/VERSION_x_y_z.md`（迭代记录 + TODO）
- [ ] 已读目标页面 `docs/prds/<页面>.md`
- [ ] 已知当前版本号（`benchscope/__init__.py`）与开发模式（`./scripts/dev.sh`）
- [ ] 已知测试约定（增量 vs 全量）与 mock 来源（`mocks/`）
- [ ] 已知「不自动 commit/push」+「英文简短提交」约定
- [ ] 已知文档同步映射（页面/版本/架构/技能）
