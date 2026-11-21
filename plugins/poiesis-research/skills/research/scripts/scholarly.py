"""Shared access to the scholarly databases used by the research scripts. Standard library only.

- OpenAlex (https://openalex.org): free. Without a key, requests share a small daily budget per network
  ($0.10: about 100 searches or 1,000 filtered lists; it resets at midnight UTC). OPENALEX_API_KEY (free:
  https://openalex.org/settings/api) gives your own budget of $1 a day.
- Semantic Scholar (https://www.semanticscholar.org/product/api): free; S2_API_KEY (optional) gives 1 request a
  second. Without a key requests are shared and may be throttled: they are retried with backoff.
- Crossref, Europe PMC and arXiv: free, no key. They answer when OpenAlex or Semantic Scholar refuses.

Every request goes through one layer (see "Request layer" below): a cache on disk, pacing per host, the OpenAlex
budget read from the response headers, a record of which databases answered (the "Coverage" line), and
record/replay for tests. No email address and no key is ever written to disk or put in a message.

Works from every database are normalized to one dict shape (see `empty` and the `norm_*` functions) and merged by
DOI, else by normalized title + year.

  scholarly.py cache [--clear]     where the cached answers are, how many, and how to remove them
"""
import contextlib
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

try:  # one request at a time per host across processes (several agents can run at once); POSIX only
    import fcntl
except ImportError:  # Windows: pacing then works inside each process only
    fcntl = None

VERSION = "2.4.0"
UA = {"User-Agent": "paper-research-skill/1.1"}
OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,year,venue,authors,citationCount,influentialCitationCount,externalIds,openAccessPdf,publicationTypes,abstract"
CROSSREF = "https://api.crossref.org/works"
CROSSREF_FIELDS = "DOI,title,author,issued,container-title,type,is-referenced-by-count,abstract,license"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
ARXIV = "https://export.arxiv.org/api/query"

# --- Request layer ---------------------------------------------------------------------------
# Every request passes through `fetch`: replay, then the cache, then the network. Each answer is written to disk
# the moment it arrives, so a run that stops keeps what it had and the next run does not pay for it again.
# The limits below come from each database's documentation, read on 2026-11-21 (research/notes of the plugin's
# repository: openalex-2026-api-documentation, fallback-databases-2026-access, signal-sources-2026-access).

OPENALEX_HOST = "api.openalex.org"
DATABASES = {
    "api.openalex.org": "OpenAlex", "api.semanticscholar.org": "Semantic Scholar", "api.crossref.org": "Crossref",
    "www.ebi.ac.uk": "Europe PMC", "export.arxiv.org": "arXiv", "api.reporter.nih.gov": "NIH RePORTER",
    "api.openaire.eu": "OpenAIRE", "hn.algolia.com": "Hacker News", "wikimedia.org": "Wikimedia pageviews",
    "huggingface.co": "Hugging Face",
}
SECRETS = {"api_key", "apikey", "mailto", "token", "access_token"}  # never written to disk or shown
CACHE_HOURS = 24.0


class Refused(RuntimeError):
    """A database did not answer: budget used up, a key needed, an answer that is not data, or a recording that
    lacks the request. The message says which."""


class BudgetExhausted(Refused):
    """A database's free daily budget is used up; the message says when it resets and how to avoid it."""


class NeedsKey(Refused):
    """The database answers this request only with a key (OpenAlex: paging past the first page with a cursor)."""


class ReplayMissing(Refused):
    """Replay is on and the recording has no answer for this request. The network is never used in its place."""


REFUSALS = (Refused, urllib.error.URLError, TimeoutError)  # HTTPError is a URLError


class _Layer:
    """How requests are served in this process, and what happened to each one."""

    def __init__(self) -> None:
        raw = os.environ.get("POIESIS_RESEARCH_CACHE", "")
        if raw.strip().lower() in ("off", "no", "0"):
            self.cache_dir: Path | None = None
        else:
            self.cache_dir = Path(raw).expanduser() if raw.strip() else Path.home() / ".cache" / "poiesis-research" / "http"
        try:
            hours = float(os.environ.get("POIESIS_RESEARCH_CACHE_HOURS", "") or CACHE_HOURS)
        except ValueError:
            hours = CACHE_HOURS
        self.max_age = hours * 3600
        self.fresh = False
        self.record: Path | None = None
        self.replay: Path | None = None
        self.events: list[dict] = []  # one per request, in order: db, how (network, cache, replay, refused), fetched, detail
        self.last: dict[str, float] = {}  # host -> when the last request started (pacing inside this process)
        self.budget: dict[str, dict] = {}  # host -> what its last answer said about the budget


LAYER = _Layer()
_sleep = time.sleep  # tests replace these two, so they neither wait nor touch the network


