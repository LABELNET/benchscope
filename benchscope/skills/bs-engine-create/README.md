# bs-engine-create

为 BenchScope 创建**自定义测试引擎**（指定版本的 vLLM / SGLang bench，或其他 OpenAI 兼容 bench 工具）：
生成引擎配置与参数描述 → 校验 → 导入。

- **版本**：1.2.0
- **规范**：遵循 [skills 项目规范](../Readme.md)

## 用途

当用户需要新增一个 bench 引擎或框架版本（如「添加 vllm 0.24」「添加 sglang 0.4.6」「自定义 bench 引擎」）时，
AI 加载本技能，按流程：

1. 确认目标框架与**确切版本**（不猜测）
2. 打开**该版本 tag** 的上游 GitHub 链接，读取真实参数（不从其他版本复制）
3. 生成两份产物：引擎条目（`configs/benchs.yaml`）+ 参数段（`configs/bench-params.yaml`）
4. 按需生成 mock 逻辑（遵循 mock 核心契约）
5. 逐项校验（全部通过方可导入）
6. 导入（Settings → Bench 引擎 → 引擎定义 → 编辑 → 保存）

## 使用方式

**给 AI（自动）**：把 `SKILL.md` 所在目录加入 AI 的技能检索路径；AI 依据 frontmatter 的
`name` / `description` 在「添加自定义引擎 / 新增版本」场景自动加载。

**给人（手动）**：直接按 `SKILL.md` 的工作流操作，或把 `SKILL.md` §5 的提示词复制给任意 AI 助手，
让其生成配置后再导入。

**离线校验**（无需启动服务）：

```bash
./scripts/validate.sh                                   # 校验仓库默认配置
./scripts/validate.sh path/to/benchs.yaml               # 校验指定引擎定义
./scripts/validate.sh path/to/benchs.yaml path/to/bench-params.yaml
```

## 目录结构

```
bs-engine-create/
├── SKILL.md                            # 技能主文档（AI 消费）
├── README.md                           # 本文件（人消费）
├── references/
│   ├── engine-schema.md                # 引擎定义字段参考 + 完整示例
│   ├── upstream-analysis.md            # ⭐ 上游核心逻辑分析（v0.23.0 / v0.5.10 源码实证，含链接与可复制代码）
│   ├── mock-core.md                    # mock 核心逻辑方法与介绍（缩放模型 / 两条硬规则）
│   └── import-checklist.md             # 导入校验项、API 与排错指引
├── templates/
│   ├── benchs-engine-entry.yaml        # 引擎条目模板
│   └── bench-params-section.yaml       # 参数段模板（选项描述必需）
└── scripts/
    ├── package.sh                      # 打包（tar.gz + 产物校验）
    └── validate.sh                     # 离线校验引擎定义
```

## 上游源码（分析与复用）

自定义引擎**必须拉取目标版本源码分析**，不得凭记忆或跨版本复制参数：

| 框架 | 版本 | Git | Zip |
| --- | --- | --- | --- |
| vLLM | v0.23.0 | https://github.com/vllm-project/vllm | https://github.com/vllm-project/vllm/archive/refs/tags/v0.23.0.zip |
| SGLang | v0.5.10 | https://github.com/sgl-project/sglang | https://github.com/sgl-project/sglang/archive/refs/tags/v0.5.10.zip |

核心逻辑（时间线采集 / 指标公式 / 并发与速率控制）已实证分析并存档于
`references/upstream-analysis.md` 与 `docs/rules/BenchUpstream.md`，实现新引擎时
**直接复用上游逻辑**，只适配 benchscope 的入口 / 出口 / mock 契约。

## 打包

```bash
chmod +x scripts/package.sh scripts/validate.sh
./scripts/package.sh                    # 产物：dist/bs-engine-create-1.0.0.tar.gz
./scripts/package.sh /tmp/skills-dist   # 指定输出目录
```

打包会：读取 `SKILL.md` frontmatter 的 `version` → 生成 `dist/<name>-<version>.tar.gz`
→ 校验产物可解压且含 `SKILL.md` / `README.md` / `scripts/package.sh` → 运行 `validate.sh` 自检。

解压后可整体复制到任意项目的 skills 目录使用：

```bash
tar -xzf dist/bs-engine-create-1.0.0.tar.gz -C <目标 skills 目录>
```

## 关键约定（速查）

| 约定 | 说明 |
| --- | --- |
| `kind` | 只能是 `builtin` / `vllm` / `sglang` |
| 自研引擎 | `kind: builtin` + `requires: []` → 环境校验恒通过 |
| 原生引擎 | 必须声明 `torch` + 框架包，且带版本 `spec` |
| 选项描述 | 每个参数 option **必须**有非空 `description`（前端选中后展示） |
| `params_key` | 必须在 `configs/bench-params.yaml` 中存在同名段 |
| mock 代码 | 唯一归属 `mocks/`；输出必须匹配 `parser.py` 正则 |
| 导入校验 | 任一项失败 → 返回 400 且**不写磁盘** |

## 上游链接（按版本 tag 固定）

| 框架 | 入口 | 链接模板 |
| --- | --- | --- |
| vLLM | `vllm bench serve` | `https://github.com/vllm-project/vllm/blob/v<VERSION>/vllm/benchmarks/serve.py` |
| SGLang | `sglang.bench_serving` | `https://github.com/sgl-project/sglang/blob/v<VERSION>/python/sglang/bench_serving.py` |

## 维护记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 1.0.0 | 2026-08-29 | 初版：引擎定义生成、mock 核心契约、导入校验清单、模板与打包 |
| 1.1.0 | 2026-08-30 | 明确导入时 mock 数据验证 + 引擎功能动态注册（导入即可用） |
| 1.2.0 | 2026-08-30 | 补充 mock 数据动态注册：每引擎独立 Mock 开关（默认关），开启即 FAKE 仿真验证 |
