#!/usr/bin/env python3
"""Check that each note's DOI exists and matches the note's title. Run with `python3 -I`.

  verify_citations.py research/notes [more folders or .md files …]

Each note's DOI, the first on its **Source** line, is looked up in the DOI registry (doi.org, which covers Crossref and DataCite) and its registered
title is compared with the note's title (first heading). A model asked whether its own citations are correct
often answers wrongly (Walters & Wilder 2023), so this check is external. Prints one line per note:
OK, MISMATCH (DOI exists, title differs: wrong DOI or wrong title), NOT FOUND, NO DOI, UNREAD (something shaped
like a DOI stands on the Source line inside other text, such as a publisher's address, so it was not read as one),
or ERROR (the registry could not be asked or did not answer: nothing was checked).

A DOI is read after `doi.org/` or a publisher's `/doi/`, or bare (`10.1038/s41598-023-41032-5`) where it starts a
word: at the start of a line, or after a space, a bracket, a quotation mark, a colon (`doi:`, `arXiv:`), a comma, a
table's bar, a `·` or bold marks. Closing marks after it (`.`, `,`, `:`, `**`, `”`, an unbalanced `)`) are dropped.
DOIs elsewhere in a note, such as those of the later work that cites it, are other works' and are not checked.

Exit code 1 when a DOI is NOT FOUND, a MISMATCH, UNREAD, or an ERROR: a check that could not be completed has not
passed. NO DOI alone does not fail, because a work may have no DOI (a book, a page with a URL).
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

# One DOI pattern and one trim, the same in verify_citations.py, verify_quotes.py and library.py (copied: each script
# stands alone). A DOI is read after doi.org/ or a publisher's /doi/ (…/doi/10.…, …/doi/full/10.…), or bare where it
# starts a word: at a line's start, or after a space, a bracket, a quotation mark, a colon (doi:, arXiv:), a comma, a
# table's bar, a `·` or bold marks. One inside another address's path (…/articles/10.…) is not read.
DOI = re.compile(r"(?:doi\.org/|/doi/(?:[a-z]+/)?|(?<![^\s(\[<{|\"'“‘`*_·:,;]))(10\.\d{4,9}/[^\s<>\[\]\"'`,;|“”‘’·]+)", re.I)
SOURCE_LINE = re.compile(r"^[ \t]*[-*+][ \t]+\*\*Source:?\*\*:?(.*(?:\n[ \t]+\S.*)*)", re.M | re.I)


def trim(doi: str) -> str:
    """Drop what ends a DOI in prose: points, commas, colons, bold or italic marks and closing quotation marks at the
    end, and unbalanced closing parentheses; keep inner ones (S0016-3287(98)00086-X)."""
    while True:
        cut = doi.rstrip(".,:;*_\"'”’")
        if cut.endswith(")") and cut.count(")") > cut.count("("):
            cut = cut[:-1]
        if cut == doi:
            return doi
        doi = cut


def source_line(text: str) -> str:
    """A note's **Source** line with the indented lines that continue it, or "" when the note has none."""
    m = SOURCE_LINE.search(text)
    return m.group(1) if m else ""


def note_doi(text: str) -> str | None:
    """A note's own DOI: the first one on its **Source** line. A DOI elsewhere in a note (under "Later work", or in
    a link in its prose) is another work's."""
    m = DOI.search(source_line(text))
    return trim(m.group(1)) if m else None
# Anything shaped like a DOI: one on the Source line that the pattern above cannot read makes the note UNREAD.
DOI_SHAPED = re.compile(r"(?<!\d)10\.\d{4,9}/[^\s<>\[\]\"'`,;|“”‘’·]+")


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
    source = source_line(text)
    m = DOI.search(source)
    if not m:
        shaped = DOI_SHAPED.search(source)
        if shaped:  # e.g. https://publisher.example/articles/10.…: write the DOI itself, bare or after doi.org/
            return "UNREAD", f"{trim(shaped.group(0))} stands inside other text on the Source line: write the DOI itself there"
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
    if counts.get("ERROR"):
        n = counts["ERROR"]
        print(f"The check could not be completed: {n} note{'' if n == 1 else 's'} could not be looked up in the registry. "
              "They have not passed; run the check again.")
    return 1 if any(counts.get(k) for k in ("MISMATCH", "NOT FOUND", "UNREAD", "ERROR")) else 0


if __name__ == "__main__":
    sys.exit(main())