def _open(req: urllib.request.Request, timeout: float = 60):
    return urllib.request.urlopen(req, timeout=timeout)


_UNSET = object()


def configure(*, fresh: bool | None = None, cache_dir=_UNSET, record=_UNSET, replay=_UNSET, hours: float | None = None) -> None:
    """Change how requests are served for the rest of this run.

    fresh=True asks the databases again and rewrites the cache; cache_dir=None turns the cache off;
    record=<folder> also saves every answer there; replay=<folder> answers only from there, never the network.
    """
    if fresh is not None:
        LAYER.fresh = fresh
    if cache_dir is not _UNSET:
        LAYER.cache_dir = Path(cache_dir) if cache_dir is not None else None
    if record is not _UNSET:
        LAYER.record = Path(record) if record is not None else None
    if replay is not _UNSET:
        LAYER.replay = Path(replay) if replay is not None else None
    if hours is not None:
        LAYER.max_age = hours * 3600


def clean_url(url: str) -> str:
    """The URL without keys or email addresses: the only form that is hashed, stored or shown."""
    parts = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in SECRETS]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def scrub(text: str, url: str = "") -> str:
    """The text without the request's secrets: the key and email parameters of its address and the keys in the
    environment, plain and percent-encoded. An answer can repeat the address it was asked at, or a key from a
    header, and nothing of that kind is stored or passed on."""
    found = [v for k, v in urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query) if k.lower() in SECRETS]
    found += [os.environ.get(name, "") for name in ("OPENALEX_API_KEY", "S2_API_KEY")]
    for secret in sorted({s for s in found if len(s) >= 4}, key=len, reverse=True):
        for form in {secret, urllib.parse.quote(secret, safe=""), urllib.parse.quote_plus(secret)}:
            text = text.replace(form, "REDACTED")
    return text


def _digest(url: str, data: bytes | None) -> str:
    return hashlib.sha256(("POST" if data else "GET").encode() + b"\n" + clean_url(url).encode() + b"\n" + (data or b"")).hexdigest()


def _cache_path(host: str, digest: str) -> Path:
    return LAYER.cache_dir / host / f"{digest}.json"


def _record_path(folder: Path, host: str, digest: str) -> Path:
    return folder / f"{host}-{digest[:16]}.json"


def _read(path: Path) -> dict | None:
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return entry if isinstance(entry, dict) else None


