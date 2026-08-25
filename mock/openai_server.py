"""本地联调用的模拟 OpenAI 兼容推理服务。

用于 Settings 的"测试连接"、Performance 的 vLLM/SGLang bench（作为目标 API）
以及 Sessions 的 SSE 流式对话。行为：

- ``GET  /v1/models``            返回模型列表
- ``POST /v1/chat/completions``  非流式返回 JSON；``stream: true`` 时返回
  SSE 流（``data: {...}`` 增量块 + 结束标志 ``data: [DONE]``），并在内容前
  模拟一段 ``reasoning_content``（思考过程），便于联调 Sessions 的思考展示。

启动：

.. code-block:: bash

    python -m mock.openai_server                 # http://127.0.0.1:8001
    python -m mock.openai_server --port 8001 --host 127.0.0.1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="mock-openai")

MODELS = [
    {"id": "/data/disk3/DeepSeek-V4-Flash-0731-W8A8", "object": "model", "owned_by": "mock"},
    {"id": "Qwen2.5-72B-Instruct", "object": "model", "owned_by": "mock"},
    {"id": "mock-vllm-model", "object": "model", "owned_by": "mock"},
    {"id": "mock-sglang-model", "object": "model", "owned_by": "mock"},
]

# 模拟思考文本（reasoning_content）与回复模板
_THINKING = (
    "好的，用户的问题是：{question}\n"
    "让我先梳理一下关键信息，然后组织一个清晰的回答。"
)
_REPLY = (
    "收到你的问题：{question}\n\n"
    "这是一个 mock 环境的模拟回答（没有真实推理服务）。\n"
    "你可以用它来联调：设置页的连接测试、Performance 的基准任务、"
    "以及 Sessions 的流式对话。\n\n"
    "当前模型：{model}，返回时间 {time}。"
)


def _mock_reply(question: str, model: str, max_tokens: int) -> str:
    reply = _REPLY.format(question=question, model=model, time=time.strftime("%H:%M:%S"))
    if max_tokens and max_tokens > 0:
        reply = reply[: max_tokens * 4]  # 粗略按字符截断，模拟 max_tokens
    return reply


@app.get("/v1/models")
def list_models():
    return {"object": "list", "data": MODELS}


@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    msgs = body.get("messages", [])
    prompt = msgs[-1]["content"] if msgs else "hi"
    model = body.get("model", MODELS[0]["id"])
    max_tokens = int(body.get("max_tokens", 64) or 64)
    stream = bool(body.get("stream", False))

    reply = _mock_reply(prompt, model, max_tokens)
    thinking = _THINKING.format(question=prompt[:80])

    if stream:
        return StreamingResponse(
            _sse_stream(model, reply, thinking),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return JSONResponse({
        "id": "chatcmpl-" + uuid.uuid4().hex[:12],
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply},
            "finish_reason": "length",
        }],
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(reply.split()),
            "total_tokens": len(prompt.split()) + len(reply.split()),
        },
    })


async def _sse_stream(model: str, reply: str, thinking: str) -> AsyncGenerator[str, None]:
    """按字产出 SSE 增量块：先 reasoning_content（思考），再 content。"""
    created = int(time.time())
    cid = "chatcmpl-" + uuid.uuid4().hex[:12]

    def chunk(delta: dict, finish: str | None = None) -> str:
        return json.dumps({
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }, ensure_ascii=False)

    # 模拟思考过程（reasoning_content 增量）
    for i in range(0, len(thinking), 8):
        yield f"data: {chunk({'reasoning_content': thinking[i:i + 8]})}\n\n"
        await asyncio.sleep(0.01)

    # 回复内容增量
    yield f"data: {chunk({'role': 'assistant', 'content': ''})}\n\n"
    for i in range(0, len(reply), 6):
        yield f"data: {chunk({'content': reply[i:i + 6]})}\n\n"
        await asyncio.sleep(0.015)

    yield f"data: {chunk({}, finish='stop')}\n\n"
    yield "data: [DONE]\n\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mock.openai_server", description="mock OpenAI 兼容推理服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args(argv)

    import uvicorn

    print(f"* mock OpenAI server: http://{args.host}:{args.port}")
    print(f"* 模型列表: {', '.join(m['id'] for m in MODELS)}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
