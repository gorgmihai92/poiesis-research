# Seven sources for signals: access rules and requests observed (read 2026-11-21)

- **Source:** each service's own documentation, and keyless requests to each API: https://api.reporter.nih.gov,
  https://graph.openaire.eu/docs/apis/graph-api/, https://hn.algolia.com/api,
  https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/access-policy.html,
  https://huggingface.co/docs/hub/rate-limits, https://info.arxiv.org/help/api/user-manual.html
- **File:** none (documentation changes; every statement below carries the date read)
- **Licence:** OpenAIRE records are CC BY, with OpenAIRE named as the source; Wikimedia's analytics data is CC0.
  The others state no licence on the pages read.
- **Evidence:** documentation (D) and observation (O) · read and run on 2026-11-21, with no key and no email.
- **Read:** NIH RePORTER API page: the section "Constraints/Limitations" and the search parameters. OpenAIRE:
  "Graph API", "Filtering search results" (the research-product parameters) and "Terms of use" in full. Hacker
  News Search API page in full, in a browser. Wikimedia Analytics API "Access policy" in full, and the lines of
  the Foundation's User-Agent policy on contact information. Hugging Face "Hub Rate limits": the headers and the
  table of tiers. arXiv User's Manual: the paragraph on `submittedDate`. Not read: each service's full reference.

## What it says

### NIH RePORTER (D, O)
- It recommends no more than one request a second, and large jobs at weekends or between 9 pm and 5 am Eastern
  time.
- A project search is a POST with criteria; `advanced_text_search` looks in the title, terms and abstract;
  `fiscal_years` selects years; `limit` is at most 500.
- Observed: the phrase "brain-computer interface" returned 137 projects for fiscal years 2025 and 2026, each
  with a title, a start date, an award amount, an organisation and a link. The response carried
  `x-rate-limit-remaining: 199`.

### OpenAIRE Graph (D, O)
- Without a token: up to 60 requests an hour. With one: up to 7,200.
- `/graph/v2/researchProducts` takes `search`, `type`, `fromPublicationDate`, `toPublicationDate` and `sortBy`.
- Observed: the same phrase returned 1,307 publications from 2026 on and 231 funded projects, the projects with
  funder, start date and amount. Sorted by date, the first publication was dated 2030: the window needs an end
  date. The keyless response carried `x-ratelimit-limit: 7199`, which does not match the documented 60.

### Hacker News, through Algolia (D, O)
- `search` sorts by relevance, then points, then comments; `search_by_date` puts the most recent first.
  `numericFilters` takes `created_at_i`, `points` and `num_comments`. The limit is 10,000 requests an hour from
  one address.
- Observed: 302 stories for the phrase, 14 of them in the six months to 2026-11-21, each with points, comments,
  a date and a link.

### Wikimedia pageviews (D, O)
- Every request needs a User-Agent header; it can carry a page on a Wikimedia wiki, a website or an email
  address. The Foundation's policy says scripts should send contact information or may be blocked without notice.
- Requests are to be sent one after another, each when the last has finished.
- Observed: monthly views of one English Wikipedia article for 24 months, with this plugin's User-Agent, which
  names the client and carries no contact.

### Hugging Face Hub (D, O)
- An anonymous address gets 500 API requests per five-minute window; going over returns 429. The page gives
  these numbers as of September 2025 and says they can change.
- Observed: the response carried `ratelimit: "api";r=499;t=72`. The model search matched the words in a
  repository's name: the phrase "brain-computer interface" returned no model, and "EEG" returned 100, the most a
  page holds.

### arXiv and Europe PMC, by date (D, O)
- arXiv has one date filter, `submittedDate:[YYYYMMDDTTTT TO YYYYMMDDTTTT]`, in GMT (User's Manual).
- Observed: arXiv returned 157 preprints for the phrase in the six months to 2026-11-21. Europe PMC answered
  `SRC:PPR` (preprints), `FIRST_PDATE:[from TO to]` and `sort=P_PDATE_D desc`: 48 preprints in the same window.

### Sources that did not answer (O, from the lab plan)
- On 2026-11-21 the lab plan's own probes got an anti-bot page from DBLP and 429 from GDELT. Patents were not
  probed: they wait for a key. None of the three is used here.

## What it means for the plugin
- `signals.py` asks these seven sources through the same request layer as the other scripts: answers are cached
  for a day, requests are spaced per host, and the Coverage line names who answered.
- Pacing: NIH RePORTER and OpenAIRE 1.05 seconds, Hacker News 0.5, Hugging Face 0.7, Wikimedia one at a time. A
  scan asks OpenAIRE twice, so about thirty scans an hour would reach its documented limit.
- Hugging Face needs its own short word (`--hf`), because it reads names and not descriptions; a count of 100 is
  reported as "100 or more".
- The window has an end date as well as a start date, because sources hold records dated in the future.
- No contact goes into the User-Agent. Wikimedia asks for one: whether this plugin's public address may be sent
  is the owner's decision, and until then a block by Wikimedia is possible and would show in the Coverage line.
- Each source's own limit is printed with its numbers: one funder, one forum, one article, names only.
