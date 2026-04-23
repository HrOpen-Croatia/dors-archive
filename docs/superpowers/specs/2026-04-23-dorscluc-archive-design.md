# DORS/CLUC Website Archive — Design

**Date:** 2026-04-23
**Status:** Approved
**Goal:** Produce a self-contained, portable static archive of every dorscluc.org conference edition (2013–2026) plus the main site, served by a single Caddyfile, before the live website is shut down.

## Context

`dorscluc.org` is about to be retired. Historically each conference edition lived at `<YEAR>.dorscluc.org`, but the backend is heterogeneous:

| Years | Backend | Notes |
|------|---------|-------|
| www, 2013, 2014, 2015, 2020, 2022, 2023, 2026 | WordPress multisite (`/var/www/dorscluc.org`) | Single Apache vhost with ServerAliases |
| 2016, 2017, 2018, 2019 | Django apps + static dirs | Each has its own Apache vhost and on-disk dir (`/var/www/{YEAR}-django/`, `/var/www/{YEAR}-static/`) |
| 2024 | — | Apache vhost redirects `2024.dorscluc.org` → `www.dorscluc.org` |
| 2023 | WP, but as a page on main site | `2023.dorscluc.org` redirects to `wp-signup.php`; real 2023 content lives at `www.dorscluc.org/dors-2023/` |
| 2021, 2025, pre-2013 | — | No public presence |

The archive must be:

1. **Portable** — a single folder + a single Caddyfile. No database, no PHP, no per-year vhost.
2. **Read-only with respect to the source** — zero writes to the live VM.
3. **Navigable under one hostname** — path-based layout, not a subdomain per year.
4. **Complete** — every visitor-visible URL today should resolve in the archive (with URLs rewritten into the archive's path scheme).

## Out of scope

- Admin UI, wp-login, wp-json, xmlrpc, any login-gated content.
- DB dumps, WP export files, plugin installation.
- Registration app (`prijave.2014.dorscluc.org`) — not publicly vhosted today.
- Setting up DNS / TLS for the final hosting environment. The Caddyfile ships with `auto_https off` and binds to a placeholder hostname; the eventual operator flips it on.
- Years that never ran publicly (pre-2013, 2021, 2024, 2025). Not listed on the landing page. No stub pages.

## Layout

```
archive/
├── Caddyfile
├── index.html            # hand-built landing page
├── 404.html
├── assets/               # css + any assets used by landing/404
├── main/                 # mirror of www.dorscluc.org
├── 2013/                 # mirror of 2013.dorscluc.org (WP)
├── 2014/                 # mirror (WP)
├── 2015/                 # mirror (WP)
├── 2016/                 # mirror of 2016.dorscluc.org (Django)
├── 2017/                 # mirror (Django)
├── 2018/                 # mirror (Django)
├── 2019/                 # mirror (Django)
├── 2020/                 # mirror (WP)
├── 2022/                 # mirror (WP)
├── 2023/                 # copy of main/dors-2023/ subtree (or symlink + rewrite)
└── 2026/                 # mirror of 2026.dorscluc.org (WP, current edition)
```

Every leaf directory contains an `index.html` produced by the crawler. All HTML is self-contained (page requisites inlined or stored alongside).

## Capture mechanism

Two passes per site, both read-only.

### Pass 1 — HTTP crawl

Tool: `wget --mirror`.

Per-year invocation (pseudo):

```
wget \
  --mirror \
  --page-requisites \
  --adjust-extension \
  --convert-links \
  --no-parent \
  --restrict-file-names=windows \
  --timestamping \
  --wait=0.5 --random-wait \
  --user-agent="dorscluc-archive/1.0" \
  --tries=3 --timeout=30 \
  --domains="${YEAR}.dorscluc.org,files.dorscluc.org,i0.wp.com" \
  --span-hosts \
  --directory-prefix="archive/${YEAR}/" \
  "https://${YEAR}.dorscluc.org/"
```

For the main site the target is `https://www.dorscluc.org/` with output prefix `archive/main/`.

Notes:
- `--timestamping` lets us re-run to top up without re-downloading.
- `--span-hosts` limited to the site's own host, a `files.` CDN if present, and `i0.wp.com` (WP photon CDN).
- `--wait=0.5 --random-wait` keeps load low on the source VM.
- One `wget` process per year at a time — not parallel — to keep the VM unstressed.
- Output lands in a host-named subdirectory created by wget (e.g. `archive/2013/2013.dorscluc.org/...`). A post-step flattens it to `archive/2013/`.

### Pass 2 — SSH rsync backfill

Optional safety net for files that exist on disk but are not linked from any crawled page (typical cause: unused uploads, older media).

- **WP years** (2013, 2014, 2015, 2020, 2022, 2023, 2026): `rsync -avP andreicek@dorscluc.org:/var/www/dorscluc.org/wp-content/blogs.dir/<site-id>/files/ archive/<year>/files/` (site-id discovered by reading wp-config.php and the `wp_blogs` table layout from a read-only listing — if that's brittle, fall back to directory listings under `wp-content/uploads/sites/<id>/`).
- **Django years** (2016–2019): `rsync -avP andreicek@dorscluc.org:/var/www/{YEAR}-static/ archive/<year>/_static-backup/`. Rendered pages come from Pass 1.
- **Main site**: same pattern as WP years for `wp-content/uploads/`.

All rsync invocations use `--dry-run` first for review, then the real pull. No `--delete`, no writes to the remote.

### Pass 3 — Cross-site link rewriting

`wget --convert-links` only rewrites links within the crawled host. With path-based archive layout, absolute cross-site references must be rewritten or they will 404 once the original domains are gone.

A Python post-processor walks `archive/**/*.html` and rewrites:

- `https?://(www\.)?dorscluc\.org/PATH` → `/main/PATH`
- `https?://(\d{4})\.dorscluc\.org/PATH` → `/<year>/PATH`
- `https?://files\.dorscluc\.org/PATH` → wherever those assets land (likely `/<year>/files/PATH` if year-scoped, else `/main/files/PATH`)

The rewriter:
- Uses `lxml` for parsing (tolerates malformed WP HTML).
- Operates on `href`, `src`, `srcset`, `action`, `data-*` attributes, and inline `style="... url(...)"`.
- Leaves external links (not on a dorscluc domain) untouched.
- Writes in-place but only after a clean parse round-trip.

### Pass 4 — 2023 reconciliation

The 2023 content lives at `www.dorscluc.org/dors-2023/`. We want it at `/2023/` too.

Options (pick at implementation time — design-level either is fine):
a) Copy `archive/main/dors-2023/` → `archive/2023/`, re-run the rewriter scoped to `/2023/` so relative links point into that subtree.
b) Leave it at `archive/main/dors-2023/` and have the Caddyfile alias `/2023/*` → `/main/dors-2023/*`.

