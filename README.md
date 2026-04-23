# dorscluc.org archive

Static snapshot of every DORS/CLUC conference edition (1996–2026) plus the
historical main site.

Licensed **[CC BY-SA 4.0](LICENSE)**: use, share, and adapt freely with
attribution; derivative works must be released under the same license.

## Contents

- `archive/` — the built archive: `Caddyfile`, landing page (`index.html`),
  `404.html`, assets, and per-year HTML trees (`main/`, `1996/` … `2026/`).
  The large crawled subtrees are **not tracked in git**; they ship as a
  tarball (~985 MB) served from the live archive.

## Downloading the archive content

The repo contains only the build pipeline + static scaffolding (~170 KB).
To get the actual crawled content, pull the tarball from the live site:

```sh
curl -O https://archive.dorscluc.org/dorscluc-archive-latest.tar.zst
tar --zstd -xf dorscluc-archive-latest.tar.zst
```

Dated builds are also available, e.g.
`https://archive.dorscluc.org/dorscluc-archive-20260423.tar.zst`.

## Fixing a page in the archive

1. Download + extract the tarball as above.
2. Find the page under `archive/<year>/…/index.html`.
3. Edit.
4. Open a PR against this repo with the rewritten file attached, and
   note what you changed in the description. A maintainer reviews,
   applies it to the source archive directory, rebuilds the tarball,
   and redeploys.

For small typo fixes inside HTML files, you can often just open an
issue with a quote of the wrong/right text — a maintainer will patch
it in.
- `scripts/` — the capture + post-processing pipeline. Re-runnable.
- `tests/` — pytest suite for the link rewriter.
- `docs/superpowers/specs/` — design doc.
- `docs/superpowers/plans/` — implementation plan this project was built from.

## What's in the archive

| Path              | Source                                        | Notes                                    |
|-------------------|-----------------------------------------------|------------------------------------------|
| `/`               | Hand-built landing page                       | Links to every year + `/main/`.          |
| `/main/`          | `www.dorscluc.org` via Yoast sitemap (376 URLs) | Evergreen pages and post archives.     |
| `/2013/` – `/2022/` | `YYYY.dorscluc.org` (WP multisite + Django)   | Full mirror of each year's subdomain.  |
| `/2023/`          | Copy of `/main/dors-2023/`                    | 2023 never got its own subdomain.        |
| `/2026/`          | `2026.dorscluc.org` (the current site)        | The final edition.                       |

Years that never ran publicly (pre-2013, 2021, 2024, 2025) are not listed.

## How to host this archive

1. Unpack the tarball somewhere: `tar --zstd -xf dorscluc-archive-*.tar.zst`
2. Install Caddy v2.
3. Edit `archive/Caddyfile`:
   - Change the site address (`:8080`) to your hostname (e.g.
     `archive.dorscluc.org`).
   - Flip `auto_https off` → `auto_https on` and add
     `email you@example.com` in the global block if you want automatic TLS.
4. `cd archive && caddy run`.

That's it — no database, no PHP, no cron.

You can also run Caddy in Docker without installing anything:

```sh
cd archive
docker run --rm -p 8080:8080 -v "$(pwd):/srv:ro" -w /srv caddy:2-alpine \
    caddy run --config /srv/Caddyfile --adapter caddyfile
```

## How to rebuild the archive

From a checkout of this repo, with the source site still live:

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install pytest lxml
pytest tests/                       # rewriter unit tests (should stay green)

scripts/crawl_all.sh                # per-year subdomain crawls (sequential)
scripts/crawl_main.sh               # www.dorscluc.org via sitemap seeds

for y in main 2013 2014 2015 2016 2017 2018 2019 2020 2022 2026; do
    python scripts/rewrite_links.py "archive/$y"
done

scripts/reconcile_2023.sh           # copy main/dors-2023/ -> 2023/
scripts/verify.sh                   # sanity checks
```

See `docs/superpowers/plans/2026-04-23-dorscluc-archive.md` for the full
design rationale and task breakdown.

## Rsync backfill (optional)

`scripts/rsync_backfill.sh` is an additional read-only pass that pulls raw
media directories (`wp-content/uploads/`, Django `*-static/`) directly
from the source VM over SSH. It catches files not linked from any crawled
page. It's not needed for the visitor-visible archive — the existing
build is complete on that axis. Run it only if you want the maximum
possible media fidelity before the source is retired; it requires filling
in the `SITE_ID` map inside the script.
