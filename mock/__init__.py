"""benchscope mock 调试环境。

在没有真实 vLLM / SGLang 运行环境时，用本包模拟两者的返回数据：

- ``bench_outputs``  生成 vLLM ``vllm bench serve`` 与 SGLang
  ``sglang.bench_serving`` 风格的 bench 结果文本（与 ``benchscope.parser``
  的解析正则严格对齐）。
- ``cli``            可独立运行的 mock bench CLI，模拟真实 bench 命令的输出。
- ``openai_server``  模拟 OpenAI 兼容推理服务（/v1/models + /v1/chat/completions，
  支持 SSE 流式），用于联调 Sessions 对话与 Settings 连接测试。

直接运行示例：

.. code-block:: bash

    # 模拟 vLLM bench 输出
    python -m mock.cli vllm bench serve --max-concurrency 32 --num-prompts 32

    # 模拟 SGLang bench 输出
    python -m mock.cli python -m sglang.bench_serving --max-concurrency 16

    # 启动 mock OpenAI 推理服务（默认 8001 端口）
    python -m mock.openai_server --port 8001

详细说明见 ``mock/README.md``。
"""