def _write(path: Path, entry: dict) -> None:
    """Write a whole file or nothing (another process may be reading it); a disk that refuses is not an error."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(entry, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age(entry: dict) -> float:
    try:
        then = dt.datetime.strptime(entry.get("fetched", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return float("inf")
    return (dt.datetime.now(dt.timezone.utc) - then).total_seconds()


def _event(host: str, how: str, entry: dict | None = None, detail: str = "") -> None:
    LAYER.events.append({"db": DATABASES.get(host, host), "host": host, "how": how, "fetched": (entry or {}).get("fetched"), "detail": detail})


def last_fetched() -> str | None:
    """When the most recent answer was fetched (its own date when it came from the cache or a recording)."""
    return next((e["fetched"] for e in reversed(LAYER.events) if e.get("fetched")), None)


def pace_seconds(host: str, url: str = "") -> float:
    """Seconds between two requests to one host: what its documentation asks, with a margin."""
    if host == OPENALEX_HOST:
        # 10 requests a second without a key; 1 a second for a search with more than 5 Boolean operators or a
        # filter with more than 10 topic ids.
        query = urllib.parse.unquote_plus(urllib.parse.urlsplit(url).query)
        broad = len(re.findall(r"\b(?:AND|OR|NOT)\b", query)) > 5
        wide = re.search(r"(?:topics?|primary_topic|concepts?)\.id:[^,&|]*(?:\|[^,&|]*){10,}", query) is not None
        return 1.1 if broad or wide else 0.2
    if host == "api.semanticscholar.org":  # 1 request a second with a key; shared and throttled without one
        return 1.05 if os.environ.get("S2_API_KEY") else 1.1
    if host == "api.crossref.org":  # public pool: 5 DOI lookups a second, 1 query a second, one at a time
        return 0.25 if urllib.parse.urlsplit(url).path.count("/") > 1 else 1.05
    if host == "export.arxiv.org":  # one request every three seconds, one connection
        return 3.1
    return {"www.ebi.ac.uk": 0.35, "api.reporter.nih.gov": 1.05, "api.openaire.eu": 1.05, "hn.algolia.com": 0.5,
            "wikimedia.org": 0.2, "huggingface.co": 0.7}.get(host, 1.0)


@contextlib.contextmanager
def _slot(host: str, url: str):
    """Wait for this host's turn: one request at a time, spaced as the host asks, across processes where the
    system allows a shared lock."""
    gap = pace_seconds(host, url)
    last = LAYER.last.get(host, 0.0)
    lock = None
    if fcntl is not None and LAYER.cache_dir is not None:
        try:
            folder = LAYER.cache_dir / "pace"
            folder.mkdir(parents=True, exist_ok=True)
            lock = open(folder / f"{host}.lock", "a+", encoding="utf-8")
            fcntl.flock(lock, fcntl.LOCK_EX)
            lock.seek(0)
            last = max(last, float(lock.read().strip() or 0))
        except (OSError, ValueError):
            pass  # no shared lock: pace inside this process only
    wait = last + gap - time.time()
    if wait > 0:
        _sleep(min(wait, gap))
    started = time.time()
    LAYER.last[host] = started
    try:
        yield
    finally:
        if lock is not None:
            try:
                lock.seek(0)
                lock.truncate()
                lock.write(repr(started))
                lock.flush()
                fcntl.flock(lock, fcntl.LOCK_UN)
            except (OSError, ValueError):
                pass
            lock.close()


def openalex_cost(url: str) -> float:
    """What an OpenAlex request costs in dollars, from its documentation: nothing for one record by ID or DOI,
    0.001 for a search, 0.0001 for a filtered list or a grouped count on one."""
    parts = urllib.parse.urlsplit(url)
    if len([s for s in parts.path.split("/") if s]) > 1:
        return 0.0
    query = urllib.parse.parse_qsl(parts.query)
    if any(k == "search" or k.startswith("search.") or (k == "filter" and ".search:" in v) for k, v in query):
        return 0.001
    return 0.0001


def _budget_file(host: str) -> Path | None:
    if LAYER.cache_dir is None:
        return None
    who = "key" if os.environ.get("OPENALEX_API_KEY") else "nokey"
    return LAYER.cache_dir / "budget" / f"{host}.{who}.json"


def _note_budget(host: str, headers) -> None:
    """Keep what an OpenAlex answer says about today's budget, for the Coverage line and for the next request."""
    if host != OPENALEX_HOST or headers is None:
        return

    def number(name: str) -> float | None:
        try:
            return float(headers.get(name))
        except (TypeError, ValueError):
            return None

    left = number("x-ratelimit-remaining-usd")
    if left is None:
        return
    reset = number("x-ratelimit-reset")
    budget = {"remaining": left + (number("x-ratelimit-prepaid-remaining-usd") or 0.0), "limit": number("x-ratelimit-limit-usd"),
              "reset_at": time.time() + reset if reset is not None else None}
    LAYER.budget[host] = budget
    if (path := _budget_file(host)) is not None:
        _write(path, budget)


def budget(host: str = OPENALEX_HOST) -> dict | None:
    """Today's budget as last seen (by this process, or by another one using the same cache folder)."""
    seen = LAYER.budget.get(host)
    if seen is None and (path := _budget_file(host)) is not None:
        seen = _read(path)
    if not seen or not seen.get("reset_at") or seen["reset_at"] <= time.time():
        return None  # nothing seen yet, or the day it was seen on is over
    return seen


def _budget_message(host: str, seconds: float) -> str:
    seconds = max(0, int(seconds))
    free = "" if os.environ.get("OPENALEX_API_KEY") else " free"
    hint = "" if os.environ.get("OPENALEX_API_KEY") else " A free key gives your own budget (OpenAlex: set OPENALEX_API_KEY)."
    return f"{host}: daily{free} budget used up, resets in {seconds // 3600}h{seconds % 3600 // 60:02d}m.{hint}"


