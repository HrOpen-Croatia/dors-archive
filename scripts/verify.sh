#!/usr/bin/env bash
# Post-build checks. Exits 0 if everything looks sane.
set -eu

pass() { printf '\033[32mOK\033[0m  %s\n' "$*"; }
warn() { printf '\033[33m??\033[0m  %s\n' "$*"; }
fail() { printf '\033[31mERR\033[0m %s\n' "$*"; FAILED=1; }

FAILED=0
ROOT="archive"

[[ -f "${ROOT}/index.html" ]] && pass "index.html present" \
    || fail "missing ${ROOT}/index.html"
[[ -f "${ROOT}/404.html" ]] && pass "404.html present" \
    || fail "missing ${ROOT}/404.html"
[[ -f "${ROOT}/Caddyfile" ]] && pass "Caddyfile present" \
    || fail "missing ${ROOT}/Caddyfile"

for y in 2013 2014 2015 2016 2017 2018 2019 2020 2022 2023 2026; do
    if [[ -f "${ROOT}/${y}/index.html" ]]; then
        n=$(find "${ROOT}/${y}" -name '*.html' | wc -l)
        pass "/${y}/ present (${n} HTML files)"
    else
        fail "/${y}/index.html missing"
    fi
done
[[ -f "${ROOT}/main/index.html" ]] && pass "/main/ present" \
    || fail "/main/index.html missing"

leftover=$(grep -rh -oE 'https?://[a-z0-9-]*\.?dorscluc\.org' "${ROOT}" \
    2>/dev/null | sort -u | wc -l)
if [[ "${leftover}" -eq 0 ]]; then
    pass "no leftover absolute dorscluc.org URLs"
else
    warn "${leftover} absolute dorscluc.org URLs remain — inspect:"
    grep -rh -oE 'https?://[a-z0-9-]*\.?dorscluc\.org' "${ROOT}" \
        2>/dev/null | sort -u | head -20
fi

echo
du -sh "${ROOT}"/* | sort -k2

if grep -q '_BLURB_' "${ROOT}/index.html"; then
    fail "unreplaced _BLURB_ placeholders in index.html"
else
    pass "all blurbs filled in"
fi

if command -v caddy >/dev/null; then
    (cd "${ROOT}" && caddy validate --config Caddyfile 2>&1) \
        && pass "Caddyfile validates" \
        || fail "Caddyfile invalid"
else
    warn "caddy not installed; skipping config validation"
fi

echo
if [[ "${FAILED:-0}" -eq 0 ]]; then
    pass "all checks passed"
    exit 0
else
    fail "some checks failed"
    exit 1
fi
