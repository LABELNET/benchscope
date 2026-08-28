# Roadmap / 版本路线

benchscope 按版本迭代推进，**倒序**列出各版本（最新在前）的目标范围与状态。

---

## 1.0.7（开发中 / In Development）

- **发布时间**：待定
- **TODO**（后续开发内容均迭代在此版本，按时间顺序追加，详见 [docs/versions/VERSION_1_0_7.md](versions/VERSION_1_0_7.md)）：

**主目标：性能测试核心引擎改造**（详见 [docs/rules/BenchEngine.md](rules/BenchEngine.md)）

- 自研 **bench（benchscope）**：基于 vLLM / SGLang bench 思路实现自研测试引擎，不依赖本地框架环境，pip 安装即可远程测 OpenAI 兼容服务
- **vllm bench 版本化**：指定具体版本的原生 vLLM bench（如 `vllm-0.23`），可因版本存在多个
- **sglang bench 版本化**：指定具体版本的原生 SGLang bench（如 `sglang-0.5.10`），可因版本存在多个
- **参数下拉 + 描述**：各引擎各项参数独立设置，下拉选择后展示描述信息
- **Settings → Bench 配置栏**：内置 `bench` / `vllm-0.23` / `sglang-0.5.10`，含介绍与对比情况
- **环境校验**：原生引擎校验 `torch` + `vllm`/`sglang` 安装版本，不满足则禁止选择参数；自研 bench 无需上述环境

次要候选（主目标后评估）：Dashboard 指标补全 · Datas/Analysis 对比分析页 · Datas/Evals 精度记录页 · Models 一键下载 · Plugins 机制 · 任务管理与导出增强

---

## 1.0.6（已发布 / Released）

- **发布时间**：2026-08-28
- **主要功能点**：
  - **Datas 主导航**（Sessions 之后）：Perfs / Evals / Analysis 副导航，Perfs 记录面板（导入/刷新/删除/备份/分享）+ 详情 5 行布局（元信息、Perf/Cases/Logs 三面板、Perf Datas 表格、分析图表）、记录对比分析
  - **内置数据集模块**：`configs/datasets.yaml` 定义（名称/描述/访问链接/下载命令），一键下载缓存到 `~/.benchscope/datasets`，分类筛选
  - **9 目录配置体系**：`data_dir` + 8 子目录，`settings.json` 持久化（旧版 `config.json` 迁移），行内编辑 + 锁定 + 重启迁移
  - **Settings 重构**：Models 厂商目录（41 厂商国内/国外分组）、Datasets 分类、缓存路径双语、布局收窄 + 滚动条贴右
  - **阈值模式升级**：TTFT/TPOT 统计量选择（Mean/Median/P99）、阈值随 groups 存储与每组独立执行判定、旧格式任务回退兼容、Cases/Realtime/Perf Datas 分组阈值展示
  - **Dashboard 改版**：Logo 放大 48px、Service 状态仅图标、Records 表格去删除 + 详情跳转 Datas 自动选中、footer 提示
  - **测试体系重构**：mock 唯一归属 `mocks/`、tests 全覆盖（API 49 + WebUI 18）、`./tests/run_tests.sh` 统一入口 + 临时数据目录隔离
  - **文档体系升级**：`docs/prds/TopBar.md`、迭代记录精确到秒、依赖/架构变更同步 docs 约定
  - **版本与发布**：`__version__` 单一来源 + TopBar 动态版本标签；发布 = PyPI + GitHub Release 总结 + tag（`scripts/release.sh` 一键）

---

## 1.0.5（已发布 / Released）

- **发布时间**：2026-08-26
- **主要功能点**：
  - UI 大改：5 栏导航（Dashboard / Performance / Accuracy / Sessions / Settings）
  - Performance **双模式**：并发压测（Concurrency）/ 阈值探测（Threshold，自动寻找满足条件的最大并发）
  - 创建任务三步表单（条件组 / 参数 YAML / 命令预览），多组条件带唯一 `case_id`（相同条件不叠加）
  - Progress 按 case 计数（1/1、2/2、N/N），与 Cases 面板一致
  - Realtime 分组表格 + Best/BestPerf 唯一高亮 + 本地阈值试算 + Excel 导出
  - Statistics 4×3 共 12 张统计图（吞吐 / TTFT / TPOT / ITL）
  - Dashboard：Overview 六宫格 + Envs info（硬件 / OS / 网络 / 框架版本）+ Perf / Eval Records
  - Settings 四栏：General（Language + Cache Paths）/ Envs（环境配置）/ Models（内置模型下载宫格）/ Plugins（占位）
  - Sessions：SSE 流式对话 + 思考/正文分离 + 会话持久化
  - i18n（中英）+ 主题（亮 / 暗 / 跟随系统）
  - mock 调试环境（`mocks/`）与 `scripts/dev.sh` 统一入口（:8080）
  - docs 文档体系重构（prds / versions / rules，时间顺序维护）

---

## 1.0.4（已发布 / Released）

- **发布时间**：2026-08-24
- **主要功能点**：
  - 补丁发布：README 完善、打包元数据更新
  - 期间完成 1.0.5 范围定义与发布前收口规划（归档于 [docs/versions/VERSION_1_0_4.md](versions/VERSION_1_0_4.md)）

---

## 1.0.3（已发布 / Released）

- **发布时间**：2026-08-24
- **主要功能点**：
  - 补丁发布：README（双语，默认英文）、打包元数据、源码链接更新
  - 仓库首个入库版本提交

---

## 1.0.2（已发布 / Released）

- **发布时间**：2026-08-24 之前（仓库历史外）
- **主要功能点**：
  - 补丁发布：README 完善、打包元数据更新

---

## 1.0.1（已发布 / Released）

- **发布时间**：2026-08-24 之前（仓库历史外）
- **主要功能点**：
  - 补丁发布：README（双语，默认英文）、打包元数据、源码链接更新

---

## 1.0.0（已发布 / Released）

- **发布时间**：2026-08 之前
- **主要功能点**：
  - 纯文本性能测试首个发布版
  - 双框架（vLLM / SGLang）、三数据集（random / ShareGPT / custom）
  - 实时结果与六条曲线、日志与 `benchmark-*.xlsx` 汇总（mean + P99）
  - 均值 / P99 分析面板与最佳并发高亮
  - 管理台风格 UI、服务 / 环境状态监控

---

## 2.0（规划中 / Planned）

- **TODO**：
  - 多模态模型性能测试（图像 / 视频输入）

---

## 3.0（规划中 / Planned）

- **TODO**：
  - 全模态模型性能测试（音频 / 视频 / 多模态）

---

## 4.0（规划中 / Planned）

- **TODO**：
  - 世界模型性能测试

---

## 5.0（规划中 / Planned）

- **TODO**：
  - 常见数据集精度测试（Accuracy 页落地，Dashboard Eval Records 接入）

---

## 6.0（规划中 / Planned）

- **TODO**：
  - ModelScope 官方模型对比（链接 + 对比结论分析）

---

## 7.0（规划中 / Planned）

- **TODO**：
  - 内置 GPU 适配模型下载：一键下载 / 部署适配模型（Settings → Models 部署按钮落地）

---

> **Notes**：
> - **Accuracy 页**（1.0.5）为 v5.0 精度测试预留占位，暂无功能逻辑。
> - **Settings → Plugins**（1.0.5）为后续版本预留占位，暂无插件管理。
> - 版本修订记录（功能概述 + TODO 明细）见 [docs/versions/](versions/)，按时间顺序维护。