def _reason(e: urllib.error.HTTPError) -> str:
    """Why the database refused, in its own words when the body says so."""
    try:
        body = json.loads(e.read().decode("utf-8", "replace"))
    except (OSError, ValueError, AttributeError):
        return ""
    if not isinstance(body, dict):
        return ""
    return " ".join(str(body[k]) for k in ("reason", "error") if body.get(k))


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def fetch(url: str, data: bytes | None = None, headers: dict | None = None, tries: int = 5, check=_is_json, not_found_ok: bool = True) -> tuple[int, str]:
    """One request through the layer. Returns (status, text): 200 with the answer, or 404 with "" when the
    database has no such record and `not_found_ok`. Raises a Refused or a urllib error when it will not answer.
    `check` says whether a 200 answer is data (an anti-bot page is not): what fails it is refused, not cached."""
    host = urllib.parse.urlsplit(url).netloc
    digest = _digest(url, data)

    if LAYER.replay is not None:
        entry = _read(_record_path(LAYER.replay, host, digest))
        if entry is None:
            _event(host, "refused", detail="not in the recording")
            raise ReplayMissing(f"{clean_url(url)}: not in the recording at {LAYER.replay}. Record it again; replay never uses the network.")
        if entry.get("refused"):  # the database refused when this was recorded: refuse the same way
            _event(host, "refused", detail=entry.get("detail") or f"HTTP {entry['status']}")
            raise {"budget": BudgetExhausted, "key": NeedsKey}.get(entry["refused"], Refused)(entry.get("message") or f"{host}: HTTP {entry['status']} (recorded)")
        _event(host, "replay", entry)
        return entry["status"], entry["body"]

    if LAYER.cache_dir is not None and not LAYER.fresh:
        entry = _read(_cache_path(host, digest))
        if entry is not None and _age(entry) <= LAYER.max_age:
            _event(host, "cache", entry)
            if LAYER.record is not None:
                _write(_record_path(LAYER.record, host, digest), entry)
            return entry["status"], entry["body"]

    def keep(status: int, text: str) -> tuple[int, str]:
        text = scrub(text, url)
        entry = {"url": clean_url(url), "method": "POST" if data else "GET", "status": status, "fetched": _now(), "body": text}
        if data:
            entry["request_body"] = scrub(data.decode("utf-8", "replace"), url)
        if LAYER.cache_dir is not None:
            _write(_cache_path(host, digest), entry)
        if LAYER.record is not None:
            _write(_record_path(LAYER.record, host, digest), entry)
        _event(host, "network", entry)
        return status, text

    def refuse(kind: str, status: int, detail: str, message: str) -> None:
        """Note a refusal for the Coverage line and, when recording, keep it so a replay refuses the same way."""
        detail, message = scrub(detail, url), scrub(message, url)
        _event(host, "refused", detail=detail)
        if LAYER.record is not None:
            _write(_record_path(LAYER.record, host, digest), {"url": clean_url(url), "method": "POST" if data else "GET", "status": status,
                                                              "fetched": _now(), "body": "", "refused": kind, "detail": detail, "message": message})

    if host == OPENALEX_HOST and (seen := budget(host)) is not None and seen["remaining"] + 1e-9 < openalex_cost(url):
        _event(host, "refused", detail="daily budget used up")
        raise BudgetExhausted(_budget_message(host, seen["reset_at"] - time.time()))

    delay = 2.0
    for attempt in range(tries):
        try:
            with _slot(host, url):
                req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
                with _open(req, 60) as res:
                    text = res.read().decode("utf-8", "replace")
                    answered = res.headers
            _note_budget(host, answered)
            if check is not None and not check(text):
                _event(host, "refused", detail="answered with something that is not data (an anti-bot page?)")
                raise Refused(f"{host}: answered with something that is not data (an anti-bot page?).")
            return keep(200, text)
        except urllib.error.HTTPError as e:
            _note_budget(host, e.headers)
            wait = e.headers.get("Retry-After") if e.headers else None
            reason = _reason(e)
            final = e.code not in (404, 429, 500, 502, 503, 504) or attempt == tries - 1
            if not final or (e.code == 404 and not_found_ok):
                e.close()  # nothing more is read from an answer that is retried or kept as "no such record"
            if e.code == 404 and not_found_ok:
                return keep(404, "")
            if e.code == 429 and ("daily_budget" in reason or (wait and wait.isdigit() and int(wait) > 300)):
                # A daily budget is used up (OpenAlex without a key): waiting would take hours.
                if wait and wait.isdigit():
                    left = float(wait)
                elif (seen := budget(host)) is not None:
                    left = seen["reset_at"] - time.time()
                else:  # OpenAlex resets at midnight UTC
                    now = dt.datetime.now(dt.timezone.utc)
                    left = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
                LAYER.budget[host] = {"remaining": 0.0, "limit": (LAYER.budget.get(host) or {}).get("limit"), "reset_at": time.time() + left}
                if (path := _budget_file(host)) is not None and host == OPENALEX_HOST:
                    _write(path, LAYER.budget[host])
                message = _budget_message(host, left)
                refuse("budget", e.code, "daily budget used up", message)
                e.close()
                raise BudgetExhausted(message) from None
            if e.code in (401, 403) and host == OPENALEX_HOST and "key" in reason.lower():
                message = scrub(f"{host}: {reason}. Set OPENALEX_API_KEY (free: https://openalex.org/settings/api).", url)
                refuse("key", e.code, "needs a key", message)
                e.close()
                raise NeedsKey(message) from None
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                # Respect the server's Retry-After when it gives one (short rate limits), capped at a minute.
                _sleep(min(60.0, float(wait)) if wait and wait.replace(".", "", 1).isdigit() else delay)
                delay *= 2
                continue
            refuse("http", e.code, f"HTTP {e.code}" + (f" {e.reason}" if e.reason else ""), f"{host}: HTTP {e.code}" + (f" {reason}" if reason else ""))
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < tries - 1:
                _sleep(delay)
                delay *= 2
                continue
            _event(host, "refused", detail=f"no connection ({getattr(e, 'reason', e)})")
            raise
    return 404, ""


