# DOAJ, OSF Preprints, Zenodo and CORE: access rules and requests observed (read 2026-11-22)

- **Source:** each service's own API documentation, and keyless requests to each API:
  https://doaj.org/api/v4/docs, https://developer.osf.io/ (and its `swagger.json`), https://developers.zenodo.org/,
  https://help.zenodo.org/guides/search/, https://api.core.ac.uk/docs/v3 (and https://api.core.ac.uk/swagger/v3.json),
  https://core.ac.uk/services/api, https://core.ac.uk/terms
- **File:** none (documentation changes; every statement below carries the date read)
- **Licence:** DOAJ article metadata is CC0. Zenodo states CC0 for the metadata of deposits. OSF states no licence
  on the pages read. CORE does not claim ownership of the metadata it harvests (see below).
- **Evidence:** documentation (D), observation (O) and product decision (P) · read and run on 2026-11-22, with no
  key and no email. The lab session's first requests of the same day are marked as such.
- **Read:** documentation, on 2026-11-22, with curl, by a helper that read and quoted the pages. DOAJ: the v4 API
  page in full, its Swagger file (search routes only) and the public data dump page. OSF: the Swagger file behind
  developer.osf.io, the sections Authentication, Pagination, Versioning, Filtering and Errors, and the paths for
  preprints and preprint providers; OSF's terms of use did not load (a script-only page). Zenodo: the developer
  page (Records, Rate limiting, status codes, the licence note) and the search guide in full. CORE: the v3 page's
  rate-limit table, field tables and query language, the OpenAPI file, the services page in full and the terms
  page, searched for metadata and licence. Not read: any service's full reference beyond these parts.

## What it says

### DOAJ (D, O)
- Base `https://doaj.org/api/`, version 4.0.0. Article search: `GET /api/search/articles/{search_query}`.
- The query is Elasticsearch query string, "The default query operator is AND." Fields use dot notation
  (`bibjson.title`), with short names `title`, `doi`, `issn`, `publisher`, `abstract`. Wildcards, regular
  expressions, fuzzy and proximity searches are disabled.
- `pageSize` defaults to 10, at most 50. The deepest result reachable by paging is not stated.
- "a rate limit of two requests per second on all API routes"; up to five requests are queued as bursts. What a
  refusal looks like is not stated.
- Keys are for publishers who deposit data; the search routes take none.
- Article metadata: "waived via CC0 1.0 Universal". Site content is CC BY-SA 4.0.
- No year field and no `total` are described on the pages read.
- Observed: an answer holds `total`, `page`, `pageSize` and `results[].bibjson`, whose `year` is a string.
- Observed: `"design anthropology"` matched 37 articles (the lab session, then again). One of them matched on its
  keywords alone; its title and abstract are in Italian.
- Observed: without quotes, `design anthropology` matched 959 articles, and the three returned came in ascending
  order of their DOAJ id, not by relevance. One sort order was seen, in one answer.
- Observed, the yearly count: `"design anthropology" AND bibjson.year:2023` gave 0, `…:2024` gave 4, and the range
  `[2023 TO 2024]` gave 4: the years add up to the range. `bibjson.year:2020` alone gave 889,270, so the total is
  not cut at 10,000.
- Observed: one record's full-text link pointed to a private network address (192.168.…). Links are the
  publisher's, as deposited.

### OSF Preprints (D, O)
- `GET https://api.osf.io/v2/preprints/` lists the preprints of every server on OSF (SocArXiv, PsyArXiv and the
  others); `/v2/providers/preprints/` lists the servers. There is no search endpoint in the API.
- "Preprints may be filtered by their `id`, `is_published`, `date_created`, `date_modified`, and `provider`."
  `title` is not on that list. "String queries are filtered using substring matching."
- Each list returns 10 by default; no maximum page size is stated for preprints. Since version 2.3 a top-level
  `meta` holds the total.
- "Unauthenticated requests have a rate limit of 100/hour"; with a token, 10,000 a day. A refusal is 429 with
  `Retry-After`. A token travels as `Authorization: Bearer <token>`.
- The licence of the metadata is not stated on the pages read.
- Observed: `filter[title]=anthropology` answered with 43 preprints (lab session, then again), the total under
  `links.meta.total`, not `meta.total`. `filter[title][icontains]=anthropology` gave the same 43 and the same first
  two, so the plain filter did not depend on case here. `filter[title]=design anthropology` gave none.
- Observed: a record holds the title, the abstract (`description`), `date_published`, the published version's DOI
  (`doi`, empty in the two seen), the preprint's own DOI under `links.preprint_doi`, the page under `links.html`
  and the server under `relationships.provider`. Authors are not in the list answer.
- Not checked: whether 43 is every preprint whose title holds "anthropology"; no other listing was compared.

### Zenodo (D, O)
- `GET https://zenodo.org/api/records` with `q`, `size`, `page`, `sort`, `type`, `communities`, `all_versions`.
- `q` is Elasticsearch query string. The search guide: a query of two words matches records with either term in
  any field; `+a +b` or `a AND b` asks for both; phrases in double quotes; `title:`, `publication_date:[2017-01-01
  TO 2018-01-01]` (capital TO); words are stemmed.
