#!/usr/bin/env python3
"""Check that each quote in a note is in its source's text, and that a report's references have notes. Run with
`python3 -I`.

  verify_quotes.py research/notes [more folders or .md files …] [--papers research/papers]
  verify_quotes.py --references report.md [--notes research/notes] [--bibliography PATH/bibliography.json]

Quotes. A quote is a list line that starts with a quotation mark, such as `- "exact words" (p. 4)`. It is looked
for in the text `extract_text.py` wrote for the note's source (the note's **File** line, or the same name in
--papers), on the page the note gives. Letters and digits must match in order; spaces, hyphens at line ends,
quotation marks and ligatures are ignored, because PDF text mangles them. One line per quote:
FOUND, WRONG PAGE (the words are in the source, on another page), NOT FOUND, or NO TEXT (the source's text is not
on this machine, so nothing was checked). An ellipsis splits a quote into parts that must all be there, in order.
A quote may run onto the next page, but it has to start on the page the note gives.

A quote that is found shows the words are in the source. It does not show that a claim built on them follows.

References. With --references, every DOI, link to a note, `[[note]]` link and `[@key]` citation in the report is
looked up in the notes folder (and in a Texere bibliography when there is one). One line per reference with no
note. "Author Year" mentions that match no note are listed as leads: they are a guess from the text, so they do
not change the exit code.

Exit code 1 when a quote is not found or is on the wrong page, or when a reference has no note. NO TEXT does not
fail by itself: add --strict to fail when any quote could not be checked, which a gate that reads only the exit
code needs.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

TEXERE_INDEX = Path("Support") / "Texere" / "Bibliography" / "bibliography.json"
DOI = re.compile(r"(?:doi\.org/|doi:\s*)(10\.\d{4,9}/[^\s>\]\"'`,;)]+(?:\([^\s)]*\)[^\s>\]\"'`,;)]*)*)", re.I)
QUOTE_MARKS = "\"“”„«»"
QUOTE_LINE = re.compile(r"^\s*[-*+]\s+[" + QUOTE_MARKS + r"](.+)$")
PAGE = re.compile(r"\bpp?\.\s*(\d+)(?:\s*[-–—]\s*(\d+))?")
MARKER = re.compile(r"^\[p\. (\d+)\]\s*$", re.M)
ELLIPSIS = re.compile(r"\s*\[?(?:…|\.\.\.)\]?\s*")
NOT_A_NOTE = re.compile(r"\.(pdf|png|jpe?g|gif|svg|webp|bmp|mp3|mp4|m4a|wav|mov|csv|json|canvas|base|xlsx?|docx?|pptx?|txt|html?|zip)$", re.I)
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
          "table", "figure", "fig", "section", "chapter", "since", "until", "from", "before", "after", "between", "during", "around", "about", "early", "late",
          "version", "edition", "spring", "summer", "autumn", "winter", "fall"}
MENTION = re.compile(r"\b([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+)(?:\s+(?:et al\.?|and|&)(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+)?)*,?\s+\(?((?:19|20)\d{2})[a-z]?\b")


# --- Quotes ----------------------------------------------------------------------------------


def fold(s: str) -> str:
    """Letters and digits only, lower case, ligatures and accents undone: what survives PDF text extraction."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s.casefold() if c.isalnum())


def pages_of(text: str) -> dict[int, str]:
    """The text by page, from the "[p. N]" markers extract_text.py writes. A text without markers is one page, 0."""
    marks = list(MARKER.finditer(text))
    if not marks:
        return {0: fold(text)}
    return {int(m.group(1)): fold(text[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(text)]) for i, m in enumerate(marks)}


def quotes_of(note: str) -> list[tuple[int, str, tuple[int, int] | None]]:
    """(line number, the quoted words, the pages given or None) for each quote line of a note."""
    out = []
    for n, line in enumerate(note.splitlines(), 1):
        m = QUOTE_LINE.match(line)
        if not m:
            continue
        rest = m.group(1)
        end = max(rest.rfind(c) for c in QUOTE_MARKS)
        if end <= 0:
            continue
        page = PAGE.search(rest[end + 1 :])
        span = (int(page.group(1)), int(page.group(2) or page.group(1))) if page else None
        out.append((n, rest[:end], span))
    return out


