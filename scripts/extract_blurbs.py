"""Extract a short blurb per year for the landing page.

Reads archive/<year>/index.html, returns (year, blurb) where blurb is the
first of:
  1. <meta name="description" content="...">
  2. <meta property="og:description" content="...">
  3. first <p> in the body, trimmed to 140 chars

Output: prints the JSON map to stdout.
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
