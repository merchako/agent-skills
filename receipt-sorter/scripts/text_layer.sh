#!/usr/bin/env bash
# Add a searchable text layer to every PDF under a folder (recursively).
# Usage: text_layer.sh <folder>
# Uses ocrmypdf --skip-text so already-digital PDFs are left untouched.
set -euo pipefail
DIR="${1:?usage: text_layer.sh <folder>}"

command -v ocrmypdf >/dev/null || { echo "ocrmypdf not installed — run: brew install ocrmypdf"; exit 1; }

ok=0; fail=0
while IFS= read -r -d '' f; do
  case "$f" in */_original\ scans/*) continue;; esac
  tmp="${f%.pdf}.__ocr.pdf"
  if ocrmypdf --skip-text --optimize 1 -l eng "$f" "$tmp" >/dev/null 2>&1; then
    mv "$tmp" "$f"; ok=$((ok+1))
  else
    rm -f "$tmp"; fail=$((fail+1)); echo "  FAILED: $f"
  fi
done < <(find "$DIR" -name '*.pdf' -print0)
echo "text layer added: OK=$ok FAIL=$fail"
