"""Shared access to the scholarly databases used by the paper-research scripts. Standard library only.

- OpenAlex (https://openalex.org): free. Without a key, requests share a small daily budget per network
  (about 100 searches; it resets at midnight UTC). OPENALEX_API_KEY (free: https://openalex.org/settings/api)
  gives your own budget.
- Semantic Scholar (https://www.semanticscholar.org/product/api): free; S2_API_KEY (optional) raises the rate
  limit. Without a key requests are shared and may be throttled: they are retried with backoff.

Works from both are normalized to one dict shape (see `norm_openalex`, `norm_s2`) and merged by DOI, else by
normalized title + year.
"""
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "paper-research-skill/1.1"}
OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,year,venue,authors,citationCount,influentialCitationCount,externalIds,openAccessPdf,publicationTypes,abstract"

# --- HTTP ------------------------------------------------------------------------------------


class BudgetExhausted(RuntimeError):
    """A database's free daily budget is used up; the message says when it resets and how to avoid it."""


def get(url: str, headers: dict | None = None, tries: int = 5) -> dict:
    """GET JSON with retries on throttling and transient errors."""
    delay = 2.0
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={**UA, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            wait = e.headers.get("Retry-After") if e.headers else None
            if e.code == 429 and wait and wait.isdigit() and int(wait) > 300:
                # A daily budget is used up (OpenAlex without a key): waiting would take hours.
                raise BudgetExhausted(
                    f"{urllib.parse.urlsplit(url).netloc}: daily free budget used up, resets in {int(wait) // 3600}h"
                    f"{int(wait) % 3600 // 60:02d}m. A free key gives your own budget (OpenAlex: set OPENALEX_API_KEY)."
                ) from None
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                # Respect the server's Retry-After when it gives one (short rate limits), capped at a minute.
                time.sleep(min(60.0, float(wait)) if wait and wait.replace(".", "", 1).isdigit() else delay)
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    return {}


def post(url: str, body: dict, headers: dict | None = None, tries: int = 5) -> list | dict:
    delay = 2.0
    data = json.dumps(body).encode()
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, headers={**UA, "Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    return []


# --- Normalizing -----------------------------------------------------------------------------


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def key(w: dict) -> str:
    """Merge key: DOI when known, else folded title + year."""
    if w.get("doi"):
        return "doi:" + w["doi"].lower()
    return f"t:{fold(w.get('title', ''))[:120]}|{w.get('year')}"


def empty() -> dict:
    return {
        "title": "", "year": None, "authors": [], "venue": "", "type": "", "doi": None,
        "cited_openalex": None, "cited_s2": None, "influential_s2": None, "cited_scholar": None,
        "percentile": None, "oa_pdf": None, "oa_status": None, "license": None, "landing": None,
        "abstract": "", "retracted": False, "openalex": None, "s2": None, "references": [],
    }


def rebuild_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)


def norm_openalex(w: dict) -> dict:
    loc = w.get("best_oa_location") or {}
    primary = w.get("primary_location") or {}
    pct = (w.get("citation_normalized_percentile") or {}).get("value")
    return {
        **empty(),
        "title": w.get("display_name") or w.get("title") or "",
        "year": w.get("publication_year"),
        "authors": [a["author"]["display_name"] for a in w.get("authorships", [])],
        "venue": ((primary.get("source") or {}).get("display_name")) or "",
        "type": w.get("type") or "",
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "cited_openalex": w.get("cited_by_count"),
        "percentile": pct if isinstance(pct, (int, float)) else None,
        "oa_pdf": loc.get("pdf_url"),
        "oa_status": (w.get("open_access") or {}).get("oa_status"),
        "license": loc.get("license"),
        "landing": loc.get("landing_page_url") or primary.get("landing_page_url"),
        "abstract": rebuild_abstract(w.get("abstract_inverted_index")),
        "retracted": w.get("is_retracted", False),
        "openalex": w.get("id"),
        "references": w.get("referenced_works") or [],
    }


def norm_s2(p: dict) -> dict:
    ids = p.get("externalIds") or {}
    pdf = p.get("openAccessPdf") or {}
    return {
        **empty(),
        "title": p.get("title") or "",
        "year": p.get("year"),
        "authors": [a.get("name", "") for a in p.get("authors") or []],
        "venue": p.get("venue") or "",
        "type": ",".join(p.get("publicationTypes") or []),
        "doi": (ids.get("DOI") or "").lower() or None,
        "cited_s2": p.get("citationCount"),
        "influential_s2": p.get("influentialCitationCount"),
        "oa_pdf": pdf.get("url") or None,
        "abstract": p.get("abstract") or "",
        "s2": p.get("paperId"),
    }


def merge(a: dict, b: dict) -> dict:
    """Fill a's gaps from b (same work from another database)."""
    out = dict(a)
    for k, v in b.items():
        if k == "references":
            out[k] = list(a.get(k) or []) + [r for r in v or [] if r not in (a.get(k) or [])]
        elif out.get(k) in (None, "", [], False) and v not in (None, "", []):
            out[k] = v
    return out


def merge_all(works: list[dict]) -> list[dict]:
    by: dict[str, dict] = {}
    titles: dict[str, str] = {}  # folded title|year -> key, to join a DOI-less record with a DOI one
    for w in works:
        k = key(w)
        tk = f"{fold(w.get('title', ''))[:120]}|{w.get('year')}"
        k = by.get(k) and k or titles.get(tk, k)
        by[k] = merge(by[k], w) if k in by else w
        titles.setdefault(tk, k)
    return list(by.values())


# --- OpenAlex --------------------------------------------------------------------------------


def openalex_auth() -> dict:
    """The user's own key when set (own budget), else the optional email for the polite pool."""
    key, mail = os.environ.get("OPENALEX_API_KEY"), os.environ.get("OPENALEX_MAILTO")
    return {"api_key": key} if key else ({"mailto": mail} if mail else {})


def openalex(params: dict) -> dict:
    return get(f"{OPENALEX}?" + urllib.parse.urlencode({**params, **openalex_auth()}))


def openalex_work(doi: str) -> dict:
    """One work by DOI (raw OpenAlex record), or {} when unknown."""
    q = urllib.parse.urlencode(openalex_auth())
    return get(f"{OPENALEX}/doi:{urllib.parse.quote(doi.removeprefix('https://doi.org/'))}" + (f"?{q}" if q else ""))


def openalex_search(q: str, limit: int = 10, sort: str | None = None, filters: list[str] | None = None, in_title_abstract: bool = False) -> list[dict]:
    f = list(filters or [])
    params: dict = {"per-page": max(1, min(limit, 200))}
    if in_title_abstract:
        f.append(f"title_and_abstract.search:{q}")
    else:
        params["search"] = q
    if f:
        params["filter"] = ",".join(f)
    if sort:
        params["sort"] = sort
    return [norm_openalex(w) for w in openalex(params).get("results", [])]


def openalex_doi(doi: str) -> dict | None:
    w = openalex_work(doi)
    return norm_openalex(w) if w else None


def openalex_ids(ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        chunk = [x.rsplit("/", 1)[-1] for x in ids[i : i + 50]]
        out += [norm_openalex(w) for w in openalex({"filter": "openalex:" + "|".join(chunk), "per-page": 50}).get("results", [])]
    return out


def openalex_dois(dois: list[str]) -> list[dict]:
    out = []
    clean = [d.lower().removeprefix("https://doi.org/") for d in dois if d]
    for i in range(0, len(clean), 50):
        chunk = clean[i : i + 50]
        out += [norm_openalex(w) for w in openalex({"filter": "doi:" + "|".join(chunk), "per-page": 50}).get("results", [])]
    return out


# --- Semantic Scholar ------------------------------------------------------------------------


def s2_headers() -> dict:
    k = os.environ.get("S2_API_KEY")
    return {"x-api-key": k} if k else {}


def s2_get(path: str, params: dict) -> dict:
    time.sleep(0 if os.environ.get("S2_API_KEY") else 1.1)  # stay under the shared rate limit
    return get(f"{S2}{path}?" + urllib.parse.urlencode(params), s2_headers())


def s2_search(q: str, limit: int = 10, by_citations: bool = False, year: str | None = None) -> list[dict]:
    if by_citations:
        params = {"query": q, "fields": S2_FIELDS, "sort": "citationCount:desc"}
        if year:
            params["year"] = year
        data = s2_get("/paper/search/bulk", params).get("data", [])[:limit]
    else:
        params = {"query": q, "fields": S2_FIELDS, "limit": max(1, min(limit, 100))}
        if year:
            params["year"] = year
        data = s2_get("/paper/search", params).get("data", [])
    return [norm_s2(p) for p in data or []]


def s2_doi(doi: str) -> dict | None:
    p = s2_get(f"/paper/DOI:{urllib.parse.quote(doi)}", {"fields": S2_FIELDS})
    return norm_s2(p) if p else None


def s2_batch(dois: list[str]) -> list[dict]:
    """Semantic Scholar records for many DOIs in one request (citations and influential citations)."""
    out = []
    ids = [f"DOI:{d}" for d in dois if d]
    for i in range(0, len(ids), 400):
        time.sleep(0 if os.environ.get("S2_API_KEY") else 1.1)
        res = post(f"{S2}/paper/batch?fields={S2_FIELDS}", {"ids": ids[i : i + 400]}, s2_headers())
        out += [norm_s2(p) for p in res or [] if p]
    return out


def on_topic(w: dict, query: str) -> bool:
    """Every query word appears in the title or abstract (S2's bulk search also matches other fields)."""
    text = fold(f"{w.get('title', '')} {w.get('abstract', '')}")
    return all(t in text for t in fold(query).split())


def s2_references(paper_id: str, limit: int = 500) -> list[tuple[dict, bool]]:
    """The works a paper cites, each with S2's 'influential' flag (the citing paper builds on it)."""
    fields = "isInfluential," + ",".join(f"citedPaper.{f}" for f in S2_FIELDS.split(",") if f != "abstract")
    data = s2_get(f"/paper/{paper_id}/references", {"fields": fields, "limit": min(limit, 1000)}).get("data") or []
    return [(norm_s2(d["citedPaper"]), bool(d.get("isInfluential"))) for d in data if d.get("citedPaper", {}).get("title")]


# --- Evidence kind ---------------------------------------------------------------------------

# Cues for the evidence kind, from the title and abstract. A first guess that the reader confirms.
REVIEW = re.compile(
    r"\b(systematic review|meta-?analys[ie]s of|literature review|scoping review|review of (?:the )?(?:literature|research|studies)|"
    r"we review|this (?:article|paper|chapter|review) (?:reviews|surveys|synthesi[sz]es|integrates)|overview of|we survey|"
    r"survey of (?:the )?(?:literature|research|approaches|methods)|we synthesi[sz]e|integrative (?:review|framework)|"
    r"state of the art in|tutorial|handbook|this review|introduction to the (?:main )?approaches|emergence and evolution|"
    r"key themes|in this chapter|we (?:discuss|outline|summari[sz]e|explore) (?:these|the main|the) (?:approaches|devices|"
    r"methods|research|literature|studies)|summary of)\b",
    re.I,
)
EMPIRICAL = re.compile(
    r"\b(meta-?analysis (?:of|shows|found)|experiments?\b|randomi[sz]ed|survey data|participants|respondents|sample of|corpus|"
    r"dataset|annotated|annotators?|panel data|regression|we (?:test|estimate|measure|find|found|collect|annotate|analy[sz]e|"
    r"investigate|examine|compare|evaluate)|n ?= ?\d|inter-?(?:coder|annotator|rater)|reliability|validat|replicat|field study|"
    r"outperform|f1|accuracy of|precision|recall|results show|we (?:present|report) the results|we demonstrate|findings)\b|\b\d+(?:\.\d+)? ?%|\b\d{1,3}(?:,\d{3})+\b",
    re.I,
)
ANALYTICAL = re.compile(r"\b(perspective|essay|commentary|we argue|conceptual|theoretical|we propose (?:a|an|that)|we suggest)\b", re.I)


def evidence_kind(w: dict) -> str:
    """A first guess from title, abstract and type: review, empirical or analytical. Confirm by reading."""
    text = f"{w.get('title', '')} {w.get('abstract', '')}"
    if not text.strip():
        return "unknown"
    if REVIEW.search(text) or "review" in (w.get("type") or "").lower():
        return "review"
    empirical = len(EMPIRICAL.findall(text))
    analytical = len(ANALYTICAL.findall(text))
    if empirical > analytical and (empirical >= 2 or analytical == 0):
        return "empirical"
    return "analytical" if w.get("abstract") else "unknown"


# --- Display ---------------------------------------------------------------------------------


def cites(w: dict) -> str:
    """Citation counts per database: GS = Google Scholar (from the user's export), OA = OpenAlex, S2 = Semantic Scholar."""
    parts = [f"{name} {w[k]}" for name, k in (("GS", "cited_scholar"), ("OA", "cited_openalex"), ("S2", "cited_s2")) if w.get(k) is not None]
    return "cited " + " · ".join(parts) if parts else "no citation count"


def brief(w: dict, head: str = "") -> str:
    who = ", ".join(w["authors"][:2]) + (" et al." if len(w["authors"]) > 2 else "")
    available = "open" if (w.get("oa_pdf") or w.get("oa_status") not in (None, "closed")) else "closed"
    flag = " · RETRACTED" if w.get("retracted") else ""
    return f"- {head}{w['title']} ({w['year']}) | {who} | {cites(w)} | {evidence_kind(w)} | {available} | {w['doi'] or '-'}{flag}"
