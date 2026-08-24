"""本地联调用的模拟 OpenAI 兼容推理服务（/v1/models + /v1/chat/completions）。"""
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="mock-openai")

MODELS = [
    {"id": "/data/disk3/DeepSeek-V4-Flash-0731-W8A8", "object": "model", "owned_by": "mock"},
    {"id": "Qwen2.5-72B-Instruct", "object": "model", "owned_by": "mock"},
]


@app.get("/v1/models")
def list_models():
    return {"object": "list", "data": MODELS}


@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    msgs = body.get("messages", [])
    prompt = msgs[-1]["content"] if msgs else "hi"
    # 生成与输入等长的模拟输出
    n = body.get("max_tokens", 64)
    words = ["token%d" % i for i in range(n)]
    time.sleep(0.01)
    return JSONResponse({
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", MODELS[0]["id"]),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": " ".join(words)},
            "finish_reason": "length",
        }],
        "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": n, "total_tokens": len(prompt.split()) + n},
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
