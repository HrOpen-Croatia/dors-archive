"""Transcode legacy HTML/text from ISO-8859-2 or Windows-1250 to UTF-8.

Caddy serves every file with `Content-Type: text/html; charset=utf-8`,
which per the HTML spec overrides any `<meta charset=...>` declaration
inside the document. The old (pre-2013) sites were authored in ISO-8859-2
(common for Croatian) or Windows-1250, and their bytes are not valid
UTF-8. Browsers then render replacement characters (U+FFFD `�`) in place
of Č, ć, š, ž, đ, etc.

Fix: read each legacy text file, detect which 8-bit encoding it actually
is (ISO-8859-2 vs Windows-1250), and rewrite in place as UTF-8. We also
rewrite any embedded `<meta ... charset=...>` declaration so it says
utf-8 — purely cosmetic, for view-source fidelity.

Only touches files under the classic-era year dirs (19YY, 2000..2010).
Modern years are already UTF-8.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TEXT_EXTS = {".html", ".htm", ".shtml", ".txt", ".css", ".js"}
LEGACY_ROOTS = [
    "archive/1996", "archive/1997", "archive/1998", "archive/1999",
    "archive/2000", "archive/2001", "archive/2002", "archive/2004",
    "archive/2005", "archive/2006", "archive/2007", "archive/2008",
    "archive/2009", "archive/2010",
]

# Bytes present in cp1250 but not meaningful in iso-8859-2 (the ranges
# cp1250 uses for punctuation like smart quotes, em-dash, bullet, etc.).
# If any of these occur in the file, prefer cp1250.
CP1250_HINT_BYTES = bytes(range(0x80, 0xA0))

# Match <meta ... charset="..."> variants. Case-insensitive.
_META_CHARSET_RE = re.compile(
    rb"(<meta[^>]*charset\s*=\s*[\"']?)([a-zA-Z0-9_\-]+)([\"']?[^>]*>)",
    re.IGNORECASE,
)


def pick_encoding(data: bytes) -> str | None:
    """Return 'iso-8859-2' or 'cp1250' if `data` is non-UTF-8 but decodes
    cleanly in one of those; `None` if already valid UTF-8; raise if
    neither works."""
    try:
        data.decode("utf-8")
        return None  # already UTF-8
    except UnicodeDecodeError:
        pass
    uses_cp1250_range = any(b in CP1250_HINT_BYTES for b in data)
    candidates = ("cp1250", "iso-8859-2") if uses_cp1250_range else ("iso-8859-2", "cp1250")
    for enc in candidates:
        try:
            data.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    raise ValueError("neither iso-8859-2 nor cp1250 decodes cleanly")


def transcode_file(path: Path) -> str | None:
    data = path.read_bytes()
    try:
        enc = pick_encoding(data)
    except ValueError as e:
        return f"!! {path}: {e}"
    if enc is None:
        return None  # already UTF-8, skip
    text = data.decode(enc)
    # Rewrite meta charset → utf-8 (cosmetic).
    new_bytes = _META_CHARSET_RE.sub(lambda m: m.group(1) + b"utf-8" + m.group(3),
                                      text.encode("utf-8"))
    path.write_bytes(new_bytes)
    return f"ok {enc:>11} -> utf-8  {path}"


def main() -> int:
    roots = [Path(r) for r in LEGACY_ROOTS if Path(r).is_dir()]
    converted = 0
    already_utf8 = 0
    failed = 0
    for root in roots:
        for f in root.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in TEXT_EXTS:
                continue
            msg = transcode_file(f)
            if msg is None:
                already_utf8 += 1
            elif msg.startswith("!!"):
                failed += 1
                print(msg, file=sys.stderr)
            else:
                converted += 1
    print(f"transcoded: {converted}, already utf-8: {already_utf8}, "
          f"failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
