# Skills 技能体系

> **适用范围**：`skills/` 目录下所有技能项目；`docs/skills/` 为技能文档的**唯一整理归口**
> **最后更新**：2026-08-29
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
| `skills/Readme.md` | **速查指针** | 精简版：技能清单 + 快速约定，规范正文以本文件为准 |

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

---

## 3. SKILL.md 规范

### 3.1 frontmatter（必需）

```yaml
---
name: <skill-name>              # 与目录名一致，kebab-case
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
| [bench-engine-authoring](../../skills/bench-engine-authoring/) | 自定义 bench 引擎（vllm/sglang/其他版本）配置与代码生成、导入校验 | 1.0.0 | [BenchEngineAuthoring.md](./BenchEngineAuthoring.md) |
| [vllm-bench-testing](../../skills/vllm-bench-testing/) | 对 vLLM 推理服务执行性能测试 | 1.1.0 | [BenchTesting.md](./BenchTesting.md) |
| [sglang-bench-testing](../../skills/sglang-bench-testing/) | 对 SGLang 推理服务执行性能测试 | 1.1.0 | [BenchTesting.md](./BenchTesting.md) |

---

## 7. 技能文档索引

| 文档 | 内容 |
| --- | --- |
| [BenchEngineAuthoring.md](./BenchEngineAuthoring.md) | **自定义引擎技能详解**：工作流、上游源码链接与获取、实现契约（Input/Core/Output/Mock）、mock 核心方法、导入校验 8 项、可复制提示词、排错 |
| [BenchTesting.md](./BenchTesting.md) | **性能测试技能说明**（vLLM / SGLang）：引擎选择与环境校验、服务与框架参数配置、数据集、并发与速率、测试流程、日志产物、排错 |

**关联文档（rules）**：

| 文档 | 关联点 |
| --- | --- |
| [rules/BenchEngine.md](../rules/BenchEngine.md) | 引擎架构：引擎抽象（自研 / vllm-<ver> / sglang-<ver>）+ 环境校验 + 参数描述 |
| [rules/BenchUpstream.md](../rules/BenchUpstream.md) | ⭐ 上游 bench 核心逻辑分析（vLLM v0.23.0 / SGLang v0.5.10 源码实证）— 自定义引擎实现的**事实依据** |
| [rules/BenchCore.md](../rules/BenchCore.md) | 自研 bench 核心实现总结（技能生成引擎时的**规范范例**） |

---

## 8. 维护约定

- **新增技能** → 在 `skills/Readme.md` 与本文档 §6 清单各追加一行，并在 `docs/skills/` 补充对应说明文档；
- **技能内容变更涉及功能/流程** → 同步 `docs/versions/VERSION_x_y_z.md` 迭代记录；
- **规范变更** → 只改本文件（`docs/skills/Readme.md`），`skills/Readme.md` 保持精简指针，不复制规范正文；
- 所有技能必须能通过 `scripts/package.sh` 成功打包（由 `tests/api/test_skills.py` 强制校验）。
