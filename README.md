# Poiesis Research

A Claude Code plugin for research you can check. It finds the literature on a topic, the evidence behind a
claim, and the EU and Romanian grants that fit a project. Every source, page, date and amount comes from a search
or a page it read, never from memory.

## The Poiesis toolkits

**Collect → connect → explore → create.** Four toolkits. Each works on its own; together, each reads what the others
left in your project, as plain files.

| Toolkit | Role | Agents | Reads | Leaves in your project |
|---|---|---|---|---|
| [poiesis-research](https://github.com/gorgmihai92/poiesis-research) | **collect:** the literature on a topic, the evidence for and against a claim, the grants that fit | `paper-scout`, `evidence-scout`, `funding-scout` | the web's scholarly databases, official funding pages | `research/` |
| [poiesis-insight](https://github.com/gorgmihai92/poiesis-insight) | **connect:** what the evidence or your data mean, and what is emerging; every conclusion challenged | `insight-analyst`, `foresight-analyst`, `challenger` | `research/`, your own data, `frontier/results/` | `insights/`, `foresight/` |
| [poiesis-frontier](https://github.com/gorgmihai92/poiesis-frontier) | **explore:** new concepts, each with the smallest experiment that could kill it | `experimentalist` | `insights/`, `foresight/`, `research/` | `frontier/` |
| [poiesis-design](https://github.com/gorgmihai92/poiesis-design) | **create:** how the interface looks and behaves, checked before release | `ui-auditor`, `ux-tester` | your code, `.poiesis-design/` | `.poiesis-design/`, design tokens, components |

```
research ──► insight ──► frontier ──► design
               ▲            │
               └─ results ◄─┘   (experiment results go back to insight as data)
```

- **One job each.** Research says what sources say; insight says what it means; frontier proposes what could be
  and how to test it; design builds and checks. None does another's job.
- **None needs another.** When one would really improve the answer, Claude says so once, in one line, and offers
  to install it. You can say no; the work goes on and the report says what was left out.
- **Depth you choose:** quick, standard (the default) or thorough, per request or as `Depth:` in
  `research/research.config.md`. A few rules hold at every depth (nothing invented, sources cited, interpretation
  labelled); the rest scale with what is at stake, and every report ends with what was **not checked**.
- **Short answers.** The answer first; the full work goes in the saved file. Agents are used only for independent
  parts in parallel, or for an independent check at thorough depth.
- **Rules limit what is reported as true, never what may be explored.**

## What it covers

| You want to know | It returns | Saved in |
|---|---|---|
| **Literature:** what is known on a topic, who founded the field, the best sources for a need | founding works first, then current work, each with citations, kind (review, empirical, analytical) and whether an open copy exists | `research/notes/` |
| **Evidence:** whether data support a claim | meta-analyses, experiments, validated measures and datasets, with design, sample and the key number; the evidence against (failed replications, critiques); and a verdict counted by independent groups: supported, mixed, not supported or not studied | `research/notes/` |
| **Funding:** which grants fit the project | open and upcoming calls from the EU Funding & Tenders Portal and Romania's official sites, each with deadline, grant per project, who can apply, fit and the date it was checked | `research/funding/` |

Research reports what the sources say. Interpreting it (patterns, gaps, opportunities, futures) is the job of
[poiesis-insight](https://github.com/gorgmihai92/poiesis-insight), or yours. Insight starts from
`research/README.md`, the index, reads the notes in `research/notes/` and cites back to the note and page; it never
edits them. Keep the index current and every claim in a note with its page, and the handover needs nothing else.

## Install

In Claude Code:

```
/plugin marketplace add gorgmihai92/poiesis-research
/plugin install poiesis-research@poiesis-research
```

It needs **Python 3**, which macOS and most Linux systems already have. It works without keys. For heavy use, two
free keys help (set them in your shell profile): `OPENALEX_API_KEY` ([openalex.org](https://openalex.org/settings/api);
without it everyone on your network shares about 100 searches a day) and `S2_API_KEY`
([Semantic Scholar](https://www.semanticscholar.org/product/api); without it that database answers slowly).

## What to ask Claude

Ask in plain language. The plugin comes in when the work is research, and you can name its agents directly.

- *"Who are the founders of framing research?"*
- *"Find the best sources on how people judge credibility from speech."*
- *"Is there evidence that short texts are enough to describe someone's style?"*
- *"Find EU and Romanian grants for a civic-tech app run by a small NGO."*
- *"Use paper-scout on persuasion, evidence-scout on measuring populism and funding-scout on grants, in parallel."*

The first time, Claude asks what your project is, the sections of your library and the language of your notes
(for funding, also who applies), and writes them to `research/research.config.md`.

## How it works

One skill, `research`, is the entry point. It reads your project's config and what the library already holds,
then picks a **playbook** for the kind of request. Each playbook has an **agent** for parallel work: the skill
works inside your conversation, while an agent runs on its own and returns only a report, so you can send several
at once, one part of a question each.

| Playbook | Agent | Where it searches |
|---|---|---|
| literature | `paper-scout` | OpenAlex and Semantic Scholar, merged; Google Scholar through your own export |
| evidence | `evidence-scout` | the same databases, empirical studies first |
| funding | `funding-scout` | EU Funding & Tenders Portal (Horizon Europe, Digital Europe, Creative Europe, Erasmus+, CERV, and calls EU projects open to SMEs); Ministry of Investments and European Projects, regional development agencies, UEFISCDI, AFIR |

- **Literature, founders first.** It reads the bibliographies of the most-cited works on the topic. Works that
  most of them cite are the field's foundations, however old. Then it adds current work by citations and
  relevance.
- **Google Scholar by hand.** Scholar has no open API. Save results from
  [Publish or Perish](https://harzing.com/resources/publish-or-perish) (free) as CSV and ask Claude to combine
  them with the other databases.
- **Funding, checked on the official page.** A call counts only from its official page, with the date it was
  checked. Stale and cancelled calls are dropped.

## The rules

The same rules apply to every playbook (`skills/research/rules.md`):

- **Nothing invented.** No source, page, number, date or amount without a search result or a page read. What
  Claude remembers but can't confirm is marked "unconfirmed".
- **Cited.** A claim names its page; a funding detail names its official page and the date checked.
- **Honest evidence.** Samples, effect sizes and limits as the source states them. One study is not a consensus,
  and disagreement is reported.
- **Searched for and against.** Every claim is also searched for replications, failures, critiques and the opposite
  claim; the studies a verdict rests on are followed forward to the later work that cites them.
- **Independent groups, not papers.** Studies that share authors, a dataset or a sample count once together.
- **Non-academic sources, checked laterally.** Reports, vendor surveys, blogs and docs are used after finding out
  who is behind them; a number from a party that profits from it is a lead, not evidence.
- **Checked against the registry.** After notes are written, every DOI is looked up in the DOI registry and must
  match its note's title; a model asked about its own citations is not a check.
- **Quality, by kind and then by the source itself.** Systematic reviews and meta-analyses, validated measures and
  experiments, other empirical studies, theory, popular books: a starting point, after which each source moves up
  or down by its own bias, sample, precision and fit. Many citations mean influence, not truth.
- **Legal copies only.** Open copies are downloaded. For the rest you get where to find one (library, the
  author, or buying it). No shadow libraries.
- **Closed-licence files stay local.** Never pushed to a public repository or shipped with a product.

## What it adds to your project

```
research/
  research.config.md          your project, library sections, note language; for funding, who applies
  README.md                   index of everything below
  papers/<section>/…pdf/.txt  sources and their text, with a page marker before each page
  notes/<section>/….md        what a source says (with pages) and what it means for the project
  funding/<call-id>.md        one call: deadline, grant, eligibility, fit, date checked
```

## What's in this repository

The repository is a Claude Code **marketplace** holding one **plugin**.

```
.claude-plugin/
  marketplace.json            the marketplace: its name and the plugins it lists (here, one)
plugins/
  poiesis-research/           the plugin
    .claude-plugin/
      plugin.json             name, version, description
    skills/research/          the skill: what Claude follows when you ask for research
      SKILL.md                entry point: reads the config, picks the playbook
      rules.md                honesty, quality order, freshness, copies; shared by all playbooks
      playbooks/
        literature.md         how to map a field and find the best sources
        evidence.md           how to weigh the data behind a claim
        funding.md            how to find and check grant calls
      scripts/                Python 3, standard library only
        search.py             search OpenAlex and Semantic Scholar together, or look up a DOI
        foundations.py        find a field's founding works from what its top papers cite
        scholar_import.py     merge a Google Scholar export (Publish or Perish CSV) with the databases
        copies.py             download the open copy of a work, or say where to find it
        extract_text.py       turn a PDF into text with "[p. N]" page markers, so notes can cite pages
        funding.py            search open and upcoming calls on the EU Funding & Tenders Portal
        citing.py             later works that cite a study, with replications and critiques flagged first
        independence.py       group studies that share authors, so evidence is counted by independent groups
        verify_citations.py   check that every DOI in the notes exists and matches its title
        scholarly.py          shared database access used by the scripts above
      templates/
        research.config.md    the project config created on first use
        note.md               a source note
        funding.md            a call note
    agents/                   agents for parallel work, one per playbook
      paper-scout.md          literature for one question
      evidence-scout.md       evidence for one claim
      funding-scout.md        funding for one project or need
research/                     the sources behind the rules: one note per source
CHANGELOG.md                  what changed in each version
LICENSE                       MIT
```

## Where the rules come from

Each rule names its source; there is one note per source in `research/notes`.

- **Nothing invented, every citation checked:** Walters & Wilder 2023. Language models fabricated 18–55% of the
  citations they wrote, and answered wrongly when asked whether a citation was correct, so citations are checked
  against the DOI registry, not by asking the model.
- **Quality by kind, then by the source itself:** Murad et al. 2016, the new evidence pyramid. The kind of study is
  a starting point; each source moves up or down by its own bias, sample, precision and fit, and a review is only as
  good as the studies it combines.
- **Citations mean influence, not truth:** Aksnes, Langfeldt & Wouters 2019.
- **Several databases, and Google Scholar through your export:** Martín-Martín et al. 2021. Google Scholar found
  88% of citations against 60% or less elsewhere, with the widest gaps in the humanities and older works.
- **Reference lists from OpenAlex:** Culbert et al. 2025. Its reference lists are as complete as Web of Science and
  Scopus for recent work.
- **Founding works from what top papers cite together:** Small 1973 (co-citation) and Wohlin 2014 (snowballing).
- **Later work that cites a study (forward snowballing):** Wohlin 2014.
- **Search against the claim, not only for it:** Nickerson 1998, confirmation bias.
- **Check who is behind a non-academic source:** Wineburg & McGrew 2019. Fact checkers who left a site to read
  about it judged credibility better, in a fraction of the time, than historians and students who stayed on it.
- **Licences, legal copies, fresh funding calls:** the plugin's own choices, not research findings.

## Update or remove

```
/plugin marketplace update poiesis-research
/plugin update poiesis-research@poiesis-research
/plugin uninstall poiesis-research@poiesis-research
```

## Changing the plugin

Edit the files under `plugins/poiesis-research/`, run `claude plugin validate .`, bump the version in
`plugin.json`, `marketplace.json` and `CHANGELOG.md`, and push. Projects get it with the update commands above.

## License

MIT. Requires Python 3.
