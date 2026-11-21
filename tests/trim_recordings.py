#!/usr/bin/env python3
"""Trim recorded answers before they are kept in this repository. Run with `python3 -I tests/trim_recordings.py`.

A recording made with --record holds everything a database sent. What is kept here is only what the scripts read:
no author or investigator names, no user names, no abstracts, and not the notice OpenAlex adds for clients without
a key (it addresses AI agents). Counts, titles, dates, identifiers and links stay as they were returned. Running
it twice changes nothing.
"""
import json
import re
import sys
from pathlib import Path

RECORDINGS = Path(__file__).resolve().parent / "recordings"


def keep(d: dict, names: tuple) -> dict:
    return {k: d[k] for k in names if k in d}


def trim(host: str, url: str, body):
    if host == "api.openalex.org" and isinstance(body, dict) and isinstance(body.get("meta"), dict):
        body["meta"].pop("notice", None)
        body["meta"].pop("x_query", None)
    elif host == "hn.algolia.com" and isinstance(body, dict):
        body = {"nbHits": body.get("nbHits"), "hits": [keep(h, ("title", "url", "points", "num_comments", "created_at", "objectID")) for h in body.get("hits") or []]}
    elif host == "api.reporter.nih.gov" and isinstance(body, dict):
        rows = []
        for r in body.get("results") or []:
            row = keep(r, ("project_title", "project_start_date", "project_detail_url", "project_num", "award_amount", "fiscal_year"))
            if isinstance(r.get("organization"), dict):
                row["organization"] = keep(r["organization"], ("org_name",))
            if isinstance(r.get("agency_ic_admin"), dict):
                row["agency_ic_admin"] = keep(r["agency_ic_admin"], ("abbreviation",))
            rows.append(row)
        body = {"meta": keep(body.get("meta") or {}, ("total", "offset", "limit")), "results": rows}
    elif host == "api.openaire.eu" and isinstance(body, dict):
        rows = []
        for r in body.get("results") or []:
            row = keep(r, ("id", "mainTitle", "publicationDate", "publisher", "pids", "title", "startDate", "code", "granted"))
            if r.get("fundings"):
                row["fundings"] = [keep(f, ("shortName", "name")) for f in r["fundings"]]
            rows.append(row)
        body = {"header": keep(body.get("header") or {}, ("numFound", "page", "pageSize")), "results": rows}
    elif host == "www.ebi.ac.uk" and isinstance(body, dict) and "resultList" in body:
        fields = ("id", "source", "title", "doi", "pubYear", "firstPublicationDate", "journalTitle", "bookOrReportDetails")
        body = {"hitCount": body.get("hitCount"), "resultList": {"result": [keep(r, fields) for r in (body["resultList"] or {}).get("result") or [] if "title" in r]}}
    elif host == "huggingface.co" and isinstance(body, list):
        body = [keep(m, ("id", "createdAt", "downloads", "likes")) for m in body]
    return body


def main() -> int:
    changed = 0
    for path in sorted(RECORDINGS.rglob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        host = path.name.rsplit("-", 1)[0]
        text = entry.get("body") or ""
        if host == "export.arxiv.org":  # an Atom feed: abstracts and author names go, the rest stays
            new = re.sub(r"<summary>.*?</summary>", "<summary>Shortened for the test recording.</summary>", text, flags=re.S)
            new = re.sub(r"\s*<author>.*?</author>", "", new, flags=re.S)
        else:
            try:
                new = json.dumps(trim(host, entry.get("url", ""), json.loads(text)), ensure_ascii=False) if text else text
            except ValueError:
                new = text
        if new != text:
            entry["body"] = new
            path.write_text(json.dumps(entry, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            changed += 1
    print(f"{changed} recordings trimmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