Preference: (a) — keeps the Caddyfile trivial and the archive filesystem-portable to non-Caddy servers.

## Caddyfile

```caddy
{
    auto_https off
}

:80, archive.dorscluc.org {
    root * {$ARCHIVE_ROOT:.}
    encode zstd gzip

    handle / {
        rewrite * /index.html
        file_server
    }

    handle /main/* {
        file_server { index index.html }
    }

    @years path_regexp year ^/(20[0-9]{2})(/.*)?$
    handle @years {
        file_server { index index.html }
    }

    handle /assets/* {
        file_server
    }

    handle {
        rewrite * /404.html
        file_server
    }
}
```

Operator swaps the site address + flips `auto_https` to get real TLS. `ARCHIVE_ROOT` env var overrides the document root.

## Landing page

Hand-authored `index.html`. No framework, no JS.

Content:
- Title: "DORS/CLUC — Archive"
- Lead paragraph: one sentence explaining that the live site retired and this is a snapshot.
- Grid of year cards, most recent first. Each card:
  - Year
  - 1–2 sentence blurb. Seed values auto-extracted from each year's `<title>`, `<meta name="description">`, or first heading; editable afterward in the HTML.
  - Link to `/<year>/`.
- Footer link to `/main/` — "original dorscluc.org pages".

Styling: a small self-contained CSS file in `assets/`. Serif/monospace, no tracking, no external fonts.

## What this design explicitly excludes

- No live server writes — no WP plugin, no `wp-cli`, no DB dumps.
- No concurrent crawling — single `wget` at a time.
- No authenticated content — login-gated URLs are skipped.
- No year stubs for never-ran years (pre-2013, 2021, 2024, 2025).
- No search functionality — archives are browseable, not queryable.
- No retention of `wp-login.php`, `wp-admin/`, `xmlrpc.php`, `wp-json` — crawler excludes these via `--reject-regex`.

## Verification

For each year after capture + rewrite:
1. Spot-check the landing page of each year loads under `caddy run` at `http://localhost/<year>/` with all images rendering.
2. Grep `archive/**/*.html` for any remaining `https?://.*\.dorscluc\.org` occurrences — expect zero (or a known allowlist of social embed URLs).
3. Random sample 10 pages per year, open in a browser, confirm no broken asset and no network request to `*.dorscluc.org`.
4. Confirm the total archive size is reasonable (target: < 5 GB before compression).

## Deliverables

- `archive/` populated folder (under the project working dir).
- `archive/Caddyfile` as specified.
- `archive/index.html`, `archive/404.html`, `archive/assets/`.
- Scripts used to build it, checked into the repo under `scripts/` (crawler driver, rewriter) — so future top-ups are trivial.
- A `README.md` at the project root with "how to host this" instructions.
