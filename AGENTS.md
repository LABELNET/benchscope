# AGENTS.md — benchscope AI 助手工作约定

> **本文件是 AI 编码助手（agents）在 benchscope 仓库工作的统一入口**（项目入口层），整合自 `agents/` 目录的三份文档；
> 通用方法论层见 [HARNESS-CODING.md](HARNESS-CODING.md)。
> 目标：无论切换哪个 AI 助手 / 模型，都按同一套约定产出**一致、可验证、可追溯**的结果。
> 完整细节见文末[参考文档](#参考文档)。

---

## 1. 项目速查

| 项 | 值 |
| --- | --- |
| 项目 | benchscope（大模型推理性能测试 + 精度评测平台） |
| 当前版本 | **以 `benchscope/__init__.py` 的 `__version__` 为单一来源** |
| 技术栈 | 后端 FastAPI + Uvicorn，前端 Vue 3 + Vite + Ant Design Vue，构建 Vite |
| 界面语言 | 中英双语（`web/src/i18n/en.js` / `zh.js`） |

**目录结构**：

| 目录 | 职责 |
| --- | --- |
| `benchscope/` | 后端（含 CLI、API、server） |
| `web/` | 前端（Vue 3 + Vite） |
| `tests/` | 测试（`api/` 后端、`webui/` 前端） |
| `mocks/` | mock / 仿真代码（**唯一归属地**） |
| `scripts/` | 脚本（`dev.sh` 开发模式、`release.sh` 发布） |
| `skills/` | 技能包 |
| `docs/` | 文档（`prds/` `versions/` `rules/` `skills/`） |
| `agents/` | harness 规范与项目记忆（本文件的来源） |

**关键入口**：

- CLI：`benchscope/cli.py`（`serve` / `perf` / `eval`）
- API：`benchscope/server/api_{accuracy,benchs,config,dashboard,logs,sessions,skills,tasks,test}.py`
- 文档：`docs/`（`prds/` / `versions/` / `rules/` / `skills/`）

---

## 2. 工作方法论（Harness Coding）

取代无约束的 Vibe Coding，遵循 **有规划（Plan）→ 有测试（Test）→ 有反馈（Feedback）** 闭环：

1. **有规划（Plan）**：先读规范 → 定位影响面 → 分解步骤（建 todo）→ 选最小改动路径。
2. **有测试（Test）**：改动必有验证 → 增量优先 → 构建 + lint + 测试通过才算完成；失败定位根因而非绕过。
3. **有反馈（Feedback）**：结果写入项目记录（迭代/版本文档）→ 文档随代码走 → 提交语义化 → 失败如实回报。

**通用行为准则（模型无关）**：

- **不臆造**：不编造 API、参数、文件路径；不确定先查证（读代码/文档/实测）。
- **不越界**：不改与当前任务无关的文件；需要重构先说明并获确认。
- **最小惊讶**：保持既有风格（命名、目录、语言、框架约定），不引入项目未使用的新依赖/新范式。
- **权限边界**：提交、推送、发布、删除等不可逆操作，须用户明确指令后执行。
- **如实汇报**：完成什么、改了哪些文件、验证结果、遗留问题，清晰列出。

### 2.1 通用 Coding 约规

> 项目自有约定（`docs/rules/`）优先；项目未约定的事项按以下默认约定执行。
> 完整方法层版本见 [HARNESS-CODING.md](HARNESS-CODING.md) §4。

1. **总原则**：可读性优先；单一职责；DRY；YAGNI；快速失败。
2. **命名**：表意；项目内一致（最小惊讶）；遵循语言惯例（变量 `snake_case`/`camelCase`、类 `PascalCase`、常量 `UPPER_SNAKE_CASE`、布尔量 `is`/`has`/`can` 前缀）。
3. **函数**：单函数 ≤ 50 行；参数 ≤ 5 个（超出封装为对象）；纯函数优先；边界校验；嵌套 ≤ 3 层。
4. **错误处理**：不吞异常（禁止空 catch）；错误带上下文；区分可恢复/致命；不外泄内部细节。
5. **注释**：解释"为什么"而非"什么"；公开接口必有文档；注释随代码走；TODO 带上下文。
6. **Git 提交**：Conventional Commits（`feat:`/`fix:`/`docs:`/`refactor:`/`test:`/`chore:`）；英文简短祈使句；一个提交一件事；不提交坏代码。
7. **依赖**：不擅自新增（须说明理由并确认）；单一声明源；版本锁定。
8. **测试代码**：一个用例一个行为；命名描述行为（`test_<模块>_<场景>`）；Arrange-Act-Assert；mock 隔离于生产数据。

---

## 3. 强制约定（最高优先级，任何 AI / 开发者切换都必须遵守）

> 违反任一条视为不合格产出。

| # | 约定 | 说明 |
| --- | --- | --- |
| 1 | **先读规范再动手** | 读本文件 + `agents/` 文档 + `docs/rules/` + 目标页面 PRD |
| 2 | **定位影响面** | 列清涉及的文件、页面、文档、测试 |
| 3 | **最小改动** | 只改需求相关部分；优先精准编辑，不顺手重构无关代码 |
| 4 | **i18n 双语同步** | 面向用户文案必须同步 `web/src/i18n/en.js` + `zh.js`，禁止只加一种 |
| 5 | **文档同步（强制）** | 变更同步 `prds/` `versions/` `rules/` `skills/`（见 §4） |
| 6 | **测试（强制）** | 后端 `tests/api/`、前端 `tests/webui/`；跑**增量测试** |
| 7 | **不自动 commit / push** | 每个任务默认只改动 + 汇报，**提交/推送须用户明确指令** |
| 8 | **git 英文简短提交** | Conventional Commits（`feat:`/`fix:`/`docs:`/`refactor:`/`test:`），禁止中文或冗长 |
| 9 | **只读不改的边界** | `README.md` / `README.zh-CN.md` 以仓库最新版为准（用户自行更新，勿按历史版本修改） |
| 10 | **如实汇报** | 完成项、改动文件、验证结果、遗留问题清晰列出；失败不隐藏 |
| 11 | **开发模式分环境** | 沙箱环境启动「沙箱开发模式」、主机环境启动「主机开发模式」（见 §6） |

---

## 4. 文档同步约定（强制）

| 变更类型 | 同步目标 |
| --- | --- |
| 页面功能 / 界面 / 逻辑 / 策略 / UI | `docs/prds/<页面>.md` |
| 版本功能与 todo | `docs/versions/VERSION_x_y_z.md`（迭代记录 + TODO，按时间顺序追加） |
| 架构 / 方案 / 设计 / 开发规范 | `docs/rules/<对应>.md` |
| 软件依赖（增/升/删） | `docs/rules/Software.md` §2 技术栈 + §3 依赖清单 |
| 技能说明 / 变更 | `docs/skills/<BsXxxYyy>.md`（一个技能一个说明文档） |
| 主导航变更 | `docs/prds/TopBar.md` §5 |

**其他**：

- 文档间引用用**相对链接**，移动/改名后同步修正。
- 迭代记录时间必须**精确至秒**（年-月-日 时:分:秒，含 commit 号）。
- 每次文档更新刷新 `docs/Readme.md` 头部「最后更新」日期。

---

## 5. 测试约定

- mock / 仿真代码**唯一归属 `mocks/`**，`tests/` 不携带 mock。
- **增量测试**（推荐）：只跑涉及变更功能的测试。
  - 前端页面：
    ```bash
    BS_TEST_URL=http://127.0.0.1:18081 BS_MOCK_URL=http://127.0.0.1:8001 \
      PYTHONPATH=$PWD python3 -m pytest tests/webui/test_ui.py -k "<功能关键词>"
    ```
  - 后端：
    ```bash
    pytest tests/api/test_<模块>.py
    ```
- 仅大规模重构 / 发版前才全量 `./tests/run_tests.sh`。

---

## 6. 开发模式（分环境启动，强制）

> 两套环境**独立启动、独立数据目录、独立端口占位**，互不干扰。
> **每执行完一个涉及代码更新的任务，须重启对应环境的开发模式**以加载最新代码。

### 6.1 主机开发模式

```bash
cd /home/yuanmingzhuo/benchscope
./scripts/dev.sh start    # mock OpenAI :8001 + 前端构建 + 后端 :8080（FAKE）
./scripts/dev.sh stop     # 停止全部
./scripts/dev.sh status   # 查看状态
```

- 每 `start` 自动 `npm run build` → `benchscope/webui`；后端 `BENCHSCOPE_FAKE_BENCH=1`，数据目录默认 `~/.benchscope`。
- 适用于有完整进程上下文的主机 shell。

### 6.2 沙箱开发模式

> 沙箱（bwrap `--unshare-pid`）**看不到主进程 PID，无法 stop/kill 主环境服务**；端口/网络与主环境隔离（沙箱内进程连不上主环境的 mock）。故沙箱内**自起一套**，与主环境端口错开或确认主环境未占用。

```bash
# 1) 沙箱 mock（:8001；若主环境 mock 占用可换端口）
cd /home/yuanmingzhuo/benchscope
env PYTHONPATH=$PWD python3 -m mocks.openai_server --host 127.0.0.1 --port 8001 &
# 2) 沙箱后端+前端（:8080，FAKE + 独立临时数据目录）
BENCHSCOPE_FAKE_BENCH=1 BENCHSCOPE_DATA_DIR=$(mktemp -d /tmp/bs-dev.XXXXXX) \
  env PYTHONPATH=$PWD python3 -m benchscope.cli --port 8080 --no-browser &
# 3) 把后端 api/Provider 指向 mock
curl -X POST http://127.0.0.1:8080/api/config -H "Content-Type: application/json" -d '{"api":{"base_url":"http://127.0.0.1:8001"}}'
curl -X PUT http://127.0.0.1:8080/api/config/providers/provider_default -H "Content-Type: application/json" -d '{"base_url":"http://127.0.0.1:8001"}'
```

- 前后端用后台 job 常驻（`run_in_background`），数据目录用 `mktemp -d` 隔离，前端读取共享的 `benchscope/webui`。
- **重启沙箱开发模式**：先停掉旧的后台 job（`job_kill`）释放端口，再按上面重起，确保加载最新代码。

### 6.3 验证

- `curl -s http://127.0.0.1:8080/api/version` 应返回当前开发版本。
- 端到端：创建并启动一个自研引擎并发任务，`status=done` 且 `metrics.successful_requests>0` 即为可用。

---

## 7. 版本与发布

- **版本单一来源**：`benchscope/__init__.py` 的 `__version__`；升版同步 `pyproject.toml` + `web/package.json`。
- **迭代规则**：未特别说明版本号时，变更默认归当前版本（追加到 `VERSION_x_y_z.md`）；仅明确「迭代下一个版本」才新建。
- **发布规则**：
  - 补丁（仅 Z）→ **不推 PyPI**，只推 GitHub tag + release；
  - 主/次（X.Y）→ PyPI + tag + release。
- **Release 说明** = AI 总结的**功能清单**（**先英文后中文**），**不搬迭代记录**，写入 `VERSION_x_y_z.md` 的「版本功能清单（Release Notes）」区块。
- 发布后同步 docs 状态（VERSION 置「已发布」+ Readme 版本表 + Roadmap）并提交。

---

## 8. 技能（Skills）约定

- 技能有版本，每次更新**自动递增**；更新内容多建议加大版本号，并发版本包到本地 `dist/`。
- 命名：技能 `bs-<模块>-<目标>`，说明文档 `<BsXxxYyy>.md`。
- 技能开发完须同步 `docs/skills/<BsXxxYyy>.md` 说明与变更内容。
- 服务提供 `GET /api/skills/{id}/download` 下载技能版本包。

**命名规范速查**：

| 对象 | 模式 | 示例 |
| --- | --- | --- |
| 技能目录 / name | `bs-<模块>-<目标>` | `bs-engine-create`、`bs-perfs-concurrency` |
| 技能说明文档 | `<BsXxxYyy>.md` | `bs-engine-create` → `BsEngineCreate.md` |
| 技能版本包 | `<name>-<version>.tar.gz` | `bs-perfs-concurrency-1.0.0.tar.gz` |
| 版本号 | `x.y.z`（dev 加 `.dev0`） | `1.1.1.dev0` |

---

## 9. 恢复上下文清单（切换 AI 助手 / 模型时）

接手本项目时，按此确认上下文就绪：

- [ ] 读 `AGENTS.md`（本文件）→ 项目速查 + 全部强制约定 + coding 约规
- [ ] 读 `agents/Memory.md`（项目记忆）+ `agents/Harness.md`（通用规范）+ `agents/Readme.md`（项目约定）
- [ ] 读 `docs/rules/`（Development / Architecture / Software / Design）
- [ ] 读当前版本 `docs/versions/VERSION_x_y_z.md`（迭代记录 + TODO）
- [ ] 读目标页面 `docs/prds/<页面>.md`
- [ ] 确认当前版本号（`benchscope/__init__.py`）与开发模式（`./scripts/dev.sh`）
- [ ] 确认测试约定（增量 vs 全量）与 mock 来源（`mocks/`）
- [ ] 确认「不自动 commit/push」+「英文简短提交」约定
- [ ] 确认文档同步映射（页面/版本/架构/技能）

---

## 参考文档

本文件为 `agents/` 目录的整合入口，完整细节见：

- [HARNESS-CODING.md](HARNESS-CODING.md) — **方法层（通用规范）**：Harness Coding 方法论（有规划、有测试、有反馈）+ 通用 coding 约规，模型/项目无关
- [agents/Readme.md](agents/Readme.md) — **项目 harness 约定**：benchscope 特有的工作方式、维护约定、入口总纲
- [agents/Harness.md](agents/Harness.md) — **通用规范档案**：`HARNESS-CODING.md` 的前身/源档案
- [agents/Memory.md](agents/Memory.md) — **项目记忆**：项目速查 + 全部强制约定 + 恢复上下文清单
- [docs/Readme.md](docs/Readme.md) — 文档体系 + 文档更新约定
- [docs/rules/](docs/rules/) — 架构 / 开发 / 设计 / 软件规范