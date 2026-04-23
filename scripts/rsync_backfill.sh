#!/usr/bin/env bash
# Read-only rsync pull of raw media directories from the source VM.
# Two modes: --dry-run (default) and --real.
#
# WP multisite stores per-site uploads under:
#   /var/www/dorscluc.org/wp-content/uploads/sites/<site_id>/
# The main (blog id 1) site uses:
#   /var/www/dorscluc.org/wp-content/uploads/
#
# Django-era static dirs:
#   /var/www/{year}-static/
#
# Site IDs have to be discovered — this script accepts them via env vars
# (DC_SITE_ID_2013=N etc.) or the static SITE_ID map below.

set -euo pipefail

MODE="${1:---dry-run}"
REMOTE="andreicek@dorscluc.org"
PORT=22123
RSYNC_OPTS=(-avh --partial --info=progress2 --no-motd)
if [[ "${MODE}" == "--dry-run" ]]; then
    RSYNC_OPTS+=(--dry-run)
fi

run() {
    echo "==> $*"
    "$@"
}

# Main site uploads
run rsync "${RSYNC_OPTS[@]}" -e "ssh -p ${PORT}" \
    "${REMOTE}:/var/www/dorscluc.org/wp-content/uploads/" \
    "archive/main/wp-content/uploads/"

# WP multisite per-site uploads. Populate by inspecting
# /var/www/dorscluc.org/wp-content/uploads/sites/ on the remote host.
declare -A SITE_ID=(
    # [2013]=""
    # [2014]=""
    # [2015]=""
    # [2020]=""
    # [2022]=""
    # [2026]=""
)

for year in "${!SITE_ID[@]}"; do
    id="${SITE_ID[$year]}"
    [[ -z "${id}" ]] && continue
    run rsync "${RSYNC_OPTS[@]}" -e "ssh -p ${PORT}" \
        "${REMOTE}:/var/www/dorscluc.org/wp-content/uploads/sites/${id}/" \
        "archive/${year}/wp-content/uploads/"
done

# Django-era static dirs
for year in 2016 2017 2018 2019; do
    run rsync "${RSYNC_OPTS[@]}" -e "ssh -p ${PORT}" \
        "${REMOTE}:/var/www/${year}-static/" \
        "archive/${year}/_static-backup/" || true
done

if [[ "${MODE}" == "--dry-run" ]]; then
    echo
    echo "Dry-run complete. Re-run with --real to actually pull."
fi
