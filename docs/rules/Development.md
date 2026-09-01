# 开发 / 验证 / 部署规范 — Development

> **文档状态**：benchscope 开发、验证与部署规范  
> **关联**：[Architecture.md](./Architecture.md) · [Software.md](./Software.md) · [Design.md](./Design.md)

---

## 1. 开发模式（FAKE，无需真实推理环境）

```bash
./scripts/dev.sh start      # mock OpenAI :8001 + 统一入口 :8080（FAKE bench，自动重建前端）
./scripts/dev.sh status     # 查看服务状态
./scripts/dev.sh stop       # 停止全部
```

- 每次 `start` 自动执行 `npm run build` → `benchscope/webui`（后端托管最新前端）。
- Python 解释器探测：优先 `.venv/bin/python`，但该环境缺少 `fastapi`/`uvicorn`（如指向系统 python 的残缺 venv）时自动回退 `${PYTHON:-python3}`，保证 mock 与后端可启动。
- 日志：`logs/dev/*.log`（openai / backend / build）。
- 前端热更新：`cd web && npm run dev`（:5173，proxy `/api`、`/ws` 到 :8080）。
- `mocks/` 单独运行：`python -m mocks.cli vllm bench serve ...` / `python -m mocks.openai_server --port 8001`。

## 2. 验证模式（真实推理）

```bash
BENCHSCOPE_FAKE_BENCH=1 python -m benchscope.cli --port 8080 --no-browser   # FAKE
python -m benchscope.cli --port 8081 --no-browser                            # 真实模式（无 FAKE）
```

- 真实模式：Settings → Envs 的 Base URL 指向真实服务（如 vLLM :8000），用于并发 / 阈值回归验证。
- mock 联调：Base URL 填 `http://127.0.0.1:8001`（mock OpenAI 服务）。

## 3. 质量检查

| 检查 | 命令 |
| --- | --- |
| i18n 键一致性（无重复、en/zh 一致） | `cd web && node scripts/check-i18n.js` |
| 后端语法 | `python -m py_compile benchscope/**/*.py` |
| 前端构建 | `cd web && npm run build`（产物含最新代码） |
| 功能测试（API + WebUI） | `./tests/run_tests.sh`（自动启动 mock :8001 + FAKE 服务 :18081，隔离临时数据目录；可选 `--api-only` / `--ui-only`） |

### 3.1 测试约定（强制）

- **mock 唯一归属**：mock 仿真代码只保留在 `mocks/`（`openai_server.py` / `bench_outputs.py` / `cli.py`），`tests/` 不携带任何 mock 代码。
- **每次开发新功能必须生成并执行 tests**：
  - 新增/修改**后端 API 或功能** → 在 `tests/api/` 生成对应测试用例（config / dashboard / tasks / logs / sessions / test 模块）；
  - 新增/修改**页面 / UI / 交互** → 在 `tests/webui/test_ui.py` 生成对应 Playwright 用例；
  - 提交前执行 `./tests/run_tests.sh` 全量通过（API + WebUI），允许以 `--api-only` / `--ui-only` 限定范围。
- **测试隔离**：`tests/run_tests.sh` 以 `BENCHSCOPE_DATA_DIR` 临时目录 + `BENCHSCOPE_FAKE_BENCH=1` 启动被测服务（:18081，与开发环境 :8080 隔离），测试不污染真实 `~/.benchscope` 数据。

## 4. 变更流程与文档同步

> **先读 harness 规范**：[agents/Harness.md](../../agents/Harness.md)（通用：有规划、有测试、有反馈）+ [agents/Readme.md](../../agents/Readme.md)（本项目约定）；动手前读规范、定位影响面、最小改动；任何 AI / 开发者切换均遵循同一套约定。

