#!/usr/bin/env bash
# benchscope 一键发布脚本
#
# 用法:
#   ./scripts/release.sh 1.0.4                        # 升版本并发布
#       发布规则：仅 Z（补丁）更新（如 1.0.4->1.0.5）→ 不推送 PyPI，只推送 GitHub tag + release；
#                X.Y（主/次）更新（如 1.0.x->1.1.0）→ 推送 PyPI + GitHub tag + release
#       即：build + (X.Y 变化时)PyPI upload + GitHub Release + git tag + push
#   ./scripts/release.sh 1.0.4 --notes notes.md       # 指定 GitHub Release 说明文件（缺省自动从 VERSION_x_y_z.md 提取迭代摘要）
#   ./scripts/release.sh 1.0.4 --dry-run              # 只升版本/构建/校验，不上传也不提交（用于试跑）
#   ./scripts/release.sh --help
#
# 前置:
#   - 已配置 ~/.pypirc (twine) 或 TWINE_USERNAME/TWINE_PASSWORD 环境变量
#   - GitHub Release：gh CLI 已认证，或 GITHUB_TOKEN/GH_TOKEN 环境变量（二者缺一则跳过 Release 创建，仅推送 tag）
#   - 已配置 ~/.git-credentials + git credential.helper (push 免 token)
#   - 已安装: python -m build, twine, 以及 web/ 的 npm 依赖
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NEW=""
DRY_RUN=0
NOTES_FILE=""

usage() {
  sed -n '1,14p' "$0" | sed 's/^# //'
}

# ---------- 参数解析 ----------
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --notes) NOTES_FILE="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) NEW="$1"; shift ;;
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

# 发布规则：
#   仅 Z（补丁）更新（如 1.0.4 -> 1.0.5）：不推送 PyPI，只推送 GitHub tag + release
#   X.Y（主/次）更新（如 1.0.x -> 1.1.0 或 2.0.0）：推送 PyPI + GitHub tag + release
# 取 X.Y 前两段（稳定提取主/次版本，兼容 dev 后缀如 1.0.7.dev0）
OLD_MM="$(echo "$OLD" | awk -F. '{print $1"."$2}')"
NEW_MM="$(echo "$NEW" | awk -F. '{print $1"."$2}')"
if [ "$OLD_MM" = "$NEW_MM" ]; then
  NEED_PYPI=0
  echo "==> 补丁版本（仅 Z 变化: ${OLD} -> ${NEW}）：跳过 PyPI 上传，仅推送 GitHub tag + release"
else
  NEED_PYPI=1
  echo "==> 主/次版本变化（X.Y: ${OLD_MM} -> ${NEW_MM}）：完整发布 = PyPI + GitHub tag + release"
fi

# ---------- 版本同步 ----------
sed -i '' "s/^version = \".*\"/version = \"$NEW\"/" pyproject.toml
sed -i '' "s/__version__ = \".*\"/__version__ = \"$NEW\"/" benchscope/__init__.py
sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW\"/" web/package.json
sed -i '' "s|>v[0-9][0-9.]*<|>v$NEW<|" web/src/components/TopBar.vue
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

