#!/usr/bin/env bash
# =============================================================================
# benchscope 功能测试一键入口
#
# 用法:
#   ./tests/run_tests.sh              # 全量: API 测试 + WebUI 测试
#   ./tests/run_tests.sh --api-only   # 仅 API 测试
#   ./tests/run_tests.sh --ui-only    # 仅 WebUI 测试
#
# 行为:
#   1. 确保 mock OpenAI 推理服务在 :8001 运行（mocks/ 目录，唯一 mock 来源）
#   2. 以「临时数据目录 + FAKE bench」启动被测服务（默认 :18081，
#      与开发环境 :8080 隔离，测试不污染 ~/.benchscope 真实数据）
#   3. 执行 pytest: tests/api（接口功能）+ tests/webui（页面功能）
#   4. 退出时自动清理临时数据目录与进程
#
# 环境变量（可覆盖默认值）:
#   BS_TEST_PORT    被测服务端口（默认 18081）
#   BS_MOCK_PORT    mock OpenAI 端口（默认 8001）
#   BS_CHROMIUM_PATH WebUI 测试浏览器可执行文件
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TEST_PORT="${BS_TEST_PORT:-18081}"
MOCK_PORT="${BS_MOCK_PORT:-8001}"
TEST_URL="http://127.0.0.1:${TEST_PORT}"
MOCK_URL="http://127.0.0.1:${MOCK_PORT}"

ONLY="all"
for arg in "$@"; do
  case "$arg" in
    --api-only) ONLY="api" ;;
    --ui-only) ONLY="ui" ;;
  esac
done

# ---------------------------------------------------------------------------
# 1. mock OpenAI（mocks/ 是唯一 mock 来源，tests/ 不再携带 mock 代码）
# ---------------------------------------------------------------------------
echo "==> [1/3] 检查 mock OpenAI 服务 (${MOCK_URL})"
if curl -sf "${MOCK_URL}/v1/models" >/dev/null 2>&1; then
  echo "    已运行，复用"
else
  echo "    启动 mocks.openai_server ..."
  (cd "$ROOT" && nohup python -m mocks.openai_server --port "$MOCK_PORT" \
    >/tmp/benchscope-mock.log 2>&1 &)
  for _ in $(seq 1 40); do
    curl -sf "${MOCK_URL}/v1/models" >/dev/null 2>&1 && break
    sleep 0.5
  done
  curl -sf "${MOCK_URL}/v1/models" >/dev/null 2>&1 \
    || { echo "ERROR: mock OpenAI 启动失败，见 /tmp/benchscope-mock.log"; exit 1; }
  echo "    已就绪"
fi

# ---------------------------------------------------------------------------
# 2. 被测服务（临时数据目录 + FAKE bench）
# ---------------------------------------------------------------------------
echo "==> [2/3] 启动被测服务 (${TEST_URL}, 临时数据目录 + FAKE bench)"
if curl -sf "${TEST_URL}/api/version" >/dev/null 2>&1; then
  echo "ERROR: 端口 ${TEST_PORT} 已被占用（${TEST_URL} 已有服务）。请停掉或设置 BS_TEST_PORT 换端口。"
  exit 1
fi

DATA_DIR="$(mktemp -d /tmp/benchscope-test.XXXXXX)"
SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$DATA_DIR"
}
trap cleanup EXIT

BENCHSCOPE_FAKE_BENCH=1 BENCHSCOPE_DATA_DIR="$DATA_DIR" \
  python -m benchscope.cli --port "$TEST_PORT" --no-browser \
  >/tmp/benchscope-test-server.log 2>&1 &
SERVER_PID=$!

READY=0
for _ in $(seq 1 120); do
  if curl -sf "${TEST_URL}/api/version" >/dev/null 2>&1; then READY=1; break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then break; fi
  sleep 0.5
done
if [ "$READY" != "1" ]; then
  echo "ERROR: 被测服务未就绪，见 /tmp/benchscope-test-server.log"
  tail -50 /tmp/benchscope-test-server.log || true
  exit 1
fi
echo "    已就绪"

export BS_TEST_URL="$TEST_URL"
export BS_MOCK_URL="$MOCK_URL"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# ---------------------------------------------------------------------------
# 3. 执行测试
# ---------------------------------------------------------------------------
echo "==> [3/3] 执行测试"
FAILED=0

if [ "$ONLY" = "all" ] || [ "$ONLY" = "api" ]; then
  echo "---- API 测试 (tests/api) ----"
  if ! python -m pytest tests/api -q; then FAILED=1; fi
fi

if [ "$ONLY" = "all" ] || [ "$ONLY" = "ui" ]; then
  echo "---- WebUI 测试 (tests/webui) ----"
  if [ ! -x "${BS_CHROMIUM_PATH:-/home/yuanmingzhuo/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome}" ]; then
    echo "SKIP: 未找到 Chromium（可设置 BS_CHROMIUM_PATH 指定浏览器路径）"
  elif ! python -m pytest tests/webui -q; then
    FAILED=1
  fi
fi

if [ "$FAILED" != "0" ]; then
  echo "==> 测试未通过，详情见上。服务日志: /tmp/benchscope-test-server.log"
  exit 1
fi
echo "==> 全部测试通过 ✅"
