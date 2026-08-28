#!/usr/bin/env bash
# 一键启动 / 停止 benchscope 开发环境 + 模拟环境（每次新会话一条命令拉起全部服务）。
#
#   ./scripts/dev.sh           启动（默认端口）
#   ./scripts/dev.sh status    查看三个服务状态
#   ./scripts/dev.sh stop      停止三个服务
#
# 启动内容：
#   1. mock OpenAI 推理服务   http://127.0.0.1:8001  （Sessions 对话 / 连接测试）
#   2. 前端构建 + benchscope 后端 http://127.0.0.1:8080（统一对外入口：
#      后端托管 vite build 产物 benchscope/webui，BENCHSCOPE_FAKE_BENCH=1
#      无真实 vLLM/SGLang 也能跑任务）。前端不单独开 5173 dev server。
#
# 每次 start 都会重新执行前端构建（npm run build），确保 8080 上的页面为最新代码。
# 环境变量覆盖：OPENAI_PORT（默认 8001）、PORT（后端，默认 8080）。
# 日志：logs/dev/*.log（openai.log / backend.log / build.log）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OPENAI_PORT="${OPENAI_PORT:-8001}"
BACKEND_PORT="${PORT:-8080}"
LOG_DIR="$ROOT/logs/dev"
mkdir -p "$LOG_DIR"

# 优先 .venv，但 .venv 缺 fastapi/uvicorn（如指向系统 python 的残缺 venv）时回退 ${PYTHON:-python3}
PY="$ROOT/.venv/bin/python"
if ! { [ -x "$PY" ] && "$PY" -c "import fastapi, uvicorn" >/dev/null 2>&1; }; then
  PY="${PYTHON:-python3}"
fi

# 环境可能没有 lsof/ss/fuser，统一用 Python 探测端口（TCP 连接成功 = 已被监听）。
# 注意不能用 bind 探测：macOS(BSD) 下 SO_REUSEADDR 允许 wildcard 覆盖特定地址监听，会误判。
port_up() {
  python3 - "$1" <<'PY'
import socket, sys
s = socket.socket()
s.settimeout(0.5)
try:
    s.connect(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)   # 连接失败 → DOWN
else:
    s.close()
    sys.exit(0)   # 连接成功 → UP
PY
}

# 查找监听指定端口的进程 PID：优先 lsof（macOS/Linux），无 lsof 时回退 /proc（Linux）
pids_on_port() {
  python3 - "$1" <<'PY'
import os, re, shutil, subprocess, sys
port = sys.argv[1]
lsof = shutil.which("lsof")
if lsof:
    try:
        out = subprocess.run([lsof, "-tiTCP:" + port, "-sTCP:LISTEN"],
                             capture_output=True, text=True, timeout=5).stdout
        pids = [p for p in out.split() if p.isdigit()]
        if pids:
            print(" ".join(pids))
            sys.exit(0)
    except Exception:
        pass
hexport = "%04X" % int(port)
inodes = set()
for f in ("/proc/net/tcp", "/proc/net/tcp6"):
    try:
        with open(f) as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 10 and parts[1].endswith(":" + hexport) and parts[3] == "0A":
                    inodes.add(parts[9])
    except OSError:
        pass
pids = set()
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        for fd in os.listdir("/proc/%s/fd" % pid):
            try:
                tgt = os.readlink("/proc/%s/fd/%s" % (pid, fd))
            except OSError:
                continue
            m = re.match(r"socket:\[(\d+)\]", tgt)
            if m and m.group(1) in inodes:
                pids.add(int(pid))
    except OSError:
        continue
print(" ".join(str(p) for p in sorted(pids)))
PY
}

status() {
  for spec in "$OPENAI_PORT:mock OpenAI 服务" "$BACKEND_PORT:benchscope 后端 + 前端(统一入口 8080)"; do
    port="${spec%%:*}"; name="${spec#*:}"
    if port_up "$port"; then echo "  [UP]   $name  http://127.0.0.1:$port"; else echo "  [DOWN] $name  http://127.0.0.1:$port"; fi
  done
}

stop() {
  echo "停止服务..."
  for port in "$OPENAI_PORT" "$BACKEND_PORT"; do
    pids="$(pids_on_port "$port")"
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
  sleep 3
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
  sleep 3
  if port_up "$BACKEND_PORT"; then
    echo "  [UP]   benchscope 后端  http://127.0.0.1:$BACKEND_PORT"
  else
    echo "  [FAIL] 后端启动失败，见 logs/dev/backend.log"
    return 1
  fi
}

# 每次 start 前强制重新构建前端（vite build → benchscope/webui），保证 8080 上是最新代码
build_frontend() {
  echo "  [..] 编译前端 (npm run build → benchscope/webui) ..."
  # 优先使用现代 Node（≥18，vite5 要求），并清除 VS Code shim 注入的 NODE_OPTIONS / BASH_ENV
  local node_bin=""
  local cand
  for cand in /root/.workbuddy/binaries/node/versions/*/bin/node "${CODEBUDDY_NODE_BIN:-}"; do
    [ -z "$cand" ] && continue
    if [ -x "$cand" ] && "$cand" -e "process.exit(Number(process.versions.node.split('.')[0]) < 18 ? 1 : 0)" 2>/dev/null; then
      node_bin="$cand"
      break
    fi
  done
  if [ -n "$node_bin" ]; then
    env -u NODE_OPTIONS -u BASH_ENV PATH="$(dirname "$node_bin"):$PATH" npm --prefix "$ROOT/web" run build >"$LOG_DIR/build.log" 2>&1
  else
    env -u NODE_OPTIONS -u BASH_ENV npm --prefix "$ROOT/web" run build >"$LOG_DIR/build.log" 2>&1
  fi
  if [ -d "$ROOT/benchscope/webui/assets" ] && [ -f "$ROOT/benchscope/webui/index.html" ]; then
    echo "  [ok]  前端编译完成 → benchscope/webui"
  else
    echo "  [FAIL] 前端编译失败，见 logs/dev/build.log"
    return 1
  fi
}

case "${1:-start}" in
  start)
    echo "========================================================"
    echo "  benchscope 开发 + 模拟环境"
    echo "  mock OpenAI : http://127.0.0.1:$OPENAI_PORT"
    echo "  统一入口    : http://127.0.0.1:$BACKEND_PORT  (前端静态页 + API，每次 start 自动重新编译前端)"
    echo "  日志        : logs/dev/*.log"
    echo "========================================================"
    start_openai
    build_frontend
    start_backend
    echo
    echo "  全部就绪 → 浏览器打开 http://127.0.0.1:$BACKEND_PORT"
    echo "  Settings → Inference API 的 Base URL 填 http://127.0.0.1:$OPENAI_PORT 即可联调"
    ;;
  stop) stop ;;
  status) status ;;
  *)
    echo "用法: $0 [start|stop|status]" >&2
    exit 1
    ;;
esac