def find(quote: str, pages: dict[int, str], span: tuple[int, int] | None) -> tuple[str, str]:
    """Where a quote is: ("FOUND" | "WRONG PAGE" | "NOT FOUND", a few words on where)."""
    parts = [fold(p) for p in ELLIPSIS.split(quote)]
    parts = [p for p in parts if p]
    if not parts:
        return "NOT FOUND", "nothing to look for"

    def start_of(text: str) -> int:
        """Where the quote begins in a text, with all its parts in order; -1 when it is not there."""
        start = at = text.find(parts[0])
        if start < 0:
            return -1
        at += len(parts[0])
        for part in parts[1:]:
            at = text.find(part, at)
            if at < 0:
                return -1
            at += len(part)
        return start

    numbers = sorted(pages)
    short = f" (short: {sum(map(len, parts))} letters, a weak check)" if sum(map(len, parts)) < 20 else ""
    cited = "" if span is None else f"cited p. {span[0]}" + ("" if span[0] == span[1] else f"–{span[1]}")
    if span is not None and numbers != [0]:
        own = "".join(pages.get(n, "") for n in range(span[0], span[1] + 1))
        # A quote can run onto the next page, but it starts on a cited one.
        if 0 <= start_of(own + pages.get(span[1] + 1, "")) < len(own):
            return "FOUND", cited.removeprefix("cited ") + short
    whole = "".join(pages[n] for n in numbers)
    start = start_of(whole)
    if start < 0:
        return "NOT FOUND", "not in the source's text"
    if numbers == [0]:
        return "FOUND", "the text has no page markers" + short
    where = next((n for n in numbers if start_of(pages[n]) >= 0), None)
    if where is None:  # it crosses a page break: name the page it starts on
        seen = 0
        for n in numbers:
            seen += len(pages[n])
            if start < seen:
                first = n
                break
        if span is None:
            return "FOUND", "across two pages" + short
        return "WRONG PAGE", f"{cited}, found starting on p. {first}"
    if span is None:
        return "FOUND", f"p. {where}" + short
    return "WRONG PAGE", f"{cited}, found on p. {where}"


def source_text(note: Path, text: str, papers: list[Path]) -> Path | None:
    """The source's extracted text: the note's **File** line, else a file with the note's name in --papers."""
    candidates = []
    m = re.search(r"^\s*[-*]\s*\*\*File:\*\*\s*`([^`]+)`", text, re.M)
    if m:
        named = (note.parent / m.group(1)).resolve()
        candidates += [named.with_suffix(".txt"), named]
    for folder in papers:
        candidates += [folder / f"{note.stem}.txt"]
        if m:
            candidates.append(folder / Path(m.group(1)).with_suffix(".txt").name)
    return next((c for c in candidates if c.suffix == ".txt" and c.is_file()), None)


