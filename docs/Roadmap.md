# Roadmap / 版本路线

benchscope 按版本迭代推进，**倒序**列出各版本（最新在前）的目标范围与状态。

---

## 1.0.6（开发中 / In Development）

- **发布时间**：待定
- **TODO**（后续开发内容均迭代在此版本，按时间顺序追加，详见 [docs/versions/VERSION_1_0_6.md](versions/VERSION_1_0_6.md)）：

规划功能：
- 设置/数据集，增加内置数据集模块，配置文件存在 configs/datasets.yaml，数据集名称/描述/访问链接/下载命令，可点击下载，缓存到 .benchscope 目录；
- 设置/通用//缓存路径 ，增加模型和数据路径 默认全部数据在.benchscope目录下∶
- 主导航：添加 Datas主导航，放到 Sessions 后面
- 主导航/Datas，实现 Perfs 分页记录，显示最佳测试记录和 Evals 分页记录，显示误差情况，暂时占位；重点 性能数据详情页面， 重新规划 如 mean/meduie/p99值，精度数据详情页面，暂不实现；
- 主导航/Datas 联动 Dashboard 表格，更多/详情
- 主导航/Datas 还有记录对比分析界面

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
