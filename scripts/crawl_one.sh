#!/usr/bin/env bash
# Crawl one dorscluc.org target host into archive/<target>/.
#
# Usage:
#   scripts/crawl_one.sh <target-label> <url>
# Examples:
#   scripts/crawl_one.sh 2013 https://2013.dorscluc.org/
#   scripts/crawl_one.sh main https://www.dorscluc.org/
#
# Idempotent: re-runs use --timestamping to only refetch changed files.
# Output tree is flattened so archive/<label>/index.html is the site root.

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <label> <url>" >&2
    exit 2
fi

LABEL="$1"
URL="$2"
DEST="archive/${LABEL}"
LOG="wget-${LABEL}.log"

mkdir -p "${DEST}"

HOST="$(echo "${URL}" | sed -E 's#https?://([^/]+)/?.*#\1#')"

echo "==> crawling ${URL} into ${DEST}/ (host=${HOST})"

wget \
    --mirror \
    --page-requisites \
    --adjust-extension \
    --convert-links \
    --no-parent \
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
    "${URL}" \
    2> "${LOG}" || echo "wget exited non-zero (some 404s are expected); see ${LOG}"

echo "==> done: $(find "${DEST}" -name '*.html' | wc -l) HTML files, $(du -sh "${DEST}" | cut -f1) total"
