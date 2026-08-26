#!/usr/bin/env bash
# 一键启动 / 停止 benchscope 开发环境 + 模拟环境（每次新会话一条命令拉起全部服务）。
#
#   ./scripts/dev.sh           启动（默认端口）
#   ./scripts/dev.sh status    查看三个服务状态
#   ./scripts/dev.sh stop      停止三个服务
#
# 启动内容：
#   1. mock OpenAI 推理服务   http://127.0.0.1:8001  （Sessions 对话 / 连接测试）
#   2. benchscope 后端        http://127.0.0.1:8080  （BENCHSCOPE_FAKE_BENCH=1，
#                                                      无真实 vLLM/SGLang 也能跑任务）
#   3. 前端 vite dev server   http://127.0.0.1:5173  （热重载，proxy /api、/ws 到 8080）
#
# 环境变量覆盖：OPENAI_PORT（默认 8001）、PORT（后端，默认 8080）；前端固定 5173。
# 日志：logs/dev/*.log（openai.log / backend.log / vite.log）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OPENAI_PORT="${OPENAI_PORT:-8001}"
BACKEND_PORT="${PORT:-8080}"
FRONTEND_PORT=5173
LOG_DIR="$ROOT/logs/dev"
mkdir -p "$LOG_DIR"

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="${PYTHON:-python3}"

port_up() { lsof -iTCP:"$1" -sTCP:LISTEN -n -P >/dev/null 2>&1; }

status() {
  for spec in "$OPENAI_PORT:mock OpenAI 服务" "$BACKEND_PORT:benchscope 后端(FAKE)" "$FRONTEND_PORT:前端 vite"; do
    port="${spec%%:*}"; name="${spec#*:}"
    if port_up "$port"; then echo "  [UP]   $name  http://127.0.0.1:$port"; else echo "  [DOWN] $name  http://127.0.0.1:$port"; fi
  done
}

stop() {
  echo "停止服务..."
  for port in "$OPENAI_PORT" "$BACKEND_PORT" "$FRONTEND_PORT"; do
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [ -n "$pids" ]; then
      kill $pids 2>/dev/null || true
      echo "  已停止端口 $port (pid: ${pids//$'\n'/ })"
    fi
  done
  sleep 0.5
  rm -f "$LOG_DIR"/*.pid
  echo "完成。"
}

start_openai() {
  if port_up "$OPENAI_PORT"; then
    echo "  [ok] mock OpenAI 服务已在运行 (http://127.0.0.1:$OPENAI_PORT)"
    return 0
  fi
  echo "  [..] 启动 mock OpenAI 服务 (port $OPENAI_PORT) ..."
  nohup "$PY" -m mocks.openai_server --host 127.0.0.1 --port "$OPENAI_PORT" >"$LOG_DIR/openai.log" 2>&1 &
  echo $! >"$LOG_DIR/openai.pid"
  sleep 1
  if port_up "$OPENAI_PORT"; then
    echo "  [UP]   mock OpenAI 服务  http://127.0.0.1:$OPENAI_PORT"
  else
    echo "  [FAIL] mock OpenAI 启动失败，见 logs/dev/openai.log"
    return 1
  fi
}

start_backend() {
  if port_up "$BACKEND_PORT"; then
    echo "  [ok] benchscope 后端已在运行 (http://127.0.0.1:$BACKEND_PORT)；如需 FAKE 模式请先 ./scripts/dev.sh stop"
    return 0
  fi
  echo "  [..] 启动 benchscope 后端 (FAKE bench, port $BACKEND_PORT) ..."
  nohup env BENCHSCOPE_FAKE_BENCH=1 "$PY" -m benchscope.cli --port "$BACKEND_PORT" --no-browser >"$LOG_DIR/backend.log" 2>&1 &
  echo $! >"$LOG_DIR/backend.pid"
  sleep 2
  if port_up "$BACKEND_PORT"; then
    echo "  [UP]   benchscope 后端  http://127.0.0.1:$BACKEND_PORT"
  else
    echo "  [FAIL] 后端启动失败，见 logs/dev/backend.log"
    return 1
  fi
}

start_frontend() {
  if port_up "$FRONTEND_PORT"; then
    echo "  [ok] 前端 vite 已在运行 (http://127.0.0.1:$FRONTEND_PORT)"
    return 0
  fi
  echo "  [..] 启动前端 vite (port $FRONTEND_PORT) ..."
  nohup npm --prefix "$ROOT/web" run dev >"$LOG_DIR/vite.log" 2>&1 &
  echo $! >"$LOG_DIR/vite.pid"
  sleep 3
  if port_up "$FRONTEND_PORT"; then
    echo "  [UP]   前端 vite  http://127.0.0.1:$FRONTEND_PORT"
  else
    echo "  [FAIL] 前端启动失败，见 logs/dev/vite.log"
    return 1
  fi
}

case "${1:-start}" in
  start)
    echo "========================================================"
    echo "  benchscope 开发 + 模拟环境"
    echo "  mock OpenAI  : http://127.0.0.1:$OPENAI_PORT"
    echo "  后端 (FAKE)  : http://127.0.0.1:$BACKEND_PORT"
    echo "  前端 vite    : http://127.0.0.1:$FRONTEND_PORT"
    echo "  日志         : logs/dev/*.log"
    echo "========================================================"
    start_openai
    start_backend
    start_frontend
    echo
    echo "  全部就绪 → 浏览器打开 http://127.0.0.1:$FRONTEND_PORT"
    echo "  Settings → Inference API 的 Base URL 填 http://127.0.0.1:$OPENAI_PORT 即可联调"
    ;;
  stop) stop ;;
  status) status ;;
  *)
    echo "用法: $0 [start|stop|status]" >&2
    exit 1
    ;;
esac
