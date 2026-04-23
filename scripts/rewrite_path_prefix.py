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
