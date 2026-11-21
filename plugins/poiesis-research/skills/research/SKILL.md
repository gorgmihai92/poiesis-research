---
name: research
description: Research for a project, from sources that can be checked. Six kinds of request - literature (what has been written on a topic, who founded the field, the best sources for a need), evidence (whether data support a claim), funding (EU and Romanian grants that fit a project), trends (how many works a subject has, year by year), signals (what is new or being noticed about a subject), prior art (the nearest existing work before something is called new). Use when the user asks to research, find papers or books, check the evidence for something, count publications over time, scan for signals, check whether something already exists, or find grants or funding calls.
---

# Research

One entry point, six playbooks. Each playbook says where to search, what to return and where to save it.

| The user wants… | Playbook | Agent for parallel work | Saved in |
|---|---|---|---|
| what is known on a topic, the field's founders, the best sources for a need | `playbooks/literature.md` | `paper-scout` | `research/notes/` |
| whether a claim is supported by data | `playbooks/evidence.md` | `evidence-scout` | `research/notes/`, and the evidence table in `research/maps/` |
| grants and funding calls that fit a project | `playbooks/funding.md` | `funding-scout` | `research/funding/` |
| how many works a subject has, year by year | `playbooks/trends.md` | none: `counts.py` does the counting | `research/data/` |
| what is new or being noticed about a subject | `playbooks/signals.md` | `signal-scout` | `research/signals/` |
| the nearest existing work, before something is called new | `playbooks/prior-art.md` | `paper-scout`, one per wording | `research/maps/` |

Interpreting results (gaps, opportunities, recommendations) is not part of research: report what the sources
say, and leave the interpretation to the user or to an insights tool. The same holds for numbers and signals:
research gives the counts and the observations, not what they mean.

## Every request

1. **Start from anything:** a question, a claim, a proposal, a document, a problem to figure out. Say in one line
   what you will look for, and start. If `research.config.md` exists (in `research/`, `docs/research/` or the
   root), read it for the project's setting; never ask for it first. Create it from `templates/research.config.md`
   only when notes are about to be saved (sections, note language) or for funding (the applicant), asking only
   what cannot be inferred.
2. **What exists:** if the project has a library, read the index (`research/README.md`) and the files that touch
   the question, and say what it already has. `python3 -I $S/library.py` lists every note with how much of its
   source was read; `python3 -I $S/library.py --has <DOI or title>` says whether one work is there.
3. **Pick the playbook** from the table. A request can use more than one (e.g. funding, then evidence for the
   application). For a broad request, the user can ask for the agents, one per part, in parallel.
4. **Follow `rules.md`**, the same for every playbook.
5. **No step without a playbook or a script.** When the request needs a step that none of them covers, stop and
   say what is missing. Offer the choices: an existing method used more narrowly, building the tool first, or
   skipping the step and recording it under "Not checked". Do not improvise the step and report it as done.

Scripts are in `${CLAUDE_SKILL_DIR}/scripts` (called `$S`; if that path does not exist, Glob for
`**/research/scripts/search.py` under `~/.claude`). They need only Python 3; run them with `python3 -I`.

Every script that asks a database ends with a **Coverage** line: the databases that answered, the ones that
refused and why, and the OpenAlex budget that is left. When OpenAlex or Semantic Scholar refuses, Crossref, Europe
PMC and arXiv answer in its place. Answers are kept on disk for a day, so a run that stopped can be run again
without asking twice; `--fresh` asks again. `python3 -I $S/scholarly.py cache` says where they are kept.

## Answers
Short and direct: the answer first, then what it rests on, in bullets or a table; no preamble, no recap. When the
work is saved, the chat gets the summary, the "Not checked" line and the file's path. Use an agent
only for independent parts that can run in parallel, or for the independent check at thorough depth; otherwise
work inline.

- **Copy, do not retype.** An agent returns rows in fixed columns and, for evidence, a verdict in fixed words.
  Put them in the answer and in saved files as returned. Do not reword a cell, merge two rows or restate a verdict.
- **Say who answered.** Keep the Coverage line of each script in the report. "Not found" names the databases that
  were asked; it never means "does not exist".
- **Say how much was read:** full text, part of the text, abstract only or title only, for every source.

## In a vault that uses Texere
When the project has `Support/Texere/Bibliography/bibliography.json`, it is an Obsidian vault whose owner reads
and annotates with Texere. That file is the index of the library: a list in which each entry has an `id` (the
citation key), an `obsidianPath` and a `reading-status`.