# ---------- 发布到 PyPI（仅主/次版本 X.Y 变化时推送；补丁 Z 变化跳过） ----------
if [ "$NEED_PYPI" -eq 1 ]; then
  # 加固：twine 自身 --retries + 外循环重试 + 单次超时，抵御瞬时网络抖动（SSL EOF 等）
  UPLOAD_RETRIES="${TWINE_UPLOAD_RETRIES:-3}"
  UPLOAD_TIMEOUT="${TWINE_UPLOAD_TIMEOUT:-180}"
  UPLOAD_OK=0
  for i in $(seq 1 "$UPLOAD_RETRIES"); do
    echo "==> 上传 PyPI (第 ${i}/${UPLOAD_RETRIES} 次) ..."
    if timeout "$UPLOAD_TIMEOUT" python3 -m twine upload \
        --non-interactive --disable-progress-bar dist/*; then
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
else
  echo "==> 补丁版本（仅 Z 变化）：跳过 PyPI 上传（产物 dist/ 仍在本地产出）"
fi

# ---------- git 提交 + 打 tag + 推送 ----------
echo "==> git 提交 + 打 tag + 推送 ..."
git add -A
git commit -m "release: benchscope v${NEW}"
git tag "v${NEW}"
git push origin main --tags

# ---------- 生成 GitHub Release 说明并推送 ----------
# 说明文件优先级：--notes 指定 > docs/versions/VERSION_x_y_z.md 自动提取迭代摘要 > 占位
VER_DOC="docs/versions/VERSION_${NEW//./_}.md"
NOTES_TMP="$(mktemp)"
cleanup() { rm -f "$NOTES_TMP"; }
trap cleanup EXIT

if [ -n "$NOTES_FILE" ]; then
  if [ ! -f "$NOTES_FILE" ]; then
    echo "错误: --notes 文件不存在: $NOTES_FILE" >&2
    exit 1
  fi
  cp "$NOTES_FILE" "$NOTES_TMP"
elif [ -f "$VER_DOC" ]; then
  echo "==> 读取 ${VER_DOC} 中的「版本功能清单（Release Notes）」区块作为 Release 说明 ..."
  # 不做机械提取：功能清单由 AI 读取版本内容后总结（先英文后中文）维护在 VERSION 文档该区块；
  # 说明只含功能清单本身，不追加标题/说明段。
  if ! python3 - "$VER_DOC" > "$NOTES_TMP" <<'PYEOF'
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"(?ms)^##\s*版本功能清单（Release Notes）\s*\n(.*?)(?=^##\s|\Z)", src)
if m:
    # 原样输出 AI 总结的功能清单区块（先英文清单 Feature Highlights，后中文清单 功能清单）
    print(m.group(1).rstrip())
else:
    print("（VERSION 文档缺少「版本功能清单（Release Notes）」区块，请用 AI 读取版本内容总结功能清单，"
          "或通过 --notes 指定说明文件。）")
    sys.exit(1)
PYEOF
  then
    echo "⚠️  未生成功能清单：请先用 AI 读取 ${VER_DOC} 总结功能清单与核心功能变化（先英文后中文）"
    echo "   填入「版本功能清单（Release Notes）」区块，或通过 --notes 提供说明文件。" >&2
  fi
else
  echo "（未提供 --notes，也无对应 VERSION 文档，请用 AI 总结功能清单后通过 --notes 提供。）" > "$NOTES_TMP"
fi

create_github_release() {
  local tag="v${NEW}"
  # gh CLI 优先
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh release view "$tag" >/dev/null 2>&1; then
      echo "  GitHub Release $tag 已存在，跳过创建。"
    else
      echo "==> 创建 GitHub Release $tag（gh CLI）..."
      gh release create "$tag" --repo LABELNET/benchscope \
        --title "benchscope v${NEW}" --notes-file "$NOTES_TMP"
    fi
    return 0
  fi
  # 回退：GitHub REST API（GITHUB_TOKEN / GH_TOKEN）
  if [ -n "${GITHUB_TOKEN:-}" ] || [ -n "${GH_TOKEN:-}" ]; then
    echo "==> 创建 GitHub Release $tag（REST API）..."
    python3 - "$tag" "$NOTES_TMP" <<'PYEOF'
import json, os, sys, urllib.error, urllib.request
tag, notes = sys.argv[1], sys.argv[2]
token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
body = open(notes, encoding="utf-8").read()
payload = json.dumps({
    "tag_name": tag, "target_commitish": "main",
    "name": f"benchscope v{tag.lstrip('v')}", "body": body,
    "draft": False, "prerelease": False,
}).encode()
req = urllib.request.Request(
    "https://api.github.com/repos/LABELNET/benchscope/releases",
    data=payload, method="POST",
    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
             "Content-Type": "application/json", "User-Agent": "benchscope-release"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
        print("  OK:", d.get("html_url", ""))
except urllib.error.HTTPError as e:
    # 422 = 已存在则视为成功（幂等）
    if e.code == 422:
        print(f"  GitHub Release {tag} 已存在，跳过创建。")
    else:
        print(f"  GitHub Release 创建失败 (HTTP {e.code}): {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        sys.exit(1)
PYEOF
    return 0
  fi
  echo "警告: 未检测到 gh CLI 或 GITHUB_TOKEN/GH_TOKEN，跳过 GitHub Release 创建（tag 已推送，可在网页手动创建）。" >&2
}
create_github_release

echo ""
echo "✅ 发布完成: benchscope v${NEW}"
if [ "$NEED_PYPI" -eq 1 ]; then
  echo "   PyPI:    https://pypi.org/project/benchscope/${NEW}/"
else
  echo "   PyPI:    （补丁版本，按发布规则已跳过推送）"
fi
echo "   GitHub:  https://github.com/LABELNET/benchscope/releases/tag/v${NEW}"
