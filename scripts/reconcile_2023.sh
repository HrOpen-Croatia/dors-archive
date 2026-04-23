#!/usr/bin/env bash
# 2023 content lives under main/dors-2023/. Surface it at /2023/ too.
set -euo pipefail

SRC="archive/main/dors-2023"
DEST="archive/2023"

if [[ ! -d "${SRC}" ]]; then
    echo "missing: ${SRC} (did main/ get crawled?)" >&2
    exit 1
fi

rm -rf "${DEST}"
cp -a "${SRC}" "${DEST}"

python scripts/rewrite_path_prefix.py \
    --in "${DEST}" \
    --from "/main/dors-2023" \
    --to   "/2023"

if [[ ! -f "${DEST}/index.html" ]]; then
    cp "${SRC}/index.html" "${DEST}/index.html" 2>/dev/null || true
fi

echo "==> 2023 reconciled: $(find "${DEST}" -name '*.html' | wc -l) HTML files"
