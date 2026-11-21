# OpenAlex API: documentation and requests observed (read 2026-11-21)

- **Source:** OpenAlex help pages, https://help.openalex.org (the Markdown copy of each page), and keyless requests
  to `api.openalex.org`
- **File:** none (documentation changes; every statement below carries the date read)
- **Licence:** the documentation says every OpenAlex record is CC0 ("Pricing").
- **Evidence:** documentation (D) and observation (O) · read and run on 2026-11-21, with no API key.
- **Read:** documentation, on 2026-11-21. In full: Pricing, Example costs, Authentication, Error handling, Group, Page through results, Work
  types, Topics, Expansion corpus, Tracking trends over time, Counting, Deprecations. In part: Searching and
  Filter (the lines on search fields, Boolean operators and the OR limit; in Searching also the sections "Text
  processing", "Exact (unstemmed) search" and "Phrase matching").

## What it says

### Budget and cost (D)
- Without a key, requests share one free budget of $0.10 a day with everyone on the same IP address. A free key
  has its own $1 a day. The budget resets at midnight UTC ("Pricing", "Example costs").
- Looking up one record by ID or DOI is free. A list with filters costs $0.0001. A search costs $0.001, and so
  does any request with a `.search` filter. A `group_by` costs what its query costs: $0.0001 on a list, $0.001 on
  a search ("Example costs", "Group").
- An error response costs nothing ("Error handling").
- Since February 2026 the `mailto` parameter is ignored; keys replaced the "polite pool" ("Deprecations").

### What a response says about the budget (D, O)
- Documented headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Credits-Used`,
  `X-RateLimit-Reset`, the last in seconds until midnight UTC ("Authentication").
- Observed on a keyless `group_by` request at 20:22 UTC: `x-ratelimit-limit-usd: 0.1`,
  `x-ratelimit-remaining-usd: 0.0963`, `x-ratelimit-cost-usd: 0.0001`, `x-ratelimit-reset: 13036`, which is the
  number of seconds to midnight UTC. The body's `meta` repeated the cost as `cost_usd`.
- Observed on seven DOI lookups: `x-ratelimit-cost-usd: 0`, and the remaining budget did not move.

### Limits (D)
- Requests per second: 10 without a key, 30 with a free key. Searches with more than 5 `AND`, `OR` or `NOT`: 1 a
  second without a key, 2 with a free key. Filters with more than 10 topic ids joined by `|`: 1 a second
  ("Authentication").
- A `429` body carries a `reason`. `daily_budget` means the day's budget is spent; the others are per-second
  limits, cost nothing and say how long to wait ("Error handling").
- At most 100 values joined by `|` in one filter, 100 results per page, and 10,000 results by page number.
  `per_page=200` is accepted as legacy behaviour and is deprecated ("Authentication", "Page through results").

### Grouping and paging (D)
- A grouped response returns at most 200 groups per page. More groups need cursor paging: `cursor=*`, then
  `meta.next_cursor` until it is null ("Group").
- Cursor paging past the first page needs a key: without one, following `next_cursor` returns a 401 ("Page
  through results").
- `group_by` takes up to three fields separated by commas; each group then carries its own `groups`. Cursor paging
  does not work with more than one field ("Group").
- `meta.count` is the number of works matching the filter; `meta.groups_count` counts only the groups on the
  current page ("Group").

### Document types (D)
- Every work has one type from a fixed vocabulary of 25, among them `article`, `review`, `preprint`, `dataset`
  and `conference-paper` ("Work types").
- The vocabulary changes: `study-registration` was added on 7 November 2026 and works are being retyped; five
  types, among them `conference-paper`, are being rolled out ("Work types").
- Each type is either traditional or not; `is_traditional:true` keeps the traditional ones ("Work types").

### Topics (D)
- 4 domains, 26 fields, 252 subfields and 4,516 topics. A work gets up to three topics; the most likely is its
  primary topic. About 10% of works have none ("Topics").
- The classifier that assigns topics was replaced in October 2026. The list of topics stayed; the assignments to
  works changed. In November 2026, 56 topics were renamed and 972 moved to another subfield ("Topics").
- For counts by topic the documentation says to filter to publication types, because datasets and catalogue
  records also get topics and a few large families of them dominate some topics ("Topics").

### Two corpora (D)
- A works query covers the core corpus only. About 122 million more works, mostly datasets and repository
  records, sit in an expansion corpus added in November 2025 and are returned only with `corpus=all` ("Expansion
  corpus").

### Search and years (D, O)
- A works `search` matches titles, abstracts, full text and keywords. Words are stemmed, so a plural also finds
  its singular, and stop words are removed. A search without stemming is a separate form, `search.exact`; most
  search filters have a `.search.exact` form too. Searches scoped to title and abstract are separate as well
  ("Searching": "Text processing", "Exact (unstemmed) search").
- Double quotes search for a phrase. One case is set apart: in title and abstract searches, stop words count
  inside a short quoted phrase (four words or fewer besides the stop words), and such a phrase is matched as
  typed, without stemming ("Searching": "Phrase matching").
- Observed by the lab's review on 2026-11-21: in `title_and_abstract.search` the quoted phrases "solid-state
  battery" and "solid-state batteries", and the two joined by OR, gave the same counts (1,446 works in 2024, 1,996
  in 2025).
- Observed on 2026-11-21 at 22:00 UTC, in the same field, counting articles, reviews and preprints: "heat pump"
  and "heat pumps", both quoted, gave the same counts (2,571 in 2024, 2,998 in 2025). "theory of mind" gave 688
  and 1,096; "theories of mind" gave 19 and 40.
- The documentation and the observations agree. Quotes keep the words together and do not turn stemming off; a
  short quoted phrase that holds a stop word is the exception and is matched as typed. Tried: two phrases with no
  stop word and one with a stop word. Not tried: longer phrases, the `.exact` forms, other fields.
- The current year is still filling in, so its count is partial ("Tracking trends over time").

## What it means for the plugin
- The request layer reads the remaining budget from the response headers and names it in the Coverage line. It
  stops with what it has saved when the budget is spent, and it no longer sends `mailto`.
- `counts.py` asks for one grouped request per series, by year and type, so the same types can be counted above
  and below the line. It records the types, the search field, the corpus and the date in the series' metadata.
- A series for a quoted phrase counts its plural too, unless the phrase holds a stop word: then it counts the
  phrase as typed, and another form of it is another series. The metadata's `search_field` says so.
- The taxonomy mode pages through `group_by=primary_topic.id`. Without a key it gets one page and says so.
- A series fetched before October 2026 and one fetched after are not comparable by topic, and type counts move
  while works are being retyped. The series carries its date so nobody compares across them unknowingly.

## Quotes
- "Without a key you get $0.10/day" ("Example costs")
- "The current year is still filling in, so its count is partial." ("Tracking trends over time")
- "Those words are then matched as typed, without stemming." ("Searching")