- `size`: "Maximum 25 for anonymous requests, 100 for authenticated requests." The deepest reachable result is
  not stated. For bulk use the page recommends OAI-PMH or the metadata dumps.
- Guests: 60 requests a minute and 2,000 an hour; "Search REST API endpoints 30 requests per minute". Headers
  `X-RateLimit-Limit`, `-Remaining`, `-Reset`; a refusal is 429.
- The page asks for a descriptive User-Agent with a contact address and warns that generic User-Agents sending
  many requests may be limited. The plugin sends no email (P), so this applies to it.
- Metadata of deposits is CC0, on the developer page; whether that covers the search answer is not stated.
- Observed: `"design anthropology"` matched 17 records. The first two did not hold the phrase in their title or
  description: it was in their keywords. Every record looked at held the phrase somewhere in its metadata.
- Observed, the yearly count: `"design anthropology" AND publication_date:[2023-01-01 TO 2023-12-31]` gave 2,
  2024 gave 2, the two years together 4. `publication_date:[2020-01-01 TO 2020-12-31]` alone gave 272,284: not
  cut at 10,000. A record called "DEPRECATED", restricted, was among them: counts include such records.
- Observed: `hits.total` is a number; a record holds a DOI (sometimes the publisher's, for a copy of a published
  work), `access_right`, `license.id`, `resource_type` and `links.self_html`.

### CORE (D, O)
- `GET` or `POST https://api.core.ac.uk/v3/search/works` with `q`, `offset`, `limit`, `stats`. The answer has
  `totalHits` and `results`. The maximum `limit` is not stated.
- Query language: AND, `+` or a space for AND; OR; brackets; `field:value`; ranges `yearPublished>=2015`;
  `_exists_:field`. Searchable fields named include `title`, `abstract`, `fullText`, `authors`, `yearPublished`.
- Rate limits in tokens (a simple query costs 1): unauthenticated 100 a day and at most 10 a minute; a registered
  personal user 1,000 a day and 25 a minute; academic users of non-member institutions 5,000 a day and 10 a
  minute. Headers `X-RateLimit-Limit`, `-Remaining`, `-Retry-After`. The services page says instead "One batch
  request or five single requests per 10 seconds": the two pages disagree, and this was not resolved.
- A key travels as `Authorization: Bearer <key>` (preferred) or as `api_key`. The services page says the API is
  free and needs no registration within its limits; "Full-text is not available for unauthenticated API users."
- Terms: CORE "does not claim ownership of any individual metadata record"; rights stay with the rightsholders;
  CORE is reviewing its licensing and may move factual metadata to CC0 or ODC-0. Using the API needs a licence,
  free for many users.
- A per-year count is documented two ways: `yearPublished` with `totalHits`, or `POST /v3/search/works/aggregate`
  with `"aggregations": ["yearPublished"]`. Whether either total is exact past 10,000 is not stated.
- Observed (lab session): a keyless free-text query answered HTTP 500 with "abstract is not a searchable field",
  and `/v3/search/works/?q=…` without the trailing slash redirected to the address with it.
- Observed: a keyless `title:"design anthropology"` with `limit=1` answered 200, the first work titled "Design
  Anthropology", and `totalHits` 2,683,661. That many works cannot all hold the phrase in their title, so the
  total was not a count of the phrase. Why was not found.

## What it means for the plugin
- Pacing per host in `scholarly.py` (P, from the limits above): DOAJ 0.55 seconds, Zenodo 2.1 (the search limit),
  OSF 36.5 (100 an hour), CORE 6.1 (the lowest per-minute limit of the tiers a free key can have).
- `search.py --db doaj|osf|zenodo|core`; `--db all` asks DOAJ, Zenodo and CORE, and OSF only when named, because
  it matches titles only and is paced 36.5 seconds (P). They are searched by query only; a DOI is looked up in the
  other five databases (P).
- The four were added for the owner's work in philosophy and design anthropology (P). How much of those fields
  each one covers was not measured.
- DOAJ is asked as typed (its default is AND). Zenodo's words are joined with AND before asking, so that both
  behave like the other databases (P). Phrases belong in double quotes in both.
- OSF is asked with `filter[title]`, which matches the query as one string in titles only, observed and not on
  the documented list of filters. A subject named only in abstracts is not found there (O, P).
- CORE is asked with CORE's documented default, free text, which answered 500 without a key; with a key it
  was not tried, so a 500 is asked again once only (P). The address ends in a slash, where the one without it
  redirected (lab session).
- CORE is asked only with `CORE_API_KEY` set; without it the Coverage line says "CORE refused (not asked: no key,
  …)" (P, set by the owner on 2026-11-22). The keyless request above shows that CORE can answer without a key
  within 100 tokens a day; that was not chosen. CORE with a key was not tried: no key was available.
- Yearly counts in `counts.py --db doaj` and `--db zenodo`: documented syntax, and the probe's years added up to
  the range, with no cut at 10,000. One phrase and one pair of years were tried, so this is what was seen, not a
  guarantee (O). OSF has no yearly count: its title filter is not documented, and no date filter for the
  publication date is. CORE has none: its total for a quoted title phrase was not a phrase count (O).
- A DOAJ record shows "open" (every DOAJ journal is open access). A Zenodo record shows "open" only when its
  `access_right` is open. A CORE record shows "open" when CORE has a download link, else "open copy unknown".