def check_quotes(paths: list[Path], papers: list[Path], strict: bool = False) -> int:
    notes = sorted(f for x in paths for f in ([x] if x.is_file() else x.rglob("*.md")))
    counts: dict[str, int] = {}
    unchecked = 0  # quotes in notes whose source text is not here

    def say(status: str, note: Path, detail: str) -> None:
        counts[status] = counts.get(status, 0) + 1
        print(f"{status:10} {note.name} · {detail}")

    for note in notes:
        text = note.read_text(encoding="utf-8")
        quotes = quotes_of(text)
        if not quotes:
            say("NO QUOTES", note, "no quote lines")
            continue
        source = source_text(note, text, papers)
        if source is None:
            say("NO TEXT", note, f"{len(quotes)} quote{'' if len(quotes) == 1 else 's'} not checked: the source's text is not here")
            unchecked += len(quotes)
            continue
        pages = pages_of(source.read_text(encoding="utf-8", errors="replace"))
        for line, quote, span in quotes:
            status, where = find(quote, pages, span)
            shown = quote if len(quote) <= 70 else quote[:67] + "…"
            say(status, note, f'line {line} · {where} · "{shown}"')
    print("\n" + (" · ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "No notes."))
    if unchecked:
        n = counts["NO TEXT"]
        print(f"{unchecked} quote{'' if unchecked == 1 else 's'} in {n} note{'' if n == 1 else 's'} could not be checked: "
              "the source's text is not on this machine." + (" With --strict that fails." if strict else " Add --strict to make that fail."))
    return 1 if counts.get("NOT FOUND") or counts.get("WRONG PAGE") or (strict and unchecked) else 0


# --- References ------------------------------------------------------------------------------


def trim(doi: str) -> str:
    doi = doi.rstrip(".").lower()
    while doi.endswith(")") and doi.count(")") > doi.count("("):
        doi = doi[:-1].rstrip(".")
    return doi


def library(notes: Path, bibliography: Path | None) -> dict:
    """What the library holds: note names, the DOIs in them, (surname, year) pairs from their headings, and the
    citation keys of a Texere bibliography."""
    lib = {"names": set(), "dois": set(), "people": set(), "keys": set()}
    for f in notes.rglob("*.md") if notes.is_dir() else []:
        text = f.read_text(encoding="utf-8", errors="replace")
        lib["names"].add(f.stem.lower())
        lib["dois"].update(trim(d) for d in DOI.findall(text))
        heading = next((l[2:] for l in text.splitlines() if l.startswith("# ")), "")
        m = re.search(r"\(([^()]*?),?\s*((?:19|20)\d{2})\)\s*$", heading)
        if m:
            for surname in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’\-]{3,}", m.group(1)):
                lib["people"].add((fold(surname), m.group(2)))
    if bibliography and bibliography.is_file():
        try:
            entries = json.loads(bibliography.read_text(encoding="utf-8"))
        except ValueError:
            entries = []
        for e in entries if isinstance(entries, list) else []:
            if isinstance(e, dict) and e.get("id"):
                lib["keys"].add(str(e["id"]))
                lib["names"].add(str(e["id"]).lower())
                if e.get("DOI"):
                    lib["dois"].add(trim(str(e["DOI"])))
    return lib


def check_references(report: Path, notes: Path, bibliography: Path | None) -> int:
    lib = library(notes, bibliography)
    text = report.read_text(encoding="utf-8")
    found, missing, leads = 0, [], []
    files = 0  # links to PDFs, images and data files: they are not notes, so they are not checked
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        line = re.sub(r"`[^`]*`", " ", line)  # what is shown as code is an example, not a reference
        for doi in {trim(d) for d in DOI.findall(line)}:
            if doi in lib["dois"]:
                found += 1
            else:
                missing.append((n, f"doi {doi}", "no note has this DOI"))
        for target in re.findall(r"\]\(([^)\s]+\.md)(?:#[^)]*)?\)", line):
            if "://" in target:
                continue
            if (report.parent / target).is_file() or Path(target).stem.lower() in lib["names"]:
                found += 1
            else:
                missing.append((n, target, "the linked note does not exist"))
        for target in re.findall(r"\[\[([^\]|#]+)", line):
            if NOT_A_NOTE.search(target.strip()):
                files += 1  # Texere links each annotation to its place in the PDF
                continue
            if Path(target.strip()).name.lower().removesuffix(".md") in lib["names"]:
                found += 1
            else:
                missing.append((n, f"[[{target.strip()}]]", "no note with this name"))
        for group in re.findall(r"\[([^\[\]]*@[^\[\]]*)\]", line):
            for key in re.findall(r"@([\w:.#$%&+?<>~/\-]*\w)", group):
                if key in lib["keys"] or key.lower() in lib["names"]:
                    found += 1
                else:
                    missing.append((n, f"[@{key}]", "not in the bibliography and no note with this name"))
        plain = re.sub(r"\[[^\]]*\]\([^)]*\)|\[\[[^\]]*\]\]|\[[^\]]*@[^\]]*\]|https?://\S+", " ", line)
        for m in MENTION.finditer(plain):
            surname, year = m.group(1), m.group(2)
            if fold(surname) in MONTHS or len(surname) < 3:
                continue
            if (fold(surname), year) not in lib["people"]:
                leads.append((n, f"{surname} {year}"))

    for n, what, why in missing:
        print(f"NO NOTE    line {n} · {what} · {why}")
    seen = set()
    for n, who in leads:
        if who not in seen:
            seen.add(who)
            print(f"MENTION    line {n} · {who} · no note with this author and year (a guess from the text: check by hand)")
    where = f"{notes}" + (f" and {bibliography}" if bibliography and bibliography.is_file() else "")
    print(f"\n{found + len(missing)} references in {report.name}: {found} have a note, {len(missing)} do not"
          f"{f'; {len(seen)} author-year mentions to check by hand' if seen else ''}. Looked in {where}."
          + (f" {files} link{' to a file that is not a note was' if files == 1 else 's to files that are not notes were'} not checked." if files else ""))
    return 1 if missing else 0


def texere_index(start: Path) -> Path | None:
    """A Texere bibliography in this folder or one above it (the vault's root)."""
    for folder in [start, *start.parents]:
        if (folder / TEXERE_INDEX).is_file():
            return folder / TEXERE_INDEX
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="*", type=Path, help="notes: folders or .md files")
    p.add_argument("--papers", type=Path, action="append", default=[], help="where the sources' .txt files are, when not next to their PDF")
    p.add_argument("--references", type=Path, help="a report: list its references that have no note")
    p.add_argument("--notes", type=Path, default=Path("research/notes"), help="the notes folder for --references (default research/notes)")
    p.add_argument("--bibliography", type=Path, help="a Texere bibliography.json (default: found from the report's folder)")
    p.add_argument("--strict", action="store_true", help="also fail when a quote could not be checked because its source's text is not here")
    a = p.parse_args()
    if a.references:
        if not a.references.is_file():
            p.error(f"{a.references} is not a file")
        return check_references(a.references, a.notes, a.bibliography or texere_index(a.references.resolve().parent))
    if not a.paths:
        p.error("give notes to check, or --references REPORT")
    return check_quotes(a.paths, a.papers, a.strict)


if __name__ == "__main__":
    sys.exit(main())
