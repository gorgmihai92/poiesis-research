---
name: research
description: Research for a project, from sources that can be checked. Three kinds of request - literature (what has been written on a topic, who founded the field, the best sources for a need), evidence (whether data support a claim), funding (EU and Romanian grants that fit a project). Use when the user asks to research, find papers or books, check the evidence for something, or find grants or funding calls.
---

# Research

One entry point, three playbooks. Each playbook says where to search, what to return and where to save it.

| The user wants… | Playbook | Agent for parallel work | Saved in |
|---|---|---|---|
| what is known on a topic, the field's founders, the best sources for a need | `playbooks/literature.md` | `paper-scout` | `research/notes/` |
| whether a claim is supported by data | `playbooks/evidence.md` | `evidence-scout` | `research/notes/` |
| grants and funding calls that fit a project | `playbooks/funding.md` | `funding-scout` | `research/funding/` |

Interpreting results (gaps, opportunities, recommendations) is not part of research: report what the sources
say, and leave the interpretation to the user or to an insights tool.

## Every request

1. **Start from anything:** a question, a claim, a proposal, a document, a problem to figure out. Say in one line
   what you will look for, and start. If `research.config.md` exists (in `research/`, `docs/research/` or the
   root), read it for the project's setting; never ask for it first. Create it from `templates/research.config.md`
   only when notes are about to be saved (sections, note language) or for funding (the applicant), asking only
   what cannot be inferred.
2. **What exists:** if the project has a library, read the index (`research/README.md`) and the files that touch
   the question, and say what it already has.
3. **Pick the playbook** from the table. A request can use more than one (e.g. funding, then evidence for the
   application). For a broad request, the user can ask for the agents, one per part, in parallel.
4. **Follow `rules.md`**, the same for every playbook.

Scripts are in `${CLAUDE_SKILL_DIR}/scripts` (called `$S`; if that path does not exist, Glob for
`**/research/scripts/search.py` under `~/.claude`). They need only Python 3; run them with `python3 -I`.

## Answers
Short and direct: the answer first, then what it rests on, in bullets or a table; no preamble, no recap. When the
work is saved, the chat gets the summary, the "Not checked" line and the file's path. Use an agent
only for independent parts that can run in parallel, or for the independent check at thorough depth; otherwise
work inline.

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
