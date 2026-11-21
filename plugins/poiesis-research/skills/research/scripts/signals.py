#!/usr/bin/env python3
"""What seven open sources show about a subject in a recent window, as observations. Run with `python3 -I`.

  signals.py '"brain-computer interface"' [--months 6] [--to 2026-11-21] [--limit 3]
             [--wikipedia "Brain–computer interface"] [--hf EEG] [--sources arxiv,epmc,nih,openaire,hn,hf]
             [--out research/signals] [--json] [--record DIR | --replay DIR] [--fresh]
  signals.py --next-id research/signals        the next free signal id (SG-001, SG-002, …)

Sources, each asked once or a few times: arXiv (preprints submitted in the window), Europe PMC (records and
preprints first published in it), NIH RePORTER (funded projects by fiscal year), OpenAIRE (publications dated in
the window, and funded projects), Hacker News (stories, with points and comments), Wikimedia (monthly views of
one Wikipedia article: name it with --wikipedia), Hugging Face (models and datasets whose name holds a word: give
it with --hf when the subject's phrase is not a name anyone would use).

For each source: how many items, and the newest or most visible few, with their dates, numbers and links. That is
what was there on the day. Whether it matters, where it leads and how strong it is are not said here. The last
line, "Coverage", names the sources that answered and the ones that refused. With --out the scan is saved as
JSON, so signal notes can point to the numbers they rest on.
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402

ALL = ["arxiv", "epmc", "nih", "openaire", "hn", "wikimedia", "hf"]
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}totalResults"
NIH = "https://api.reporter.nih.gov/v2/projects/search"
OPENAIRE = "https://api.openaire.eu/graph"
HN = "https://hn.algolia.com/api/v1"
PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
HF = "https://huggingface.co/api"


def months_before(day: dt.date, months: int) -> dt.date:
    year, month = divmod(day.year * 12 + day.month - 1 - months, 12)
    month += 1
    last = (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)).day
    return dt.date(year, month, min(day.day, last))


def phrase(term: str) -> str:
    """The term as one phrase for sources that take a quoted phrase."""
    return term if term.startswith('"') else f'"{term}"' if " " in term else term


def bare(term: str) -> str:
    return term.strip('"')


# --- One function per source: each returns {"source", "kind", "what", "counts", "items", "limits"} ----------


def arxiv(term: str, start: dt.date, end: dt.date, limit: int) -> dict:
    def ask(query: str, n: int) -> tuple[int, list[dict]]:
        feed = sc.get_text(f"{sc.ARXIV}?" + urllib.parse.urlencode({"search_query": query, "start": 0, "max_results": n, "sortBy": "submittedDate", "sortOrder": "descending"}), check=sc._is_feed)
        root = ET.fromstring(feed) if feed else None
        total = int(root.findtext(OPENSEARCH) or 0) if root is not None else 0
        works = [w for w in (sc.norm_arxiv(e) for e in root.findall("a:entry", sc.ATOM)) if w["arxiv"] and w["title"]] if root is not None else []
        dates = [" ".join((e.findtext("a:published", default="", namespaces=sc.ATOM)).split())[:10] for e in root.findall("a:entry", sc.ATOM)] if root is not None else []
        return total, [{"date": d, "title": w["title"], "link": w["landing"], "id": f"arXiv:{w['arxiv']}"} for w, d in zip(works, dates)]

    base = sc.arxiv_query(phrase(term))
    window = f"submittedDate:[{start:%Y%m%d}0000 TO {end:%Y%m%d}2359]"
    in_window, items = ask(f"{base} AND {window}", limit)
    ever, _ = ask(base, 1)
    return {"source": "arXiv", "kind": "preprint server", "what": f"preprints with the words anywhere in the record, submitted {start} to {end}",
            "counts": {"in the window": in_window, "all dates": ever}, "items": items,
            "limits": "physics, mathematics, computer science and nearby fields; it gives no citations or views"}


def epmc(term: str, start: dt.date, end: dt.date, limit: int) -> dict:
    words = f"TITLE_ABS:{phrase(term)}" if not re.search(r"\b[A-Z_]{2,}:", term) else term
    window = f"FIRST_PDATE:[{start} TO {end}]"
    data = sc.epmc("/search", {"query": f"{words} AND SRC:PPR AND {window}", "resultType": "lite", "pageSize": max(1, limit), "sort": "P_PDATE_D desc"})
    items = [{"date": r.get("firstPublicationDate") or str(r.get("pubYear") or ""), "title": sc.strip_tags(r.get("title") or "").rstrip("."),
              "link": f"https://doi.org/{r['doi']}" if r.get("doi") else None, "id": f"{r.get('source')}/{r.get('id')}",
              "where": (r.get("bookOrReportDetails") or {}).get("publisher") or r.get("journalTitle") or ""} for r in (data.get("resultList") or {}).get("result") or []]
    counts = {"preprints in the window": int(data.get("hitCount") or 0), "all records in the window": sc.epmc_count(f"{words} AND {window}"),
              "preprints, all dates": sc.epmc_count(f"{words} AND SRC:PPR"), "all records, all dates": sc.epmc_count(words)}
    return {"source": "Europe PMC", "kind": "journal and preprint index", "what": f"records with the words in the title or abstract, first published {start} to {end}",
            "counts": counts, "items": items, "limits": "life sciences first; the items listed are preprints, newest first"}


def nih(term: str, start: dt.date, end: dt.date, limit: int) -> dict:
    def ask(years: list[int], n: int, fields: list[str] | None = None) -> dict:
        body = {"criteria": {"advanced_text_search": {"operator": "and", "search_field": "projecttitle,terms,abstracttext", "search_text": phrase(term)}, "fiscal_years": years},
                "offset": 0, "limit": n, "sort_field": "project_start_date", "sort_order": "desc"}
        if fields:
            body["include_fields"] = fields
        return sc.post(NIH, body)

    years = [end.year - 2, end.year - 1, end.year]
    data = ask(years[1:], max(1, limit))
    items = [{"date": (r.get("project_start_date") or "")[:10], "title": r.get("project_title") or "", "link": r.get("project_detail_url"), "id": r.get("project_num"),
              "where": " · ".join(x for x in ((r.get("organization") or {}).get("org_name"), (r.get("agency_ic_admin") or {}).get("abbreviation")) if x),
              "visible": f"award ${r['award_amount']:,} in fiscal year {r.get('fiscal_year')}" if isinstance(r.get("award_amount"), (int, float)) else ""}
             for r in data.get("results") or []]
    counts = {f"fiscal years {years[1]}–{years[2]}": int((data.get("meta") or {}).get("total") or 0)}
    for year in years:
        counts[f"fiscal year {year}"] = int((ask([year], 1, ["ProjectNum"]).get("meta") or {}).get("total") or 0)
    return {"source": "NIH RePORTER", "kind": "funder", "what": "projects funded by the US National Institutes of Health with the words in the title, terms or abstract",
            "counts": counts, "items": items, "limits": "one funder, one country, biomedical; a project counts once in each fiscal year it is funded"}


def openaire(term: str, start: dt.date, end: dt.date, limit: int) -> dict:
    def ask(path: str, params: dict) -> dict:
        return sc.get(f"{OPENAIRE}{path}?" + urllib.parse.urlencode({**params, "search": phrase(term), "pageSize": max(1, limit)}, quote_via=urllib.parse.quote), tries=2)

    products = ask("/v2/researchProducts", {"type": "publication", "fromPublicationDate": str(start), "toPublicationDate": str(end), "sortBy": "publicationDate DESC"})
    projects = ask("/v1/projects", {"sortBy": "startDate DESC"})
    items = []
    for r in projects.get("results") or []:
        funders = ", ".join(f.get("shortName") or f.get("name") or "" for f in r.get("fundings") or [])
        granted = r.get("granted") or {}
        amount = f"{granted.get('currency') or ''} {granted['fundedAmount']:,.0f}".strip() if granted.get("fundedAmount") else ""
        items.append({"date": r.get("startDate") or "", "title": r.get("title") or "", "link": None, "id": f"project {r.get('code') or r.get('id')}", "where": funders,
                      "visible": f"funded {amount}" if amount else ""})
    for r in products.get("results") or []:
        doi = next((p.get("value") for p in r.get("pids") or [] if p.get("scheme") == "doi"), None)
        items.append({"date": r.get("publicationDate") or "", "title": r.get("mainTitle") or "", "link": f"https://doi.org/{doi}" if doi else None, "id": r.get("id"), "where": r.get("publisher") or ""})
    return {"source": "OpenAIRE", "kind": "funder and publication index", "what": f"funded projects (all dates) and publications dated {start} to {end}, with the words in the record",
            "counts": {"publications in the window": int((products.get("header") or {}).get("numFound") or 0), "projects, all dates": int((projects.get("header") or {}).get("numFound") or 0)},
            "items": items, "limits": "projects from the funders OpenAIRE collects (the EU, national funders, NSF and others); 60 requests an hour without a token"}


def hn(term: str, start: dt.date, end: dt.date, limit: int) -> dict:
    def stamp(day: dt.date, last: bool = False) -> int:
        return int(dt.datetime.combine(day, dt.time.max if last else dt.time.min, tzinfo=dt.timezone.utc).timestamp())

    def ask(path: str, params: dict) -> dict:
        return sc.get(f"{HN}/{path}?" + urllib.parse.urlencode({"query": phrase(term), "tags": "story", "hitsPerPage": max(1, limit), **params}))

    def item(h: dict) -> dict:
        return {"date": (h.get("created_at") or "")[:10], "title": h.get("title") or "", "link": f"https://news.ycombinator.com/item?id={h.get('objectID')}", "id": f"HN {h.get('objectID')}",
                "where": h.get("url") or "", "visible": f"{h.get('points') or 0} points, {h.get('num_comments') or 0} comments"}

    recent = ask("search_by_date", {"numericFilters": f"created_at_i>{stamp(start)},created_at_i<{stamp(end, True)}"})
    ever = ask("search", {})
    items = [item(h) for h in recent.get("hits") or []] + [{**item(h), "note": "most visible of all dates"} for h in (ever.get("hits") or [])[:1]]
    return {"source": "Hacker News", "kind": "news and discussion", "what": f"stories with the words, posted {start} to {end} (newest first), and the most visible story of all dates",
            "counts": {"stories in the window": int(recent.get("nbHits") or 0), "stories, all dates": int(ever.get("nbHits") or 0)}, "items": items,
            "limits": "one English-language technology forum; points and comments are as of the day asked"}


def wikimedia(article: str, lang: str, end: dt.date) -> dict:
    last_full = end.replace(day=1) - dt.timedelta(days=1)
    first = months_before(last_full.replace(day=1), 23)
    title = urllib.parse.quote(article.replace(" ", "_"), safe="")
    data = sc.get(f"{PAGEVIEWS}/{lang}.wikipedia/all-access/user/{title}/monthly/{first:%Y%m%d}00/{last_full:%Y%m%d}00")
    views = {i["timestamp"][:4] + "-" + i["timestamp"][4:6]: int(i["views"]) for i in data.get("items") or []}
    if not views:
        return {"source": "Wikimedia pageviews", "kind": "encyclopedia traffic", "what": f'monthly views of the {lang}.wikipedia article "{article}"', "counts": {}, "items": [],
                "limits": f'no article with exactly this title: "{article}". Titles are case-sensitive and use the article\'s own punctuation.'}
    months = sorted(views)
    latest, year_before = months[-1], f"{int(months[-1][:4]) - 1}{months[-1][4:]}"
    counts = {f"views in {latest}": views[latest]}
    if year_before in views:
        counts[f"views in {year_before}"] = views[year_before]
    top = max(months, key=lambda m: views[m])
    counts[f"most in one month ({top})"] = views[top]
    counts["months read"] = len(months)
    return {"source": "Wikimedia pageviews", "kind": "encyclopedia traffic", "what": f'monthly views by people (not bots) of the {lang}.wikipedia article "{article}"',
            "counts": counts, "items": [{"date": m, "title": f"{views[m]:,} views", "link": None, "id": ""} for m in months[-min(len(months), 6):]],
            "limits": "one article in one language; a spike can be one news event", "monthly_views": views}


def hf(name: str, start: dt.date, end: dt.date, limit: int) -> dict:
    def ask(kind: str, sort: str, n: int) -> list[dict]:
        got = sc.get(f"{HF}/{kind}?" + urllib.parse.urlencode({"search": name, "sort": sort, "direction": -1, "limit": n}))
        return got if isinstance(got, list) else []

    def item(kind: str, m: dict) -> dict:
        return {"date": (m.get("createdAt") or "")[:10], "title": m.get("id") or "", "link": f"https://huggingface.co/{'datasets/' if kind == 'datasets' else ''}{m.get('id')}", "id": m.get("id"),
                "where": kind[:-1], "visible": f"{m.get('downloads') or 0:,} downloads, {m.get('likes') or 0} likes"}

    counts, items = {}, []
    for kind in ("models", "datasets"):
        newest = ask(kind, "createdAt", 100)
        created = [m for m in newest if str(start) <= (m.get("createdAt") or "")[:10] <= str(end)]
        full = len(newest) == 100 and len(created) == len(newest)
        counts[f"{kind} created in the window"] = f"{len(created)} or more" if full else len(created)
        counts[f"{kind} with the word in their name"] = f"{len(newest)} or more" if len(newest) == 100 else len(newest)
        items += [item(kind, m) for m in ask(kind, "downloads", max(1, limit))]
    return {"source": "Hugging Face", "kind": "code and model hub", "what": f'models and datasets whose name holds "{name}": how many, how many were created {start} to {end}, and the most downloaded',
            "counts": counts, "items": items, "limits": "the search reads names, not descriptions; counts stop at 100; downloads and likes are as the Hub reports them on the day asked"}


# --- Running and showing ---------------------------------------------------------------------


def next_id(folder: Path) -> str:
    """The next free signal id in a project: one more than the highest SG number in its signal notes."""
    numbers = [int(n) for f in (folder.rglob("*.md") if folder.is_dir() else []) for n in re.findall(r"\*\*Id:\*\*\s*SG-(\d+)", f.read_text(encoding="utf-8", errors="replace"))]
    return f"SG-{max(numbers, default=0) + 1:03d}"


def show(block: dict) -> None:
    counts = " · ".join(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}" for k, v in block["counts"].items())
    print(f"{block['source']} ({block['kind']}) · {block['what']}")
    print(f"  {counts or 'nothing found'}")
    for i in block["items"]:
        extra = " · ".join(x for x in (i.get("where"), i.get("visible"), i.get("note"), i.get("link") or i.get("id")) if x)
        print(f"  - {i['date']} · {i['title']}" + (f" · {extra}" if extra else ""))
    print(f"  Limits: {block['limits']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("term", nargs="?", help="the subject, as the phrase its field uses; quote a phrase")
    p.add_argument("--months", type=int, default=6, help="the window: this many months back from --to (default 6)")
    p.add_argument("--to", type=dt.date.fromisoformat, help="the window's last day, YYYY-MM-DD (default today)")
    p.add_argument("--limit", type=int, default=3, help="items shown per source (default 3)")
    p.add_argument("--wikipedia", help="the exact title of a Wikipedia article whose views to read")
    p.add_argument("--wiki-lang", default="en", help="the Wikipedia's language code (default en)")
    p.add_argument("--hf", help="a word to look for in Hugging Face names (default: the term)")
    p.add_argument("--sources", default=",".join(ALL), help=f"which sources to ask (default: {','.join(ALL)})")
    p.add_argument("--out", type=Path, help="save the scan as JSON in this folder (research/signals)")
    p.add_argument("--next-id", type=Path, metavar="FOLDER", help="print the next free signal id in this folder and stop")
    p.add_argument("--record", type=Path, help="also save every answer in this folder")
    p.add_argument("--replay", type=Path, help="answer only from this folder, never the network")
    p.add_argument("--json", action="store_true")
    sc.add_request_args(p)
    a = p.parse_args()
    if a.next_id:
        print(next_id(a.next_id))
        return 0
    if not a.term:
        p.error("give the subject to look for")
    sc.apply_request_args(a)
    if a.record and a.replay:
        p.error("--record and --replay are two different runs")
    if a.record or a.replay:
        sc.configure(record=a.record, replay=a.replay)
    wanted = [s.strip() for s in a.sources.split(",") if s.strip()]
    if unknown := [s for s in wanted if s not in ALL]:
        p.error(f"unknown source: {', '.join(unknown)} (choose from {', '.join(ALL)})")
    end = a.to or dt.date.today()
    start = months_before(end, a.months)
    term = a.term.strip()

    jobs = {
        "arxiv": lambda: arxiv(term, start, end, a.limit), "epmc": lambda: epmc(term, start, end, a.limit), "nih": lambda: nih(term, start, end, a.limit),
        "openaire": lambda: openaire(term, start, end, a.limit), "hn": lambda: hn(term, start, end, a.limit),
        "wikimedia": lambda: wikimedia(a.wikipedia, a.wiki_lang, end) if a.wikipedia else None, "hf": lambda: hf(a.hf or bare(term), start, end, a.limit),
    }
    names = {"arxiv": "arXiv", "epmc": "Europe PMC", "nih": "NIH RePORTER", "openaire": "OpenAIRE", "hn": "Hacker News", "wikimedia": "Wikimedia pageviews", "hf": "Hugging Face"}
    blocks, refused, skipped = [], [], []
    for source in wanted:
        try:
            block = jobs[source]()
        except sc.REFUSALS as e:
            refused.append({"source": names[source], "why": str(e)})
            continue
        if block is None:
            skipped.append("Wikimedia pageviews (no article named: add --wikipedia \"<title>\")")
        else:
            blocks.append(block)

    scan = {"term": term, "window": [str(start), str(end)], "asked": (sc.last_fetched() or sc._now())[:10], "sources": blocks, "refused": refused, "not_asked": skipped,
            "script": {"name": "signals.py", "plugin": "poiesis-research", "version": sc.VERSION}, "coverage": sc.coverage_line()}
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        path = a.out / f"{scan['asked']}-{'-'.join(sc.fold(term).split()[:6]) or 'scan'}.scan.json"
        path.write_text(json.dumps(scan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        scan["saved"] = str(path)
    if a.json:
        json.dump(scan, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    print(f"{term} · window {start} to {end} · asked {scan['asked']}\n")
    for block in blocks:
        show(block)
        print()
    for r in refused:
        print(f"{r['source']}: refused. {r['why']}")
    for s in skipped:
        print(f"Not asked: {s}")
    kinds = sorted({b["kind"] for b in blocks})
    print(f"{len(blocks)} of {len(wanted)} sources answered, of {len(kinds)} kinds: {', '.join(kinds) or 'none'}.")
    if a.out:
        print(f"Saved: {scan['saved']}")
    return 0


if __name__ == "__main__":
    sys.exit(sc.finish(main))
