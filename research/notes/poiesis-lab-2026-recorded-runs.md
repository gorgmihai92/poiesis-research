# Two recorded runs of the Poiesis plugins (observations, 2026-11-17 and 2026-11-21)

- **Source:** the Poiesis Lab notebook, a private repository: `fixtures/trend-scan/`, `fixtures/README.md` and
  `lab/plan.md`. The files are not in this repository.
- **File:** none here.
- **Licence:** the owner's own data.
- **Evidence:** observation (O) · two runs of the plugins on 2026-11-17, recorded as files, and the lab plan's
  account of them, written on 2026-11-21.
- **Read:** observation: `fixtures/README.md` and `lab/plan.md` in full; `fixtures/trend-scan/openalex.json` and
  the first row of the two challenge files by script, on 2026-11-21. The numbers below marked "recomputed" were
  computed again from `openalex.json` on that day. The agents' raw reports were not saved, so they were not read.

## What it says

### Counting
- The run counted yearly OpenAlex works for five areas, fetched on 2026-11-17 with no API key
  (`openalex.json`, field `fetched`).
- From 2024 to 2025 the count of all works rose 29.3%, the count of articles, reviews and preprints rose 17.9%,
  and the count of all other records rose 46.8% (recomputed).
- For solid-state batteries, the share of all works fell 3.6% from 2024 to 2025, while the share among articles,
  reviews and preprints rose 6.7% (recomputed). The fall came from the base, not from the field.
- The first pass used three requests per area and a base of all works; a second pass counted the same three
  types above and below the line (`fixtures/scripts/fetch.py`, `fetch_typed.py`).
- 2026 was a partial year in the data and was left out of the analysis (`fixtures/scripts/analyze.py`).

### Requests
- The keyless OpenAlex budget ran out twice, and Semantic Scholar answered 429 (`lab/plan.md`, the table for
  poiesis-research 2.4.0).
- One script lost its results because it saved them only at the end (the brief for this version; the script's
  output was not kept).

### Agents' reports
- The agents' word limits were exceeded at every run, and their prose was retyped by hand (`lab/plan.md`).
- One verdict drifted in the retyping: the published file says `kept` for conclusion `c6`, and the challenger's
  verdict was `weakened` (`fixtures/README.md`; both files read).

### One more observation, 2026-11-21
- The arXiv record of Beel, Kan & Baumgart 2025 gives the paper's DOI with the last digit missing; the DOI
  registry has the full one. A DOI copied from a database record is not yet a verified DOI.

## What it means for the plugin
- A share counts the same document types above and below the line, and the series says which. This is the rule
  in `playbooks/trends.md`, and `counts.py` computes shares only that way.
- A partial year is marked in the series, not silently included.
- Every response is saved to disk as it arrives, and a script that stops says what it has. Nothing waits for the
  end of a run.
- The scouts return one row per source in fixed columns, so nothing is retyped from prose, and each row says how
  its DOI was verified.
- Two runs by one person on one machine: they show what went wrong, not how often it would.
