#!/usr/bin/env python3
"""Find a field's founding works from the field's own citations, not from keywords. Run with `python3 -I`.

  foundations.py "field" [--seeds 25] [--top 25] [--min-share 0.15] [--json]

1. Seeds: the most-cited reviews and articles about the field, from OpenAlex and Semantic Scholar.
2. Their bibliographies are read, and every work they cite is counted once per seed.
3. Works cited by many seeds come first, whatever their age. Generic method works (statistics, PRISMA) also
   rise: skip them.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query", nargs="?")
    p.add_argument("--doi", action="append", default=[], help="use these works as seeds instead of a search")
    p.add_argument("--seeds", type=int, default=25)
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--min-share", type=float, default=0.15, help="minimum share of seeds that must cite a work")
    p.add_argument("--no-s2", action="store_true", help="OpenAlex only")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    notes: list[str] = []
    s2_ok = not a.no_s2

    def s2(fn, *args, **kw):
        nonlocal s2_ok
        if not s2_ok:
            return None
        try:
            return fn(*args, **kw)
        except Exception as e:
            s2_ok = False
            notes.append("Semantic Scholar was busy; the rest uses OpenAlex.")
            return None

    # 1. Seeds.
    if a.doi:
        dois = [d.removeprefix("https://doi.org/") for d in a.doi]
        seeds = sc.openalex_dois(dois) + (s2(sc.s2_batch, dois) or [])
    elif a.query:
        reviews = sc.openalex_search(a.query, a.seeds, "cited_by_count:desc", ["type:review"], in_title_abstract=True)
        rest = sc.openalex_search(a.query, a.seeds, "cited_by_count:desc", in_title_abstract=True)
        s2_seeds = [w for w in s2(sc.s2_search, a.query, a.seeds * 2, by_citations=True) or [] if sc.on_topic(w, a.query)][: a.seeds]
        # Semantic Scholar seeds get their OpenAlex twin, whose bibliography is usually complete.
        twins = sc.openalex_dois([w["doi"] for w in s2_seeds if w.get("doi")])
        seeds = reviews[: a.seeds] + rest[: a.seeds] + s2_seeds + twins
    else:
        p.error("give a query or --doi")
    seeds = sc.merge_all(seeds)
    seeds = sorted(seeds, key=lambda w: -max(w.get("cited_openalex") or 0, w.get("cited_s2") or 0))[: a.seeds * 2]
    if not seeds:
        print("No seeds found.")
        return 1
    seed_keys = {sc.key(s) for s in seeds}
    if a.query:
        # Seeds matched only in the abstract can drift to another field (e.g. "argumentation" in finance).
        in_title = sum(1 for s in seeds if all(t in sc.fold(s["title"]) for t in sc.fold(a.query).split()))
        if in_title < len(seeds) / 3:
            notes.append(
                f"Only {in_title} of {len(seeds)} seeds have the query words in their title: check that the seeds are "
                "about the right field, or use the field's own term (e.g. 'logical fallacy' instead of 'fallacies')."
            )

    citing: dict[str, set[str]] = collections.defaultdict(set)
    influential: collections.Counter = collections.Counter()
    works: dict[str, dict] = {}
    with_refs: set[str] = set()

    def add(w: dict, seed: str, infl: bool = False) -> None:
        k = sc.key(w)
        works[k] = sc.merge(works[k], w) if k in works else w
        citing[k].add(seed)
        if infl:
            influential[k] += 1

    # 2a. OpenAlex bibliographies.
    by_id: dict[str, set[str]] = collections.defaultdict(set)
    for s in seeds:
        if s.get("references"):
            with_refs.add(sc.key(s))
            for r in set(s["references"]):
                by_id[r].add(sc.key(s))
    common = [r for r, c in sorted(by_id.items(), key=lambda x: -len(x[1])) if len(c) >= 2][: a.top * 6]
    for w in sc.openalex_ids(common):
        for seed in by_id[w["openalex"]]:
            add(w, seed)

    # 2b. Semantic Scholar bibliographies (influential flags), when the publisher allows them.
    for s in seeds:
        if s.get("s2") and s2_ok:
            refs = s2(sc.s2_references, s["s2"]) or []
            if refs:
                with_refs.add(sc.key(s))
            for w, infl in refs:
                add(w, sc.key(s), infl)

    # Join records of the same work that came with and without a DOI.
    by_title: dict[str, str] = {}
    for k in list(works):
        tk = f"{sc.fold(works[k]['title'])[:120]}|{works[k]['year']}"
        if tk in by_title and by_title[tk] != k:
            other = by_title[tk]
            works[other] = sc.merge(works[other], works.pop(k))
            citing[other] |= citing.pop(k, set())
            influential[other] += influential.pop(k, 0)
        else:
            by_title[tk] = k

    # Shares are over the seeds whose bibliography we could read, not all seeds.
    base = max(1, len(with_refs))
    need = max(2, round(a.min_share * base))
    ranked = sorted(
        (k for k in works if len(citing[k]) >= need and k not in seed_keys),
        key=lambda k: (-len(citing[k]), -influential[k], -max(works[k].get("cited_openalex") or 0, works[k].get("cited_s2") or 0)),
    )[: a.top]

    # 3. Citation counts from both databases for the result.
    missing = [works[k]["doi"] for k in ranked if works[k].get("doi") and works[k].get("cited_s2") is None]
    for w in s2(sc.s2_batch, missing) or []:
        k = next((r for r in ranked if (works[r].get("doi") or "").lower() == (w.get("doi") or "")), None)
        if k:
            works[k] = sc.merge(works[k], w)

    if a.json:
        out = [{**{x: y for x, y in works[k].items() if x != "references"}, "seed_share": len(citing[k]) / base,
                "influential_from_seeds": influential[k], "evidence": sc.evidence_kind(works[k])} for k in ranked]
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    print(f"Read the bibliographies of the {base} most-cited works on the topic:")
    for s in seeds[:8]:
        print("  " + sc.brief(s))
    if len(seeds) > 8:
        print(f"  … and {len(seeds) - 8} more")
    print(f"\nFounding works (cited by at least {need} of them):")
    for k in ranked:
        head = f"cited by {len(citing[k])} of {base} · "
        print(sc.brief(works[k], head))
    if not ranked:
        print("  none: lower --min-share or broaden the query")
    for n in notes:
        print(f"\nNote: {n}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except sc.BudgetExhausted as e:
        print(f"Stopped: {e}", file=sys.stderr)
        sys.exit(2)
