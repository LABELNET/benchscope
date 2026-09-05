# Skills 技能体系

> **适用范围**：`skills/` 目录下所有技能项目；`docs/skills/` 为技能文档的**唯一整理归口**
> **最后更新**：2026-08-31
> **目标**：让技能（skill）可被 AI 直接消费、可打包分发、可校验

---

## 1. 定位

Skills 是给 **AI 编程助手**消费的领域知识包：描述「如何完成某类任务」，包含工作流、参考文档、模板与脚本。

与 `docs/`（给人看的文档）不同，skills 面向 AI，要求**可直接执行**、**指令明确**、**含可复制产物**。

**分工**：

| 位置 | 角色 | 说明 |
| --- | --- | --- |
| `skills/<name>/` | **可分发产物** | 技能本体（SKILL.md / references / templates / scripts），可打包成 tar.gz 供任意项目使用 |
| `docs/skills/` | **说明文档归口** | 技能规范、各技能详解、上游分析索引；给人阅读与维护 |
| `benchscope/skills/Readme.md` | **速查指针** | 精简版：技能清单 + 快速约定，规范正文以本文件为准 |

---

## 2. 目录结构规范（强制）

```
skills/
├── Readme.md                      # 速查指针（清单 + 关键约定，规范正文见 docs/skills/Readme.md）
└── <skill-name>/                  # 单个技能项目（kebab-case 命名）
    ├── SKILL.md                   # 【必需】技能主文档（含 YAML frontmatter）
    ├── README.md                  # 【必需】说明：用途 / 使用方式 / 目录说明 / 打包
    ├── references/                # 【推荐】参考文档（按需加载的补充知识）
    │   └── *.md
    ├── templates/                 # 【推荐】可复制的产物模板
    │   └── *
    ├── scripts/                   # 【推荐】可执行脚本
    │   └── package.sh             # 【强制】打包脚本
    └── assets/                    # 【可选】其他资源
```

**强制项**：`SKILL.md`、`README.md`、`scripts/package.sh`。

### 2.1 命名规范（强制）

所有技能及产物统一采用 **`bs-` 前缀**：

| 对象 | 命名模式 | 示例 |
| --- | --- | --- |
| 技能目录 / SKILL.md `name` | `bs-<模块>-<目标>` | `bs-engine-create` · `bs-perfs-concurrency` · `bs-perfs-threshold` |
| 技能版本包 | `bs-<模块>-<目标>-<版本>.tar.gz` | `bs-perfs-concurrency-1.0.0.tar.gz` |
| 技能生成产物目录 | `bs-<模块>-<目标>-<版本>-pkgs/` | `bs-engine-vllm-0.28-pkgs/` |
| 技能生成产物包 | `bs-<模块>-<目标>-<版本>.tar.gz` | `bs-engine-vllm-0.28.tar.gz` |
| **说明文档**（docs/skills/） | `<BsXxxYyy>.md`（每段去连字符 + 首字母大写） | `bs-engine-create` → `BsEngineCreate.md` · `bs-perfs-concurrency` → `BsPerfsConcurrency.md` · `bs-perfs-threshold` → `BsPerfsThreshold.md` |

- `模块`：能力域，如 `engine`（引擎生成）、`perfs`（压测）；
- `目标`：具体对象，如 `create`（动作）、`concurrency`（并发）、`threshold`（阈值）、`vllm` / `sglang`（框架）；
- 技能自身的分发打包产物仍为 `<skill-name>-<version>.tar.gz`（见 §5）；
- 例：使用 `bs-engine-create` 生成 vLLM 0.28 引擎 → 产物命名为 `bs-engine-vllm-0.28.tar.gz`；
- **一个技能一个说明文档**：每个技能在 `docs/skills/` 下对应一个 `<BsXxxYyy>.md` 说明文档（命名见上表），禁止多技能合并到一份文档。

---

## 3. SKILL.md 规范

### 3.1 frontmatter（必需）

```yaml
---
name: bs-<module>-<target>      # 与目录名一致，bs- 前缀命名（见 §2.1）
description: >-                 # 一句话描述（AI 据此判断何时加载该技能）
  动词开头的用途描述，包含关键场景与关键词，便于 AI 检索匹配。
version: 1.0.0                  # 语义化版本
---
```

