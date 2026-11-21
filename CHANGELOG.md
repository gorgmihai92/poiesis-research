# Changelog

## 2.4.0
Everything is added: no path or field of 2.3.3 was renamed or removed, and a script that got its answers before
gets the same ones, followed by a Coverage line. One request parameter is no longer sent (see "Removed").
- **Requests.** Every script that asks a database goes through one layer in `scholarly.py`: answers are cached on
  disk as they arrive (a day, in `~/.cache/poiesis-research/`; `--fresh` asks again), requests to one host are
  spaced as its documentation asks, and the OpenAlex budget is read from the response headers, so a spent budget
  stops before the next paid request. Crossref, Europe PMC and arXiv answer when OpenAlex or Semantic Scholar
  refuses. Each script ends with a **Coverage** line naming the databases that answered and the ones that refused
  (on stderr with `--json`). `search.py` takes `--db crossref|epmc|arxiv|all`.
- **Counts.** `counts.py` and `playbooks/trends.md`: yearly counts for a search, within a base search, for a topic
  or for the whole OpenAlex topic taxonomy, with the same document types above and below the line of every share
  and the unfinished year marked. Saved in `research/data/` as CSV with a metadata file: query, database, date,
  types, script. `--db epmc` counts in Europe PMC. `--record` and `--replay` save and replay answers. Without a
  key the taxonomy scan stops at 200 topics and says so. It reports counts and shares; it does not judge trends.
- **Evidence table.** `playbooks/evidence.md` asks for one row per study: population, what was varied, the
  comparison, what was measured, the setting, how it was verified and how much was read. Saved in
  `research/maps/` from `templates/evidence-map.md`.
- **Quotes and references.** `verify_quotes.py` looks for every quote of a note in the source's extracted text, on
  the page given, and with `--references` lists a report's references that have no note.
- **Signals.** `signals.py`, `playbooks/signals.md`, `templates/signal.md` and the `signal-scout` agent: what
  arXiv, Europe PMC, NIH RePORTER, OpenAIRE, Hacker News, Wikimedia pageviews and Hugging Face show about a
  subject in a recent window. A signal note holds the observation only, with an id (`SG-001`), in
  `research/signals/`.
- **Prior art.** `playbooks/prior-art.md`: before anything is called new, the nearest existing works and what
  differs.
- **Agents.** `paper-scout` and `evidence-scout` return one row per source in fixed columns (citation, DOI, how it
  was verified, how much was read, what it says, open copy) and a short summary; the 400-word limit is gone. They
  read the project's bibliography first and give the DOI, never the address of a copy.
- **Texere.** In a vault with `Support/Texere/Bibliography/bibliography.json` the skill reads it as the index of
  the library (`library.py`), cites as `[@key, p. N]`, and never writes in Texere's folders.
- **Notes.** A **Read** line says how much of a source was read. Eleven new notes in `research/notes`.
- **Removed:** the `mailto` parameter is no longer sent. OpenAlex ignores it since February 2026, and no email
  address goes into any request.
- **Not checked in this version:** requests with an OpenAlex or Semantic Scholar key (none was available), the
  taxonomy scan past 200 topics, and a real Texere bibliography (the reader was tested on one built from its
  description).
- Tests in `tests/`, run with `python3 -I -m unittest discover -s tests`; eval cases in the plugin's `evals/`.

## 2.3.3
- Suggestions of another Poiesis plugin, from the skill or its agents, give the plugin's link and name the skill or
  agent to use.

## 2.3.2
- Starts from any question, claim, proposal or document; asks for `research.config.md` only when saving notes
  or for funding.
- "Files": the paths and fields shared with the other Poiesis plugins, as a contract (changed only in a major
  version), in the skill and the README; other plugins' files are read tolerantly.

## 2.3.1
- Depth is set with a `Depth:` line in the project's `CLAUDE.md`, so it works without poiesis-research.

## 2.3.0
- Evidence: every claim is also searched against (replications, failures, critiques, the opposite claim); the
  report lists what was searched and the evidence against.
- `citing.py`: the later works that cite a study (forward snowballing), with replications, failures and critiques
  flagged first; used on the studies a verdict rests on and on founding works the user keeps. Notes get "Later work".
- `independence.py`: groups studies that share authors; verdicts count independent groups, not papers.
- Rules for non-academic sources: find out who is behind them first (lateral reading).
- Two new research notes: Nickerson 1998, Wineburg & McGrew 2019.
- Depth: quick, standard (default) or thorough, per request or `Depth:` in `research.config.md`. A few rules hold
  at every depth; the rest are defaults, skippable if the report says why. Every report ends with "Not checked".
  Rules limit what is reported as true, never what may be explored.
- Answers short and direct, the answer first; agents only for independent parallel parts or the thorough check;
  each agent has a word limit.
- "Other Poiesis plugins": when another one would change the result, Claude suggests it once and installs it only
  if the user agrees.
- README: the four toolkits, their roles, agents, what each reads and leaves, and how they connect.

## 2.2.1
- `verify_citations.py` keeps parentheses inside DOIs (e.g. `S0016-3287(98)00086-X`).

## 2.2.0
- Each rule names its source; one note per source in `research/notes`.
- `verify_citations.py`: every DOI in the notes must exist and match its title; a step of "Add".
- Quality rule: the kind of evidence as a starting point, then up or down by each source's own quality.
- Better evidence-kind guess: narrative reviews, results given as percentages or counts.
- `OPENALEX_API_KEY` support; a clear stop when a free daily budget is used up; a warning when the founding-works
  seeds drift to another field.

## 2.1.1
- Rate limits: requests wait as the server asks; `search.py` keeps going when OpenAlex is unavailable.

## 2.1.0
- One entry skill with three playbooks: literature, evidence, funding; shared rules.
- Funding: `funding.py` for open and upcoming EU calls (grant per project, deadline, link); Romanian official sites
  in the playbook; `funding-scout` agent; call template and applicant section in the project config.

## 2.0.0
- Renamed to Poiesis Research (`poiesis-research`; the skill is `research`); three steps: find, add, use.

## 1.x
- Literature search in OpenAlex and Semantic Scholar, founding works by co-citation, Google Scholar import, open
  copies, PDF text with page markers, source notes; `paper-scout` and `evidence-scout` agents.
