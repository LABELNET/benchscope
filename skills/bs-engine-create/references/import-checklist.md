# 导入校验清单（Import Validation）

> 引擎定义导入时**逐项校验，全部通过方可写入**；任一项失败返回 `400` 且**不写磁盘**。

## 校验项

| # | 校验 | 规则 | 失败消息（detail） |
| --- | --- | --- | --- |
| 1 | YAML 合法 | `yaml.safe_load` 可解析 | `YAML 格式错误：...` |
| 2 | 顶层为对象 | 顶层必须是 mapping | `配置顶层必须是对象（含 engines / comparison 键）` |
| 3 | `engines` 存在 | 非空 list | `engines 必须是非空列表` |
| 4 | 每项含 `id` | 每项 dict 且有 `id` | `engines[i] 缺少 id 字段` |
| 5 | `id` 唯一 | 无重复 | `engines[i] id 重复：<id>` |
| 6 | `kind` 合法 | ∈ {`builtin`, `vllm`, `sglang`} | `engines[i]（<id>）的 kind 必须是 builtin / vllm / sglang` |
| 7 | 原生引擎 requires | `kind` 非 builtin 时必须含 `torch` + 框架包，且带 `spec` | `engines[i]（<id>）原生引擎必须声明 torch 与 <framework> 环境要求` |
| 8 | `params_key` 存在 | 引用的键必须在 `configs/bench-params.yaml` 中存在 | `engines[i]（<id>）的 params_key <key> 在 bench-params.yaml 中不存在` |
| 9 | 选项描述完整 | 参数集中每个 option 必须有非空 `description` | `参数 <key> 的选项 <value> 缺少 description` |
| 10 | Mock 输出（可选） | 若提交 `mock_output`，须包含解析器要求的指标行 | `mock 输出缺少必需指标行：<line>` |

## API

```
GET  /api/benchs/config/yaml          # 读取引擎定义原文
PUT  /api/benchs/config/yaml          # 保存（带上述校验）
POST /api/benchs/import               # 导入引擎定义（校验 + 返回逐项结果）
GET  /api/benchs                      # 引擎清单（含环境校验状态）
GET  /api/benchs/{id}/env-check       # 单引擎环境校验
GET  /api/benchs/{id}/params          # 参数集（描述 + 选项）
```

## 导入请求示例

```bash
curl -X POST http://127.0.0.1:8080/api/benchs/import \
  -H "Content-Type: application/json" \
  -d '{"content": "<完整 benchs.yaml 内容>", "dry_run": true}'
```

响应（成功）：

```json
{
  "ok": true,
  "checks": [
    {"item": "yaml",        "ok": true, "message": "YAML 解析通过"},
    {"item": "engines",     "ok": true, "message": "3 个引擎"},
    {"item": "kind",        "ok": true, "message": "kind 合法"},
    {"item": "requires",    "ok": true, "message": "原生引擎环境要求完整"},
    {"item": "params_key",  "ok": true, "message": "params_key 均已定义"},
    {"item": "option_desc", "ok": true, "message": "选项描述完整"}
  ],
  "engines": [ ... ],
  "applied": false
}
```

响应（失败，`applied` 恒为 false，不写磁盘）：

```json
{
  "ok": false,
  "checks": [ ... , {"item": "kind", "ok": false, "message": "engines[1]（x）的 kind 必须..."}],
  "applied": false
}
```

## 排错指引

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `params_key 不存在` | 只加了引擎条目，未加参数段 | 在 `configs/bench-params.yaml` 增加同名顶层键 |
| `选项缺少 description` | 选项只写了 value/label | 为每个 option 补 `description` |
| `原生引擎必须声明 torch...` | vllm/sglang 引擎 requires 缺项 | 补 `torch` 与框架包（带 `spec`） |
| 导入成功但指标全 0 | mock/CLI 输出不匹配 parser 正则 | 参见 [mock-core.md](mock-core.md) §3 规则 1 |
| 环境校验恒失败 | `spec` 与已装版本不符 | `pip show vllm sglang torch` 核对后调整 spec |
