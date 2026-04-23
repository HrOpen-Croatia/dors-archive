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

# The copy preserved wget's relative `../` paths, which used to resolve
# into main/ (parent of dors-2023/). Now they resolve into the archive
# root which isn't useful — everything reachable via `..` from the old
# location actually lives under /main/. dors-2023/ is only one level
# deep, so every `../` in its HTML maps unambiguously to `/main/`.
python - <<'PY'
from pathlib import Path

dest = Path("archive/2023")
changed = 0
for html in dest.rglob("*.html"):
    orig = html.read_text(encoding="utf-8", errors="replace")
    new = orig.replace("../", "/main/")
    if new != orig:
        html.write_text(new, encoding="utf-8")
        changed += 1
print(f"rewrote ../ -> /main/ in {changed} files under {dest}")
PY

if [[ ! -f "${DEST}/index.html" ]]; then
    cp "${SRC}/index.html" "${DEST}/index.html" 2>/dev/null || true
fi

echo "==> 2023 reconciled: $(find "${DEST}" -name '*.html' | wc -l) HTML files"
