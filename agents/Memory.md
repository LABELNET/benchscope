# 项目记忆（Project Memory）

> **文档状态**：benchscope 项目的**长期记忆与强制约定**集中地
> **用途**：切换 AI 助手（agents）/ 模型 / 新开发者接手时，**读这一份即可恢复全部上下文与约定**，
> 避免每个模型各写各的（减小模型切换带来的项目影响）。
> **最后更新**：2026-09-01
> **关联**：[Readme.md](./Readme.md)（项目 harness 约定）· [Harness.md](./Harness.md)（通用 harness 规范）·
> [docs/Readme.md](../docs/Readme.md)（文档体系 + 文档更新约定）· [docs/rules/](../docs/rules/)（架构/开发/设计/软件）

---

## 1. 项目速查

| 项 | 值 |
| --- | --- |
| 项目 | benchscope（推理性能测试 + 精度评测平台） |
| 当前版本 | `1.0.8.dev0`（单一来源 `benchscope/__init__.py __version__`） |
| 技术栈 | 后端 FastAPI + Uvicorn，前端 Vue 3 + Vite + Ant Design Vue，构建 Vite |
| 语言 | 界面中英双语（`web/src/i18n/en.js` / `zh.js`） |
| 目录 | `benchscope/`（后端）· `web/`（前端）· `tests/`（测试）· `mocks/`（仿真）· `scripts/`（脚本）· `skills/`（技能）· `docs/`（文档）· `agents/`（harness 规范与记忆） |

**关键入口**：
- CLI：`benchscope/cli.py`（`serve` / `perf` / `eval`）
- API：`benchscope/server/api_{accuracy,benchs,config,dashboard,logs,sessions,skills,tasks,test}.py`
- 文档：`docs/`（prds / versions / rules / skills）

---

## 2. 强制约定速查（最高优先级）

> 任何 AI / 开发者切换都必须遵守；违反视为不合格产出。

| # | 约定 | 说明 |
| --- | --- | --- |
| 1 | **先读规范再动手** | 读 `Harness.md` + `Readme.md` + `docs/rules/` + 目标页面 PRD |
| 2 | **定位影响面** | 列清涉及的文件、页面、文档、测试 |
| 3 | **最小改动** | 只改需求相关部分；优先精准编辑，不顺手重构无关代码 |
| 4 | **i18n 双语同步** | 面向用户文案必须同步 `en.js` + `zh.js`，禁止只加一种 |
| 5 | **文档同步（强制）** | 变更同步 `prds/` `versions/` `rules/` `skills/`（见 §3） |
| 6 | **测试（强制）** | 后端 `tests/api/`、前端 `tests/webui/`；跑**增量测试** |
| 7 | **不自动 commit / push** | 每个任务默认只改动 + 汇报，**提交/推送须用户明确指令** |
| 8 | **git 英文简短提交** | Conventional Commits（`feat:`/`fix:`/`docs:`/`refactor:`/`test:`），禁止中文或冗长 |
| 9 | **只读不改的边界** | `README.md` / `README.zh-CN.md` 以仓库最新版为准（用户自行更新，勿按历史版本修改） |
| 10 | **如实汇报** | 完成项、改动文件、验证结果、遗留问题清晰列出；失败不隐藏 |
| 11 | **开发模式分环境** | **沙箱环境启动「沙箱开发模式」、主机环境启动「主机开发模式」**：两套独立启动/数据/端口；涉及代码更新的任务执行完毕须重启对应环境的开发模式（见 §10 开发模式） |

---

## 3. 文档同步约定（强制）

| 变更类型 | 同步目标 |
| --- | --- |
| 页面功能 / 界面 / 逻辑 / 策略 / UI | `docs/prds/<页面>.md` |
| 版本功能与 todo | `docs/versions/VERSION_x_y_z.md`（迭代记录 + TODO 清单，按时间顺序追加） |
| 架构 / 方案 / 设计 / 开发规范 | `docs/rules/<对应>.md` |
| 软件依赖（增/升/删） | `docs/rules/Software.md` §2 技术栈 + §3 依赖清单 |
| 技能说明 / 变更 | `docs/skills/<BsXxxYyy>.md`（一个技能一个说明文档） |
| 主导航变更 | `docs/prds/TopBar.md` §5 |

**其他**：
- 文档间引用用**相对链接**，移动/改名后同步修正。
- 迭代记录时间必须**精确至秒**（年-月-日 时:分:秒，含 commit 号）。
- 每次文档更新刷新 `docs/Readme.md` 头部「最后更新」日期。

---

## 4. 测试约定

- mock / 仿真代码**唯一归属 `mocks/`**，`tests/` 不携带 mock。
- **增量测试**（推荐）：只跑涉及变更功能的测试。
  - 前端页面：`BS_TEST_URL=http://127.0.0.1:18081 BS_MOCK_URL=http://127.0.0.1:8001 PYTHONPATH=$PWD python3 -m pytest tests/webui/test_ui.py -k "<功能关键词>"`
  - 后端：`pytest tests/api/test_<模块>.py`
