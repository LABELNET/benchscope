# BenchScope Skills

> **规范正文**：[docs/skills/Readme.md](../docs/skills/Readme.md)（技能目录结构 / SKILL.md /
> README.md / 打包规范，以该文档为准）
> **最后更新**：2026-08-30

本目录是**可分发的技能产物**；技能文档整理在 `docs/skills/`。

---

## 1. 技能清单

| 技能 | 用途 | 版本 | 文档 |
| --- | --- | --- | --- |
| [bs-engine-create](./bs-engine-create/) | 创建自定义 bench 引擎压缩包（vllm/sglang/其他版本）；导入时校验 + mock 数据验证 + 功能动态注册 | 1.1.0 | [BenchEngineAuthoring.md](../docs/skills/BenchEngineAuthoring.md) |
| [bs-perfs-concurrency](./bs-perfs-concurrency/) | 安装 benchscope 并用 `benchscope perf` 进行并发（concurrency）压测；内置表单 + 生成可导入 Datas/perfs 的 zip | 1.0.0 | [BenchTesting.md](../docs/skills/BenchTesting.md) |
| [bs-perfs-threshold](./bs-perfs-threshold/) | 安装 benchscope 并用 `benchscope perf --mode threshold` 进行阈值搜索压测；内置表单 + 生成可导入 Datas/perfs 的 zip | 1.0.0 | [BenchTesting.md](../docs/skills/BenchTesting.md) |

---

## 1.1 命名规范（强制）

所有技能及产物统一采用 `bs-` 前缀：

| 对象 | 命名模式 | 示例 |
| --- | --- | --- |
| 技能目录 / SKILL.md `name` | `bs-<模块>-<目标>` | `bs-engine-create` · `bs-perfs-concurrency` · `bs-perfs-threshold` |
| 技能版本包 | `bs-<模块>-<目标>-<版本>.tar.gz` | `bs-perfs-concurrency-1.0.0.tar.gz` |
| 生成产物目录 | `bs-<模块>-<目标>-<版本>-pkgs/` | `bs-engine-vllm-0.28-pkgs/` |
| 生成产物包 | `bs-<模块>-<目标>-<版本>.tar.gz` | `bs-engine-vllm-0.28.tar.gz` |

- `模块`：能力域，如 `engine`（引擎生成）、`perfs`（压测）；
- `目标`：具体对象，如 `create`（动作）、`concurrency`（并发）、`threshold`（阈值）、`vllm` / `sglang`（框架）；
- 例：使用 `bs-engine-create` 生成 vLLM 0.28 引擎 → 产物命名为 `bs-engine-vllm-0.28.tar.gz`。

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

### 4.1 版本递增与发版（强制约定）

- **技能有版本**：每个技能 `SKILL.md` frontmatter 的 `version` 为语义化版本 `x.y.z`。
- **每次更新技能自动增加版本号**：任何对 `SKILL.md` / `README.md` / `references` / `templates` /
  `scripts` 的内容变更，都必须递增 `version`（`x.y.z` → `x.y.z+1`）。
- **更新内容多时建议加大版本号**：涉及功能重构、接口/流程变更、或多项行为变化，建议增加**大版本号**
  （`x.y` 提升，如 `1.0.0` → `1.1.0`）；仅小修/文案调整递增末位（`1.0.0` → `1.0.1`）。
- **每次发版到本地**：更新后运行 `./scripts/package.sh`，生成 `dist/<name>-<version>.tar.gz`，
  作为可分发产物提交到仓库。
- **服务可下载技能包**：benchscope 提供 `GET /api/skills/{id}/download`，服务启动后即可访问下载
  已发版的技能包（优先返回 `dist/` 产物，未发版则实时打包）。
