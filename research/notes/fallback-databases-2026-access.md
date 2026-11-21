# Crossref, Europe PMC, arXiv and Semantic Scholar: access rules and requests observed (read 2026-11-21)

- **Source:** each service's own documentation, and keyless requests to each API:
  https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/,
  https://info.arxiv.org/help/api/tou.html, https://info.arxiv.org/help/api/user-manual.html,
  https://www.semanticscholar.org/product/api
- **File:** none (documentation changes; every statement below carries the date read)
- **Licence:** not applicable.
- **Evidence:** documentation (D) and observation (O) · read and run on 2026-11-21, with no key and no email.
- **Read:** Crossref "Access and authentication" in full. arXiv API Terms of Use, the section "Rate limits", and
  the lines of the User's Manual on `search_query`, `id_list`, `max_results` and `sortBy`. Semantic Scholar's API
  product page, the paragraphs on rate limits. Europe PMC's "Developer resources" page and the list of modules
  on its "Articles RESTful API" page, both read in a browser: they answer automated requests with a challenge
  page (HTTP 403). Europe PMC's search syntax guide was not read.

## What it says

### Crossref (D, O)
- No sign-up is needed. Without an email address a request is in the public pool: 5 DOI lookups a second and 1
  query a second, one request at a time. The "polite" pool, which is faster, needs an email address.
- Going over the limit returns 429; a manual block returns 403.
- The page asks clients to cache answers and not to repeat requests.
- Observed: a DOI lookup answered with `x-rate-limit-limit: 5`, `x-rate-limit-interval: 1s`,
  `x-concurrency-limit: 1` and `x-api-pool: public-single`; a query answered with a limit of 1 and
  `public-array`.
- Observed: seven DOI lookups returned the registered title, authors, year, journal and citation count. Two of the
  seven carried an abstract; none said whether an open copy exists.

### arXiv (D, O)
- No more than one request every three seconds, on a single connection ("Rate limits").
- A query returns an Atom feed; `max_results` is at most 2,000 per request (User's Manual).
- Observed: the record of one paper carried the published version's DOI with its last digit missing. That DOI is
  typed by the authors.

### Semantic Scholar (D, O)
- Without a key, requests share 1,000 requests a second among all unauthenticated users and can be throttled
  further. A key starts at 1 request a second on every endpoint.
- Observed: four keyless requests answered 200 on 2026-11-21, among them `/paper/DOI:…/citations` with
  `citingPaper.` fields. The lab plan records 429 answers earlier the same day. For one closed paper the abstract
  was withheld by the publisher.

### Europe PMC (D, O)
- The two pages read state no rate limit. They say the RESTful API gives access to open-access content and to
  metadata, and that automated bulk download of other content is not permitted.
- The API has modules this plugin does not use yet, among them `fields` (the list of search fields) and
  `profile` (hit counts by publication type and source).
- Observed: the REST API answered every request: a search by `DOI:"…"`, a free-text search, a count with
  `TITLE_ABS:"…" AND PUB_YEAR:2024` and `resultType=idlist`, and the `citations` and `references` of one record,
  the first with `pageSize=1000`.
- Observed: a record says whether it is open access and lists full-text links. A citing work carries a title,
  authors, a year and a citation count, and no DOI or abstract.
- Observed: the recorded run of 2026-11-17 spaced its requests 0.35 seconds apart and was not refused.

## What it means for the plugin
- Pacing per host in `scholarly.py`: arXiv 3.1 seconds, Crossref 1.05 seconds for a query and 0.25 for a DOI
  lookup, Semantic Scholar 1.1 seconds without a key and 1.05 with one. Europe PMC's 0.35 seconds comes from the
  recorded run, not from documentation.
- One request at a time per host, across processes, because Crossref and arXiv ask for a single connection and
  several scouts can run at once.
- No email is sent, so Crossref is used through its public pool.
- When OpenAlex or Semantic Scholar refuses, Crossref answers first (the widest registry), then Europe PMC (life
  sciences first, with open-access links), then arXiv (preprints in its own fields, no citation counts).
- A record from Crossref shows "open copy unknown", never "closed": Crossref does not know.
- arXiv's typed DOI is kept apart from the DOI arXiv registers for the preprint, and is looked up before use.
- Europe PMC states no rate limit on the pages read; the plugin keeps the spacing of the recorded run.