def get(url: str, headers: dict | None = None, tries: int = 5) -> dict:
    """GET JSON with a cache, pacing and retries on throttling and transient errors; {} for "no such record"."""
    status, text = fetch(url, None, headers, tries)
    return json.loads(text) if status == 200 else {}


def get_text(url: str, headers: dict | None = None, tries: int = 5, check=None) -> str:
    """GET an answer that is not JSON (arXiv's Atom feed), through the same layer; "" for "no such record"."""
    status, text = fetch(url, None, headers, tries, check=check)
    return text if status == 200 else ""


def post(url: str, body: dict, headers: dict | None = None, tries: int = 5) -> list | dict:
    """POST JSON through the same layer; the body is part of what identifies the request in the cache."""
    _, text = fetch(url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})}, tries, not_found_ok=False)
    return json.loads(text)


def coverage_line() -> str:
    """One line naming the databases this run asked: which answered, which refused, what came from the cache, and
    the OpenAlex budget that is left. "" when nothing was asked."""
    if not LAYER.events:
        return ""
    per: dict[str, dict] = {}
    for e in LAYER.events:
        seen = per.setdefault(e["db"], {"network": 0, "cache": 0, "replay": 0, "refused": []})
        if e["how"] == "refused":
            if e["detail"] not in seen["refused"]:
                seen["refused"].append(e["detail"])
        else:
            seen[e["how"]] += 1
    parts = []
    for db, seen in per.items():
        n = seen["network"] + seen["cache"] + seen["replay"]
        said = []
        if n:
            stored = [f"{seen[k]} from {name}" for k, name in (("cache", "the cache"), ("replay", "a recording")) if seen[k]]
            said.append(f"answered ({n} request{'' if n == 1 else 's'}" + (", of which " + " and ".join(stored) if stored else "") + ")")
        if seen["refused"]:
            said.append(f"refused ({'; '.join(seen['refused'])})")
        parts.append(f"{db} " + " and ".join(said))
    dates = sorted({e["fetched"][:10] for e in LAYER.events if e.get("fetched")})
    when = _now()[:10] if not dates else dates[0] if len(dates) == 1 else f"{dates[0]} to {dates[-1]}"
    line = f"Coverage ({when}): " + "; ".join(parts) + "."
    left = LAYER.budget.get(OPENALEX_HOST)
    if left is not None:
        line += f" OpenAlex budget left: ${left['remaining']:.4f}" + (f" of ${left['limit']:.2f} a day" if left.get("limit") else "") + "."
    return line


def refused(db: str) -> bool:
    """Whether a database (by its name in the Coverage line) refused a request in this run."""
    return any(e["db"] == db and e["how"] == "refused" for e in LAYER.events)


def finish(main) -> int:
    """Run a script's main() and end its output with the Coverage line. With --json the line goes to stderr, so
    the JSON on stdout stays valid."""
    try:
        return main()
    finally:
        line = coverage_line()
        if line:
            as_json = "--json" in sys.argv
            print(line if as_json else "\n" + line, file=sys.stderr if as_json else sys.stdout)


def add_request_args(parser) -> None:
    parser.add_argument("--fresh", action="store_true", help="ask the databases again instead of using answers cached in the last day")


def apply_request_args(args) -> None:
    if getattr(args, "fresh", False):
        configure(fresh=True)


def ask(fn, *args, **kw):
    """Call a database function; None when the database refuses (the Coverage line then says so)."""
    try:
        return fn(*args, **kw)
    except REFUSALS:
        return None


