#!/usr/bin/env python3
"""Search open and upcoming EU funding calls on the EU Funding & Tenders Portal. Run with `python3 -I`.

  funding.py "query" [--status open|forthcoming|both] [--programme HORIZON] [--cascade] [--limit 20] [--json]

Covers the programmes the Commission manages on the portal (Horizon Europe, Digital Europe, Creative Europe,
Erasmus+, LIFE, CERV, EU4Health, Single Market, …). With --cascade it also lists calls that EU-funded projects
open to third parties (often smaller grants for SMEs and startups). National and regional programmes, including
Romania's, are not on this portal: search their official sites.

Each call: identifier, title, programme, status, next deadline, grant size per project, action type, link.
The portal is the source of truth: check the call page before relying on a date or amount.
"""
import argparse
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
import uuid

API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
STATUS = {"open": "31094501", "forthcoming": "31094502"}
STATUS_NAME = {v: k for k, v in STATUS.items()} | {"31094503": "closed"}
PROGRAMMES = {
    "HORIZON": "Horizon Europe", "DIGITAL": "Digital Europe", "CREA": "Creative Europe", "ERASMUS": "Erasmus+",
    "LIFE": "LIFE", "CERV": "Citizens, Equality, Rights and Values", "EU4H": "EU4Health", "SMP": "Single Market",
    "CEF": "Connecting Europe Facility", "EDF": "European Defence Fund", "EMFAF": "Maritime, Fisheries and Aquaculture",
    "I3": "Interregional Innovation Investments", "AMIF": "Asylum, Migration and Integration", "ISF": "Internal Security",
    "RFCS": "Research Fund for Coal and Steel", "EUAF": "Union Anti-Fraud", "JUST": "Justice", "SOCPL": "Social Prerogative",
    "PPPA": "Pilot projects and preparatory actions", "EUBA": "Border management", "UCPM": "Civil Protection",
    "ESF": "European Social Fund+", "INNOVFUND": "Innovation Fund", "EIC": "European Innovation Council",
}


def post(query: str, must: list, page_size: int) -> dict:
    """The portal's search API takes multipart form fields; results come by relevance to the text."""
    boundary = uuid.uuid4().hex
    fields = {
        "query": json.dumps({"bool": {"must": must}}),
        "languages": json.dumps(["en"]),
    }
    body = "".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\nContent-Type: application/json\r\n\r\n{v}\r\n'
        for k, v in fields.items()
    ) + f"--{boundary}--\r\n"
    params = {"apiKey": "SEDIA", "text": query or "***", "pageSize": page_size, "pageNumber": 1}
    req = urllib.request.Request(
        f"{API}?{urllib.parse.urlencode(params)}",
        data=body.encode(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "poiesis-research/2"},
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.load(res)


def first(m: dict, k: str) -> str:
    v = m.get(k) or [""]
    return v[0] if isinstance(v, list) else v


def programme(identifier: str) -> str:
    prefix = identifier.split("-")[0].upper()
    return PROGRAMMES.get(prefix, prefix)


def next_deadline(m: dict) -> str | None:
    """The next deadline still ahead; None when every deadline has passed (the index keeps stale statuses)."""
    today = dt.date.today().isoformat()
    dates = sorted(d[:10] for d in m.get("deadlineDate") or [])
    if not dates:
        return "-"
    upcoming = [d for d in dates if d >= today]
    return upcoming[0] if upcoming else None


def grant_size(m: dict) -> str:
    """Grant per project for this topic, from the call's budget table (which lists every topic of the call)."""
    raw = first(m, "budgetOverview")
    ident = first(m, "identifier")
    lo, hi, n = [], [], 0
    if raw:
        try:
            rows = [a for actions in json.loads(raw).get("budgetTopicActionMap", {}).values() for a in actions]
            own = [a for a in rows if str(a.get("action", "")).startswith(ident + " ")]
            for a in own or rows:
                if a.get("minContribution"):
                    lo.append(a["minContribution"])
                if a.get("maxContribution"):
                    hi.append(a["maxContribution"])
                n += a.get("expectedGrants") or 0
        except (ValueError, AttributeError):
            pass
    if lo or hi:
        low, high = min(lo or hi), max(hi or lo)
        span = f"€{low:,.0f} per project" if low == high else f"€{low:,.0f}–{high:,.0f} per project"
        return span + (f", ~{n} grants" if n else "")
    budget = first(m, "budget")
    return f"€{float(budget):,.0f} total" if budget else "-"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--status", choices=["open", "forthcoming", "both"], default="both")
    p.add_argument("--programme", help="identifier prefix, e.g. HORIZON, DIGITAL, CREA, ERASMUS, CERV")
    p.add_argument("--cascade", action="store_true", help="also calls that EU-funded projects open to third parties")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    statuses = list(STATUS.values()) if a.status == "both" else [STATUS[a.status]]
    types = ["1", "2"] + (["8"] if a.cascade else [])
    must = [{"terms": {"type": types}}, {"terms": {"status": statuses}}]
    results = post(a.query, must, 100).get("results", [])

    calls, seen = [], set()
    for r in results:
        m = r.get("metadata", {})
        ident = first(m, "identifier")
        if a.programme and not ident.upper().startswith(a.programme.upper()):
            continue
        key = (ident, first(m, "callTitle") if first(m, "type") == "8" else "")
        if key in seen:
            continue
        seen.add(key)
        cascade = first(m, "type") == "8"
        deadline = next_deadline(m)
        title = first(m, "callTitle") if cascade else first(m, "title")
        if deadline is None or "CANCELLED" in ident.upper() or "cancelled" in title.lower():
            continue
        page = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{ident}"
        calls.append({
            "id": ident,
            "title": title,
            "programme": programme(ident) + (" · third-party call" if cascade else ""),
            "status": STATUS_NAME.get(first(m, "status"), first(m, "status")),
            "next_deadline": deadline,
            "grant": grant_size(m),
            "action": first(m, "typesOfAction"),
            "url": r.get("url") if cascade and r.get("url") else page,
        })
        if len(calls) >= a.limit:
            break

    if a.json:
        json.dump({"checked": dt.date.today().isoformat(), "calls": calls}, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    print(f"EU Funding & Tenders Portal · checked {dt.date.today().isoformat()} · {len(calls)} calls\n")
    for c in calls:
        print(f"- {c['title']} [{c['id']}]")
        print(f"  {c['programme']} · {c['status']} · next deadline {c['next_deadline']} · {c['grant']}" + (f" · {c['action']}" if c["action"] else ""))
        print(f"  {c['url']}")
    if not calls:
        print("No open or upcoming calls match. Try broader words or --cascade.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
