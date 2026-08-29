# BenchScope Skills

> **规范正文**：[docs/skills/Readme.md](../docs/skills/Readme.md)（技能目录结构 / SKILL.md /
> README.md / 打包规范，以该文档为准）
> **最后更新**：2026-08-29

本目录是**可分发的技能产物**；技能文档整理在 `docs/skills/`。

---

## 1. 技能清单

| 技能 | 用途 | 版本 | 文档 |
| --- | --- | --- | --- |
| [bench-engine-authoring](./bench-engine-authoring/) | 自定义 bench 引擎（vllm/sglang/其他版本）配置与代码生成、导入校验 | 1.0.0 | [BenchEngineAuthoring.md](../docs/skills/BenchEngineAuthoring.md) |
| [vllm-bench-testing](./vllm-bench-testing/) | 对 vLLM 推理服务执行性能测试 | 1.1.0 | [BenchTesting.md](../docs/skills/BenchTesting.md) |
| [sglang-bench-testing](./sglang-bench-testing/) | 对 SGLang 推理服务执行性能测试 | 1.1.0 | [BenchTesting.md](../docs/skills/BenchTesting.md) |

---

## 2. 强制结构（速查）

```
<skill-name>/
├── SKILL.md            # 【必需】含 frontmatter（name / description / version）
├── README.md           # 【必需】用途 / 使用方式 / 目录 / 打包 / 维护记录
├── references/*.md     # 【推荐】参考文档
├── templates/*         # 【推荐】可复制模板
└── scripts/package.sh  # 【必需】打包 → <name>-<version>.tar.gz
```

打包：`./scripts/package.sh [输出目录]`（版本取自 `SKILL.md` frontmatter）。

---

## 3. 关键约定（速查）

| 约定 | 说明 |
| --- | --- |
| `kind` | 只能是 `builtin` / `vllm` / `sglang` |
| 自研引擎 | `kind: builtin` + `requires: []` → 环境校验恒通过 |
| 原生引擎 | 必须声明 `torch` + 框架包，且带版本 `spec` |
| 选项描述 | 每个参数 option **必须**有非空 `description`（前端选中后展示） |
| `params_key` | 必须在 `configs/bench-params.yaml` 中存在同名段 |
| mock 代码 | 唯一归属 `mocks/`；输出必须匹配 `parser.py` 正则 |
| 导入校验 | 任一项失败 → 返回 400 且**不写磁盘** |
| 上游源码 | 自定义引擎**必须拉取目标版本源码**核实参数与核心逻辑，禁止跨版本复制 |

---

## 4. 维护约定

- 新增技能 → 在本文件 §1 与 `docs/skills/Readme.md` §6 各追加一行，并在 `docs/skills/` 补充说明文档；
- 技能内容变更涉及功能/流程 → 同步 `docs/versions/VERSION_x_y_z.md` 迭代记录；
- 所有技能必须能通过 `scripts/package.sh` 成功打包（由 `tests/api/test_skills.py` 强制校验）。
