"""Extract talks / sessions / speakers from every year of the archive into
a single talks.json file.

Coverage varies by year because the source sites had radically different
structures. The extractor is pragmatic: it tries the richest format first
(WordPress Conference Scheduler sessions with per-talk pages and Yoast
SEO metadata), then falls back to per-speaker pages, then to scraping
whatever schedule HTML exists.

Output schema (one entry per record, deduped by URL):
    {
        "year":     int,            # which edition it belongs to
        "title":    str,            # talk title or speaker name
        "speakers": [str, ...],
        "abstract": str,            # description / bio, may be empty
        "track":    str | None,
        "room":     str | None,
        "day":      str | None,     # "May 15, 2024" or "11.5.2018." etc.
        "url":      str,            # archive-relative path
        "kind":     "talk"|"speaker"|"session"
    }
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup

ARCHIVE = Path("archive")

# ---- helpers ---------------------------------------------------------

_MONTHS = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
_DAY_EN = re.compile(rf"\b{_MONTHS}\s+(\d{{1,2}}),\s+(\d{{4}})\b")


def _og(soup: BeautifulSoup, prop: str) -> str | None:
    m = soup.find("meta", property=prop)
    return m.get("content") if m else None


def _clean_title(s: str, year_suffixes: list[str]) -> str:
    t = re.sub(r"\s*[-—|–]\s*DORS/?CLUC[^<]*$", "", s).strip()
    for suf in year_suffixes:
        if t.endswith(suf):
            t = t[: -len(suf)].strip()
    return t


def _text_of(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


# ---- WP Conference Scheduler session pages ---------------------------

_SPEAKER_LABEL_RE = re.compile(r"Speaker[s]?\s*:\s*(.+?)(?:\s{2,}|$)", re.IGNORECASE)


def _parse_wpsc_session(path: Path, default_year: int) -> dict | None:
    html = path.read_text(encoding="utf-8", errors="replace")
    if "wpsc-single-session" not in html and "wpcs_session" not in html:
        return None
    soup = BeautifulSoup(html, "lxml")

    title = _og(soup, "og:title") or (soup.title.string if soup.title else "")
    title = _clean_title(title or "", [" - DORS/CLUC", " - DORS/CLUC 2022"])

    abstract = _og(soup, "og:description") or ""
    abstract = re.sub(r"\s*(?:&hellip;|\.\.\.)?\s*Read more\s*$", "", abstract).strip()

    article = soup.find("article", class_=re.compile(r"wpsc-single-session|wpcs_session"))
    body_text = _text_of(article)

    # Year from article body "May 15, 2024" if present, else default.
    year = default_year
    daym = _DAY_EN.search(body_text)
    day = None
    if daym:
        day = daym.group(0)
        year = int(daym.group(3))

    # Speakers — <div class="session-speakers">, "Speakers:" label, or
    # <a rel="speaker"> links.
    speakers: list[str] = []
    spk_container = None
    if article:
        spk_container = article.find(class_=re.compile(r"session-speaker|wpsc-.*speaker"))
    if spk_container:
        for a in spk_container.find_all("a"):
            name = _text_of(a)
            if name:
                speakers.append(name)
        if not speakers:
            txt = _text_of(spk_container)
            speakers = [s.strip() for s in re.split(r",| and ", txt) if s.strip()]
    if not speakers:
        lm = _SPEAKER_LABEL_RE.search(body_text)
        if lm:
            chunk = lm.group(1).strip()
            # The speaker block is usually followed by the abstract.
            # Take up to the first capitalised sentence start heuristic.
            cut = re.split(r"(?<=[.!?])\s+[A-Z]", chunk, maxsplit=1)[0]
            speakers = [s.strip() for s in re.split(r",| and ", cut) if s.strip()]

    # Track / room from class names.
    track = None
    room = None
    if article:
        cls = " ".join(article.get("class", []))
        m = re.search(r"wpcs_track-([a-z0-9-]+)", cls)
        if m:
            track = m.group(1).replace("-", " ").title()
        m = re.search(r"wpcs_location-([a-z0-9-]+)", cls)
        if m:
            room = m.group(1).replace("-", " ").title()

    url = "/" + str(path.parent.relative_to(ARCHIVE)).replace("\\", "/") + "/"

    return {
        "year": year,
        "title": title,
        "speakers": speakers,
        "abstract": abstract,
        "track": track,
        "room": room,
        "day": day,
        "url": url,
        "kind": "session",
    }


# ---- WP person (speaker) pages ---------------------------------------

def _parse_wp_person(path: Path, default_year: int) -> dict | None:
    html = path.read_text(encoding="utf-8", errors="replace")
    if "/person/" not in str(path):
        return None
    soup = BeautifulSoup(html, "lxml")
    title = _og(soup, "og:title") or (soup.title.string if soup.title else "")
    title = _clean_title(title or "", [" - DORS/CLUC", " – DORS/CLUC"])
    abstract = _og(soup, "og:description") or ""
    url = "/" + str(path.parent.relative_to(ARCHIVE)).replace("\\", "/") + "/"
    return {
        "year": default_year,
        "title": title,
        "speakers": [title],
        "abstract": abstract,
        "track": None,
        "room": None,
        "day": None,
        "url": url,
        "kind": "speaker",
    }


# ---- Modern WP years (2013-2020): scrape speakers / schedule pages ---

def _parse_wp_speakers_index(path: Path, year: int) -> Iterable[dict]:
    """Extract speakers from a site's /speakers/ index page.

    Django theme (2016–2019) wraps each speaker in a `.speaker-name`.
    Older WP themes use plain <h3> headings per entry.
    """
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []

    # Django theme
    for sel in (".speaker-name", ".speaker h3", "h3.speaker-name"):
        nodes = soup.select(sel)
        if 3 <= len(nodes) < 200:
            for n in nodes:
                name = _text_of(n)
                if not name or len(name) > 200:
                    continue
                # Bio: nearest description element.
                bio_el = n.find_parent().find(class_=re.compile(r"description|bio"))
                bio = _text_of(bio_el)
                out.append({
                    "year": year, "title": name, "speakers": [name],
                    "abstract": bio[:800],
                    "track": None, "room": None, "day": None,
                    "url": f"/{year}/speakers/",
                    "kind": "speaker",
                })
            return out

    # WP fallback: h3 headings in the main content.
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return out
    for h in main.find_all(re.compile(r"^h[2-4]$")):
        name = _text_of(h)
        if not name or len(name) > 200:
            continue
        if re.search(r"skip to|menu|copyright|sitemap|sponsors|partner|friends",
                     name, re.I):
            continue
        a = h.find("a") or h.find_next("a")
        href = a.get("href") if a else None
        url = href if (href and href.startswith("/")) else f"/{year}/speakers/"
        out.append({
            "year": year, "title": name, "speakers": [name],
            "abstract": "",
            "track": None, "room": None, "day": None,
            "url": url, "kind": "speaker",
        })
    return out


# ---- Simple schedule-page scrape for legacy PHP years (2004–2010) ----

_CROATIAN_DATE = re.compile(r"\b(\d{1,2})[.](\d{1,2})[.](\d{2,4})[.]?\b")


def _parse_legacy_program(path: Path, year: int) -> Iterable[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    # Strip scripts and style; work on tables that look like schedules.
    for s in soup(["script", "style"]):
        s.extract()
    out: list[dict] = []
    seen_titles: set[str] = set()
    for tr in soup.find_all("tr"):
        cells = [_text_of(c) for c in tr.find_all(["td", "th"])]
        if not cells:
            continue
        # Heuristic: a row with >=2 non-empty cells where one is a time-like
        # string and another looks like a title.
        long_cells = [c for c in cells if len(c) > 15]
        if not long_cells:
            continue
        title = long_cells[0]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        # Try to pull a speaker name (short cell with a capitalised
        # two-word pattern).
        speakers: list[str] = []
        for c in cells:
            if re.match(r"^[A-ZŠŽČĆĐ][a-zšžčćđ]+\s+[A-ZŠŽČĆĐ][a-zšžčćđ]+", c) and len(c) < 80:
                speakers.append(c)
        out.append({
            "year": year,
            "title": title[:200],
            "speakers": speakers[:3],
            "abstract": "",
            "track": None, "room": None, "day": None,
            "url": f"/{year}/" + path.relative_to(ARCHIVE / str(year)).as_posix(),
            "kind": "talk",
        })
    return out


# ---- Main driver -----------------------------------------------------

def harvest() -> list[dict]:
    records: list[dict] = []

    # 1) /main/sessions/*/ — 2023–2025 talks on main site. Year comes from
    #    the article body's date; default 2023 if missing.
    for idx in (ARCHIVE / "main" / "sessions").glob("*/index.html"):
        rec = _parse_wpsc_session(idx, default_year=2023)
        if rec:
            records.append(rec)

    # 2) /2022/sessions/*/
    for idx in (ARCHIVE / "2022" / "sessions").glob("*/index.html"):
        rec = _parse_wpsc_session(idx, default_year=2022)
        if rec:
            records.append(rec)

    # 3) /2022/person/ and /2026/person/ — speaker pages.
    for year_dir in ("2022", "2026"):
        person_root = ARCHIVE / year_dir / "person"
        if not person_root.is_dir():
            continue
        for idx in person_root.glob("*/index.html"):
            rec = _parse_wp_person(idx, default_year=int(year_dir))
            if rec:
                records.append(rec)

    # 4) /main/person/ — speakers from the main site (for 2024/2025).
    mp = ARCHIVE / "main" / "person"
    if mp.is_dir():
        for idx in mp.glob("*/index.html"):
            rec = _parse_wp_person(idx, default_year=2024)
            if rec:
                records.append(rec)

    # 5) Modern WP years 2013-2020: walk /speakers/index.html best-effort.
    for y in (2013, 2014, 2015, 2020):
        for path in [ARCHIVE / str(y) / "speakers" / "index.html",
                     ARCHIVE / str(y) / "keynotes-and-speakers" / "index.html"]:
            if path.is_file():
                records.extend(_parse_wp_speakers_index(path, y))

    # 6) Django years 2016-2019: /speakers/ has rich HTML list with bios.
    for y in (2016, 2017, 2018, 2019):
        idx = ARCHIVE / str(y) / "speakers" / "index.html"
        if idx.is_file():
            records.extend(_parse_wp_speakers_index(idx, y))

    # 7) Legacy PHP years: program.php.html scrape.
    for y in (2004, 2005, 2006, 2007, 2008, 2009, 2010):
        for candidate in (
            ARCHIVE / str(y) / "program.php.html",
            ARCHIVE / str(y) / "program.shtml.html",
            ARCHIVE / str(y) / "program.html",
        ):
            if candidate.is_file():
                records.extend(_parse_legacy_program(candidate, y))
                break

    # Dedupe. Speakers: by (year, name). Sessions: by url. Talks: by
    # (year, title) because legacy scrapes often have no unique URL.
    seen_speaker: set[tuple[int, str]] = set()
    seen_session_urls: set[str] = set()
    seen_talks: set[tuple[int, str]] = set()
    out: list[dict] = []
    for r in records:
        if r["kind"] == "speaker":
            k = (r["year"], r["title"].lower())
            if k in seen_speaker:
                continue
            seen_speaker.add(k)
        elif r["kind"] == "session":
            if r["url"] in seen_session_urls:
                continue
            seen_session_urls.add(r["url"])
        else:  # talk
            k = (r["year"], r["title"].lower())
            if k in seen_talks:
                continue
            seen_talks.add(k)
        out.append(r)
    return out


def main() -> int:
    out_path = ARCHIVE / "talks.json"
    records = harvest()
    out_path.write_text(json.dumps(records, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    # Summary
    per_year: dict[int, int] = {}
    per_kind: dict[str, int] = {}
    for r in records:
        per_year[r["year"]] = per_year.get(r["year"], 0) + 1
        per_kind[r["kind"]] = per_kind.get(r["kind"], 0) + 1
    print(f"wrote {len(records)} records -> {out_path}")
    print("  by year:", sorted(per_year.items()))
    print("  by kind:", per_kind)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
