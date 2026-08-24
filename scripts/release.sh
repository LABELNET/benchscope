#!/usr/bin/env bash
# benchscope 一键发布脚本
#
# 用法:
#   ./scripts/release.sh 1.0.4                 # 升版本并完整发布（build + upload + git tag + push）
#   ./scripts/release.sh 1.0.4 --dry-run       # 只升版本/构建/校验，不上传也不提交（用于试跑）
#   ./scripts/release.sh --help
#
# 前置:
#   - 已配置 ~/.pypirc (twine) 或 TWINE_USERNAME/TWINE_PASSWORD 环境变量
#   - 已配置 ~/.git-credentials + git credential.helper (push 免 token)
#   - 已安装: python -m build, twine, 以及 web/ 的 npm 依赖
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NEW=""
DRY_RUN=0

usage() {
  sed -n '1,12p' "$0" | sed 's/^# //'
}

# ---------- 参数解析 ----------
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    --help|-h) usage; exit 0 ;;
    *) NEW="$a" ;;
  esac
done

if [ -z "$NEW" ]; then
  echo "错误: 请提供版本号，如 1.0.4" >&2
  usage >&2
  exit 1
fi

if ! [[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "错误: 版本号格式应为 X.Y.Z，如 1.0.4" >&2
  exit 1
fi

# ---------- 前置检查 ----------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "错误: 当前目录不是 git 仓库" >&2; exit 1
fi
if [ -z "$(git status --porcelain)" ]; then
  : # 干净
elif [ "$DRY_RUN" -eq 1 ]; then
  echo "提示: 工作区有未提交改动，--dry-run 不影响，继续。" >&2
else
  echo "错误: 工作区有未提交改动，请先提交或使用 --dry-run 试跑。" >&2
  echo "      （${NEW} 发布前请确保干净，以便区分『版本号/前端』改动与业务改动。）" >&2
  exit 1
fi

# 读取旧版本（以 pyproject.toml 为准）
OLD="$(grep -E '^version = ' pyproject.toml | head -1 | sed -n 's/.*"\(.*\)".*/\1/p')"
echo "版本: ${OLD} -> ${NEW}"

# ---------- 版本同步 ----------
sed -i "s/^version = \".*\"/version = \"$NEW\"/" pyproject.toml
sed -i "s/__version__ = \".*\"/__version__ = \"$NEW\"/" benchscope/__init__.py
sed -i "s/\"version\": \".*\"/\"version\": \"$NEW\"/" web/package.json
sed -i "s|>v[0-9][0-9.]*<|>v$NEW<|" web/src/components/TopBar.vue
echo "已同步版本: pyproject.toml / benchscope/__init__.py / web/package.json / TopBar badge(前端)"

# ---------- 构建 ----------
echo "==> 重建前端 (vite build) ..."
( cd "$ROOT/web" && npm run build ) >/dev/null

echo "==> 构建 sdist + wheel ..."
rm -rf dist
python3 -m build >/dev/null

echo "==> twine check ..."
python3 -m twine check dist/*

if [ "$DRY_RUN" -eq 1 ]; then
  echo ""
  echo "[dry-run] 完成。未上传/未提交。产物:"
  ls -1 dist/
  exit 0
fi

# ---------- 发布到 PyPI ----------
# 加固：twine 自身 --retries + 外循环重试 + 单次超时，抵御瞬时网络抖动（SSL EOF 等）
UPLOAD_RETRIES="${TWINE_UPLOAD_RETRIES:-3}"
UPLOAD_TIMEOUT="${TWINE_UPLOAD_TIMEOUT:-180}"
UPLOAD_OK=0
for i in $(seq 1 "$UPLOAD_RETRIES"); do
  echo "==> 上传 PyPI (第 ${i}/${UPLOAD_RETRIES} 次) ..."
  if timeout "$UPLOAD_TIMEOUT" python3 -m twine upload \
      --non-interactive --disable-progress-bar --retries 3 dist/*; then
    UPLOAD_OK=1
    break
  else
    echo "  本次上传未成功，稍后重试..." >&2
    sleep 5
  fi
done
if [ "$UPLOAD_OK" -ne 1 ]; then
  echo "错误: PyPI 上传在 ${UPLOAD_RETRIES} 次尝试后仍失败，已中止（未打 tag/未推送）。" >&2
  exit 1
fi

# ---------- git 提交 + 打 tag + 推送 ----------
echo "==> git 提交 + 打 tag + 推送 ..."
git add -A
git commit -m "release: benchscope v${NEW}"
git tag "v${NEW}"
git push origin main --tags

echo ""
echo "✅ 发布完成: benchscope v${NEW}"
echo "   PyPI:    https://pypi.org/project/benchscope/${NEW}/"
echo "   GitHub:  https://github.com/LABELNET/benchscope/releases/tag/v${NEW}"
