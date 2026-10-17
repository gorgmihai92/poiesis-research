#!/usr/bin/env python3
"""Group studies that share an author, so a body of evidence is counted by independent groups. Run with `python3 -I`.

  independence.py 10.1037/a0019486 10.1177/1745691616652873 ...

Studies linked by a shared author, directly or through another study, form one group. Shared datasets and samples
are not in the metadata: check the methods of each group by hand. A group is a lead about independence, not proof:
a shared author is not always a shared method, and different authors can share one dataset. A large consortium
paper (dozens of authors) can link groups that are otherwise independent: read who links them.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dois", nargs="+")
    a = p.parse_args()

    works = sc.openalex_dois(a.dois)
    found = {(w["doi"] or "").lower() for w in works}
    missing = [d for d in a.dois if d.lower().removeprefix("https://doi.org/") not in found]

    parent = list(range(len(works)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_author: dict[str, int] = {}
    for i, w in enumerate(works):
        for name in w["authors"]:
            k = sc.fold(name)
            if k in by_author:
                parent[root(i)] = root(by_author[k])
            else:
                by_author[k] = i

    groups: dict[int, list[int]] = {}
    for i in range(len(works)):
        groups.setdefault(root(i), []).append(i)
    print(f"{len(works)} studies, {len(groups)} independent groups by author.\n")
    for n, members in enumerate(sorted(groups.values(), key=len, reverse=True), 1):
        names = [{sc.fold(x) for x in works[i]["authors"]} for i in members]
        shared = set.intersection(*names) if len(members) > 1 else set()
        linked = {x for i, s in enumerate(names) for x in s if any(x in t for j, t in enumerate(names) if j != i)}
        who = ", ".join(sorted(shared or linked)[:4]) if len(members) > 1 else "no shared author"
        print(f"Group {n} ({len(members)}): {who}")
        for i in members:
            print("  " + sc.brief(works[i]))
    if missing:
        print(f"\nNot found in OpenAlex (check by hand): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