# --- Normalizing -----------------------------------------------------------------------------


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def strip_tags(s: str) -> str:
    """Plain text from a title or abstract that carries markup (Crossref's JATS tags, Europe PMC's headings)."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


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
        "cited_crossref": None, "cited_epmc": None, "crossref": None, "epmc": None, "arxiv": None, "doi_published": None,
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


def norm_crossref(m: dict) -> dict:
    """A Crossref record. Crossref knows the registered metadata and how often its members cite the work; it does
    not say whether an open copy exists, unless the publisher deposited a Creative Commons licence."""
    issued = ((m.get("issued") or {}).get("date-parts") or [[None]])[0] or [None]
    licences = (re.search(r"creativecommons\.org/(?:licenses|publicdomain)/([a-z\-]+)", (x.get("URL") or "").lower()) for x in m.get("license") or [])
    cc = next((x.group(1) for x in licences if x), None)
    doi = (m.get("DOI") or "").lower() or None
    people = [" ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name") or "" for a in m.get("author") or []]
    return {
        **empty(),
        "title": strip_tags((m.get("title") or [""])[0]),
        "year": issued[0],
        "authors": [p for p in people if p],
        "venue": strip_tags((m.get("container-title") or [""])[0]),
        "type": m.get("type") or "",
        "doi": doi,
        "cited_crossref": m.get("is-referenced-by-count"),
        "oa_status": "open" if cc else "unknown",
        "license": None if cc is None else "cc0" if cc == "zero" else f"cc-{cc}",
        "landing": f"https://doi.org/{doi}" if doi else None,
        "abstract": strip_tags(m.get("abstract") or ""),
        "crossref": doi,
    }


def norm_epmc(r: dict) -> dict:
    """A Europe PMC record (a search result, or a citing work, which carries fewer fields)."""
    urls = (r.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    free = [u for u in urls if (u.get("availability") or "").lower() in ("open access", "free")]
    people = (r.get("authorList") or {}).get("author") or []
    names = [" ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) or a.get("fullName") or a.get("collectiveName") or "" for a in people]
    if not names and r.get("authorString"):
        names = [x.strip() for x in r["authorString"].rstrip(".").split(",")]
    year = str(r.get("pubYear") or "")
    doi = (r.get("doi") or "").lower() or None
    return {
        **empty(),
        "title": strip_tags(r.get("title") or "").rstrip("."),
        "year": int(year) if year.isdigit() else None,
        "authors": [n for n in names if n],
        "venue": (((r.get("journalInfo") or {}).get("journal") or {}).get("title")) or r.get("journalAbbreviation") or "",
        "type": ",".join((r.get("pubTypeList") or {}).get("pubType") or []) or r.get("citationType") or "",
        "doi": doi,
        "cited_epmc": r.get("citedByCount"),
        "oa_pdf": next((u.get("url") for u in free if u.get("documentStyle") == "pdf"), None),
        "oa_status": "open" if r.get("isOpenAccess") == "Y" or free else "unknown",
        "license": (r.get("license") or "").replace(" ", "-") or None,
        "landing": next((u.get("url") for u in free), None) or (f"https://doi.org/{doi}" if doi else None),
        "abstract": strip_tags(r.get("abstractText") or ""),
        "epmc": f"{r['source']}/{r['id']}" if r.get("source") and r.get("id") else None,
    }


ATOM = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}


def norm_arxiv(e: ET.Element) -> dict:
    """One entry of arXiv's Atom feed. `doi` is the DOI arXiv registers for the preprint itself; `doi_published`
    is the published version's DOI as the authors typed it, which can be wrong: look it up before using it."""

    def text(path: str) -> str:
        return " ".join((e.findtext(path, default="", namespaces=ATOM) or "").split())

    ident = re.sub(r"v\d+$", "", text("a:id").rsplit("/abs/", 1)[-1]) if "/abs/" in text("a:id") else ""
    published = text("a:published")
    return {
        **empty(),
        "title": text("a:title"),
        "year": int(published[:4]) if published[:4].isdigit() else None,
        "authors": [n for n in (" ".join((a.findtext("a:name", default="", namespaces=ATOM) or "").split()) for a in e.findall("a:author", ATOM)) if n],
        "venue": "arXiv",
        "type": "preprint",
        "doi": f"10.48550/arxiv.{ident.lower()}" if ident else None,
        "oa_pdf": f"https://arxiv.org/pdf/{ident}" if ident else None,
        "oa_status": "green" if ident else None,
        "landing": f"https://arxiv.org/abs/{ident}" if ident else None,
        "abstract": text("a:summary"),
        "arxiv": ident or None,
        "doi_published": text("x:doi").lower() or None,
    }


def merge(a: dict, b: dict) -> dict:
    """Fill a's gaps from b (same work from another database)."""
    out = dict(a)
    for k, v in b.items():
        if k == "references":
            out[k] = list(a.get(k) or []) + [r for r in v or [] if r not in (a.get(k) or [])]
        elif out.get(k) in (None, "", [], False, "unknown") and v not in (None, "", []):
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
    """The user's own key when set (own budget). No email is sent: OpenAlex ignores `mailto` since February 2026."""
    key = os.environ.get("OPENALEX_API_KEY")
    return {"api_key": key} if key else {}


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
    # The request layer spaces these (see pace_seconds), so an answer from the cache does not wait.
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


def s2_citations(doi: str, limit: int = 200) -> list[dict]:
    """The works that cite a DOI, as Semantic Scholar knows them."""
    fields = ",".join(f"citingPaper.{f}" for f in S2_FIELDS.split(","))
    data = s2_get(f"/paper/DOI:{urllib.parse.quote(doi)}/citations", {"fields": fields, "limit": max(1, min(limit, 1000))}).get("data") or []
    return [norm_s2(d["citingPaper"]) for d in data if (d.get("citingPaper") or {}).get("title")]


