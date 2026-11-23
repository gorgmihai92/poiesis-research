# Changelog

## 2.6.1
Fixes found by the audit of 2026-11-23 and by the review of this version. No path or field was renamed or removed.
- **What is read where.** A note's own DOI is the first one on its **Source** line (with the indented lines that
  continue it), in all three scripts that read notes: `verify_citations.py` checks it, `library.py` lists it and
  answers `--has` with it, and `verify_quotes.py --references` counts it as held. A DOI elsewhere in a note, such
  as one under "Later work", is another work's and is not read. Before, `verify_citations.py` and `library.py` took
  the first `doi.org/` DOI anywhere in the note and `--references` counted every one; a note with no Source line
  now has NO DOI. In a report, `--references` still reads every DOI on every line, so an evidence map's DOI cells
  are references.
- **One DOI pattern and one trim,** copied the same into the three scripts, so they read the same DOI from the same
  text. A DOI is read after `doi.org/` or a publisher's `/doi/` (`…/doi/10.…`, `…/doi/full/10.…`), or bare where
  it starts a word: at a line's start, or after a space, a bracket, a quotation mark, a colon (`doi:`, `arXiv:`),
  a comma, a table's bar, a `·` or bold marks. The templates ask for the DOI itself (`<DOI or URL>`,
  `<10.xxxx/…>`), and before only the forms after `doi.org/` or `doi:` were read: a bare DOI was NO DOI and passed.
  A DOI ends at a space, `<`, `>`, a square bracket, a quotation mark, a comma, `;`, `|` or `·`; then points,
  commas, colons, `*`, `_`, closing quotation marks and unbalanced closing parentheses are dropped from its end, and
  balanced ones inside are kept (`10.1016/0007-6813(90)90040-i`). A DOI-like path inside another address
  (`…/articles/10.…`) is not read, and an address with a DOI counts once.
- **ERROR fails.** `verify_citations.py` exited 0 when the registry could not be reached, so every note passed.
  ERROR now makes the exit code 1, and the summary says the check could not be completed and the notes have not
  passed.
- **NO DOI stays exit 0,** because a work may have none (a book, a page with a URL). A Source line with something
  shaped like a DOI that the pattern cannot read (`…/articles/10.…`) is UNREAD and fails: write the DOI itself
  there. Something DOI-shaped elsewhere in a note does not make it UNREAD. `rules.md` and the literature playbook
  say what to do on ERROR and on UNREAD.
- **The quote check keeps the marks of a number.** `verify_quotes.py` compared letters and digits only, so
  "3.5%" was FOUND where the source says "35%", and "n = 1,000" or "r = 0.2" matched "n = 1000" or "r = -0.2". It
  now keeps a point or comma between digits, a sign before a digit (any minus read as `-`) and % < > = ±: the
  comparison of poiesis-insight's `quote_gate.py`, copied, so both plugins answer the same on the same quote.
  Spaces, ligatures and accents fold away as before. Not handled, as in insight: a range "3–5" and a middle dot
  "3·5" both fold to "35".
- **Tests.** New `test_verify_citations.py`: bare, prefixed, `/doi/` and `arXiv:` DOIs, closing marks, parentheses,
  a DOI-like path in another address, the three scripts reading the same DOIs, only the Source line giving a
  note's DOI, and the exit code for OK, NO DOI, UNREAD, ERROR, NOT FOUND and MISMATCH, with the registry replaced
  by canned titles. In `test_verify_quotes.py`: the marks of a number, plain words folding as before, bare DOIs in
  a report's table and parentheses, a Later-work DOI not held, a DOI with parentheses. In `test_library.py`:
  `--has` by a bare DOI and by one with parentheses, and a Later-work DOI not taken for the note's.
- **Not checked in this version:** a run against the real DOI registry, and any run on a topic.

## 2.6.0
Everything is added: no path or field of 2.5.0 was renamed or removed, and the scripts read every note as before.
- **Properties.** Each template starts with a block of Obsidian properties (YAML between two `---` lines): `type`,
  `plugin`, `date` and `topic`; a note, a signal, an evidence map and a funding call, which hold one object each,
  add `id`, `status` and `from`. The block is a copy for Obsidian's views (Bases): the label lines stay the record,
  and the scripts read those. In the block no line starts with `#`, text is quoted, and a link is one quoted list
  item, `- "[[note-name]]"`.
- **`verify_quotes.py` skips the block.** A list item in it that starts with a quotation mark was read as a quote,
  and a `[[link]]` or DOI there as a reference with no note. Its lines are now blanked before reading, so line
  numbers stay the same. Only a block on the very first line counts (after a byte-order mark, if there is one),
  and one that is never closed is not a block. A quote line inside the block is skipped without a word.
- **Tests.** In `test_verify_quotes.py`, three tests that failed before the fix, one that guards it (a `---` further
  down or never closed is not a block) and one for a note that starts with a byte-order mark; `test_templates.py`:
  the block in each template, its rules, and `library.py`, `signals.py --next-id` and `verify_quotes.py
  --references` reading a note the same with it as without it.
- **The block is a copy.** `SKILL.md` asks for a value in the block to change in the same edit as its label line,
  and for `status` to hold the label's first words only.
- **Docs.** The READMEs name five products, with a Poiesis Foresight row and `poiesis-studio` in the Design row; `SKILL.md` suggests poiesis-foresight,
  not poiesis-insight, for what is emerging.
- **Not checked in this version:** how Obsidian shows the properties (no vault was opened), and any run on a topic.

## 2.5.0
Everything is added: no path or field of 2.4.0 was renamed or removed, and a request that was asked before is asked
the same way.
- **Open sources.** `search.py --db doaj|osf|zenodo|core`; `--db all` asks DOAJ, Zenodo and CORE too, and OSF only
  when named (titles only, 100 requests an hour): DOAJ (articles in open-access journals), OSF Preprints
  (SocArXiv, PsyArXiv and the other servers on OSF), Zenodo (reports, datasets, software, papers) and CORE (works
  harvested from repositories and journals, with a download link when CORE has one). They go through the same request layer:
  cache, pacing per host from each documentation, the Coverage line. Their rows have the same shape as the other
  databases'; they are searched by query, not by DOI. An answer that is not in the expected shape is a refusal
  named in the Coverage line, not a stop of the run. A DOAJ 404 is a refusal, never a count of 0.
- **CORE's key.** `CORE_API_KEY` is read from the environment and sent in a header, never in the address, and it is
  scrubbed from every answer, cache file and recording like the other keys. A header Python refuses to send
  (a key with a line break) is reported without Python's own words, which repeat the key. Without it CORE is not asked, and the
  Coverage line says "CORE refused (not asked: no key, …)".
- **Counts.** `counts.py --db doaj` and `--db zenodo`, one request per year. OSF and CORE have no yearly counts:
  OSF documents no title and no publication-date filter for preprints, and CORE's total for a quoted phrase was
  not a count of that phrase when tried.
- **Notes and playbooks.** `research/notes/open-sources-2026-access`: each API's documentation read on 2026-11-22
  and what a few keyless requests showed. `playbooks/literature.md` and `playbooks/trends.md` say when to use each
  source and what it does not match.
- **Not checked in this version:** CORE with a key (none was available; its rows were tested on one keyless answer),
  Zenodo and OSF with a token, DOAJ and Zenodo counts beyond one phrase and two years, and any run on a topic.

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
  the page given, and with `--references` lists a report's references that have no note. `--strict` also fails
  when a quote could not be checked because the source's text is not there.
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
