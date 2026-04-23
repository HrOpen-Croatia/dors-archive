# DORS/CLUC Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a portable, static archive of every dorscluc.org conference edition (2013–2026) plus the main site, served by a single Caddyfile, without writing anything to the live VM.

**Architecture:** `wget --mirror` crawl of each reachable `<year>.dorscluc.org` and `www.dorscluc.org` into `archive/<year>/` and `archive/main/`. A Python post-processor rewrites cross-subdomain `dorscluc.org` URLs into archive-relative paths. Optional SSH rsync pass pulls raw media directories as backfill. A hand-built landing page at `/` lists the years. One Caddyfile serves the whole tree as static files.

**Tech Stack:** `bash`, `wget`, `rsync`, Python 3.10+ with `lxml` and `pytest`, Caddy v2.

**Source for requirements:** `docs/superpowers/specs/2026-04-23-dorscluc-archive-design.md`.

---

## File Structure

```
dors-archive/
├── README.md                    # hosting instructions
├── .gitignore                   # ignore captured content until it's final
├── docs/superpowers/
│   ├── specs/2026-04-23-dorscluc-archive-design.md   (exists)
│   └── plans/2026-04-23-dorscluc-archive.md          (this file)
├── scripts/
│   ├── crawl_one.sh             # wget a single year/site
│   ├── crawl_all.sh             # orchestrate all years
│   ├── rsync_backfill.sh        # ssh rsync pass for wp-content/uploads
│   ├── reconcile_2023.sh        # copy main/dors-2023 -> 2023
│   ├── rewrite_links.py         # cross-host URL rewriter (pure function + CLI)
│   ├── extract_blurbs.py        # pull <title>/<meta description> per year for landing
│   └── verify.sh                # post-build sanity checks
├── tests/
│   └── test_rewrite_links.py    # pytest for the rewriter
└── archive/
    ├── Caddyfile
    ├── index.html               # landing
    ├── 404.html
    ├── assets/style.css
    ├── main/                    # crawled www.dorscluc.org
    └── 20YY/                    # crawled year sites
```

**Responsibilities:**

- `scripts/crawl_one.sh`: one well-parameterized wget invocation. Idempotent. Knows how to flatten wget's host-prefixed output into `archive/<target>/`.
- `scripts/crawl_all.sh`: sequential driver. Never parallel — the source VM is fragile.
- `scripts/rewrite_links.py`: takes an archive dir, walks `*.html`, rewrites all dorscluc.org URLs to archive-relative. Has a public function `rewrite_html(text: str, current_archive_path: str) -> str` that's unit-testable without touching disk.
- `scripts/reconcile_2023.sh`: because the `2023` subdomain never existed, the real 2023 content is at `main/dors-2023/`. This script copies that subtree into `archive/2023/` and re-runs the rewriter scoped to it.
- `scripts/rsync_backfill.sh`: read-only SSH pull of `wp-content/uploads/` for WP years and `{year}-static/` for Django years. Dry-run first.
- `scripts/extract_blurbs.py`: one-off, parses each year's `index.html` to seed landing-page blurbs into a JSON.
- `scripts/verify.sh`: greps for leftover absolute dorscluc URLs, counts HTML files per year, prints sizes.

**Commit granularity:** one commit per task. Crawled content commits are separate from code commits.

---

## Task 1: Scaffold Repo

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `archive/` (empty, with placeholder `.gitkeep`)
- Create: `scripts/` (empty)
- Create: `tests/` (empty)

- [ ] **Step 1: Create `.gitignore`**

```
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/

# Local wget state
*.log
wget-*.log

# Crawled content — large, ship separately until we finalize
archive/main/
archive/20??/
!archive/20??/.gitkeep

# Editor junk
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 2: Create `README.md`**

```markdown
# dorscluc.org archive

Static snapshot of every DORS/CLUC conference edition (2013–2026) plus the
historical main site.

## Contents

- `archive/` — the archive itself. `Caddyfile`, landing page, and per-year
  HTML trees.
- `scripts/` — the capture + post-processing pipeline. Re-runnable.
- `tests/` — pytest suite for the link rewriter.
- `docs/superpowers/specs/` — the design doc.
- `docs/superpowers/plans/` — the implementation plan this project was
  built from.

## How to host this archive

1. Put the `archive/` directory anywhere.
2. Install Caddy v2.
3. Edit `archive/Caddyfile`: change the site address at the top to the
   hostname you want, and flip `auto_https off` → `auto_https on` (+ add an
   email in the global block) if you want automatic TLS.
