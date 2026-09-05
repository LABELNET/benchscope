#!/usr/bin/env bash
# 打包 bs-perfs-threshold 技能为可分发的 tar.gz
#
# 用法: ./scripts/package.sh [输出目录]
#   输出目录缺省为 ./dist
# 产物: <输出目录>/bs-perfs-threshold-<version>.tar.gz
#       （version 从 SKILL.md 的 frontmatter 读取）
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "$SKILL_DIR")"
VERSION="$(grep -m1 '^version:' "$SKILL_DIR/SKILL.md" | sed 's/version: *//' | tr -d '"' | tr -d "'" | tr -d '\r' || true)"
VERSION="${VERSION:-0.0.0}"
OUT_DIR="${1:-$SKILL_DIR/dist}"

mkdir -p "$OUT_DIR"
ARCHIVE="$OUT_DIR/${NAME}-${VERSION}.tar.gz"

tar -czf "$ARCHIVE" -C "$(dirname "$SKILL_DIR")" \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='.DS_Store' \
  --exclude='*.pyc' \
  --exclude='dist' \
  "$NAME"

echo "✅ 打包完成: $ARCHIVE"

# 产物校验：可解压且包含必需文件
tar -tzf "$ARCHIVE" >/dev/null || { echo "❌ 产物损坏（无法解压）" >&2; exit 1; }
for required in "SKILL.md" "README.md" "scripts/package.sh"; do
  if ! tar -tzf "$ARCHIVE" | grep -q "${NAME}/${required}"; then
    echo "❌ 产物缺少必需文件: ${required}" >&2
    exit 1
  fi
done
echo "✅ 产物校验通过（可解压，含 SKILL.md / README.md / scripts/package.sh）"
