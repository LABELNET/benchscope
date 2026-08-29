# bs-perfs-threshold

用 **benchscope** 自研引擎的 `benchscope perf --mode threshold` 命令，对一个 OpenAI 兼容
推理服务执行**阈值搜索压测**（找满足延迟/吞吐阈值的最大并发），并产出**可在网页 Datas/perfs
导入的压缩包**。

- **版本**：1.0.0
- **规范**：遵循 [skills 项目规范](../Readme.md)

## 用途

当用户想用 benchscope 快速做**阈值搜索压测**、或需要**可导入 Datas/perfs 的压缩包**归档结果时，
AI 加载本技能，按流程：

1. 展示**内置简单表单**（模型 / 服务地址 / 阈值 / 搜索上限等）
2. 根据表单组装并执行 `benchscope perf --mode threshold` 命令
3. 保存任务数据（`run.json`）与终端日志（`perf_<run_id>_*.log`）
4. 打包为**扁平 zip**（含 run.json + 日志 + 指标）
5. 指导用户在网页 **Datas/perfs** 导入该 zip

## 使用方式

**给 AI（自动）**：把 `SKILL.md` 所在目录加入技能检索路径；AI 依据 frontmatter 的
`name` / `description` 在「阈值搜索压测 / 找最佳并发」场景自动加载。

**给人（手动）**：按 `SKILL.md` 的工作流操作，用 `templates/bench-perfs-config.yaml`
作为表单字段清单。

## 目录结构

```
bs-perfs-threshold/
├── SKILL.md                              # 技能主文档（AI 消费）
├── README.md                             # 本文件（人消费）
├── templates/
│   └── bench-perfs-config.yaml           # 内置简单表单参数 schema
└── scripts/
    └── package.sh                        # 打包（tar.gz + 产物校验）
```

## 打包（发版）

```bash
chmod +x scripts/package.sh
./scripts/package.sh                      # 产物：dist/bs-perfs-threshold-1.0.0.tar.gz
./scripts/package.sh /tmp/skills-dist     # 指定输出目录
```

## 维护记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 1.0.0 | 2026-08-30 | 初版：benchscope perf 阈值搜索 + 内置表单 + 生成可导入 Datas/perfs 的 zip |
