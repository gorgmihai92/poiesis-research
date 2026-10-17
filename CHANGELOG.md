# Changelog

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
