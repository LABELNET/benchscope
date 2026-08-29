"""FastAPI 应用装配：API 路由 + WebSocket + 前端静态托管。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from benchscope import __version__
from benchscope.server import api_config, api_logs, api_tasks, api_dashboard, api_sessions, api_test, api_benchs, api_skills
from benchscope.server.state import state

log = logging.getLogger("benchscope.app")

WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"


def _version_display() -> str:
    """版本显示：开发中 v1.0.6-dev，正式发布 v1.0.6。"""
    base = __version__.split(".dev")[0]
    dev = ".dev" in __version__
    return f"v{base}-dev" if dev else f"v{base}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.monitor.start()
    yield
    state.monitor.stop()
    state.tasks.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="benchscope",
        description="LLM inference performance testing tool. Supports vLLM, SGLang, and any OpenAI-compatible API.",
        version=__version__,
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
    app.include_router(api_tasks.router)
    app.include_router(api_logs.router)
    app.include_router(api_dashboard.router)
    app.include_router(api_sessions.router)
    # 精度测试（Accuracy）API：路由/模型已实现，统一随服务挂载（覆盖 /api/test*）
    app.include_router(api_test.router)
    # 内置 bench 引擎 API（引擎清单 / 详情 / 环境校验）
    app.include_router(api_benchs.router)
    # 内置技能清单 API（Settings → Skills）
    app.include_router(api_skills.router)

    @app.get("/api/version", include_in_schema=False)
    def version():
        return {"version": __version__, "display": _version_display()}

    # ---------------- WebSocket ----------------
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        import asyncio
        import json

        loop = asyncio.get_running_loop()
        state.hub.register(ws, loop)
        try:
            snap = state.monitor.check_once(broadcast=False)
            snap["web"] = "ready"
            await ws.send_text(json.dumps({"type": "status", "status": snap}, ensure_ascii=False))
            # 推送所有任务快照
            for task in state.tasks.list_tasks():
                await ws.send_text(json.dumps({"type": "task_snapshot", "task_id": task["task_id"], "task": task}, ensure_ascii=False))
            while True:
                await ws.receive_text()
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

    @app.get("/bs-logo.png", include_in_schema=False)
    def logo():
        logo_path = WEBUI_DIR / "bs-logo.png"
        if logo_path.exists():
            return FileResponse(logo_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Logo not found")

    @app.get("/blue_logo.png", include_in_schema=False)
    def blue_logo():
        logo_path = WEBUI_DIR / "blue_logo.png"
        if logo_path.exists():
            return FileResponse(logo_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Logo not found")

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
