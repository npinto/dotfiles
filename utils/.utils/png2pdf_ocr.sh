#!/usr/bin/env bash
# png2pdf_ocr_hash.sh  <slides_folder>  [base_name]
# ──────────────────────────────────────────────────────────────────────────────
# slide_*.png  ──▶  <base>_<hash>.pdf                     (raw, no OCR)
#               └─▶ <base>_<hash>_ocr_compressed.pdf      (searchable, slim)

set -euo pipefail

SLIDES_DIR="${1:?need folder with slide_*.png}"
BASE="${2:-presentation}"

# ────────── deterministic hash from slide contents ──────────
HASH=$(md5sum "${SLIDES_DIR}"/slide_*.png | md5sum | cut -c1-8)

RAW_PDF="${BASE}_${HASH}.pdf"
FINAL_PDF="${BASE}_${HASH}_ocr_compressed.pdf"

echo "➜ Building raw PDF $RAW_PDF ..."
convert "${SLIDES_DIR}"/slide_*.png "$RAW_PDF"

echo "➜ OCR + compress → $FINAL_PDF ..."
ocrmypdf --optimize 3 --clean --rotate-pages --skip-text \
         --output-type pdfa "$RAW_PDF" "$FINAL_PDF"

echo "✅  Raw (no‑OCR):          $RAW_PDF"
echo "✅  OCR‑compressed final:  $FINAL_PDF"

