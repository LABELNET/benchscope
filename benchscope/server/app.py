"""FastAPI 应用装配：API 路由 + WebSocket + 前端静态托管。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from benchscope.server import api_config, api_logs, api_test
from benchscope.server.state import state

log = logging.getLogger("benchscope.app")

WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.monitor.start()
    yield
    state.monitor.stop()
    state.tests.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="benchscope",
        description="vLLM / SGLang 推理服务性能测试工具",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_config.router)
    app.include_router(api_test.router)
    app.include_router(api_logs.router)

    # ---------------- WebSocket ----------------
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        import asyncio
        import json

        loop = asyncio.get_running_loop()
        state.hub.register(ws, loop)
        try:
            # 连接后立即推送一次状态
            snap = state.monitor.check_once(broadcast=False)
            snap["web"] = "ready"
            await ws.send_text(json.dumps({"type": "status", "status": snap}, ensure_ascii=False))
            run = state.tests.current
            if run:
                await ws.send_text(
                    json.dumps({"type": "run_snapshot", "run": run.snapshot()}, ensure_ascii=False)
                )
            while True:
                await ws.receive_text()  # 保持连接，忽略客户端消息
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            state.hub.unregister(ws)

    # ---------------- 前端静态托管 ----------------
    assets_dir = WEBUI_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return _spa_response()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path == "ws":
            raise HTTPException(status_code=404, detail="Not Found")
        return _spa_response()

    return app


def _spa_response():
    index = WEBUI_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="前端未构建，请先运行 `npm run build` 或使用 Vite dev server")
