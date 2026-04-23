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

# Plain form. Matches:  scheme://[www.|YYYY.|files.]dorscluc.org[rest]
# Captures: 1 = subdomain label or empty, 2 = path/query/fragment (may be empty)
_DORSCLUC_URL_RE = re.compile(
    r"https?://"
    r"(?:([a-z0-9-]+)\.)?"
    r"dorscluc\.org"
    r"(/[^\s\"'<>()]*)?",
    re.IGNORECASE,
)

# JSON-escaped form found inside inline <script> data: https:\/\/...
_DORSCLUC_URL_ESCAPED_RE = re.compile(
    r"https?:\\/\\/"
    r"(?:([a-z0-9-]+)\.)?"
    r"dorscluc\.org"
    r"((?:\\/[^\s\"'<>()\\]*)*)",
    re.IGNORECASE,
)

# URL-encoded form found in query strings like ?url=https%3A%2F%2F...
_DORSCLUC_URL_PERCENT_RE = re.compile(
    r"https?%3A%2F%2F"
    r"(?:([a-z0-9-]+)\.)?"
    r"dorscluc\.org"
    r"((?:%2F[^\s\"'<>()%]*)*(?:%2F)?)",
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
    if rest.startswith("/"):
        return prefix + rest
    return prefix + "/" + rest


def _rewrite_escaped_match(match: re.Match[str]) -> str:
    sub = match.group(1)
    rest = match.group(2) or ""
    prefix = _map_subdomain(sub).replace("/", r"\/")
    if not rest:
        return prefix + r"\/"
    return prefix + rest


def _rewrite_percent_match(match: re.Match[str]) -> str:
    sub = match.group(1)
    rest = match.group(2) or ""
    prefix = _map_subdomain(sub).replace("/", "%2F")
    if not rest:
        return prefix + "%2F"
    return prefix + rest


def rewrite_html(text: str) -> str:
    """Rewrite every absolute dorscluc.org URL in `text` to archive-relative.

    Purely textual — does not parse HTML. This matters for malformed WP
    output and for URLs inside inline `style="..."` / `srcset="..."` /
    `<meta content="...">` strings, which a tag-aware rewriter would miss.
    Handles three encodings that appear in WP-generated HTML:
      1. plain          https://YYYY.dorscluc.org/path
      2. JSON-escaped   https:\\/\\/YYYY.dorscluc.org\\/path   (in inline JS)
      3. URL-encoded    https%3A%2F%2FYYYY.dorscluc.org%2Fpath (in query strings)
    External URLs, relative URLs, and non-http schemes are untouched.
    """
    text = _DORSCLUC_URL_RE.sub(_rewrite_match, text)
    text = _DORSCLUC_URL_ESCAPED_RE.sub(_rewrite_escaped_match, text)
    text = _DORSCLUC_URL_PERCENT_RE.sub(_rewrite_percent_match, text)
    return text


def rewrite_file(path: Path) -> bool:
    """Rewrite `path` in place. Return True if content changed."""
    original = path.read_text(encoding="utf-8", errors="replace")
    rewritten = rewrite_html(original)
    if rewritten != original:
        path.write_text(rewritten, encoding="utf-8")
        return True
    return False


_REWRITABLE_EXTS = (".html", ".htm", ".css", ".js", ".xml", ".txt", ".json")


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
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in _REWRITABLE_EXTS:
            total += 1
            if rewrite_file(path):
                changed += 1
    print(f"rewrote {changed}/{total} files under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