# --- Crossref, Europe PMC, arXiv: the databases that answer when the first two refuse --------------


def crossref_search(q: str, limit: int = 10, from_year: int | None = None) -> list[dict]:
    params: dict = {"query.bibliographic": q, "rows": max(1, min(limit, 100)), "select": CROSSREF_FIELDS}
    if from_year:
        params["filter"] = f"from-pub-date:{from_year}-01-01"
    return [norm_crossref(m) for m in (get(f"{CROSSREF}?" + urllib.parse.urlencode(params)).get("message") or {}).get("items") or []]


def crossref_work(doi: str) -> dict:
    """One raw Crossref record by DOI, or {} when Crossref does not have it (a DataCite DOI, for example)."""
    return get(f"{CROSSREF}/{urllib.parse.quote(doi.removeprefix('https://doi.org/'), safe='/')}").get("message") or {}


def crossref_doi(doi: str) -> dict | None:
    m = crossref_work(doi)
    return norm_crossref(m) if m else None


def crossref_references(doi: str) -> list[str]:
    """The DOIs a work cites, as its publisher deposited them. Often incomplete: a reference the publisher could
    not match carries no DOI and is left out."""
    return [r["DOI"].lower() for r in crossref_work(doi).get("reference") or [] if r.get("DOI")]


def epmc(path: str, params: dict) -> dict:
    return get(f"{EPMC}{path}?" + urllib.parse.urlencode({**params, "format": "json"}))


def epmc_search(q: str, limit: int = 10, from_year: int | None = None) -> list[dict]:
    query = f"({q}) AND PUB_YEAR:[{from_year} TO 3000]" if from_year else q
    data = epmc("/search", {"query": query, "resultType": "core", "pageSize": max(1, min(limit, 100))})
    return [norm_epmc(r) for r in (data.get("resultList") or {}).get("result") or []]


def epmc_record(doi: str) -> dict:
    """The raw Europe PMC record for a DOI, or {} when it has none."""
    data = epmc("/search", {"query": f'DOI:"{doi}"', "resultType": "core", "pageSize": 1})
    hits = (data.get("resultList") or {}).get("result") or []
    return hits[0] if hits else {}


def epmc_doi(doi: str) -> dict | None:
    r = epmc_record(doi)
    return norm_epmc(r) if r else None


def epmc_count(query: str) -> int:
    """How many Europe PMC records match a query in its own syntax, e.g. TITLE_ABS:"heat" AND PUB_YEAR:2024."""
    return int(epmc("/search", {"query": query, "resultType": "idlist", "pageSize": 1}).get("hitCount") or 0)


def epmc_citations(doi: str, limit: int = 200) -> list[dict]:
    """The works that cite a DOI, as Europe PMC knows them (life sciences first). They carry no abstract and no DOI."""
    r = epmc_record(doi)
    if not r.get("source") or not r.get("id"):
        return []
    data = epmc(f"/{r['source']}/{r['id']}/citations", {"page": 1, "pageSize": max(1, min(limit, 1000))})
    return [norm_epmc(c) for c in (data.get("citationList") or {}).get("citation") or []]


def _is_feed(text: str) -> bool:
    head = text.lstrip()[:600]
    return head.startswith("<?xml") and "<feed" in head and "<!DOCTYPE" not in text and "<!ENTITY" not in text


def arxiv_query(q: str) -> str:
    """An arXiv search_query from plain words: a quoted phrase stays a phrase, and everything is joined with AND."""
    terms = [t.strip("()") for t in re.findall(r'"[^"]+"|\S+', q)]
    return " AND ".join(f"all:{t}" for t in terms if t and t.upper() not in ("AND", "OR", "NOT"))


def arxiv_entries(params: dict) -> list[dict]:
    feed = get_text(f"{ARXIV}?" + urllib.parse.urlencode(params), check=_is_feed)
    entries = ET.fromstring(feed).findall("a:entry", ATOM) if feed else []
    return [w for w in (norm_arxiv(e) for e in entries) if w["arxiv"] and w["title"]]


def arxiv_search(q: str, limit: int = 10, from_year: int | None = None) -> list[dict]:
    works = arxiv_entries({"search_query": arxiv_query(q), "start": 0, "max_results": max(1, min(limit, 100)), "sortBy": "relevance"})
    return [w for w in works if not from_year or (w["year"] or 0) >= from_year]


def arxiv_doi(doi: str) -> dict | None:
    """The preprint behind an arXiv DOI (10.48550/arXiv.<id>); None for any other DOI."""
    m = re.match(r"10\.48550/arxiv\.(.+)$", doi.lower().removeprefix("https://doi.org/"))
    works = arxiv_entries({"id_list": m.group(1), "max_results": 1}) if m else []
    return works[0] if works else None


