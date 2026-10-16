#!/usr/bin/env python3
"""Check that every DOI in a library's notes exists and matches the note's title. Run with `python3 -I`.

  verify_citations.py research/notes [more folders or .md files …]

Each note's DOI is looked up in the DOI registry (doi.org, which covers Crossref and DataCite) and its registered
title is compared with the note's title (first heading). A model asked whether its own citations are correct
often answers wrongly (Walters & Wilder 2023), so this check is external. Prints one line per note:
OK, MISMATCH (DOI exists, title differs: wrong DOI or wrong title), NOT FOUND, or NO DOI.
"""
import argparse
import difflib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOI = re.compile(r"(?:doi\.org/|doi:\s*)(10\.\d{4,9}/[^\s>\]\"'`,;]+)", re.I)


def trim(doi: str) -> str:
    """Drop trailing punctuation and unbalanced closing parentheses; keep inner ones (S0016-3287(98)00086-X)."""
    doi = doi.rstrip(".")
    while doi.endswith(")") and doi.count(")") > doi.count("("):
        doi = doi[:-1].rstrip(".")
    return doi


UA = {"User-Agent": "poiesis-research/2 (citation check)", "Accept": "application/vnd.citationstyles.csl+json"}


def fold(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split()


def registered_title(doi: str) -> str | None:
    req = urllib.request.Request(f"https://doi.org/{urllib.parse.quote(doi, safe='/')}", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.load(res)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    title = data.get("title")
    return title[0] if isinstance(title, list) else title


def similarity(a: str, b: str) -> float:
    wa, wb = fold(a), fold(b)
    if not wa or not wb:
        return 0.0
    # Notes may shorten or extend a title (subtitle, edition): compare the shorter against the longer's start.
    short, long_ = sorted((wa, wb), key=len)
    return difflib.SequenceMatcher(None, short, long_[: len(short) + 2]).ratio()


def check(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    heading = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), "")
    title = re.sub(r"\s*\([^)]*\d{4}[^)]*\)\s*$", "", heading)  # drop "(Author, Year)"
    m = DOI.search(text)
    if not m:
        return "NO DOI", heading
    doi = trim(m.group(1))
    try:
        reg = registered_title(doi)
    except Exception as e:  # network or registry trouble: say so, never guess
        return "ERROR", f"{doi}: {e}"
    if reg is None:
        return "NOT FOUND", doi
    score = similarity(title, reg)
    return ("OK" if score >= 0.6 else "MISMATCH"), f"{doi} · registered: {reg}" + ("" if score >= 0.6 else f" · note: {title}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="+", type=Path)
    a = p.parse_args()
    files = sorted(f for x in a.paths for f in ([x] if x.is_file() else x.rglob("*.md")))
    counts: dict[str, int] = {}
    for f in files:
        status, detail = check(f)
        counts[status] = counts.get(status, 0) + 1
        print(f"{status:9} {f.name} · {detail}")
    print("\n" + " · ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    return 1 if counts.get("MISMATCH") or counts.get("NOT FOUND") else 0


if __name__ == "__main__":
    sys.exit(main())
