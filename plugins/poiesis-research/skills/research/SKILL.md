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

1. **Project context:** read `research.config.md` (in `research/`, `docs/research/` or the root). If there is
   none, ask what the project is, the library's sections and the note language, and create it from
   `templates/research.config.md`. For funding, the config also needs the applicant (see the template).
2. **What exists:** read the index (`research/README.md`) and the files that touch the question, and say what
   the project already has.
3. **Pick the playbook** from the table. A request can use more than one (e.g. funding, then evidence for the
   application). For a broad request, the user can ask for the agents, one per part, in parallel.
4. **Follow `rules.md`**, the same for every playbook.

Scripts are in `${CLAUDE_SKILL_DIR}/scripts` (called `$S`; if that path does not exist, Glob for
`**/research/scripts/search.py` under `~/.claude`). They need only Python 3; run them with `python3 -I`.
