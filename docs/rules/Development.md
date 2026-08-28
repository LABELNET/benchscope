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

1. 修改代码（后端 `benchscope/` / 前端 `web/` / 脚本 `scripts/` / mock `mocks/` / 依赖 `pyproject.toml`、`web/package.json`）。
2. **文档同步（强制）**：设计/界面修改、逻辑与策略调整、UI 调整、依赖与架构变更，**必须同步更新**对应文档：
   - 页面功能与约束 → `docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings / Datas / TopBar）
   - 版本修订与 todo → `docs/versions/VERSION_1_0_7.md`（当前开发版本；新版本另建 `VERSION_x_y_z.md`）
   - 架构 / 方案 / 设计 / 开发规范 → `docs/rules/`（Architecture / Software / Design / Development）
   - **软件依赖变更（新增/升级/移除）** → 同步 `docs/rules/Software.md` §2 技术栈与 §3 依赖清单
3. **测试（强制）**：生成/更新对应 tests（API → `tests/api/`，WebUI → `tests/webui/`），运行 `check-i18n` + 构建 + `./tests/run_tests.sh` 全量通过。
4. 提交。

## 5. 发布（Release checklist）

```bash
# 一键发布：升版本 → 构建 → PyPI 上传 → GitHub Release（自动提取迭代摘要）→ git tag + push
TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> ./scripts/release.sh 1.0.6
# 可选 --notes 指定 Release 说明文件；缺省自动从 docs/versions/VERSION_1_0_6.md 提取迭代摘要
```

- **发布 = 打包推送 PyPI + 推送 GitHub Release 总结 + 推送版本 tag**（三者缺一不算完整发布）：
  1. **PyPI**：`python -m build` + `twine upload`（`TWINE_USERNAME=__token__` + PyPI API token）；
  2. **GitHub Release 总结**：`scripts/release.sh` 自动创建（`gh release create` 或 `GITHUB_TOKEN` REST API 回退），说明默认从 `docs/versions/VERSION_x_y_z.md` 迭代记录提取，可用 `--notes <file>` 覆盖；
  3. **版本 tag**：`git tag vX.Y.Z` + `git push origin main --tags`。
- 前置：PyPI token（`TWINE_USERNAME/TWINE_PASSWORD` 或 `~/.pypirc`）+ GitHub 凭据（`gh auth` 或 `GITHUB_TOKEN`）。
- 发布记录写入 `docs/versions/VERSION_x_y_z.md`（按时间顺序），并将该版本状态置为「已发布（Released）」，同步 `docs/Readme.md` 最后更新日期与版本表。

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
