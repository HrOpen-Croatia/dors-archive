#!/usr/bin/env bash
# Crawl the historical (pre-2013) DORS/CLUC sites that live on close.open.hr.
#
# close.open.hr is not public; we reach it via an SSH port forward:
#
#   ssh -f -N -L 18088:localhost:80 -p 22 andrei@close.open.hr
#
# Apache on close.open.hr serves each year's site under a directory path:
#   /var/www/dors96            -> http://localhost:18088/dors96/
#   /var/www/dc2005            -> http://localhost:18088/dc2005/index.shtml
#   ...
#
# This script crawls each of those into archive/<year>/ so the final
# archive is uniform: every year is a folder named by the 4-digit year.

set -euo pipefail

BASE="${BASE:-http://localhost:18088}"

# Mapping: directory-on-close -> year-in-archive, with a seed URL suffix
# because some sites have non-standard index files (index.shtml).
# Format: "<remote_path> <archive_year> <seed_suffix>"
TARGETS=(
    "dors96       1996  /"
    "dors97       1997  /"
    "dors98       1998  /"
    "dors99       1999  /"
    "dors2000     2000  /"
    "dors2001     2001  /"
    "dors2002     2002  /"
    "clucdors2004 2004  /"
    "dc2005       2005  /index.shtml"
    "dc2006       2006  /"
    "dc2007       2007  /"
    "dc2008       2008  /"
    "dc2009       2009  /"
    "dc2010       2010  /"
)

for row in "${TARGETS[@]}"; do
    read -r remote year seed <<<"${row}"
    dest="archive/${year}"
    url="${BASE}/${remote}${seed}"
    log="wget-${year}.log"

    echo "==> crawling ${url} into ${dest}/"
    mkdir -p "${dest}"

    # -e robots=off because close.open.hr/robots.txt disallows /dors*/,
    # /dc*/, /clucdors2004/ — it wasn't meant for future archivists.
    wget \
        --mirror \
        --page-requisites \
        --adjust-extension \
        --convert-links \
        --no-parent \
        --restrict-file-names=windows \
        --timestamping \
        --wait=0.2 --random-wait \
        --tries=3 --timeout=30 \
        --user-agent="dorscluc-archive/1.0 (legacy crawl via ssh tunnel)" \
        -e robots=off \
        --reject-regex='(\.php\?.*submit=|\?sort=|anketa\..*=)' \
        --directory-prefix="${dest}" \
        --no-host-directories \
        --cut-dirs=1 \
        "${url}" \
        2> "${log}" || echo "wget exited non-zero; see ${log}"

    count=$(find "${dest}" -name '*.html' -o -name '*.htm' -o -name '*.shtml' 2>/dev/null | wc -l)
    size=$(du -sh "${dest}" 2>/dev/null | cut -f1)
    echo "==> done: ${count} HTML-ish files, ${size} total"
done

echo
echo "==> rewriting close.open.hr localhost URLs to archive-relative paths"

# After wget --convert-links, URLs pointing back into close.open.hr (via the
# ssh tunnel's `localhost:<port>` base) stay absolute — they'd break once
# the tunnel is gone. Rewrite them to archive-relative /<year>/ paths.
python - <<'PY'
import re
from pathlib import Path

# Map every apache dir on close.open.hr to its archive year.
MAPPING = {
    "dors96":       "/1996",
    "dors97":       "/1997",
    "dors98":       "/1998",
    "dors99":       "/1999",
    "dors2000":     "/2000",
    "dors2001":     "/2001",
    "dors2002":     "/2002",
    "clucdors2004": "/2004",
    "dc2005":       "/2005",
    "dc2006":       "/2006",
    "dc2007":       "/2007",
    "dc2008":       "/2008",
    "dc2009":       "/2009",
    "dc2010":       "/2010",
}

# Match any scheme://host[:port]/<dir>/... where host is localhost or
# close.open.hr (any port). Captures dir and the remainder.
pat = re.compile(
    r"https?://(?:localhost(?::\d+)?|close\.open\.hr)/"
    r"(" + "|".join(re.escape(k) for k in MAPPING) + r")"
    r"(/[^\s\"'<>()]*)?",
    re.IGNORECASE,
)

def sub(m):
    dir_ = m.group(1).lower()
    rest = m.group(2) or "/"
    return MAPPING[dir_] + rest

exts = (".html", ".htm", ".shtml", ".css", ".js")
changed = 0
total = 0
for year in MAPPING.values():
    root = Path(f"archive{year}")
    if not root.is_dir():
        continue
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in exts:
            total += 1
            txt = f.read_text(encoding="utf-8", errors="replace")
            new = pat.sub(sub, txt)
            if new != txt:
                f.write_text(new, encoding="utf-8")
                changed += 1
print(f"rewrote localhost refs in {changed}/{total} files")
PY

echo
echo "==> all legacy crawls complete"
