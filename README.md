# Poiesis Research

Research you can check, in Claude Code. Poiesis Research finds the literature on a topic, the evidence behind a
claim, and the EU and Romanian grants that fit a project. It also counts how much is published on a subject year
by year, records what is being noticed about it now, and looks for the nearest existing work before anything is
called new. Every source, page, date, count and amount comes from a search or a page it read, never from memory.

For a thesis, a paper, a grant application or a product decision that has to rest on sources someone else can check.
Poiesis Research is one of the four products in the [Poiesis Toolkit](#part-of-the-poiesis-toolkit) and works on its
own, as one plugin. Install it below and ask in plain language.

## Part of the Poiesis Toolkit

The Poiesis Toolkit is four products for Claude Code, one for each step from a question to a finished product:
**Research** collects, **Insight** connects, **Frontier** explores, **Design** creates. Each installs and works on
its own. Insight and Frontier also read what the other steps left in your project, as plain files, and Design
builds a Frontier concept when you ask.

| Product | What it does | Plugins | Agents | Reads | Leaves in your project |
|---|---|---|---|---|---|
| [Poiesis Research](https://github.com/gorgmihai92/poiesis-research) | **collect:** the literature on a topic, the evidence for and against a claim, the grants that fit | `poiesis-research` | `paper-scout`, `evidence-scout`, `funding-scout` | the web's scholarly databases, official funding pages | `research/` |
| [Poiesis Insight](https://github.com/gorgmihai92/poiesis-insight) | **connect:** what the evidence or your data mean, and what is emerging; every conclusion challenged | `poiesis-insight` | `insight-analyst`, `foresight-analyst`, `challenger` | `research/`, your own data, `frontier/results/` | `insights/`, `foresight/` |
| [Poiesis Frontier](https://github.com/gorgmihai92/poiesis-frontier) | **explore:** new concepts, each with the smallest experiment that could kill it | `poiesis-frontier` | `experimentalist` | `insights/`, `foresight/`, `research/` | `frontier/` |
| [Poiesis Design](https://github.com/gorgmihai92/poiesis-design) | **create:** how the interface looks, behaves and what it says, built from components that already pass, checked before release | `poiesis-ui`, `poiesis-ux`, `poiesis-copy`, `poiesis-components` | `ui-auditor`, `ux-tester`, `copy-reviewer` | your code, `.poiesis-design/` | `.poiesis-design/`, design tokens, components |

```
Research ──► Insight ──► Frontier ──► Design
               ▲            │
               └─ results ◄─┘   (experiment results go back to Insight as data)
```

- **One job each.** Research says what sources say; Insight says what it means; Frontier proposes what could be
  and how to test it; Design builds and checks. None does another's job.
- **None needs another.** When another product would really improve the answer, Claude says so once, in one line,
  and offers to install it. You can say no; the work goes on and the report says what was left out.
- **Depth you choose:** quick, standard (the default) or thorough, per request or as a line in your project's
  `CLAUDE.md`, e.g. `Depth: quick`. A few rules hold at every depth (nothing invented, sources cited, interpretation
  labelled); the rest scale with what is at stake, and every report ends with what was **not checked**.
- **Short answers.** The answer first; the full work goes in the saved file. Agents are used only for independent
  parts in parallel, or for an independent check at thorough depth.
- **Rules limit what is reported as true, never what may be explored.**

## Six kinds of question

| You want to know | It returns | Saved in |
|---|---|---|
| **Literature:** what is known on a topic, who founded the field, the best sources for a need | founding works first, then current work, each with citations, kind (review, empirical, analytical) and whether an open copy exists | `research/notes/` |
| **Evidence:** whether data support a claim | meta-analyses, experiments, validated measures and datasets, with design, sample and the key number; the evidence against (failed replications, critiques); and a verdict counted by independent groups: supported, mixed, not supported or not studied | `research/notes/` |
| **Funding:** which grants fit the project | open and upcoming calls from the EU Funding & Tenders Portal and Romania's official sites, each with deadline, grant per project, who can apply, fit and the date it was checked | `research/funding/` |
| **Trends:** how much is published on a subject, year by year | counts and shares per 100,000 works, with the same document types above and below the line, the unfinished year marked, and the database and date they came from | `research/data/` |
| **Signals:** what is new or being noticed about a subject | what seven open sources show in a recent window: preprints, funded projects, models and datasets, discussion, article views, each with its date, numbers and link | `research/signals/` |
| **Prior art:** whether something already exists | the nearest existing works and what differs, searched by what the thing does, in several databases; never the word "new" | `research/maps/` |

Research reports what the sources say, what the counts are and what was observed. Interpreting it (patterns, gaps, opportunities, trends, futures) is the job of
[Poiesis Insight](https://github.com/gorgmihai92/poiesis-insight), or yours. It starts from
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
([Semantic Scholar](https://www.semanticscholar.org/product/api); without it that database answers slowly). A
third, `CORE_API_KEY` ([CORE](https://core.ac.uk/services/api)), lets it search CORE, which gathers works from
repositories and journals; without it CORE is left out and the result says so. The plugin never sends your email address anywhere, and it does not
create keys for you.

Answers from the databases are kept for a day in `~/.cache/poiesis-research/`, outside your projects, so a search
that stopped halfway can be run again without asking twice. Set `POIESIS_RESEARCH_CACHE` to another folder, or to
`off`. When OpenAlex's free budget for the day is used up, or Semantic Scholar is busy, Crossref, Europe PMC and
arXiv answer in their place, and each result ends with a line that says which databases answered.

For the humanities and social sciences, four open sources can be asked too: DOAJ (open-access journals), OSF
Preprints (SocArXiv, PsyArXiv and the others; titles only), Zenodo (reports, datasets, software) and CORE (works
from repositories, with a download link when it has one). Ask for them by name; asking every database at once
includes all but OSF.

## Ask in plain language

The plugin comes in when the work is research, and you can name its agents directly.

- *"Who are the founders of framing research?"*
- *"Find the best sources on how people judge credibility from speech."*
- *"Is there evidence that short texts are enough to describe someone's style?"*
- *"Find EU and Romanian grants for a civic-tech app run by a small NGO."*
- *"How much has been published on solid-state batteries each year since 2015?"*
- *"What is being noticed about brain-computer interfaces in the last six months?"*
- *"Has anyone built this already? Find the nearest existing work."*
- *"Use paper-scout on persuasion, evidence-scout on measuring populism and funding-scout on grants, in parallel."*

The first time, Claude asks what your project is, the sections of your library and the language of your notes
(for funding, also who applies), and writes them to `research/research.config.md`.

## One skill picks a playbook; an agent can run each part

One skill, `research`, is the entry point. It reads your project's config and what the library already holds,
then picks a **playbook** for the kind of request. Each playbook has an **agent** for parallel work: the skill
works inside your conversation, while an agent runs on its own and returns only a report, so you can send several
at once, one part of a question each.

| Playbook | Agent | Where it searches |
|---|---|---|
| literature | `paper-scout` | OpenAlex and Semantic Scholar, merged; Google Scholar through your own export; DOAJ, OSF Preprints, Zenodo and CORE when asked |
| evidence | `evidence-scout` | the same databases, empirical studies first |
| funding | `funding-scout` | EU Funding & Tenders Portal (Horizon Europe, Digital Europe, Creative Europe, Erasmus+, CERV, and calls EU projects open to SMEs); Ministry of Investments and European Projects, regional development agencies, UEFISCDI, AFIR |
| trends | none: a script counts | OpenAlex, by year and by document type; Europe PMC, DOAJ or Zenodo as a second database |
| signals | `signal-scout` | arXiv, Europe PMC, NIH RePORTER, OpenAIRE, Hacker News, Wikimedia pageviews, Hugging Face |
| prior art | `paper-scout` | every database above for papers: OpenAlex, Semantic Scholar, Crossref, Europe PMC, arXiv, DOAJ, Zenodo, CORE; OSF Preprints when asked |

- **Literature, founders first.** It reads the bibliographies of the most-cited works on the topic. Works that
  most of them cite are the field's foundations, however old. Then it adds current work by citations and
  relevance.
- **Google Scholar by hand.** Scholar has no open API. Save results from
  [Publish or Perish](https://harzing.com/resources/publish-or-perish) (free) as CSV and ask Claude to combine
  them with the other databases.
- **Funding, checked on the official page.** A call counts only from its official page, with the date it was
  checked. Stale and cancelled calls are dropped.
- **Counts, on the same document types.** In one recorded run a database's count of other kinds of records rose
  faster than its count of articles, and a share of articles among all records fell for that reason alone. A share
  here counts the same types above and below the line, and the file says which.
- **Signals, as observations.** A signal says what was seen, where, when, how visible and how widespread. What it
  means is left to you or to Poiesis Insight.
- **Scouts return rows, not prose.** Each source is one row in fixed columns: citation, DOI, how it was verified,
  how much was read, what it says, whether an open copy exists. Rows are copied into the saved file as returned.

## The same rules for every request: nothing invented, everything cited

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
- **Quotes checked against the text.** Every quote in a note is looked for in the source's text, on the page the
  note gives. Before a report goes out, its references are checked against the notes.
- **How much was read.** Each source says it: full text, part of the text, abstract only, or title only.
- **Who answered.** Each search ends by naming the databases that answered and the ones that refused. "Not found"
  is never "does not exist".
- **Nothing called new without a search.** The nearest existing works are listed first, with what differs.
- **No silent improvisation.** When a step has no playbook or script, Claude stops and says what is missing.
- **Quality, by kind and then by the source itself.** Systematic reviews and meta-analyses, validated measures and
  experiments, other empirical studies, theory, popular books: a starting point, after which each source moves up
  or down by its own bias, sample, precision and fit. Many citations mean influence, not truth.
- **Legal copies only.** Open copies are downloaded. For the rest you get where to find one (library, the
  author, or buying it). No shadow libraries.
- **Closed-licence files stay local.** Never pushed to a public repository or shipped with a product.

## Everything it finds stays in `research/`

```
research/
  research.config.md          your project, library sections, note language; for funding, who applies
  README.md                   index of everything below
  papers/<section>/…pdf/.txt  sources and their text, with a page marker before each page
  notes/<section>/….md        what a source says (with pages) and what it means for the project
  funding/<call-id>.md        one call: deadline, grant, eligibility, fit, date checked
  maps/<date>-….md            an evidence table for a claim, or the nearest existing works for an idea
  data/<name>.csv             a yearly series, with <name>.types.csv and <name>.meta.json beside it
  signals/<date>-….md         one signal each, and the scan its numbers come from
```

In an Obsidian vault that uses Texere, the plugin reads `Support/Texere/Bibliography/bibliography.json` as the
index of your library and cites as Texere does, `[@key, p. N]`. It never writes in Texere's folders.

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
        trends.md             how to count works by year and report shares
        signals.md            how to record what is being noticed, as observations
        prior-art.md          how to find the nearest existing work before calling something new
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
        verify_quotes.py      check that every quote is in its source's text, and a report's references in the notes
        counts.py             yearly counts and shares for a search, a topic or the whole topic taxonomy
        signals.py            what seven open sources show about a subject in a recent window
        library.py            what the project's library already holds, with a Texere bibliography when there is one
        scholarly.py          shared database access: cache, pacing, budget, fallback databases, the Coverage line
      templates/
        research.config.md    the project config created on first use
        note.md               a source note
        funding.md            a call note
        evidence-map.md       an evidence table for one claim
        signal.md             a signal note
    agents/                   agents for parallel work
      paper-scout.md          literature for one question
      evidence-scout.md       evidence for one claim
      funding-scout.md        funding for one project or need
      signal-scout.md         signals for one subject
    evals/                    cases for `claude plugin eval`
research/                     the sources behind the rules: one note per source
tests/                        tests of the scripts; they never use the network
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
- **Quotes checked against the text:** Wu et al. 2025, read in full. Between 50% and 90% of language models'
  answers to medical questions were not fully supported by the sources they cited.
- **References checked against the notes, and the DOI verified:** Chelli et al. 2024, read in full as the accepted
  manuscript. Three models invented between 28.6% and 91.4% of the references they gave; for the real papers two
  of them returned, the DOI was right in 15.9% and 20.2% of cases.
- **Nothing called new without the nearest existing work:** Beel, Kan & Baumgart 2025, read in full as a preprint.
  A system that took "no match found" for "new" marked 12 of 12 ideas as new; four were known techniques.
- **The same document types on both sides of a share:** two recorded runs of these plugins (an observation), and
  Liu, Ni & Hu 2024, read in part: counts show the database's growth as well as the field's.
- **The evidence table and the map:** Robinson, Saldanha & Mckoy 2011 and Snilstveit et al. 2016, both read at
  abstract level only.
- **The signal record:** the horizon-scanning section of the UK Government Office for Science's Futures Toolkit
  (2024). It is practitioner guidance, not evidence that scanning works.
- **What each database allows:** its own documentation, as read on 2026-11-21 (DOAJ, OSF, Zenodo and CORE on
  2026-11-22).
- **Licences, legal copies, fresh funding calls, where the cache lives, the default document types and the
  six-month signal window:** the plugin's own choices, not research findings.

## Files shared with the other products

Writes the index `research/README.md`; notes in `research/notes/<section>/<slug>.md` with **Source**, **Evidence**, "What it says" (claims with pages), "Later work", "What it means for the project"; calls in `research/funding/`. Read by Insight and Frontier.

Added in 2.4.0, with everything above unchanged: a **Read** line in each note; evidence maps and prior-art maps in
`research/maps/`; yearly series in `research/data/` as CSV with a metadata file (query, database, date, document
types, script); signal notes in `research/signals/` with an id (`SG-001`) and the fields What, Where, When, How
visible, How widespread; and a Coverage line at the end of every search. In a Texere vault the plugin reads
`Support/Texere/Bibliography/bibliography.json` and writes nothing in Texere's folders.

The paths and fields the other products read are a contract: they change only in a major version, noted in the
changelog. Every plugin reads the others' files tolerantly: a missing file or field is reported as unknown, never
an error. The full list is in each skill's `SKILL.md`, so Claude knows it too.

## Update or remove

```
/plugin marketplace update poiesis-research
/plugin update poiesis-research@poiesis-research
/plugin uninstall poiesis-research@poiesis-research
```

## Changing the plugin

Edit the files under `plugins/poiesis-research/`, then run the two checks from the repository's root:

```
python3 -I -m unittest discover -s tests
claude plugin validate plugins/poiesis-research
```

Validate at the plugin's path: `claude plugin validate .` at the root checks only the marketplace file. The tests
never use the network. A new rule starts with reading its source and a note in `research/notes/` that says how much
was read. Bump the version (major if a field under "Files" changes) in `plugin.json`, `marketplace.json` and
`CHANGELOG.md`, and push. Projects get it with the update commands above.

## License

MIT.