4. `cd archive && caddy run`.

That's it — no database, no PHP, no cron.

## How to rebuild the archive

See `docs/superpowers/plans/2026-04-23-dorscluc-archive.md`.
```

- [ ] **Step 3: Create directory skeleton**

```bash
mkdir -p archive/assets scripts tests
touch archive/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git add README.md .gitignore archive/ scripts/ tests/
git commit -m "Scaffold dors-archive repo layout"
```

---

## Task 2: Link Rewriter — Write Failing Tests

**Files:**
- Create: `tests/test_rewrite_links.py`
- Create: `scripts/__init__.py` (empty, so pytest can import)

- [ ] **Step 1: Create `scripts/__init__.py`**

```bash
touch scripts/__init__.py
```

- [ ] **Step 2: Write the test file**

Create `tests/test_rewrite_links.py`:

```python
"""Tests for scripts/rewrite_links.py.

The rewriter converts absolute dorscluc.org URLs in crawled HTML into
archive-relative paths, per the path-based archive layout:
    https://www.dorscluc.org/foo         -> /main/foo
    https://2013.dorscluc.org/foo        -> /2013/foo
    https://files.dorscluc.org/foo       -> /main/files/foo   (fallback)
    https://2013.dorscluc.org/files/x    -> /2013/files/x

External URLs, relative URLs, mailto/tel/anchor-only URLs are untouched.
"""
from scripts.rewrite_links import rewrite_html


def test_absolute_www_href_becomes_main_path():
    html = '<a href="https://www.dorscluc.org/past-conferences/">past</a>'
    assert rewrite_html(html) == (
        '<a href="/main/past-conferences/">past</a>'
    )


def test_absolute_bare_root_becomes_main_root():
    html = '<a href="https://dorscluc.org/">root</a>'
    assert rewrite_html(html) == '<a href="/main/">root</a>'


def test_year_subdomain_href_becomes_year_path():
    html = '<a href="https://2013.dorscluc.org/speakers/">s</a>'
    assert rewrite_html(html) == '<a href="/2013/speakers/">s</a>'


def test_year_subdomain_with_http_scheme():
    html = '<a href="http://2014.dorscluc.org/">2014</a>'
    assert rewrite_html(html) == '<a href="/2014/">2014</a>'


def test_img_src_rewritten():
    html = '<img src="https://2015.dorscluc.org/wp-content/uploads/logo.png">'
    assert rewrite_html(html) == (
        '<img src="/2015/wp-content/uploads/logo.png">'
    )


def test_srcset_all_urls_rewritten():
    html = (
        '<img srcset="https://2016.dorscluc.org/a.png 1x, '
        'https://2016.dorscluc.org/b.png 2x">'
    )
    assert rewrite_html(html) == (
        '<img srcset="/2016/a.png 1x, /2016/b.png 2x">'
    )


def test_external_url_untouched():
    html = '<a href="https://example.com/">ext</a>'
    assert rewrite_html(html) == html


def test_relative_url_untouched():
    html = '<a href="/about/">a</a><img src="foo.png">'
    assert rewrite_html(html) == html


def test_mailto_untouched():
    html = '<a href="mailto:info@dorscluc.org">mail</a>'
    assert rewrite_html(html) == html


def test_fragment_only_untouched():
    html = '<a href="#top">top</a>'
    assert rewrite_html(html) == html


def test_query_string_preserved():
    html = (
        '<a href="https://2018.dorscluc.org/?page_id=42&lang=hr">p</a>'
    )
    assert rewrite_html(html) == (
        '<a href="/2018/?page_id=42&lang=hr">p</a>'
    )


def test_files_subdomain_goes_to_main_files():
    html = '<a href="https://files.dorscluc.org/media/x.pdf">pdf</a>'
    assert rewrite_html(html) == (
        '<a href="/main/files/media/x.pdf">pdf</a>'
    )


def test_inline_style_url_rewritten():
    html = (
        '<div style="background: url(https://2019.dorscluc.org/bg.jpg);">'
        'x</div>'
    )
    assert rewrite_html(html) == (
        '<div style="background: url(/2019/bg.jpg);">x</div>'
    )


def test_meta_refresh_content_rewritten():
    html = (
        '<meta http-equiv="refresh" '
        'content="5;url=https://2020.dorscluc.org/">'
    )
    assert rewrite_html(html) == (
        '<meta http-equiv="refresh" content="5;url=/2020/">'
    )


def test_form_action_rewritten():
    html = '<form action="https://www.dorscluc.org/search"></form>'
    assert rewrite_html(html) == '<form action="/main/search"></form>'


