#!/usr/bin/env python3
"""Forward citations: the later works that cite a study, with replications and critiques flagged. Run with `python3 -I`.

  citing.py --doi 10.1037/a0019486 [--limit 200]

Reads up to --limit citing works from OpenAlex (the most cited first, plus a search among them for replications,
critiques, comments and reanalyses), and prints the flagged ones first, then the most cited followers. A flag is a
first guess from the title and abstract: confirm it by reading the work.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402

FLAGS = {
    "replication": r"\breplicat|\breproduc|many labs|multi-?(?:lab|site)|registered report",
    "failed": r"fail(?:s|ed|ure)? to (?:replicate|reproduce|find)|no evidence|null (?:effect|result|finding)|does not replicate|not replicate",
    "critique": r"\bcritiqu|\bcritic(?:al|ism)|\bcomment(?:ary)? on\b|\breply\b|\brebuttal|reanalys|re-analys|\bre-?examin|revisit|\bcorrection\b|erratum|\bbias(?:es)? in\b|\bflaw",
}
SEARCHES = ["replication", "failed to replicate", "no evidence", "critique", "comment", "reanalysis"]


def flags(w: dict) -> list[str]:
    text = f"{w['title']} {w['abstract']}".lower()
    return [name for name, rx in FLAGS.items() if re.search(rx, text)]


def rank(w: dict) -> tuple:
    """Flags in the title before flags only in the abstract, then the most cited."""
    in_title = any(re.search(rx, w["title"].lower()) for rx in FLAGS.values())
    return (not in_title, -(w["cited_openalex"] or 0))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--doi", required=True)
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--show", type=int, default=15, help="flagged works to show (0 = all)")
    p.add_argument("--top", type=int, default=5, help="most cited followers to show")
    a = p.parse_args()

    raw = sc.openalex_work(a.doi)
    if not raw:
        print(f"Not found in OpenAlex: {a.doi}")
        return 1
    seed = sc.norm_openalex(raw)
    wid = seed["openalex"].rsplit("/", 1)[-1]
    cites = [f"cites:{wid}"]
    found = [sc.norm_openalex(w) for w in sc.openalex({"filter": cites[0], "sort": "cited_by_count:desc", "per-page": min(a.limit, 200)}).get("results", [])]
    for q in SEARCHES:  # in the title, the most cited first: big replications rank low by relevance
        r = sc.openalex({"filter": f"{cites[0]},title.search:{q}", "sort": "cited_by_count:desc", "per-page": 25})
        found += [sc.norm_openalex(w) for w in r.get("results", [])]
    works = {w["openalex"]: w for w in found}.values()

    print(f"{seed['title']} ({seed['year']}) · {sc.cites(seed)}" + (" · RETRACTED" if seed["retracted"] else ""))
    print(f"Read {len(works)} of {seed['cited_openalex'] or 0} citing works (OpenAlex).\n")
    flagged = sorted((w for w in works if flags(w) or w["retracted"]), key=rank)
    shown = flagged[: a.show] if a.show else flagged
    print(f"Flagged ({len(flagged)}), title matches first, then most cited:" if flagged else "Flagged: none in the works read.")
    for w in shown:
        print(sc.brief(w, "[" + ", ".join(flags(w) or ["retracted"]) + "] "))
    if len(shown) < len(flagged):
        print(f"... {len(flagged) - len(shown)} more (--show 0 for all)")
    rest = sorted((w for w in works if not (flags(w) or w["retracted"])), key=lambda w: -(w["cited_openalex"] or 0))[: a.top]
    if rest:
        print("\nMost cited followers:")
        for w in rest:
            print(sc.brief(w))
    if (seed["cited_openalex"] or 0) > len(works):
        print(f"\nNot all citing works were read: raise --limit, or search them by topic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