- 仅大规模重构 / 发版前才全量 `./tests/run_tests.sh`。

---

## 5. 版本与发布

- **版本单一来源**：`benchscope/__init__.py __version__`；升版同步 `pyproject.toml` + `web/package.json`。
- **迭代规则**：未特别说明版本号时，变更默认归当前版本（追加到 `VERSION_x_y_z.md`）；仅明确「迭代下一个版本」才新建。
- **发布规则**：
  - 补丁（仅 Z）→ **不推 PyPI**，只推 GitHub tag + release；
  - 主/次（X.Y）→ PyPI + tag + release。
- **Release 说明** = AI 总结的**功能清单**（**先英文后中文**），**不搬迭代记录**，写入 `VERSION_x_y_z.md` 的「版本功能清单（Release Notes）」区块。
- 发布后同步 docs 状态（VERSION 置「已发布」+ Readme 版本表 + Roadmap）并提交。

---

## 6. 技能（Skills）约定

- 技能有版本，每次更新**自动递增**；更新内容多建议加大版本号，并发版本包到本地 `dist/`。
- 命名：技能 `bs-<模块>-<目标>`，说明文档 `<BsXxxYyy>.md`。
- 技能开发完须同步 `docs/skills/<BsXxxYyy>.md` 说明与变更内容。
- 服务提供 `GET /api/skills/{id}/download` 下载技能版本包。

---

## 7. 命名规范速查

| 对象 | 模式 | 示例 |
| --- | --- | --- |
| 技能目录 / name | `bs-<模块>-<目标>` | `bs-engine-create`、`bs-perfs-concurrency` |
| 技能说明文档 | `<BsXxxYyy>.md` | `bs-engine-create` → `BsEngineCreate.md` |
| 技能版本包 | `<name>-<version>.tar.gz` | `bs-perfs-concurrency-1.0.0.tar.gz` |
| 版本号 | `x.y.z`（dev 加 `.dev0`） | `1.0.8.dev0` |

---

## 8. Harness 工作法（三要素闭环）

详见 [Harness.md](./Harness.md)：

1. **有规划（Plan）**：读规范 → 定位影响面 → 分解步骤 → 最小路径。
2. **有测试（Test）**：改动必有验证 → 增量优先 → 构建 + lint + 测试通过才算完成。
3. **有反馈（Feedback）**：结果写入项目记录（迭代/版本文档）→ 文档随代码走 → 提交语义化 → 失败如实回报。

---

## 9. 恢复上下文清单（切换模型时）

- [ ] 读 `agents/Memory.md`（本文件）→ 项目速查 + 全部强制约定
- [ ] 读 `agents/Harness.md` + `agents/Readme.md` → harness 规范与项目约定
- [ ] 读 `docs/rules/`（Development / Architecture / Software / Design）
- [ ] 读当前版本 `docs/versions/VERSION_x_y_z.md`（迭代记录 + TODO）
- [ ] 读目标页面 `docs/prds/<页面>.md`
- [ ] 开发模式：**主机环境** `./scripts/dev.sh start`（mock 8001 + 前端构建 + 后端 8080）；**沙箱环境**手动起 mock + 后端（见 §10）

---

## 10. 开发模式（分环境启动，强制）

> 约定来源（2026-09-01）：**沙箱环境启动「沙箱开发模式」，主机环境启动「主机开发模式」**；
> 两套环境**独立启动、独立数据目录、独立端口占位**，互不干扰；
> **每执行完一个涉及代码更新的任务，须重启对应环境的开发模式**以加载最新代码。

### 主机开发模式

```bash
cd /home/yuanmingzhuo/benchscope
./scripts/dev.sh start    # mock OpenAI :8001 + 前端构建 + 后端 :8080（FAKE）
./scripts/dev.sh stop     # 停止全部
./scripts/dev.sh status   # 查看状态
```

- 每 `start` 自动 `npm run build` → `benchscope/webui`；后端 `BENCHSCOPE_FAKE_BENCH=1`，数据目录默认 `~/.benchscope`。
- 适用于在有完整进程上下文的主机 shell 中启动 / 验证。

### 沙箱开发模式

> 沙箱（bwrap `--unshare-pid`）**看不到主进程的 PID，无法 stop/kill 主环境服务**；端口/网络与主环境隔离（沙箱内进程连不上主环境的 mock）。故沙箱内**自起一套**，与主环境端口错开或确认主环境未占用。

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

- 前后端用后台 job 常驻（`run_in_background`），数据目录用 `mktemp -d` 隔离，前端读取共享的 `benchscope/webui`（沙箱内 `npm run build` 会直接写入主环境可见的该目录）。
- **重启沙箱开发模式**：先停掉旧的后台 job（`job_kill`）释放端口，再按上面重起，确保加载最新代码。

### 验证

- `curl -s http://127.0.0.1:8080/api/version` 应返回当前开发版本（如 `1.0.9.dev0`）。
- 端到端：创建并启动一个自研引擎并发任务，`status=done` 且 `metrics.successful_requests>0` 即为可用。
