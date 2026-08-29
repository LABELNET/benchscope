# vllm-bench-testing

使用 benchscope 对 **vLLM 推理服务**执行性能测试：引擎选择与环境校验 → 服务配置 → 参数配置 → 执行 → 日志与报表分析。

- **版本**：1.1.0
- **规范**：遵循 [skills 项目规范](../Readme.md)

## 用途

给 AI 提供的 vLLM 压测操作手册，覆盖：

1. **引擎选择与环境校验**（1.0.7+）：`benchscope` 自研引擎（无框架依赖）/ `vllm-0.23` 原生引擎（需 `torch` + `vllm`）；
2. 服务配置（Base URL / Endpoint / API Key / GPU / 阈值）；
3. `vllm bench serve` 参数、数据集、并发与速率；
4. 执行与实时监控；
5. 日志、CSV 与 `benchmark-*.xlsx` 报表分析。

**新增 vLLM bench 版本**（如 vllm 0.24）请用
[bench-engine-authoring](../bench-engine-authoring/) 技能，而非手工改配置。

## 使用方式

**给 AI（自动）**：将本目录加入 AI 技能检索路径；AI 依据 `SKILL.md` frontmatter 的
`name` / `description`，在「vLLM 性能压测」场景自动加载。

**给人（手动）**：按 `SKILL.md` 的工作流逐步操作，或把其中命令片段复制到终端执行。

## 目录结构

```
vllm-bench-testing/
├── SKILL.md              # 技能主文档（AI 消费）
├── README.md             # 本文件（人消费）
└── scripts/
    └── package.sh        # 打包（tar.gz + 产物校验）
```

## 打包

```bash
chmod +x scripts/package.sh
./scripts/package.sh                    # 产物：dist/vllm-bench-testing-1.1.0.tar.gz
./scripts/package.sh /tmp/skills-dist   # 指定输出目录
```

解压后整体复制到目标项目的 skills 目录即可使用：

```bash
tar -xzf dist/vllm-bench-testing-1.1.0.tar.gz -C <目标 skills 目录>
```

## 关键约定（速查）

| 约定 | 说明 |
| --- | --- |
| 引擎环境校验 | 原生引擎（vllm）必须校验 `torch` + `vllm` 版本，不满足则**禁止进入参数配置** |
| 自研引擎 | `benchscope` 无框架依赖，可对任意 OpenAI 兼容服务（含远程）压测 |
| 参数描述 | 参数面板下拉选择，选中后展示该选项描述（见 `configs/bench-params.yaml`） |
| 引擎定义 | yaml 驱动（`configs/benchs.yaml`），可在 Settings → Bench 引擎扩展 |
| 无本地 vLLM | 可用 FAKE 模式：`BENCHSCOPE_FAKE_BENCH=1 python -m benchscope` |

## 维护记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 1.0.0 | 2026-08（初始） | 初版：服务配置 / 参数 / 数据集 / 并发 / 日志分析 |
| 1.1.0 | 2026-08-29 | 按 skills 规范重构：补 version frontmatter、README、package.sh；新增「引擎选择与环境校验」章节；补充自研引擎与参数描述说明 |