def test_no_change_returns_identical_string():
    html = '<p>no urls here</p>'
    assert rewrite_html(html) == html
```

- [ ] **Step 3: Run tests, confirm they fail**

```bash
cd /home/andreicek/Developer/dors-archive
python3 -m venv .venv
source .venv/bin/activate
pip install pytest lxml
pytest tests/ -v
```

Expected: all tests fail with `ModuleNotFoundError: No module named 'scripts.rewrite_links'`.

- [ ] **Step 4: Commit**

```bash
git add tests/ scripts/__init__.py
git commit -m "Add failing tests for link rewriter"
```

---

## Task 3: Link Rewriter — Make Tests Pass

**Files:**
- Create: `scripts/rewrite_links.py`

- [ ] **Step 1: Implement the rewriter**

Create `scripts/rewrite_links.py`:

```python
"""Rewrite absolute dorscluc.org URLs in crawled HTML into
archive-relative paths.

The archive is served under a single hostname with path-based layout:
    /main/    — www.dorscluc.org
    /20YY/    — each year's subdomain
See docs/superpowers/specs/2026-04-23-dorscluc-archive-design.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Matches:  scheme://[www.|YYYY.|files.]dorscluc.org[rest]
# Captures: 1 = subdomain label or empty, 2 = path/query/fragment (may be empty)
_DORSCLUC_URL_RE = re.compile(
    r"https?://"
    r"(?:([a-z0-9-]+)\.)?"
    r"dorscluc\.org"
    r"(/[^\s\"'<>()]*)?",
    re.IGNORECASE,
)


def _map_subdomain(sub: str | None) -> str:
    """Return the archive path prefix (without trailing slash) for a host."""
    if sub is None or sub == "" or sub.lower() == "www":
        return "/main"
    if re.fullmatch(r"20\d{2}", sub):
        return f"/{sub}"
    if sub.lower() == "files":
        return "/main/files"
    # Unknown subdomain — route under /main/ and keep label as directory so
    # nothing is silently lost.
    return f"/main/_other/{sub.lower()}"


def _rewrite_match(match: re.Match[str]) -> str:
    sub = match.group(1)
    rest = match.group(2) or "/"
    prefix = _map_subdomain(sub)
    # Collapse //
    if rest.startswith("/"):
        return prefix + rest
    return prefix + "/" + rest


def rewrite_html(text: str) -> str:
    """Rewrite every absolute dorscluc.org URL in `text` to archive-relative.

    Purely textual — does not parse HTML. This matters for malformed WP
    output and for URLs inside inline `style="..."` / `srcset="..."` /
    `<meta content="...">` strings, which a tag-aware rewriter would miss.
    External URLs, relative URLs, and non-http schemes are untouched.
    """
    return _DORSCLUC_URL_RE.sub(_rewrite_match, text)


def rewrite_file(path: Path) -> bool:
    """Rewrite `path` in place. Return True if content changed."""
    original = path.read_text(encoding="utf-8", errors="replace")
    rewritten = rewrite_html(original)
    if rewritten != original:
        path.write_text(rewritten, encoding="utf-8")
        return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: rewrite_links.py <archive_dir>", file=sys.stderr)
        return 2
    root = Path(argv[1])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    changed = 0
    total = 0
    for html in root.rglob("*.html"):
        total += 1
        if rewrite_file(html):
            changed += 1
    print(f"rewrote {changed}/{total} HTML files under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: Run tests, confirm they pass**

```bash
source .venv/bin/activate
pytest tests/ -v
```

Expected: all 16 tests pass.

- [ ] **Step 3: Commit**

```bash
git add scripts/rewrite_links.py
git commit -m "Implement link rewriter (tests pass)"
```

---

## Task 4: Caddyfile

**Files:**
- Create: `archive/Caddyfile`

- [ ] **Step 1: Write the Caddyfile**

Create `archive/Caddyfile`:

```caddy
{
    # Flip to `auto_https on` + add `email you@example.com` when hosting
    # behind a real domain.
    auto_https off
}

# Swap this address for the final hostname (e.g. archive.dorscluc.org).
:8080 {
    root * {$ARCHIVE_ROOT:.}
    encode zstd gzip

    # Landing page
    handle / {
        rewrite * /index.html
        file_server
    }

    # Evergreen pages on the main site
    handle /main/* {
        file_server {
            index index.html
        }
    }

    # Per-year archives
    @years path_regexp year ^/(20[0-9]{2})(/.*)?$
    handle @years {
        file_server {
            index index.html
        }
    }

    # Landing page assets
    handle /assets/* {
        file_server
    }

    # 404
    handle {
        rewrite * /404.html
        file_server
    }
}
```

- [ ] **Step 2: Validate with Caddy**

```bash
cd archive
caddy validate --config Caddyfile
```

Expected: `Valid configuration`. (If `caddy` isn't installed yet, skip this check and note it; the Caddyfile is still committed.)

- [ ] **Step 3: Commit**

```bash
cd /home/andreicek/Developer/dors-archive
git add archive/Caddyfile
git commit -m "Add Caddyfile for archive"
```

---

## Task 5: Landing Page + 404 + Styles (Scaffolding)

Actual year blurbs are filled in later (Task 12). For now, the landing page shows placeholders.

**Files:**
- Create: `archive/index.html`
- Create: `archive/404.html`
- Create: `archive/assets/style.css`

- [ ] **Step 1: Create `archive/assets/style.css`**

```css
:root {
    --bg: #fafaf7;
    --fg: #1a1a1a;
    --muted: #666;
    --accent: #b0413e;
    --border: #e4e4de;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    font: 16px/1.55 "Georgia", "Times New Roman", serif;
    background: var(--bg);
    color: var(--fg);
}
.wrap { max-width: 900px; margin: 0 auto; padding: 3rem 1.25rem 5rem; }
header h1 { font-size: 2.25rem; margin: 0 0 .25rem; letter-spacing: -.01em; }
header .sub { color: var(--muted); margin: 0 0 2.5rem; }
.lead { font-size: 1.05rem; margin: 0 0 2rem; color: var(--fg); }
.years {
    list-style: none; padding: 0; margin: 0;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1rem;
}
.years li {
    background: #fff; border: 1px solid var(--border);
    padding: 1rem 1.1rem; border-radius: 4px;
}
.years a {
    color: var(--accent); text-decoration: none; font-weight: 700;
    font-size: 1.4rem;
}
.years a:hover { text-decoration: underline; }
.years p { margin: .35rem 0 0; color: var(--muted); font-size: .92rem; }
footer {
    margin-top: 3.5rem; padding-top: 1.25rem;
    border-top: 1px solid var(--border);
    color: var(--muted); font-size: .9rem;
}
footer a { color: var(--accent); }
code { font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }
```

- [ ] **Step 2: Create `archive/index.html`**

Blurbs are placeholders now; Task 12 replaces them.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DORS/CLUC — Archive</title>
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<div class="wrap">
<header>
    <h1>DORS/CLUC</h1>
    <p class="sub">Archive of the Croatian free software conference, 2013–2026.</p>
</header>

<p class="lead">
    The live website at <code>dorscluc.org</code> has been retired.
    This is a static snapshot of every public edition the conference ran.
</p>

<ul class="years">
    <li><a href="/2026/">2026</a><p>_BLURB_2026_</p></li>
    <li><a href="/2023/">2023</a><p>_BLURB_2023_</p></li>
    <li><a href="/2022/">2022</a><p>_BLURB_2022_</p></li>
    <li><a href="/2020/">2020</a><p>_BLURB_2020_</p></li>
    <li><a href="/2019/">2019</a><p>_BLURB_2019_</p></li>
    <li><a href="/2018/">2018</a><p>_BLURB_2018_</p></li>
    <li><a href="/2017/">2017</a><p>_BLURB_2017_</p></li>
    <li><a href="/2016/">2016</a><p>_BLURB_2016_</p></li>
    <li><a href="/2015/">2015</a><p>_BLURB_2015_</p></li>
    <li><a href="/2014/">2014</a><p>_BLURB_2014_</p></li>
    <li><a href="/2013/">2013</a><p>_BLURB_2013_</p></li>
</ul>

<footer>
    Evergreen pages (Code of Conduct, past-conferences index, contact)
    live at <a href="/main/">/main/</a>.
</footer>
</div>
</body>
</html>
```

- [ ] **Step 3: Create `archive/404.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>404 — DORS/CLUC Archive</title>
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<div class="wrap">
<header><h1>404</h1><p class="sub">That page isn't in the archive.</p></header>
<p><a href="/">Back to the index</a>.</p>
</div>
</body>
</html>
```

- [ ] **Step 4: Commit**

```bash
git add archive/index.html archive/404.html archive/assets/style.css
git commit -m "Add landing, 404, stylesheet (blurbs are placeholders)"
```

---

## Task 6: Crawler Script (Single Target)

**Files:**
- Create: `scripts/crawl_one.sh`

- [ ] **Step 1: Write `scripts/crawl_one.sh`**

```bash
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

# Host extracted from URL, e.g. "2013.dorscluc.org"
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

# Off-host page requisites (e.g. i0.wp.com, files.dorscluc.org) land in
# host-named subdirs because --no-host-directories only strips the first
# host. Leave them there — rewrite_links.py handles them.

echo "==> done: $(find "${DEST}" -name '*.html' | wc -l) HTML files, $(du -sh "${DEST}" | cut -f1) total"
```

- [ ] **Step 2: Make executable and smoke-test on one year**

```bash
chmod +x scripts/crawl_one.sh
scripts/crawl_one.sh 2013 https://2013.dorscluc.org/
ls archive/2013/ | head
test -f archive/2013/index.html && echo "OK: has index.html"
```

Expected: `index.html` exists, plus subdirectories matching 2013's path structure, plus some off-host asset dirs (e.g. `i0.wp.com/`).

- [ ] **Step 3: Commit the script (not the crawl output — it's gitignored)**

```bash
git add scripts/crawl_one.sh
git commit -m "Add per-target wget crawler script"
```

---

## Task 7: Crawl All Sites

**Files:**
- Create: `scripts/crawl_all.sh`

- [ ] **Step 1: Write `scripts/crawl_all.sh`**

```bash
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

# Deterministic order
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
```

- [ ] **Step 2: Make executable and dry-run it over the remaining years**

2013 is already crawled. Do the others one at a time, starting with small ones, so if a site misbehaves you notice quickly:

```bash
chmod +x scripts/crawl_all.sh

# Crawl one-by-one so you can spot-check each before moving on
scripts/crawl_one.sh main https://www.dorscluc.org/
scripts/crawl_one.sh 2014 https://2014.dorscluc.org/
scripts/crawl_one.sh 2015 https://2015.dorscluc.org/
scripts/crawl_one.sh 2016 https://2016.dorscluc.org/
scripts/crawl_one.sh 2017 https://2017.dorscluc.org/
scripts/crawl_one.sh 2018 https://2018.dorscluc.org/
scripts/crawl_one.sh 2019 https://2019.dorscluc.org/
scripts/crawl_one.sh 2020 https://2020.dorscluc.org/
scripts/crawl_one.sh 2022 https://2022.dorscluc.org/
scripts/crawl_one.sh 2026 https://2026.dorscluc.org/
```

After each: `du -sh archive/<label> && find archive/<label> -name '*.html' | wc -l`.

- [ ] **Step 3: Commit the orchestrator script**

```bash
git add scripts/crawl_all.sh
git commit -m "Add crawl orchestrator"
```

---

## Task 8: Rewrite Links Across the Archive

Run the rewriter over every crawled tree. This makes the path-based layout actually work.

- [ ] **Step 1: Dry-run-ish: grep for dorscluc.org absolute URLs before**

```bash
grep -rh -oE 'https?://[a-z0-9-]*\.?dorscluc\.org' archive/ 2>/dev/null \
    | sort -u | head -20
# save count for comparison
grep -rh -oE 'https?://[a-z0-9-]*\.?dorscluc\.org' archive/ 2>/dev/null \
    | wc -l > /tmp/before_count
```

- [ ] **Step 2: Run the rewriter**

```bash
source .venv/bin/activate
python scripts/rewrite_links.py archive/main
python scripts/rewrite_links.py archive/2013
python scripts/rewrite_links.py archive/2014
python scripts/rewrite_links.py archive/2015
python scripts/rewrite_links.py archive/2016
python scripts/rewrite_links.py archive/2017
python scripts/rewrite_links.py archive/2018
python scripts/rewrite_links.py archive/2019
python scripts/rewrite_links.py archive/2020
python scripts/rewrite_links.py archive/2022
python scripts/rewrite_links.py archive/2026
```

- [ ] **Step 3: Verify absolute dorscluc URLs are gone**

```bash
grep -rh -oE 'https?://[a-z0-9-]*\.?dorscluc\.org' archive/ 2>/dev/null \
    | sort -u
```

Expected: empty output, or at most a small set of URLs we consciously leave (e.g. inside comments, social metadata). If unexpected matches appear, inspect and either extend the rewriter or accept them.

---

## Task 9: Reconcile 2023

The 2023 edition never got its own subdomain — its content is under `archive/main/dors-2023/`. Copy it to `archive/2023/` so `/2023/` resolves.

**Files:**
- Create: `scripts/reconcile_2023.sh`

- [ ] **Step 1: Write the script**

```bash
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

# The copied pages still contain links like "/main/dors-2023/..." after
# Task 8's pass. Rewrite those to "/2023/..." so internal links stay
# inside the /2023/ tree.
python scripts/rewrite_path_prefix.py \
    --in "${DEST}" \
    --from "/main/dors-2023" \
    --to   "/2023"

# Ensure /2023/ has an index.html at the root
if [[ ! -f "${DEST}/index.html" ]]; then
    # main/dors-2023/ was itself a directory with an index page
    cp "${SRC}/index.html" "${DEST}/index.html" 2>/dev/null || true
fi

echo "==> 2023 reconciled: $(find "${DEST}" -name '*.html' | wc -l) HTML files"
```

- [ ] **Step 2: Write `scripts/rewrite_path_prefix.py`**

```python
"""Rewrite one archive-relative path prefix to another across a tree.