> `name` 与 `description` 是 AI 检索技能的唯一依据，**必须准确描述触发场景**。

### 3.2 正文结构（推荐顺序）

| 章节 | 内容 | 必需 |
| --- | --- | --- |
| 标题 + 简介 | 一句话说明做什么、适用什么场景 | ✅ |
| When to use | 触发场景清单（条目化） | ✅ |
| Prerequisites | 前置条件（依赖 / 环境 / 权限） | ✅ |
| 主工作流 | 分步骤（1./2./3.…），每步含可操作指令 | ✅ |
| 参考资源 | 链接（官方文档 / GitHub / 规范） | ✅ |
| 可复制产物 | 提示词 / 模板 / 命令（AI 可直接复制给用户） | 推荐 |
| 校验清单 | 完成前的自检项 | 推荐 |
| Troubleshooting | 常见错误与处理 | 推荐 |

### 3.3 写作原则

1. **指令化**：用祈使句（"执行…" / "检查…"），不用描述句（"你可以…"）。
2. **可复制**：提示词、命令、配置片段放代码块，用户可直接复制。
3. **链接完整**：所有外部引用给完整 URL，并说明「该链接用于什么」。
4. **不重复**：详细参考放 `references/`，`SKILL.md` 只放主干 + 链接索引。
5. **单一职责**：一个技能只解决一类问题，避免大而全。

---

## 4. README.md 规范

面向**人**（开发者/维护者），必须包含：

1. 用途（一句话）
2. 使用方式（如何被 AI 加载 / 如何手动使用）
3. 目录结构说明
4. **打包方式**（`scripts/package.sh` 用法与产物）
5. 维护记录（版本与变更）

---

## 5. 打包规范（强制）

每个技能必须提供 `scripts/package.sh`，产出可分发的压缩包。

**要求**：
- 可执行：`chmod +x scripts/package.sh`
- 用法：`./scripts/package.sh [输出目录]`
- 产物：`<skill-name>-<version>.tar.gz`（version 从 `SKILL.md` frontmatter 读取）
- 行为：排除 `__pycache__` / `.git` / `.DS_Store` / `*.pyc`；打包后校验产物可解压
- 退出码：成功 0，失败非 0

**统一实现**（各技能 `package.sh` 直接引用本规范，见下）：

```bash
#!/usr/bin/env bash
# 用法: ./scripts/package.sh [输出目录]
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "$SKILL_DIR")"
VERSION="$(grep -m1 '^version:' "$SKILL_DIR/SKILL.md" | sed 's/version: *//' | tr -d '"'"'"'"' | tr -d '\r')"
VERSION="${VERSION:-0.0.0}"
OUT_DIR="${1:-$SKILL_DIR/dist}"
mkdir -p "$OUT_DIR"
ARCHIVE="$OUT_DIR/${NAME}-${VERSION}.tar.gz"
tar -czf "$ARCHIVE" -C "$(dirname "$SKILL_DIR")" \
  --exclude='__pycache__' --exclude='.git' --exclude='.DS_Store' --exclude='*.pyc' \
  --exclude='dist' "$NAME"
echo "✅ 打包完成: $ARCHIVE"
tar -tzf "$ARCHIVE" >/dev/null && echo "✅ 产物校验通过（可解压）"
```

---

## 6. 技能清单

| 技能 | 用途 | 版本 | 文档 |
| --- | --- | --- | --- |
| [bs-engine-create](../../benchscope/skills/bs-engine-create/) | 创建自定义 bench 引擎压缩包（vllm/sglang/其他版本）；导入时校验 + mock 数据验证 + 功能动态注册 | 1.2.0 | [BsEngineCreate.md](./BsEngineCreate.md) |
| [bs-perfs-concurrency](../../benchscope/skills/bs-perfs-concurrency/) | 安装 benchscope 并用 `benchscope perf` 进行并发（concurrency）压测；内置表单 + 生成可导入 Datas/perfs 的 zip | 1.0.0 | [BsPerfsConcurrency.md](./BsPerfsConcurrency.md) |
| [bs-perfs-threshold](../../benchscope/skills/bs-perfs-threshold/) | 安装 benchscope 并用 `benchscope perf --mode threshold` 进行阈值搜索压测；内置表单 + 生成可导入 Datas/perfs 的 zip | 1.0.0 | [BsPerfsThreshold.md](./BsPerfsThreshold.md) |

