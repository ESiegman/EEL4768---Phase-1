#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DIST="$ROOT/dist"
rm -rf "$DIST"
mkdir -p "$DIST/output"

shopt -s nullglob
sources=(*.s)
if [ ${#sources[@]} -eq 0 ]; then
    echo "no .s files in the repo root" >&2
    exit 1
fi

for src in "${sources[@]}"; do
    base="${src%.s}"
    out="$DIST/output/$base"
    mkdir -p "$out"
    echo "assembling $src"
    bash tools/run_student.sh "$src" "$out"
done

for f in assembler.py README.md; do
    [ -f "$f" ] && cp "$f" "$DIST/"
done
cp "${sources[@]}" "$DIST/"

{
    echo "build:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "commit:  ${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
    echo "ref:     ${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)}"
    echo "sources: ${sources[*]}"
} > "$DIST/BUILDINFO.txt"

echo
echo "staged in dist/:"
find "$DIST" -type f | sed "s|$DIST|dist|"
