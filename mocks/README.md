# mocks 调试环境

没有真实 vLLM / SGLang / GPU 运行环境时，用本目录模拟完整调试环境。

## 目录结构

```
mocks/
├── bench_outputs.py    # vLLM / SGLang 两种 bench 结果的仿真生成器（与 parser 正则对齐）
├── cli.py              # 可独立运行的 mock bench CLI（冒充 vllm bench serve / sglang.bench_serving）
├── openai_server.py    # mock OpenAI 兼容推理服务（/v1/models + chat/completions，支持 SSE 流式）
├── run_mock.sh         # 一键启动脚本（mock OpenAI + FAKE bench 后端）
└── README.md
```

## 快速开始（一键）

```bash
./mocks/run_mock.sh
# mock OpenAI server: http://127.0.0.1:8001
# benchscope 后端:    http://127.0.0.1:8080 （BENCHSCOPE_FAKE_BENCH=1，跑任务不需要真实 CLI）

# 另开终端启动前端
cd web && npm run dev   # http://127.0.0.1:5173
```

然后：

1. **Settings → Inference API**：Base URL 填 `http://127.0.0.1:8001`，点"测试连接"。
2. **Performance**：新建任务（vLLM 或 SGLang 均可），FAKE 模式会生成对应框架风格的仿真输出，
   实时表格与六条曲线照常更新。
3. **Sessions**：新建会话即可用 SSE 流式对话（会先模拟一段"思考"增量再出正文）。

## 独立运行各组件

### 1. 模拟 bench 输出（mock vLLM / sglang 返回数据）

```bash
# vLLM 风格（参数与真实 vllm bench serve 相同）
python -m mocks.cli vllm bench serve --max-concurrency 32 --num-prompts 32 \
    --model Qwen2.5-72B-Instruct --random-input-len 3072 --random-output-len 1024

# SGLang 风格
python -m mocks.cli python -m sglang.bench_serving --max-concurrency 16 \
    --model Qwen2.5-72B-Instruct --random-input-len 1024 --random-output-len 1024

# 逐行流式输出（模拟真实运行过程，便于观察 UI 实时刷新）
python -m mocks.cli vllm bench serve --max-concurrency 64 --stream-interval 0.05

# 固定随机种子，结果可复现
python -m mocks.cli --framework sglang --max-concurrency 8 --seed 42

# 保存到文件
python -m mocks.cli vllm bench serve --max-concurrency 32 --save /tmp/mock_vllm.txt
```

输出格式与 `benchscope/parser.py` 的解析正则严格对齐，可直接验证解析结果：

```python
from benchscope.parser import parse_metrics
from mocks.bench_outputs import generate_output

out = generate_output("vllm", concurrency=32, input_len=3072, output_len=1024, seed=1)
print(parse_metrics(out))
```

### 2. mock OpenAI 推理服务

```bash
python -m mocks.openai_server --port 8001
```

- `GET  /v1/models` → 4 个 mock 模型（含 `mock-vllm-model`、`mock-sglang-model`）
- `POST /v1/chat/completions`
  - 非流式：返回 JSON 回答
  - `stream: true`：SSE 流式，先发 `reasoning_content`（思考）增量，再发正文增量，以 `data: [DONE]` 结束

### 3. 只跑 FAKE bench 后端（不启动 mock OpenAI）

```bash
BENCHSCOPE_FAKE_BENCH=1 python -m benchscope.cli --port 8080 --no-browser
```

## 与内置 FAKE 模式的关系

`benchscope/benches/runner.py` 在 `BENCHSCOPE_FAKE_BENCH=1` 时优先使用本目录
`mocks/bench_outputs.py` 生成输出（并按命令自动区分 vLLM / SGLang 风格）；
若 `mocks` 包不可导入（例如 pip 安装的独立环境），自动回退到内置的简化仿真生成器，
因此两种场景行为一致、互不影响。