FALLBACKS = {"crossref": (crossref_search, crossref_doi), "epmc": (epmc_search, epmc_doi), "arxiv": (arxiv_search, arxiv_doi)}


def fallback_search(q: str, limit: int = 10, from_year: int | None = None, need: int = 1) -> list[dict]:
    """Search Crossref, then Europe PMC, then arXiv, until `need` of them have answered. Results come in each
    database's own order of relevance."""
    out: list[dict] = []
    answered = 0
    for name in ("crossref", "epmc", "arxiv"):
        if answered >= need:
            break
        got = ask(FALLBACKS[name][0], q, limit, from_year)
        if got is not None:
            answered += 1
            out += got
    return out


def fallback_doi(doi: str) -> dict | None:
    """One work by DOI from the fallback databases: arXiv for its own DOIs, then Crossref, then Europe PMC."""
    doi = doi.lower().removeprefix("https://doi.org/")
    for name in (("arxiv",) if doi.startswith("10.48550/arxiv.") else ()) + ("crossref", "epmc"):
        w = ask(FALLBACKS[name][1], doi)
        if w:
            return w
    return None


def works_by_doi(dois: list[str]) -> list[dict]:
    """Records for a list of DOIs: OpenAlex in batches; when it refuses, each DOI from the fallback databases."""
    try:
        return openalex_dois(dois)
    except REFUSALS:
        return [w for w in (fallback_doi(d) for d in dois if d) if w]


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

COUNTS = (("GS", "cited_scholar"), ("OA", "cited_openalex"), ("S2", "cited_s2"), ("CR", "cited_crossref"), ("EPMC", "cited_epmc"))


def most_cited(w: dict) -> int:
    """The highest citation count any database gives for a work (counts differ by database)."""
    return max(w.get(k) or 0 for _, k in COUNTS)


def cites(w: dict) -> str:
    """Citation counts per database: GS = Google Scholar (from the user's export), OA = OpenAlex, S2 = Semantic
    Scholar, CR = Crossref, EPMC = Europe PMC."""
    parts = [f"{name} {w[k]}" for name, k in COUNTS if w.get(k) is not None]
    return "cited " + " · ".join(parts) if parts else "no citation count"


def brief(w: dict, head: str = "") -> str:
    who = ", ".join(w["authors"][:2]) + (" et al." if len(w["authors"]) > 2 else "")
    if w.get("oa_pdf") or w.get("oa_status") not in (None, "closed", "unknown"):
        available = "open"
    else:
        available = "open copy unknown" if w.get("oa_status") == "unknown" else "closed"
    flag = " · RETRACTED" if w.get("retracted") else ""
    return f"- {head}{w['title']} ({w['year']}) | {who} | {cites(w)} | {evidence_kind(w)} | {available} | {w['doi'] or '-'}{flag}"


# --- The cache, from the command line --------------------------------------------------------


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("what", choices=["cache"])
    p.add_argument("--clear", action="store_true", help="remove every cached answer")
    a = p.parse_args()
    if LAYER.cache_dir is None:
        print("The cache is off (POIESIS_RESEARCH_CACHE=off).")
        return 0
    # Only what this layer wrote counts as the cache: answers named by their hash, and its budget and pacing
    # files. Anything else in the folder is someone else's and is never removed.
    present = [f for f in LAYER.cache_dir.rglob("*") if f.is_file()] if LAYER.cache_dir.is_dir() else []
    answers = [f for f in present if f.parent.parent == LAYER.cache_dir and re.fullmatch(r"[0-9a-f]{64}\.json", f.name)]
    state = [f for f in present if f.parent.parent == LAYER.cache_dir
             and ((f.parent.name == "budget" and f.name.endswith((".key.json", ".nokey.json"))) or (f.parent.name == "pace" and f.suffix == ".lock"))]
    others = len(present) - len(answers) - len(state)
    size = sum(f.stat().st_size for f in answers)
    print(f"Cache: {LAYER.cache_dir} · {len(answers)} answers · {size / 1e6:.1f} MB · an answer is used for {LAYER.max_age / 3600:g} hours")
    print("Change the folder with POIESIS_RESEARCH_CACHE=<folder>, or turn the cache off with POIESIS_RESEARCH_CACHE=off.")
    if a.clear:
        for f in answers + state:
            f.unlink(missing_ok=True)
        for folder in sorted({f.parent for f in answers + state}):
            with contextlib.suppress(OSError):
                folder.rmdir()  # only when nothing else is in it
        print(f"Cleared {len(answers)} answer{'' if len(answers) == 1 else 's'}."
              + (f" {others} other file{'' if others == 1 else 's'} in the folder {'was' if others == 1 else 'were'} left alone." if others else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
