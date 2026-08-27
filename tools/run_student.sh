#!/usr/bin/env bash
set -euo pipefail

SRC="$1"
OUT="$2"
mkdir -p "$OUT"

BASE="$(basename "$SRC" .s)"
WORK="$(mktemp -d)"
cp "$SRC" "$WORK/"

( cd "$WORK" && python3 "$OLDPWD/assembler.py" "$BASE.s" )

cp "$WORK/${BASE}_instr.hex.txt" "$OUT/text.hex"
cp "$WORK/${BASE}_instr.bin.txt" "$OUT/text.bin"
cp "$WORK/${BASE}_data.hex.txt"  "$OUT/data.hex" 2>/dev/null || true
cp "$WORK/${BASE}_data.bin.txt"  "$OUT/data.bin" 2>/dev/null || true

rm -rf "$WORK"
