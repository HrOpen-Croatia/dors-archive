#!/usr/bin/env bash
# Crawl www.dorscluc.org. The root `/` redirects to the current year's
# subdomain, which breaks a naive wget mirror — we seed from the Yoast
# sitemap URL list and ask wget to fetch exactly those URLs plus their
# page requisites.
#
# Usage: scripts/crawl_main.sh

set -euo pipefail

DEST="archive/main"
LOG="wget-main.log"
URLS_FILE="scripts/data/main-sitemap-urls.txt"

if [[ ! -f "${URLS_FILE}" ]]; then
    echo "missing ${URLS_FILE} — regenerate with:" >&2
    echo "  for sm in post page organisation person wpcs_session category post_tag; do" >&2
    echo "      curl -sL https://www.dorscluc.org/\${sm}-sitemap.xml | \\" >&2
    echo "          grep -oE '<loc>[^<]+</loc>' | sed -E 's#</?loc>##g; s#^http://#https://#'" >&2
    echo "  done | sort -u > ${URLS_FILE}" >&2
    exit 2
fi

mkdir -p "${DEST}"

echo "==> main crawl: $(wc -l < "${URLS_FILE}") seeded URLs"

wget \
    --input-file="${URLS_FILE}" \
    --page-requisites \
    --adjust-extension \
    --convert-links \
    --restrict-file-names=windows \
    --timestamping \
    --wait=0.5 --random-wait \
    --tries=3 --timeout=30 \
    --user-agent="dorscluc-archive/1.0 (one-time archival crawl)" \
    --reject-regex='(wp-login\.php|wp-admin|xmlrpc\.php|wp-json|/feed/|/comments/feed|/embed/|\?replytocom=)' \
    --exclude-directories='/wp-admin,/wp-login.php,/xmlrpc.php' \
    --directory-prefix="${DEST}" \
    --no-host-directories \
    --cut-dirs=0 \
    2> "${LOG}" || echo "wget exited non-zero (some 404s are expected); see ${LOG}"

echo "==> done: $(find "${DEST}" -name '*.html' | wc -l) HTML files, $(du -sh "${DEST}" | cut -f1) total"
