#!/usr/bin/env python3
"""Yearly counts of works for a search or a topic, as counts and shares. Run with `python3 -I`.

  counts.py '"solid-state battery"' ['"quantum computing" OR "quantum computer"' …] [--from 2015] [--to 2026]
  counts.py --topic T10001 [--topic …]        an OpenAlex topic (the works whose primary topic it is)
  counts.py --taxonomy [--from 2022]          every OpenAlex topic, by year; past 200 topics it needs a free key
  counts.py '"moral injury"' --base 'moral OR morality'    shares within the works that match another search
  counts.py 'TITLE_ABS:"moral injury"' --db epmc           the same count in Europe PMC, one request per year
  counts.py '"design anthropology"' --db doaj             in DOAJ (open-access journals), one request per year
  counts.py '"design anthropology"' --db zenodo           in Zenodo (every resource type), one request per year

A share is a count per 100,000 works of the base, and it counts the same document types above and below the line
(--types, by default article, review and preprint). The current year is marked partial. The series is saved in
--out (default research/data) as NAME.csv, NAME.types.csv (every type, so other choices can be recomputed) and
NAME.meta.json: the query, the database, the date fetched, the types and this script. Each answer is written to
disk when it arrives; a run that stops says what it saved.

This script reports counts and shares. Whether a series is a trend is a judgement, and it is not made here.

  --record DIR   also save every answer in DIR        --replay DIR   answer only from DIR, never the network
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402

ALL = ("all",)
DEFAULT_TYPES = ("article", "preprint", "review")
TOPICS = "https://api.openalex.org/topics"
TOPICS_DOCUMENTED = 4516  # OpenAlex "Topics" page, read 2026-11-21


# --- Counting --------------------------------------------------------------------------------


class Counts:
    """Yearly counts of one set of works, with the document types that were counted."""

    def __init__(self, types, by_year: dict) -> None:
        self.types = tuple(sorted(types))
        self.by_year = {int(y): int(n) for y, n in by_year.items()}


def per_100k(count: int, base: int) -> float | None:
    """Works per 100,000 works of the base; None when the base is empty."""
    return 1e5 * count / base if base else None


def share(series: Counts, base: Counts) -> dict[int, float | None]:
    """Each year's count per 100,000 works of the base.

    Both sides must count the same document types. In OpenAlex the count of all works rose 29% from 2024 to 2025
    and the count of articles, reviews and preprints rose 18%: a share of articles over all works falls for that
    reason alone (research/notes/poiesis-lab-2026-recorded-runs in the plugin's repository).
    """
    if series.types != base.types:
        raise ValueError(f"a share needs the same document types on both sides: {', '.join(series.types)} above the line, {', '.join(base.types)} below")
    return {y: per_100k(series.by_year.get(y, 0), base.by_year[y]) for y in sorted(base.by_year)}


def select(table: dict[int, dict[str, int]], types: tuple[str, ...], years: range) -> Counts:
    """The counts of the chosen types from a table of year by type; ALL takes every type in the table."""
    if tuple(types) == ALL:
        return Counts(ALL, {y: sum(table.get(y, {}).values()) for y in years})
    return Counts(types, {y: sum(table.get(y, {}).get(t, 0) for t in types) for y in years})


def is_partial(year: int, fetched: str) -> bool:
    """A year that was not over on the day the counts were fetched."""
    return year >= int(fetched[:4])


# --- OpenAlex --------------------------------------------------------------------------------


def openalex_table(filters: list[str], y0: int, y1: int) -> dict[int, dict[str, int]]:
    """Works by year and by document type for a filter, in one request (two requests cost what one search costs)."""
    data = sc.openalex({"filter": ",".join([f"publication_year:{y0}-{y1}", *filters]), "group_by": "publication_year,type"})
    table: dict[int, dict[str, int]] = {}
    for group in data.get("group_by") or []:
        if "groups" not in group:  # never read an answer that is not split by type as "zero works of each type"
            raise sc.Refused("OpenAlex answered without the split by document type (group_by=publication_year,type).")
        if str(group.get("key", "")).isdigit():
            table[int(group["key"])] = {g["key_display_name"]: int(g["count"]) for g in group["groups"]}
    return table


def search_filter(query: str, base: str | None) -> str:
    """Title and abstract only, as the lab's recorded run did. OpenAlex stems words, inside double quotes too:
    quotes keep the words together as a phrase. Its documentation names one exception, a short quoted phrase that
    holds a stop word ("theory of mind"), which is matched as typed. An unstemmed search is a separate `.exact`
    form. See the note `openalex-2026-api-documentation` in the plugin's repository."""
    return "title_and_abstract.search:" + (f"({base}) AND ({query})" if base else query)


def counted(meta: dict) -> dict:
    """What a run counts, whatever the order of its arguments and however it was asked (--fresh, --json)."""
    return {k: meta.get(k) for k in ("database", "years", "share", "base", "series", "corpus")}


def free_name(folder: Path, name: str, meta: dict) -> str:
    """A default file name that does not overwrite another run's series: a run that counts the same things gets
    its own files again (one that stopped is run again, or asked again with --fresh), and a run that counts
    something else gets the name with -2, -3 and so on."""
    candidate, n = name, 1
    while (folder / f"{candidate}.meta.json").is_file():
        try:
            before = json.loads((folder / f"{candidate}.meta.json").read_text(encoding="utf-8"))
            same = counted(before) == counted(meta)
        except (OSError, ValueError, AttributeError):
            same = False
        if same:
            break
        n += 1
        candidate = f"{name}-{n}"
    return candidate


def topic_id(value: str) -> str:
    m = re.search(r"T\d+$", value.strip(), re.I)
    if not m:
        raise SystemExit(f"{value!r} is not an OpenAlex topic id (it looks like T10001).")
    return m.group(0).upper()


def topic_name(tid: str) -> str:
    """The topic's name, from its own record (one record by ID is free)."""
    q = urllib.parse.urlencode(sc.openalex_auth())
    return (sc.ask(sc.get, f"{TOPICS}/{tid}" + (f"?{q}" if q else "")) or {}).get("display_name") or tid


def taxonomy_pages(year: int, types: tuple[str, ...], paging: dict):
    """Every topic's count for one year, a page of 200 topics at a time. Yields (topics, base): `base` is the
    count of all works of those types that year, with or without a topic. Stops, and says why in `paging`, when
    the next page needs a key."""
    filters = [f"publication_year:{year}"] + ([] if tuple(types) == ALL else ["type:" + "|".join(types)])
    cursor = "*"
    while cursor:
        if cursor != "*" and paging.get("stopped"):
            return  # an earlier year already showed that paging needs a key: do not ask again
        try:
            data = sc.openalex({"filter": ",".join(filters), "group_by": "primary_topic.id", "per-page": 200, "cursor": cursor})
        except sc.NeedsKey as e:
            paging["stopped"] = str(e)
            return
        meta = data.get("meta") or {}
        yield [(g["key"].rsplit("/", 1)[-1], g.get("key_display_name") or "", int(g["count"])) for g in data.get("group_by") or []], int(meta.get("count") or 0)
        cursor = meta.get("next_cursor")


# --- Europe PMC ------------------------------------------------------------------------------


def epmc_query(q: str) -> str:
    """A Europe PMC query from plain words: each phrase or word is looked for in titles and abstracts. A query that
    already names a field (TITLE_ABS:, SRC:, …) is used as written."""
    if re.search(r"\b[A-Z_]{2,}:", q):
        return q
    parts = re.findall(r'"[^"]+"|[()]|[^\s()]+', q)
    return " ".join(p if p in ("(", ")") or p.upper() in ("AND", "OR", "NOT") else f"TITLE_ABS:{p}" for p in parts)


# The databases counted one request per year: how a query is written, how a year is named, and the count.
# OSF and CORE are not here: OSF's API filters titles only, and CORE's totals for a quoted phrase were not a phrase
# count when tried (research/notes/open-sources-2026-access, 2026-11-22).
YEARLY = {
    "epmc": ("Europe PMC", epmc_query, lambda y: f"PUB_YEAR:{y}", lambda q: sc.epmc_count(q)),
    "doaj": ("DOAJ", lambda q: q, lambda y: f"bibjson.year:{y}", lambda q: sc.doaj_count(q)),
    "zenodo": ("Zenodo", sc.and_join, lambda y: f"publication_date:[{y}-01-01 TO {y}-12-31]", lambda q: sc.zenodo_count(q)),
}
SEARCH_FIELD = {
    "epmc": ("title and abstract (TITLE_ABS), unless the query names its own fields. Words are matched as typed: on "
             "2026-11-21 a singular and its plural gave different counts, quoted and not."),
    "doaj": ("every field DOAJ searches by default, keywords too: on 2026-11-22 an article matched on its keywords alone. "
             "Words are joined with AND (DOAJ's default). The year is the article's bibjson.year."),
    "zenodo": ("every field Zenodo searches, keywords too, with words joined with AND (Zenodo's own default is OR). Every "
               "resource type is counted (papers, reports, datasets, software, presentations…), the latest version of each "
               "record. The year is the record's publication_date."),
}


def db_query(db: str, q: str) -> str:
    return YEARLY[db][1](q)


def db_series(db: str, query: str | None, base: str | None, years: range) -> dict[int, int]:
    _, write, year, count = YEARLY[db]
    terms = [f"({write(x)})" for x in (base, query) if x]
    return {y: count(" AND ".join([*terms, year(y)])) for y in years}


def epmc_series(query: str | None, base: str | None, years: range) -> dict[int, int]:
    return db_series("epmc", query, base, years)


# --- Files -----------------------------------------------------------------------------------


def slug(text: str) -> str:
    return "-".join(sc.fold(text).split()[:6]) or "series"


def number(x: float | None) -> str:
    return "" if x is None else f"{x:.4f}"


def script_identity(argv: list[str]) -> dict:
    """This script as it ran: name, version, a hash of the code that computed the numbers, and the command."""
    here = Path(__file__).resolve()
    digest = hashlib.sha256(here.read_bytes() + (here.parent / "scholarly.py").read_bytes()).hexdigest()
    command, skip = [], False
    for arg in argv:  # where files go does not change the numbers, so it is left out of the record
        if skip:
            skip = False
        elif arg in ("--out", "--record", "--replay"):
            skip = True
        elif not arg.startswith(("--out=", "--record=", "--replay=")):
            command.append(arg)
    return {"name": here.name, "plugin": "poiesis-research", "version": sc.VERSION, "sha256": digest, "command": ["counts.py", *command]}


class Files:
    """The series on disk. Rows are appended and flushed as each answer arrives; the metadata file is rewritten
    after each step and says `complete: false` until the run ends."""

    def __init__(self, folder: Path, name: str, header: list[str], meta: dict, types_file: bool) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        self.paths = {"csv": folder / f"{name}.csv", "meta": folder / f"{name}.meta.json"}
        if types_file:
            self.paths["types"] = folder / f"{name}.types.csv"
        self.meta = {**meta, "files": [p.name for k, p in self.paths.items() if k != "meta"], "complete": False}
        self.rows = 0
        self._open = {}
        for key, head in (("csv", header), ("types", ["series", "year", "type", "count"])):
            if key in self.paths:
                f = self.paths[key].open("w", newline="", encoding="utf-8")
                self._open[key] = (f, csv.writer(f, lineterminator="\n"))
                self._open[key][1].writerow(head)
        self.save()

    def add(self, rows: list[list], types_rows: list[list] | None = None) -> None:
        for key, some in (("csv", rows), ("types", types_rows or [])):
            if key in self._open and some:
                f, writer = self._open[key]
                writer.writerows(some)
                f.flush()
                os.fsync(f.fileno())
        self.rows += len(rows)
        self.save()

    def save(self, **more) -> None:
        self.meta.update(more)
        self.meta["rows"] = self.rows
        tmp = self.paths["meta"].with_name(f".{self.paths['meta'].name}.tmp")
        tmp.write_text(json.dumps(self.meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, self.paths["meta"])

    def close(self) -> None:
        for f, _ in self._open.values():
            f.close()


# --- Main ------------------------------------------------------------------------------------

HEADER = ["series", "label", "year", "partial", "count", "base", "share_per_100k", "count_all_types", "base_all_types", "share_all_types_per_100k"]
TAXONOMY_HEADER = ["topic_id", "topic", "year", "partial", "count", "base", "share_per_100k"]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query", nargs="*", help="one search per series; put phrases in double quotes")
    p.add_argument("--topic", action="append", default=[], help="an OpenAlex topic id, e.g. T10001")
    p.add_argument("--taxonomy", action="store_true", help="every OpenAlex topic, by year")
    p.add_argument("--base", help="count shares within the works that match this search (default: all works)")
    p.add_argument("--label", action="append", default=[], help="a name for each series, in order")
    p.add_argument("--from", dest="y0", type=int, help="first year (default: ten years before this one)")
    p.add_argument("--to", dest="y1", type=int, help="last year (default: this year, which is marked partial)")
    p.add_argument("--types", help='document types counted above and below the line, or "all" (default: article,preprint,review)')
    p.add_argument("--db", choices=["openalex", *YEARLY], default="openalex")
    p.add_argument("--out", type=Path, default=Path("research/data"))
    p.add_argument("--name", help="file name without extension (default: the first series and the date fetched)")
    p.add_argument("--record", type=Path, help="also save every answer in this folder")
    p.add_argument("--replay", type=Path, help="answer only from this folder, never the network")
    p.add_argument("--json", action="store_true", help="print the series as JSON")
    sc.add_request_args(p)
    a = p.parse_args(argv)
    sc.apply_request_args(a)
    if a.record and a.replay:
        p.error("--record and --replay are two different runs")
    if a.record or a.replay:
        sc.configure(record=a.record, replay=a.replay)

    modes = bool(a.query) + bool(a.topic) + a.taxonomy
    if modes != 1:
        p.error("give searches, or --topic, or --taxonomy (one of the three)")
    if a.taxonomy and a.base:
        p.error("--base does not combine with --taxonomy: the taxonomy is counted in all works of the chosen types")
    chosen = a.types or ",".join(DEFAULT_TYPES)
    types = ALL if chosen.strip().lower() == "all" else tuple(sorted(t.strip() for t in chosen.split(",") if t.strip()))
    if a.db != "openalex":
        if a.topic or a.taxonomy:
            p.error("topics are OpenAlex's: --topic and --taxonomy need --db openalex")
        if a.types and types != ALL:
            p.error(f"--types names OpenAlex's document types; with --db {a.db}, restrict the query itself (and --base the same way)")
        types = ALL
    this_year = int((sc._now())[:4])
    y1 = a.y1 or this_year
    y0 = a.y0 or (y1 - 10)
    if y0 > y1:
        p.error("--from is after --to")
    years = range(y0, y1 + 1)
    database = "OpenAlex" if a.db == "openalex" else YEARLY[a.db][0]
    meta = {
        "script": script_identity(argv), "database": database, "years": [y0, y1],
        "share": {"per": 100000, "numerator_types": list(types), "denominator_types": list(types)},
    }
    if a.db == "openalex":
        meta["corpus"] = "core (OpenAlex's default; the expansion corpus is not counted)"
        meta["key"] = bool(sc.api_key("OPENALEX_API_KEY"))
    else:
        meta["share"]["note"] = f"every record type {database} holds, on both sides"

    box: dict = {}  # the files, as soon as they exist: a run that stops must be able to say what it saved
    try:
        out = run_taxonomy(a, years, types, meta, box) if a.taxonomy else run_series(a, years, types, meta, box)
    except sc.REFUSALS as e:
        files = box.get("files")
        saved = f"{files.rows} rows are saved in {files.paths['csv']}, marked incomplete" if files else "nothing was saved"
        if files:
            files.save(stopped=str(e), coverage=sc.coverage_line())
            files.close()
        print(f"Stopped: {e}\n{saved}. Run the same command again: answers already fetched are not asked for twice.", file=sys.stderr)
        return 2
    files = box["files"]
    files.save(complete=not files.meta.get("stopped"), coverage=sc.coverage_line())
    files.close()
    report(a, files, out, types, database)
    if box.get("renamed_from"):  # with --json it is said beside the JSON, not inside it
        print(f"Another run's files already have the name {box['renamed_from']}, so this series is kept under a new name. --name sets one.",
              file=sys.stderr if a.json else sys.stdout)
    return 0 if files.meta["complete"] else 2  # 2: saved, and marked incomplete


def run_series(a, years: range, types: tuple[str, ...], meta: dict, box: dict) -> list[dict]:
    y0, y1 = years[0], years[-1]
    if a.db == "openalex":
        base_filters = [search_filter(a.base, None)] if a.base else []
        base_table = openalex_table(base_filters, y0, y1)
        base, base_all = select(base_table, types, years), select(base_table, ALL, years)
        meta["base"] = {"what": f"works of those types matching: {a.base}" if a.base else "all works of those types", "filter": ",".join([f"publication_year:{y0}-{y1}", *base_filters])}
        meta["search_field"] = ("title and abstract (title_and_abstract.search). OpenAlex stems words, inside double quotes too: on "
                                "2026-11-21 \"heat pump\" and \"heat pumps\" gave the same counts. Its documentation names one exception, "
                                "seen the same day: a short quoted phrase that holds a stop word (\"theory of mind\") is matched as typed.")
    else:
        base_table = None
        base = base_all = Counts(ALL, db_series(a.db, None, a.base, years))
        meta["base"] = {"what": f"records matching: {a.base}" if a.base else "all records",
                        "query": db_query(a.db, a.base) if a.base else ("PUB_YEAR only" if a.db == "epmc" else YEARLY[a.db][2]("<year>") + " only")}
        meta["search_field"] = SEARCH_FIELD[a.db]
    fetched = sc.last_fetched() or sc._now()
    meta["fetched"] = fetched[:10]
    meta["partial_years"] = [y for y in years if is_partial(y, fetched)]

    wanted = [("topic", topic_id(t)) for t in a.topic] if a.topic else [("search", q) for q in a.query]
    labels = list(a.label) + [None] * len(wanted)
    series_meta, ids = [], []
    for (kind, value), label in zip(wanted, labels):
        if kind == "topic":
            name = label or (topic_name(value) if a.db == "openalex" else value)
            # Within a base, the topic's works are counted within that base too: the two sides of a share must
            # be the same set of works, apart from the series itself.
            within = f",{search_filter(a.base, None)}" if a.base else ""
            series_meta.append({"id": value, "label": name, "topic": value, "filter": f"primary_topic.id:{value}{within}"})
        else:
            name = label or value
            where = {"filter": search_filter(value, a.base)} if a.db == "openalex" else {"query": " AND ".join(f"({db_query(a.db, x)})" for x in (a.base, value) if x)}
            series_meta.append({"id": slug(name), "label": name, "search": value, **where})
        ids.append(series_meta[-1]["id"])
    if len(set(ids)) != len(ids):
        raise SystemExit("two series would get the same name: give each one a --label")
    meta["series"] = series_meta

    default = f"{ids[0]}-{meta['fetched']}"
    name = a.name or free_name(a.out, default, meta)
    if name != default and not a.name:
        box["renamed_from"] = default
    files = box["files"] = Files(a.out, name, HEADER, meta, types_file=base_table is not None)
    if base_table is not None:
        files.add([], [["_base", y, t, n] for y in years for t, n in sorted(base_table.get(y, {}).items())])

    out = []
    for s in series_meta:
        if a.db == "openalex":
            table = openalex_table([s["filter"]], y0, y1)
            counts, counts_all = select(table, types, years), select(table, ALL, years)
            types_rows = [[s["id"], y, t, n] for y in years for t, n in sorted(table.get(y, {}).items())]
        else:
            counts = counts_all = Counts(ALL, db_series(a.db, s["search"], a.base, years))
            types_rows = None
        shares, shares_all = share(counts, base), share(counts_all, base_all)
        rows = [[s["id"], s["label"], y, "true" if is_partial(y, fetched) else "false", counts.by_year[y], base.by_year[y], number(shares[y]),
                 counts_all.by_year[y], base_all.by_year[y], number(shares_all[y])] for y in years]
        files.add(rows, types_rows)
        out.append({"id": s["id"], "label": s["label"], "rows": [dict(zip(HEADER[2:], r[2:])) for r in rows]})
    return out


def run_taxonomy(a, years: range, types: tuple[str, ...], meta: dict, box: dict) -> list[dict]:
    paging: dict = {}
    files: Files | None = None
    topics: set[str] = set()
    for year in years:
        for page, base in taxonomy_pages(year, types, paging):
            fetched = sc.last_fetched() or sc._now()
            if files is None:
                meta.update(fetched=fetched[:10], partial_years=[y for y in years if is_partial(y, fetched)],
                            base={"what": "all works of those types that year, with or without a topic"},
                            series=[{"id": "taxonomy", "label": "every OpenAlex topic (a work counts under its primary topic)", "filter": "group_by=primary_topic.id"}])
                default = f"taxonomy-{years[0]}-{years[-1]}-{meta['fetched']}"
                name = a.name or free_name(a.out, default, meta)
                if name != default and not a.name:
                    box["renamed_from"] = default
                files = box["files"] = Files(a.out, name, TAXONOMY_HEADER, meta, types_file=False)
            partial = "true" if is_partial(year, fetched) else "false"
            topics.update(tid for tid, _, _ in page)
            files.meta["topics"] = {"fetched": len(topics), "documented": TOPICS_DOCUMENTED}
            files.add([[tid, name, year, partial, n, base, number(per_100k(n, base))] for tid, name, n in page])
    if files is None:
        raise sc.Refused(paging.get("stopped") or "OpenAlex returned no topics for these years.")
    if paging.get("stopped"):
        files.save(stopped=paging["stopped"])
    return [{"id": "taxonomy", "topics": len(topics)}]


def report(a, files: Files, out: list[dict], types: tuple[str, ...], database: str) -> None:
    meta = files.meta
    if a.json:
        json.dump({"meta": meta, "series": out}, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return
    counted = "every document type" if types == ALL else ", ".join(types)
    print(f"{database}, fetched {meta['fetched']}. Counted above and below the line: {counted}. Shares are per 100,000 of the base: {meta['base']['what']}.")
    if a.taxonomy:
        t = meta["topics"]
        print(f"Topics: {t['fetched']} of {t['documented']} documented, for {meta['years'][0]}–{meta['years'][1]}: {files.rows} rows.")
        if meta.get("stopped"):
            print(f"Incomplete: {meta['stopped']} The topics saved are the first {t['fetched']} by id, not the largest.")
    else:
        full = [y for y in range(meta["years"][0], meta["years"][1] + 1) if y not in meta["partial_years"]]
        for s in out:
            rows = {r["year"]: r for r in s["rows"]}
            shown = [f"{y}: {rows[y]['count']:,} ({float(rows[y]['share_per_100k'] or 0):.2f})" for y in ([full[0], full[-1]] if len(full) > 1 else full)]
            partial = [f"{y}: {rows[y]['count']:,} so far" for y in meta["partial_years"]]
            print(f"- {s['label']} · " + " · ".join(shown + partial))
    if meta["partial_years"]:
        print(f"Partial: {', '.join(map(str, meta['partial_years']))} (not over when fetched).")
    print("Saved: " + ", ".join(str(p) for p in files.paths.values()))


if __name__ == "__main__":
    sys.exit(sc.finish(main))
