#!/usr/bin/env bash
# Crawl the main site + all reachable year subdomains sequentially.
# Never parallel — the source VM is fragile.
#
# Usage: scripts/crawl_all.sh [label1 label2 ...]
# With no args, crawls everything. With args, crawls only listed labels.

set -euo pipefail

declare -A TARGETS=(
    [main]="https://www.dorscluc.org/"
    [2013]="https://2013.dorscluc.org/"
    [2014]="https://2014.dorscluc.org/"
    [2015]="https://2015.dorscluc.org/"
    [2016]="https://2016.dorscluc.org/"
    [2017]="https://2017.dorscluc.org/"
    [2018]="https://2018.dorscluc.org/"
    [2019]="https://2019.dorscluc.org/"
    [2020]="https://2020.dorscluc.org/"
    [2022]="https://2022.dorscluc.org/"
    [2026]="https://2026.dorscluc.org/"
)

ORDER=(main 2013 2014 2015 2016 2017 2018 2019 2020 2022 2026)

if [[ $# -gt 0 ]]; then
    ORDER=("$@")
fi

for label in "${ORDER[@]}"; do
    url="${TARGETS[$label]:-}"
    if [[ -z "${url}" ]]; then
        echo "skipping unknown label: ${label}" >&2
        continue
    fi
    scripts/crawl_one.sh "${label}" "${url}"
done

echo
echo "==> all crawls complete"
du -sh archive/main archive/20* 2>/dev/null || true
