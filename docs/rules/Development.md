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
| 端到端冒烟 | `tests/ui_smoke.py`（Playwright，需浏览器缓存） |

## 4. 变更流程与文档同步

1. 修改代码（后端 `benchscope/` / 前端 `web/` / 脚本 `scripts/` / mock `mocks/`）。
2. **文档同步（强制）**：设计/界面修改、逻辑与策略调整、UI 调整，**必须同步更新**对应文档：
   - 页面功能与约束 → `docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings）
   - 版本修订与 todo → `docs/versions/VERSION_1_0_5.md`（新版本另建 `VERSION_x_y_z.md`）
   - 架构 / 方案 / 设计 / 开发规范 → `docs/rules/`（Architecture / Software / Design / Development）
3. 运行 `check-i18n` + 构建 + 冒烟验证。
4. 提交。

## 5. 发布（Release checklist）

```bash
# 1. 版本号：pyproject.toml、benchscope/__init__.py、web/package.json
# 2. 构建 + 打包
cd web && npm run build
cd .. && python -m build
python -m twine check dist/*
# 3. 发布（~/.pypirc 或 TWINE_USERNAME/TWINE_PASSWORD）
python -m twine upload dist/*
```

- 发布记录写入 `docs/versions/VERSION_x_y_z.md`（按时间顺序）。

## 6. 目录约定

```text
benchscope/        # Python 后端（server/ benches/ 等）
web/               # Vue 前端源码（构建产物 → benchscope/webui/）
mocks/             # mock 仿真（bench 输出 + OpenAI 服务）
scripts/           # dev.sh / maca.sh / release 脚本
tests/             # mock OpenAI server / UI 冒烟
docs/              # README（目录）· Roadmap · Projects · prds/ · versions/ · rules/
asserts/           # 截图与示例产物
```
