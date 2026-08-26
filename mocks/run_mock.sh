#!/usr/bin/env bash
# 一键启动 benchscope mock 调试环境（无真实 vLLM / SGLang 也可完整联调）。
#
# 启动内容：
#   1. mock OpenAI 推理服务   http://127.0.0.1:8001  （Sessions 对话 / 连接测试）
#   2. benchscope 后端         http://127.0.0.1:8080  （BENCHSCOPE_FAKE_BENCH=1，
#                                                      无需真实 bench CLI 即可跑任务）
#
# 前端另行启动：cd web && npm run dev  →  http://127.0.0.1:5173
#
# 用法：
#   ./mocks/run_mock.sh                 # 默认端口 8001 / 8080
#   OPENAI_PORT=9001 PORT=9000 ./mocks/run_mock.sh
#   NO_OPENAI=1 ./mocks/run_mock.sh     # 只启动后端（不需要对话功能时）
#
# 按 Ctrl+C 退出，两个进程都会被终止。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENAI_PORT="${OPENAI_PORT:-8001}"
PORT="${PORT:-8080}"

# 优先使用项目虚拟环境，否则用系统 python
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi

echo "========================================================"
echo "  BenchScope mock 调试环境"
echo "  mock OpenAI server : http://127.0.0.1:${OPENAI_PORT}"
echo "  benchscope 后端    : http://127.0.0.1:${PORT}  (FAKE bench)"
echo "========================================================"

OPENAI_PID=""
cleanup() {
  if [ -n "$OPENAI_PID" ] && kill -0 "$OPENAI_PID" 2>/dev/null; then
    echo; echo "停止 mock OpenAI server (pid $OPENAI_PID)..."
    kill "$OPENAI_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [ "${NO_OPENAI:-0}" != "1" ]; then
  echo "[mock] 启动 mock OpenAI server ..."
  "$PY" -m mocks.openai_server --host 127.0.0.1 --port "$OPENAI_PORT" &
  OPENAI_PID=$!
  sleep 1.5
fi

echo "[mock] 启动 benchscope 后端（BENCHSCOPE_FAKE_BENCH=1）..."
echo "[mock] Settings → Inference API 的 Base URL 可填 http://127.0.0.1:${OPENAI_PORT}"
cd "$ROOT"
BENCHSCOPE_FAKE_BENCH=1 "$PY" -m benchscope.cli --port "$PORT" --no-browser
