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

## 4. TODO 清单

（1.0.9 待办，按规划补充后逐项勾选）

---

## 5. 相关文档

- 页面级功能与约束：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings / Datas / TopBar）
- 架构 / 方案 / 设计 / 开发规范：`docs/rules/`（Architecture / Software / Design / Development / BenchEngine / BenchCore / BenchUpstream / AccuracyEngine）
- 版本路线：`docs/Roadmap.md`
