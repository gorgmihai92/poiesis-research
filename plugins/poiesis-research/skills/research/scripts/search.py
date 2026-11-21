#!/usr/bin/env python3
"""Search OpenAlex and Semantic Scholar together. Run with `python3 -I`.

  search.py "query" [--limit 10] [--from-year 2000] [--sort relevance|cited|recent] [--brief]
  search.py --doi 10.1017/S0266267124000063
  search.py "query" --db all          every database: also Crossref, Europe PMC and arXiv

Each work shows its citations in each database, a first guess of the evidence kind (review / empirical /
analytical, from title and abstract) and whether an open copy exists.

When OpenAlex or Semantic Scholar refuses (budget used up, throttled, no connection), Crossref, then Europe PMC,
then arXiv answer in its place, so two databases are asked whenever two will answer. The last line, "Coverage",
names the databases that answered and the ones that refused. Answers are cached for a day; --fresh asks again.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402

SORTS = {"relevance": None, "cited": "cited_by_count:desc", "recent": "publication_date:desc"}


def full(w: dict, n: int | None) -> None:
    head = f"{n}. " if n is not None else ""
    print(f"{head}{w['title']} ({w['year']})")
    print(f"   {', '.join(w['authors'][:6])}{' et al.' if len(w['authors']) > 6 else ''}")
    print(f"   {w['venue'] or '?'} · {w['type'] or '?'} · {sc.cites(w)} · {sc.evidence_kind(w)}" + (" · RETRACTED" if w["retracted"] else ""))
    print(f"   doi: {w['doi'] or '-'} · OA: {w['oa_status'] or '-'} · licence: {w['license'] or '-'}")
    if w["oa_pdf"]:
        print(f"   pdf: {w['oa_pdf']}")
    elif w["landing"]:
        print(f"   page: {w['landing']}")
    if w["abstract"]:
        words = w["abstract"].split()
        print(f"   {' '.join(words[:60])}{' …' if len(words) > 60 else ''}")
    print()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query", nargs="?")
    p.add_argument("--doi")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--from-year", type=int)
    p.add_argument("--oa-only", action="store_true")
    p.add_argument("--sort", choices=SORTS, default="relevance")
    p.add_argument("--db", choices=["both", "openalex", "s2", "crossref", "epmc", "arxiv", "all"], default="both")
    p.add_argument("--json", action="store_true")
    p.add_argument("--brief", action="store_true", help="one line per work, for scanning many queries")
    sc.add_request_args(p)
    a = p.parse_args()
    sc.apply_request_args(a)

    works: list[dict] = []
    refused = 0  # how many of the two first databases did not answer
    others = [d for d in ("crossref", "epmc", "arxiv") if a.db in (d, "all")]
    if a.doi:
        doi = a.doi.removeprefix("https://doi.org/")
        if a.db in ("both", "openalex", "all"):
            try:
                works += [w for w in [sc.openalex_doi(doi)] if w]
            except sc.REFUSALS as e:
                refused += 1
                print(f"(OpenAlex unavailable: {e})", file=sys.stderr)
        if a.db in ("both", "s2", "all"):
            try:
                works += [w for w in [sc.s2_doi(doi)] if w]
            except sc.REFUSALS as e:
                refused += 1
                print(f"(Semantic Scholar unavailable: {e})", file=sys.stderr)
        for name in others:
            works += [w for w in [sc.ask(sc.FALLBACKS[name][1], doi)] if w]
        if a.db == "both" and refused:
            works += [w for w in [sc.fallback_doi(doi)] if w]
    elif a.query:
        if a.db in ("both", "openalex", "all"):
            filters = []
            if a.from_year:
                filters.append(f"from_publication_date:{a.from_year}-01-01")
            if a.oa_only:
                filters.append("is_oa:true")
            try:
                works += sc.openalex_search(a.query, a.limit, SORTS[a.sort], filters)
            except sc.BudgetExhausted as e:
                refused += 1
                print(f"(OpenAlex unavailable: {e})", file=sys.stderr)
            except Exception as e:  # short rate limit or outage: keep going with Semantic Scholar
                refused += 1
                print(f"(OpenAlex unavailable: {e}; try again in a minute)", file=sys.stderr)
        if a.db in ("both", "s2", "all"):
            try:
                works += sc.s2_search(a.query, a.limit, by_citations=a.sort == "cited", year=f"{a.from_year}-" if a.from_year else None)
            except Exception as e:  # S2 throttling must not lose the OpenAlex results
                refused += 1
                print(f"(Semantic Scholar unavailable: {e})", file=sys.stderr)
        for name in others:
            works += sc.ask(sc.FALLBACKS[name][0], a.query, a.limit, a.from_year) or []
        if a.db == "both" and refused:  # Crossref, Europe PMC, arXiv: one for each database that refused
            works += sc.fallback_search(a.query, a.limit, a.from_year, need=refused)
    else:
        p.error("give a query or --doi")

    works = sc.merge_all(works)
    if a.oa_only:
        works = [w for w in works if w.get("oa_pdf") or w.get("oa_status") not in (None, "closed", "unknown")]
    if a.sort == "cited":
        works.sort(key=lambda w: -sc.most_cited(w))

    if a.json:
        json.dump([{k: v for k, v in w.items() if k != "references"} | {"evidence": sc.evidence_kind(w)} for w in works], sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif a.brief:
        for w in works:
            print(sc.brief(w))
    else:
        for i, w in enumerate(works, 1):
            full(w, i if len(works) > 1 else None)
    if not works:
        print("No results.")
    return 0


if __name__ == "__main__":
    sys.exit(sc.finish(main))
