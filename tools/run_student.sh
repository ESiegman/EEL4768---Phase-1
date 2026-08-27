#!/usr/bin/env bash
set -euo pipefail

SRC="$1"
OUT="$2"
mkdir -p "$OUT"

WORK="$(mktemp -d)"
cp "$SRC" "$WORK/"
BASE="$(basename "$SRC" .s)"
( cd "$WORK" && python3 "$OLDPWD/assembler.py" "$BASE.s" )
cp "$WORK/${BASE}_sol.hex.txt"       "$OUT/text.hex"
cp "$WORK/${BASE}_sol.bin.txt"       "$OUT/text.bin"
cp "$WORK/${BASE}_sol_data.hex.txt"  "$OUT/data.hex" 2>/dev/null || true
cp "$WORK/${BASE}_sol_data.bin.txt"  "$OUT/data.bin" 2>/dev/null || true
rm -rf "$WORK"
