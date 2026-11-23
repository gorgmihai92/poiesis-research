#!/usr/bin/env python3
"""What a project's library already holds, one line per source. Run with `python3 -I`. It reads; it never writes.

  library.py [project folder]                 every note, and every entry of a Texere bibliography when there is one
  library.py --has 10.1037/a0019486           whether the library holds a work, by DOI, citation key or title words
  library.py --json

It reads `research/notes/**/*.md` (also under `docs/research/`): the title, authors and year from the heading, the
DOI from the **Source** line, and how much of the source was read (the **Read** line, or "abstract only" in older
notes). It counts the files in `research/maps`, `research/signals`, `research/data` and `research/funding`.

In a vault that uses Texere it also reads `Support/Texere/Bibliography/bibliography.json`: a list in which each
entry has an `id` (the citation key), an `obsidianPath` and a `reading-status`. A source held there is cited as
`[@key, p. N]`. Texere's folders belong to the owner: nothing in them is ever changed.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

TEXERE_INDEX = Path("Support") / "Texere" / "Bibliography" / "bibliography.json"
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


KINDS = {"maps": "evidence maps and prior-art maps", "signals": "signal notes", "data": "data series", "funding": "funding calls"}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def research_folder(root: Path) -> Path | None:
    return next((p for p in (root / "research", root / "docs" / "research") if p.is_dir()), None)


def texere_index(root: Path) -> Path | None:
    """The Texere bibliography of this folder, or of a folder above it (the vault's root)."""
    return next((f / TEXERE_INDEX for f in [root, *root.parents] if (f / TEXERE_INDEX).is_file()), None)


def read_note(path: Path, root: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    heading = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), path.stem)
    who = re.search(r"\(([^()]*?),?\s*((?:19|20)\d{2})\)\s*$", heading)
    doi = note_doi(text)
    read = re.search(r"^\s*[-*]\s*\*\*Read:\*\*\s*(.+)$", text, re.M)
    level = read.group(1).strip() if read else "abstract only" if re.search(r"\*\*abstract[^*]*only\*\*", text, re.I) else "not stated"
    return {"name": path.stem, "title": heading[: who.start()].strip() if who else heading, "authors": who.group(1).strip() if who else "", "year": who.group(2) if who else "",
            "doi": doi.lower() if doi else None, "read": re.split(r"[:,;.·(]", level)[0].strip()[:60] or "not stated", "path": str(path.relative_to(root))}


def read_texere(index: Path) -> tuple[list[dict], str | None]:
    """The entries of a Texere bibliography, read tolerantly: a missing field is "unknown", never an error."""
    try:
        data = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [], f"could not be read ({e})"
    if not isinstance(data, list):
        return [], "is not a list of entries"
    out = []
    for e in data:
        if not isinstance(e, dict) or not e.get("id"):
            continue
        title = e.get("title")
        year = (((e.get("issued") or {}).get("date-parts") or [[None]])[0] or [None])[0] if isinstance(e.get("issued"), dict) else None
        out.append({"key": str(e["id"]), "path": e.get("obsidianPath") or "unknown", "status": e.get("reading-status") or "unknown",
                    "title": title if isinstance(title, str) else "", "year": str(year or ""), "doi": str(e["DOI"]).lower() if e.get("DOI") else None})
    return out, None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", nargs="?", type=Path, default=Path("."), help="the project (default: this folder)")
    p.add_argument("--has", action="append", default=[], help="a DOI, a citation key, or words of a title")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    root = a.folder.resolve()
    research = research_folder(root)
    notes = sorted((read_note(f, root) for f in (research / "notes").rglob("*.md")), key=lambda n: n["name"]) if research and (research / "notes").is_dir() else []
    other = {kind: len([f for f in (research / kind).rglob("*") if f.is_file() and not f.name.startswith(".")]) for kind in KINDS if research and (research / kind).is_dir()}
    index = texere_index(root)
    entries, problem = read_texere(index) if index else ([], None)

    if a.has:
        code = 0
        for wanted in a.has:
            needle, words = wanted.lower().removeprefix("https://doi.org/").strip(), fold(wanted)
            hits = [f"note {n['path']} (read: {n['read']})" for n in notes if needle == n["doi"] or needle == n["name"].lower() or (len(words) > 8 and words in fold(n["title"]))]
            hits += [f"Texere @{e['key']} (reading-status: {e['status']}), cite as [@{e['key']}, p. N]" for e in entries
                     if needle.lstrip("@") == e["key"].lower() or needle == e["doi"] or (len(words) > 8 and words in fold(e["title"]))]
            print(f"{wanted}: " + ("; ".join(hits) if hits else "not in the library"))
            code = code or (0 if hits else 1)
        return code

    if a.json:
        json.dump({"folder": str(root), "notes": notes, "other": other, "texere": {"index": str(index) if index else None, "entries": entries, "problem": problem}}, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    if research is None and index is None:
        print(f"No library in {root}: no research/ folder and no Texere bibliography.")
        return 0
    print(f"Library of {root.name}: {len(notes)} source notes" + "".join(f", {n} {KINDS[k]}" for k, n in other.items() if n) + ".")
    for n in notes:
        who = f"{n['authors']} {n['year']}".strip() or "no author and year in the heading"
        print(f"- {n['name']} · {who} · {n['doi'] or 'no DOI'} · read: {n['read']} · {n['path']}")
    if index:
        where = index.relative_to(root) if index.is_relative_to(root) else index
        print(f"\nTexere bibliography ({where}): " + (problem or f"{len(entries)} entries. Cite one as [@key, p. N]. Its folders are read, never changed."))
        for e in entries:
            about = " · ".join(x for x in (e["title"][:70], e["year"], e["doi"]) if x)
            print(f"- @{e['key']} · reading-status: {e['status']} · {e['path']}" + (f" · {about}" if about else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
