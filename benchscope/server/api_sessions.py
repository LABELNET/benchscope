"""会话 API：创建、查询、删除会话，SSE 流式对话。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from benchscope.server.state import state

log = logging.getLogger("benchscope.api_sessions")

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: str = ""
    model: str = ""
    system_prompt: str = ""


class ChatRequest(BaseModel):
    message: str
    model: str = ""


@router.get("")
def list_sessions():
    return {"sessions": state.sessions.list_sessions()}


@router.post("")
def create_session(req: CreateSessionRequest):
    session = state.sessions.create_session(req.title, req.model, req.system_prompt)
    return {"session": session.to_dict()}


@router.get("/{session_id}")
def get_session(session_id: str):
    session = state.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.delete("/{session_id}")
def delete_session(session_id: str):
    state.sessions.delete_session(session_id)
    return {"ok": True}


@router.delete("")
def clear_sessions():
    state.sessions.clear_all()
    return {"ok": True}


@router.post("/{session_id}/chat")
def chat(session_id: str, req: ChatRequest):
    session = state.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    def event_stream():
        for chunk in state.sessions.stream_chat(session_id, req.message, model=req.model):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
