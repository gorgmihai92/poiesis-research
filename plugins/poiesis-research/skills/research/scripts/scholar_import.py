#!/usr/bin/env python3
"""Combine Google Scholar results with OpenAlex and Semantic Scholar. Run with `python3 -I`.

  scholar_import.py export.csv [more.csv …] [--foundations foundations.json] [--top 40]

Google Scholar can only be searched by hand, so export the results from Publish or Perish
(https://harzing.com/resources/publish-or-perish, free: data source Google Scholar, File → Save as CSV).
Duplicates are merged, each work gets its counts from the other databases, works the field's top papers cite
(from foundations.py --json) come first, and works only Google Scholar has are flagged.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402


def read_pop(path: Path) -> list[dict]:
    out = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            title = (row.get("Title") or "").strip()
            if not title:
                continue
            authors = [x.strip() for x in (row.get("Authors") or "").split(",") if x.strip()]
            year = int(row["Year"]) if (row.get("Year") or "").strip().isdigit() else None
            cites = int(row["Cites"]) if (row.get("Cites") or "").strip().isdigit() else None
            out.append({
                **sc.empty(), "title": title, "authors": authors, "year": year,
                "venue": row.get("Source") or row.get("Publisher") or "", "type": row.get("Type") or "",
                "doi": (row.get("DOI") or "").strip().lower().removeprefix("https://doi.org/") or None,
                "cited_scholar": cites, "landing": row.get("ArticleURL") or None, "abstract": row.get("Abstract") or "",
                "oa_pdf": row.get("FullTextURL") or None,
            })
    return out


def find_openalex(w: dict) -> dict | None:
    if w.get("doi"):
        return sc.openalex_doi(w["doi"])
    for cand in sc.openalex_search(w["title"], 3):
        if sc.fold(cand["title"]) == sc.fold(w["title"]) and (not w["year"] or not cand["year"] or abs(cand["year"] - w["year"]) <= 2):
            return cand
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", nargs="+", type=Path)
    p.add_argument("--foundations", type=Path, help="foundations.py --json output to merge")
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    scholar = sc.merge_all([w for f in a.csv for w in read_pop(f)])
    # Old or obscure items are matched by title; many books keep no DOI.
    for i, w in enumerate(scholar):
        twin = find_openalex(w)
        if twin:
            scholar[i] = sc.merge(w, twin)
    try:
        for s2 in sc.s2_batch([w["doi"] for w in scholar if w.get("doi")]):
            for i, w in enumerate(scholar):
                if (w.get("doi") or "") == (s2.get("doi") or "-"):
                    scholar[i] = sc.merge(w, s2)
    except Exception as e:
        print(f"(Semantic Scholar unavailable: {e})", file=sys.stderr)

    found = json.loads(a.foundations.read_text()) if a.foundations else []
    for w in found:
        w.setdefault("cited_scholar", None)
    combined = sc.merge_all(scholar + [{**sc.empty(), **w} for w in found])
    share = {sc.key(w): w.get("seed_share", 0) for w in found}
    in_scholar = {sc.key(w) for w in scholar}

    def best(w: dict) -> int:
        return max(w.get("cited_scholar") or 0, w.get("cited_openalex") or 0, w.get("cited_s2") or 0)

    combined.sort(key=lambda w: (-share.get(sc.key(w), 0), -best(w)))
    combined = combined[: a.top]

    if a.json:
        json.dump([{k: v for k, v in w.items() if k != "references"} | {"seed_share": share.get(sc.key(w), 0),
                   "in_scholar": sc.key(w) in in_scholar, "evidence": sc.evidence_kind(w)} for w in combined],
                  sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    print(f"{len(scholar)} works from Google Scholar" + (f", {len(found)} from foundations" if found else "") + ":\n")
    for w in combined:
        tags = []
        if share.get(sc.key(w)):
            tags.append(f"{share[sc.key(w)]:.0%} of seeds")
        if sc.key(w) in in_scholar and not w.get("openalex") and not w.get("s2"):
            tags.append("only in Google Scholar")
        if found and sc.key(w) not in in_scholar:
            tags.append("not in the Scholar export")
        print(sc.brief(w, (" · ".join(tags) + " · ") if tags else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