---

## 7. 技能文档索引（一个技能一个说明文档）

| 文档 | 对应技能 | 内容 |
| --- | --- | --- |
| [BsEngineCreate.md](./BsEngineCreate.md) | bs-engine-create | **自定义引擎技能详解**：工作流、上游源码链接与获取、实现契约（Input/Core/Output/Mock）、mock 核心方法、导入校验 8 项、可复制提示词、排错 |
| [BsPerfsConcurrency.md](./BsPerfsConcurrency.md) | bs-perfs-concurrency | **并发压测技能说明**：内置表单、命令、产物打包、Datas/perfs 导入、排错 |
| [BsPerfsThreshold.md](./BsPerfsThreshold.md) | bs-perfs-threshold | **阈值搜索压测技能说明**：内置表单、阈值探测策略、产物打包、Datas/perfs 导入、排错 |

**关联文档（rules）**：

| 文档 | 关联点 |
| --- | --- |
| [rules/BenchEngine.md](../rules/BenchEngine.md) | 引擎架构：引擎抽象（自研 / vllm-<ver> / sglang-<ver>）+ 环境校验 + 参数描述 |
| [rules/BenchUpstream.md](../rules/BenchUpstream.md) | ⭐ 上游 bench 核心逻辑分析（vLLM v0.23.0 / SGLang v0.5.10 源码实证）— 自定义引擎实现的**事实依据** |
| [rules/BenchCore.md](../rules/BenchCore.md) | 自研 bench 核心实现总结（技能生成引擎时的**规范范例**） |

---

## 8. 维护约定

- **新增技能** → 在 `benchscope/skills/Readme.md` 与本文档 §6 清单各追加一行，并在 `docs/skills/` 补充对应说明文档；
- **一个技能一个说明文档（强制）**：每个技能在 `docs/skills/` 下对应一个 `<BsXxxYyy>.md` 说明文档（命名见 §2.1），**禁止多技能合并到一份文档**；
- **技能内容变更涉及功能/流程** → 同步 `docs/versions/VERSION_x_y_z.md` 迭代记录；
- **规范变更** → 只改本文件（`docs/skills/Readme.md`），`benchscope/skills/Readme.md` 保持精简指针，不复制规范正文；
- 所有技能必须能通过 `scripts/package.sh` 成功打包（由 `tests/api/test_skills.py` 强制校验）。
- **技能开发完成（强制）**：任何技能的开发/变更完成后，必须**同步更新 `docs/skills/` 文件夹下对应说明与变更内容**：
  - `docs/skills/Readme.md` §6 技能清单（版本/用途）、命名规范、文档索引如有变化需同步；
  - 对应技能的说明文档（如 `BsEngineCreate.md` / `BsPerfsConcurrency.md` / `BsPerfsThreshold.md`）更新功能描述与维护记录表；
  - 变更内容同步 `docs/versions/VERSION_x_y_z.md` 迭代记录；若涉及能力/命名/发布规则变更，同步 `benchscope/skills/Readme.md`。

### 8.1 版本递增与发版（强制约定）

- **技能有版本**：每个技能 `SKILL.md` frontmatter 的 `version` 为语义化版本 `x.y.z`。
- **每次更新技能自动增加版本号**：任何内容变更（SKILL.md / README / references / templates / scripts）
  都必须递增 `version`（末位 +1）。
- **更新内容多时建议加大版本号**：涉及功能重构 / 接口或流程变更 / 多项行为变化，建议提升**大版本号**
  （如 `1.0.0` → `1.1.0`）；仅小修 / 文案调整递增末位。
- **每次发版到本地**：更新后运行 `./scripts/package.sh` 生成 `dist/<name>-<version>.tar.gz` 提交。
- **服务可下载技能包**：benchscope 提供 `GET /api/skills/{id}/download`，服务启动后即可访问下载
  已发版技能包（优先 `dist/` 产物，未发版实时打包）。
