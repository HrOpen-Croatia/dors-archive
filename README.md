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