1. 修改代码（后端 `benchscope/` / 前端 `web/` / 脚本 `scripts/` / mock `mocks/` / 依赖 `pyproject.toml`、`web/package.json`）。
2. **文档同步（强制）**：设计/界面修改、逻辑与策略调整、UI 调整、依赖与架构变更，**必须同步更新**对应文档：
   - 页面功能与约束 → `docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings / Datas / TopBar）
   - 版本修订与 todo → `docs/versions/VERSION_1_0_7.md`（当前开发版本；新版本另建 `VERSION_x_y_z.md`）
   - 架构 / 方案 / 设计 / 开发规范 → `docs/rules/`（Architecture / Software / Design / Development）
   - **软件依赖变更（新增/升级/移除）** → 同步 `docs/rules/Software.md` §2 技术栈与 §3 依赖清单
3. **测试（强制）**：生成/更新对应 tests（API → `tests/api/`，WebUI → `tests/webui/`），运行 `check-i18n` + 构建 + `./tests/run_tests.sh` 全量通过。
4. 提交（**git 提交规范，强制**）：提交描述一律使用**英文**，**简短总结**变更（Conventional Commits 风格，如 `feat:` / `fix:` / `docs:` / `refactor:` / `test:` 前缀），如 `feat: add per-engine mock switch`。正文可补充要点，但保持简洁。禁止中文或冗长描述。
5. **不自动 commit 与 push（强制）**：**每个任务默认不做自动 `git commit` 和 `git push`**——所有提交与推送都需用户明确发出指令后才执行（如「提交」「commit」「push」「推送」等）。任务完成后仅完成代码/文档改动并汇报，等待用户指令再提交/推送。

## 5. 发布（Release checklist）

```bash
# 一键发布：升版本 → 构建 → PyPI 上传 → GitHub Release（自动提取迭代摘要）→ git tag + push
TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> ./scripts/release.sh 1.0.6
# 可选 --notes 指定 Release 说明文件；缺省自动从 docs/versions/VERSION_1_0_6.md 提取迭代摘要
```

- **发布规则（按版本号 X.Y.Z 区分）**：
  1. **仅 Z（补丁）更新**（如 `1.0.7 → 1.0.8`）：**不推送 PyPI**，只推送 **GitHub tag + Release**；
  2. **X.Y（主/次）更新**（如 `1.0.8 → 1.1.0` 或 `1.1.0 → 2.0.0`）：推送 **PyPI + GitHub tag + Release**（完整发布）。
  `scripts/release.sh` 会自动比较新旧版本的 X.Y 决定是否上传 PyPI（`NEED_PYPI`）。
- 完整发布（X.Y 变化时）= 打包推送 PyPI + 推送 GitHub Release 总结 + 推送版本 tag：
  1. **PyPI**：`python -m build` + `twine upload`（`TWINE_USERNAME=__token__` + PyPI API token）；
  2. **GitHub Release 总结（功能清单，强制规则）**：`scripts/release.sh` 自动创建（`gh release create` 或 `GITHUB_TOKEN` REST API 回退），说明默认从 `docs/versions/VERSION_x_y_z.md` 的 **「版本功能清单（Release Notes）」** 区块提取（中英双语，按功能按条总结）；**不能直接搬迭代记录**——不输出迭代标题、不带时间、不是逐迭代记录，而是**按功能归纳总结、中英文对照**。规则：
     - **功能清单由 AI 总结（release.sh 不做机械提取）**：发布前**由 AI 读取 `VERSION_x_y_z.md` 版本内容**，总结功能清单与核心功能变化，写入「版本功能清单（Release Notes）」区块，**格式为先英文清单、后中文清单**：
       `### Feature Highlights`（英文条目）+ `### 功能清单`（中文条目），每条 = `- **功能**（细节）`；
     - release.sh 只**原样读取**该区块作为 Release 说明（不提取迭代记录、不做机械处理）；缺区块时提示用 AI 总结或 `--notes` 指定；
     - 可用 `--notes <file>` 覆盖；**补丁版本不推 PyPI，但 Release 仍带功能清单照常推送**；
  3. **版本 tag**：`git tag vX.Y.Z` + `git push origin main --tags`。
- 前置：PyPI token（`TWINE_USERNAME/TWINE_PASSWORD` 或 `~/.pypirc`，仅 X.Y 变化时需要）+ GitHub 凭据（`gh auth` 或 `GITHUB_TOKEN`）。
- **发布完成后（强制）**：同步更改 docs 文件状态并提交——
  1. `docs/versions/VERSION_x_y_z.md`：状态置为「已发布（Released）」+ 发布时间；
  2. `docs/Readme.md`：§2 版本表标记该版本已发布 + 刷新头部「最后更新」日期；
  3. `docs/Roadmap.md`：该版本状态更新为已发布；
  4. **提交**：按 §4 提交规范（英文、简短，如 `docs: mark vX.Y.Z as released`）提交并推送这些 docs 变更。

## 6. 目录约定

```text
benchscope/        # Python 后端（server/ benches/ 等）
web/               # Vue 前端源码（构建产物 → benchscope/webui/）
mocks/             # mock 仿真（bench 输出 + OpenAI 服务）
scripts/           # dev.sh / maca.sh / release 脚本
tests/             # 功能测试（tests/api 接口 + tests/webui 页面），统一入口 run_tests.sh；不携带 mock（mock 唯一来源 mocks/）
docs/              # README（目录）· Roadmap · Projects · prds/ · versions/ · rules/
asserts/           # 截图与示例产物
```