- **Read it first.** `python3 -I $S/library.py` lists its entries next to the project's own notes. A source it
  holds is already in the library: say so, and do not present it as found.
- **Cite as Texere does:** `[@key, p. N]` after the claim, in notes and in reports. A source that is not in the
  bibliography is cited by its note and page as usual, and the report says it is not in the bibliography. Never
  make up a key.
- **Never write in Texere's folders.** `1. References`, `2. Notes`, `3. Workspace`, `4. Export` and `Support` are
  read, never created in, edited or deleted from. Research writes only under `research/`. Adding a source to the
  bibliography is the owner's step in Texere: name the source and stop there.
- **The owner's annotations are quotes a person checked.** A line such as `#claim text [@key, p. N]` in their
  notes can be quoted as theirs. `verify_quotes.py` does not check it again.
- `python3 -I $S/verify_quotes.py --references <report.md>` finds the bibliography by itself and lists the
  `[@key]` citations that are not in it.
- A missing or unreadable index means this is not a Texere vault: work as in any project.

## Other Poiesis plugins
This plugin works alone. Suggest another one only when it would change the result: once, in one line, and go
on without it if the user says no (say what was left out). Check with `claude plugin list`; install only after
the user agrees, with `claude plugin marketplace add gorgmihai92/<repo>` and then
`claude plugin install <plugin>@<repo>` (it works after Claude Code restarts).
Every suggestion, from the skill or an agent, gives the plugin's link (below) and names the skill or agent
to use, e.g. "[poiesis-insight](https://github.com/gorgmihai92/poiesis-insight), `foresight-analyst`".
- **[poiesis-insight](https://github.com/gorgmihai92/poiesis-insight)**: when the user wants to know what the sources mean (patterns,
  contradictions, implications) or what is emerging; research stops at what they say.
- **[poiesis-frontier](https://github.com/gorgmihai92/poiesis-frontier)**: when the user wants new concepts or experiments from the gaps the
  library shows.

## Files other Poiesis plugins read
These paths and fields are a contract between the Poiesis plugins: rename or remove one only in a major version,
and say so in the changelog; adding fields is free. Read other plugins' files tolerantly: a missing file or field
means "unknown", said in the report, never an error.
- `research/README.md`: the index, one line per source under its section.
- `research/notes/<section>/<slug>.md`: **Source** (DOI or URL), **Evidence**, "What it says" (each claim with
  `(p. N)`), "Later work", "What it means for the project". Read by insight and frontier.
- `research/funding/<call-id>.md`: the call, its official page and the date checked.

Added in 2.4.0. Everything above is unchanged.
- In a note: **Read**, how much of the source was read (full text, part of the text, abstract only, title only).
  Quote lines under "Quotes" are `- "exact words" (p. N)`; `verify_quotes.py` checks them against the source's text.
- `research/maps/<date>-<claim>.md`: an evidence map. Its table has one row per study and these columns, in this
  order: Citation, DOI, Verified, Read, What it says, Open copy, Population, What was varied, Compared with, What
  was measured, Setting, Design, Key number, Side, Group. The first six are the same in every table of sources;
  a new column goes at the end; no cell contains a `|`. `research/maps/<date>-prior-art-<name>.md` holds the
  nearest existing works for something called new.
- `research/data/<name>.csv`: a series, one row per series and year: `series`, `label`, `year`, `partial`,
  `count`, `base`, `share_per_100k`, `count_all_types`, `base_all_types`, `share_all_types_per_100k`. A taxonomy
  scan has `topic_id`, `topic`, `year`, `partial`, `count`, `base`, `share_per_100k`.
  `<name>.types.csv` has `series`, `year`, `type`, `count`. `<name>.meta.json` has `database`, `fetched`, `years`,
  `partial_years`, `share` (`numerator_types` and `denominator_types`, always the same), `series`, `base`,
  `script`, `coverage` and `complete`.
- `research/signals/<date>-<name>.md`: one signal: **Id** (`SG-001`, never used twice), **What**, **Where**,
  **When**, **How visible**, **How widespread**, **Kind of source**, **Read**, **Scan**. It holds the observation
  and no interpretation. `research/signals/<date>-<term>.scan.json` is the scan its numbers come from.
- The Coverage line: `Coverage (<date>): <database> answered (<n> requests …); <database> refused (<why>).`
- In a Texere vault, `Support/Texere/Bibliography/bibliography.json` is read, and sources in it are cited as
  `[@key, p. N]`. Nothing is written in Texere's folders.
