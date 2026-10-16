#!/usr/bin/env python3
"""Search OpenAlex and Semantic Scholar together. Run with `python3 -I`.

  search.py "query" [--limit 10] [--from-year 2000] [--sort relevance|cited|recent] [--brief]
  search.py --doi 10.1017/S0266267124000063

Each work shows its citations in each database, a first guess of the evidence kind (review / empirical /
analytical, from title and abstract) and whether an open copy exists.
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
    p.add_argument("--db", choices=["both", "openalex", "s2"], default="both")
    p.add_argument("--json", action="store_true")
    p.add_argument("--brief", action="store_true", help="one line per work, for scanning many queries")
    a = p.parse_args()

    works: list[dict] = []
    if a.doi:
        doi = a.doi.removeprefix("https://doi.org/")
        if a.db in ("both", "openalex"):
            works += [w for w in [sc.openalex_doi(doi)] if w]
        if a.db in ("both", "s2"):
            works += [w for w in [sc.s2_doi(doi)] if w]
    elif a.query:
        if a.db in ("both", "openalex"):
            filters = []
            if a.from_year:
                filters.append(f"from_publication_date:{a.from_year}-01-01")
            if a.oa_only:
                filters.append("is_oa:true")
            try:
                works += sc.openalex_search(a.query, a.limit, SORTS[a.sort], filters)
            except sc.BudgetExhausted as e:
                print(f"(OpenAlex unavailable: {e})", file=sys.stderr)
            except Exception as e:  # short rate limit or outage: keep going with Semantic Scholar
                print(f"(OpenAlex unavailable: {e}; try again in a minute)", file=sys.stderr)
        if a.db in ("both", "s2"):
            try:
                works += sc.s2_search(a.query, a.limit, by_citations=a.sort == "cited", year=f"{a.from_year}-" if a.from_year else None)
            except Exception as e:  # S2 throttling must not lose the OpenAlex results
                print(f"(Semantic Scholar unavailable: {e})", file=sys.stderr)
    else:
        p.error("give a query or --doi")

    works = sc.merge_all(works)
    if a.oa_only:
        works = [w for w in works if w.get("oa_pdf") or w.get("oa_status") not in (None, "closed")]
    if a.sort == "cited":
        works.sort(key=lambda w: -max(w.get("cited_openalex") or 0, w.get("cited_s2") or 0))

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
    sys.exit(main())