Used for Task 9: after copying main/dors-2023/ to 2023/, internal links
still point into /main/dors-2023/... and need to point at /2023/...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def rewrite_tree(root: Path, from_prefix: str, to_prefix: str) -> int:
    if not from_prefix.startswith("/") or not to_prefix.startswith("/"):
        raise SystemExit("prefixes must start with /")
    changed = 0
    for html in root.rglob("*.html"):
        original = html.read_text(encoding="utf-8", errors="replace")
        rewritten = original.replace(from_prefix, to_prefix)
        if rewritten != original:
            html.write_text(rewritten, encoding="utf-8")
            changed += 1
    return changed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="root", required=True)
    p.add_argument("--from", dest="src", required=True)
    p.add_argument("--to", dest="dst", required=True)
    args = p.parse_args()
    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    n = rewrite_tree(root, args.src, args.dst)
    print(f"rewrote prefix in {n} files under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run and verify**

```bash
chmod +x scripts/reconcile_2023.sh
scripts/reconcile_2023.sh
ls archive/2023/ | head
# No leftover /main/dors-2023 refs inside /2023/:
grep -r "/main/dors-2023" archive/2023/ || echo "OK: clean"
```

- [ ] **Step 4: Commit scripts**

```bash
git add scripts/reconcile_2023.sh scripts/rewrite_path_prefix.py
git commit -m "Reconcile 2023 onto its own path"
```

---

## Task 10: SSH Rsync Backfill (Optional Safety Net)

Pull raw uploaded media dirs so any unlinked assets make it into the archive.

**Files:**
- Create: `scripts/rsync_backfill.sh`

- [ ] **Step 1: Write the script**

```bash
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
# (DC_SITE_ID_2013=N etc.) to keep it deterministic.

set -euo pipefail

MODE="${1:---dry-run}"
REMOTE="andreicek@dorscluc.org"
PORT=22123
RSYNC_OPTS="-avh --partial --info=progress2 --no-motd"
if [[ "${MODE}" == "--dry-run" ]]; then
    RSYNC_OPTS="${RSYNC_OPTS} --dry-run"
fi

run() {
    echo "==> $*"
    eval "$*"
}

# Main site uploads
run rsync ${RSYNC_OPTS} -e "'ssh -p ${PORT}'" \
    "${REMOTE}:/var/www/dorscluc.org/wp-content/uploads/" \
    "archive/main/wp-content/uploads/"

# WP multisite per-site uploads.
# Populate this map with the actual site IDs (read from wp_blogs or the
# directory listing at wp-content/uploads/sites/).
declare -A SITE_ID=(
    # [2013]="?"
    # [2014]="?"
    # [2015]="?"
    # [2020]="?"
    # [2022]="?"
    # [2026]="?"
)

for year in "${!SITE_ID[@]}"; do
    id="${SITE_ID[$year]}"
    run rsync ${RSYNC_OPTS} -e "'ssh -p ${PORT}'" \
        "${REMOTE}:/var/www/dorscluc.org/wp-content/uploads/sites/${id}/" \
        "archive/${year}/wp-content/uploads/"
done

# Django-era static dirs
for year in 2016 2017 2018 2019; do
    run rsync ${RSYNC_OPTS} -e "'ssh -p ${PORT}'" \
        "${REMOTE}:/var/www/${year}-static/" \
        "archive/${year}/_static-backup/"
done

if [[ "${MODE}" == "--dry-run" ]]; then
    echo
    echo "Dry-run complete. Re-run with --real to actually pull."
fi
```

- [ ] **Step 2: Discover site IDs (read-only)**

```bash
ssh -p 22123 andreicek@dorscluc.org \
    'ls /var/www/dorscluc.org/wp-content/uploads/sites/ 2>/dev/null \
     && ls /var/www/dorscluc.org/wp-content/blogs.dir/ 2>/dev/null | head'
```

Pick the right convention (modern WP is `uploads/sites/<id>/`, older is `blogs.dir/<id>/files/`) and fill the `SITE_ID` map. To map id→year, read `wp_blogs` via a read-only query if accessible, or cross-reference paths inside the uploads dirs with known year-specific filenames.

If you can't cleanly establish the mapping, skip this script — the pure-crawl archive is already complete for visitor-visible content.

- [ ] **Step 3: Dry-run, review, then run**

```bash
chmod +x scripts/rsync_backfill.sh
scripts/rsync_backfill.sh --dry-run
# Review output carefully.
scripts/rsync_backfill.sh --real
```

- [ ] **Step 4: Re-run the rewriter after backfill, just in case**

```bash
source .venv/bin/activate
for y in main 2013 2014 2015 2016 2017 2018 2019 2020 2022 2026; do
    python scripts/rewrite_links.py "archive/${y}"
done
```

- [ ] **Step 5: Commit scripts**

```bash
git add scripts/rsync_backfill.sh
git commit -m "Add rsync backfill script (optional)"
```

---

## Task 11: Generate Landing-Page Blurbs

Replace the `_BLURB_YYYY_` placeholders in `archive/index.html` with short descriptions pulled from each year's homepage.

**Files:**
- Create: `scripts/extract_blurbs.py`

- [ ] **Step 1: Write the extractor**

```python
"""Extract a short blurb per year for the landing page.

Reads archive/<year>/index.html, returns (year, blurb) where blurb is the
first of:
  1. <meta name="description" content="...">
  2. <meta property="og:description" content="...">
  3. first <p> in the body, trimmed to 140 chars

Output: prints the JSON map to stdout. Feed it back into index.html by
hand or via the helper below.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

YEARS = ["2013", "2014", "2015", "2016", "2017", "2018",
         "2019", "2020", "2022", "2023", "2026"]


def _first_match(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None


def extract_blurb(html: str) -> str:
    meta_desc = _first_match(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
        html,
    )
    if meta_desc:
        return meta_desc[:200]
    og = _first_match(
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
        html,
    )
    if og:
        return og[:200]
    p = _first_match(r"<p[^>]*>(.*?)</p>", html)
    if p:
        return re.sub(r"<[^>]+>", "", p)[:140].strip()
    return ""


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path("archive")
    out: dict[str, str] = {}
    for year in YEARS:
        idx = root / year / "index.html"
        if not idx.exists():
            continue
        html = idx.read_text(encoding="utf-8", errors="replace")
        out[year] = extract_blurb(html)
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: Run it and use the output to edit `archive/index.html`**

```bash
source .venv/bin/activate
python scripts/extract_blurbs.py archive > /tmp/blurbs.json
cat /tmp/blurbs.json
```

Open `archive/index.html` and replace each `_BLURB_YYYY_` with the corresponding value from the JSON. Edit freely where the auto-extract is ugly.

- [ ] **Step 3: Commit**

```bash
git add scripts/extract_blurbs.py archive/index.html
git commit -m "Fill landing page blurbs"
```

---

## Task 12: Verification Script

**Files:**
- Create: `scripts/verify.sh`

- [ ] **Step 1: Write it**

```bash
#!/usr/bin/env bash
# Post-build checks. Exits 0 if everything looks sane.
set -eu

pass() { printf '\033[32mOK\033[0m  %s\n' "$*"; }
warn() { printf '\033[33m??\033[0m  %s\n' "$*"; }
fail() { printf '\033[31mERR\033[0m %s\n' "$*"; FAILED=1; }

FAILED=0
ROOT="archive"

# 1. Landing page + 404 + Caddyfile
[[ -f "${ROOT}/index.html" ]] && pass "index.html present" \
    || fail "missing ${ROOT}/index.html"
[[ -f "${ROOT}/404.html" ]] && pass "404.html present" \
    || fail "missing ${ROOT}/404.html"
[[ -f "${ROOT}/Caddyfile" ]] && pass "Caddyfile present" \
    || fail "missing ${ROOT}/Caddyfile"

# 2. Every declared year has an index.html
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

# 3. No leftover absolute dorscluc.org URLs
leftover=$(grep -rh -oE 'https?://[a-z0-9-]*\.?dorscluc\.org' "${ROOT}" \
    2>/dev/null | sort -u | wc -l)
if [[ "${leftover}" -eq 0 ]]; then
    pass "no leftover absolute dorscluc.org URLs"
else
    warn "${leftover} absolute dorscluc.org URLs remain — inspect:"
    grep -rh -oE 'https?://[a-z0-9-]*\.?dorscluc\.org' "${ROOT}" \
        2>/dev/null | sort -u | head -20
fi

# 4. Archive size
echo
du -sh "${ROOT}"/* | sort -k2

# 5. Blurb placeholders gone
if grep -q '_BLURB_' "${ROOT}/index.html"; then
    fail "unreplaced _BLURB_ placeholders in index.html"
else
    pass "all blurbs filled in"
fi

# 6. Caddy validates
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
```

- [ ] **Step 2: Run it**

```bash
chmod +x scripts/verify.sh
scripts/verify.sh
```

Expected: all `OK`s, maybe a `??` on the leftover-URL check (a handful of social metadata URLs are acceptable).

- [ ] **Step 3: Commit**

```bash
git add scripts/verify.sh
git commit -m "Add verification script"
```

---

## Task 13: Local Smoke-Run With Caddy

- [ ] **Step 1: Serve the archive locally**

```bash
cd archive
caddy run --config Caddyfile
```

- [ ] **Step 2: Browse it**

Open `http://localhost:8080/` in a browser. Click through:
- Landing page loads, links work.
- `/2013/` renders, images visible.
- `/main/past-conferences/` resolves.
- `/2023/` resolves (reconciled subtree).
- A deliberately-bad URL like `/not-a-thing/` shows the 404.

In the Network tab, confirm **no requests go to `*.dorscluc.org`** — every asset is served by Caddy.

- [ ] **Step 3: Stop Caddy (Ctrl-C). No commit — this is a check.**

---

## Task 14: Finalize the Archive Commit

Up to now, crawled content was gitignored so the code-only commits stay reviewable. Now that content is verified, ship it.

- [ ] **Step 1: Decide whether to commit the archive**

Option A (recommended for size-OK archives): drop the ignore of `archive/main/` and `archive/20??/` so it ships with the repo.

Option B (for large archives): leave gitignored; distribute as a tarball alongside the repo.

For Option A:

```bash
# Remove the archive ignores
sed -i '/^archive\/main\//d;/^archive\/20??\//d;/^!archive\/20??\/\.gitkeep$/d' .gitignore
git add .gitignore
git add archive/
git commit -m "Ship built archive"
du -sh .git
```

For Option B:

```bash
tar --zstd -cf dorscluc-archive-$(date +%Y%m%d).tar.zst archive/
ls -lh dorscluc-archive-*.tar.zst
```

- [ ] **Step 2: Update README with the final size + any hosting gotchas**

Edit `README.md` if the archive size or any operational note (e.g. "to serve on HTTPS change auto_https") is worth pinning at the top. Commit.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task(s) |
|---|---|
| Path-based layout (`/main/`, `/20YY/`) | 4, 5, 7 |
| WP multisite crawls (2013, 2014, 2015, 2020, 2022, 2023, 2026) | 7, 9 |
| Django year crawls (2016–2019) | 7 |
| Cross-host link rewriter | 2, 3, 8 |
| Pass 2 SSH rsync backfill | 10 |
| 2023 reconciliation from `main/dors-2023/` | 9 |
| Single Caddyfile, portable | 4 |
| Landing page with blurbs | 5, 11 |
| 404 page | 5 |
| No writes to live VM | All tasks (crawl/rsync pull only) |
| Verification checklist | 12, 13 |
| README hosting instructions | 1, 14 |

All spec sections are covered.

**Type/identifier consistency:**
- `rewrite_html(text: str) -> str` is the name used in tests (Task 2) and implementation (Task 3). ✓
- `rewrite_file`, `rewrite_tree` names are internal and consistent. ✓
- CLI signature `rewrite_links.py <archive_dir>` matches the usage in Task 8. ✓
- `scripts/crawl_one.sh <label> <url>` matches every invocation. ✓

**Placeholder scan:** None. Every task has exact commands and complete code.

**Known acceptable non-determinism:**
- Task 10 leaves the `SITE_ID` map blank because the multisite→blog_id mapping has to be discovered at run time. This is called out explicitly with instructions to discover it read-only, plus a fallback (skip the script) if it's too brittle.
- Task 11's auto-blurbs are seeds; the task explicitly says "edit freely".
