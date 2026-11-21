#!/usr/bin/env python3
"""Forward citations: the later works that cite a study, with replications and critiques flagged. Run with `python3 -I`.

  citing.py --doi 10.1037/a0019486 [--limit 200]

Reads up to --limit citing works from OpenAlex (the most cited first, plus a search among them for replications,
critiques, comments and reanalyses), and prints the flagged ones first, then the most cited followers. A flag is a
first guess from the title and abstract: confirm it by reading the work.

When OpenAlex refuses, the citing works come from Semantic Scholar and Europe PMC, which know fewer of them: the
output says how many were read and from where, and the last line, "Coverage", names the databases that answered.
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
    return (not in_title, -sc.most_cited(w))


def from_openalex(doi: str, limit: int) -> tuple[dict, list[dict]]:
    """The work and the works that cite it, from OpenAlex. Raises when OpenAlex refuses."""
    raw = sc.openalex_work(doi)
    if not raw:
        return {}, []
    seed = sc.norm_openalex(raw)
    wid = seed["openalex"].rsplit("/", 1)[-1]
    cites = [f"cites:{wid}"]
    found = [sc.norm_openalex(w) for w in sc.openalex({"filter": cites[0], "sort": "cited_by_count:desc", "per-page": min(limit, 200)}).get("results", [])]
    for q in SEARCHES:  # in the title, the most cited first: big replications rank low by relevance
        r = sc.openalex({"filter": f"{cites[0]},title.search:{q}", "sort": "cited_by_count:desc", "per-page": 25})
        found += [sc.norm_openalex(w) for w in r.get("results", [])]
    return seed, list({w["openalex"]: w for w in found}.values())


def from_others(doi: str, limit: int) -> tuple[dict, list[dict], list[str]]:
    """The work and the works that cite it, from the databases that answer when OpenAlex refuses."""
    seed = sc.ask(sc.s2_doi, doi) or sc.fallback_doi(doi) or {}
    found, names = [], []
    for name, fn in (("Semantic Scholar", sc.s2_citations), ("Europe PMC", sc.epmc_citations)):
        got = sc.ask(fn, doi, limit)
        if got:
            found += got
            names.append(name)
    return seed, sc.merge_all(found), names


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--doi", required=True)
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--show", type=int, default=15, help="flagged works to show (0 = all)")
    p.add_argument("--top", type=int, default=5, help="most cited followers to show")
    sc.add_request_args(p)
    a = p.parse_args()
    sc.apply_request_args(a)
    doi = a.doi.removeprefix("https://doi.org/")

    source = "OpenAlex"
    try:
        seed, works = from_openalex(doi, a.limit)
        if not seed:
            print(f"Not found in OpenAlex: {a.doi}")
            return 1
    except sc.REFUSALS as e:
        print(f"(OpenAlex unavailable: {e})", file=sys.stderr)
        seed, works, names = from_others(doi, a.limit)
        if not seed and not works:
            print(f"OpenAlex refused and no other database had {a.doi}: nothing was read. Try again later.")
            return 1
        seed = {**sc.empty(), "doi": doi, "title": doi, **seed}
        source = " and ".join(names) if names else "no database"

    known = sc.most_cited(seed)
    print(f"{seed['title']} ({seed['year']}) · {sc.cites(seed)}" + (" · RETRACTED" if seed["retracted"] else ""))
    print(f"Read {len(works)} of {known} citing works ({source}).\n")
    flagged = sorted((w for w in works if flags(w) or w["retracted"]), key=rank)
    shown = flagged[: a.show] if a.show else flagged
    print(f"Flagged ({len(flagged)}), title matches first, then most cited:" if flagged else "Flagged: none in the works read.")
    for w in shown:
        print(sc.brief(w, "[" + ", ".join(flags(w) or ["retracted"]) + "] "))
    if len(shown) < len(flagged):
        print(f"... {len(flagged) - len(shown)} more (--show 0 for all)")
    rest = sorted((w for w in works if not (flags(w) or w["retracted"])), key=lambda w: -sc.most_cited(w))[: a.top]
    if rest:
        print("\nMost cited followers:")
        for w in rest:
            print(sc.brief(w))
    if known > len(works):
        print(f"\nNot all citing works were read: raise --limit, or search them by topic.")
    if source != "OpenAlex":
        print("OpenAlex did not answer, so the title search for replications and critiques among the citing works was not run.")
    return 0


if __name__ == "__main__":
    sys.exit(sc.finish(main))
