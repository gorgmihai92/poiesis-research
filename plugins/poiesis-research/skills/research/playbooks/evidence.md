# Evidence

Whether data support a claim. Not what theorists argue (that is literature), but what was measured.

## Read first
The evidence table below rests on two notes in `research/notes` of the plugin's repository, both read **at
abstract level only**: `robinson-2011-research-gaps-framework` (the PICOS elements that describe a study and a
gap) and `snilstveit-2016-evidence-gap-maps` (an overview saved as a map of what was studied and what was not).

## Find
1. Turn the claim into testable questions: what is measured, on what, compared with what.
2. Search empirical work first:
   `python3 -I $S/search.py "<concept> meta-analysis" --sort cited --brief`, then the same with "experiment",
   "validation reliability", "dataset". Each line has a first guess of the evidence kind; confirm it from the
   abstract.
3. **Search against the claim too**, with the same weight: the concept with "replication", "failed to replicate",
   "critique", and the opposite claim in plain words. Searching only for support finds support for almost anything
   (Nickerson 1998).
4. **Forward:** for the 3–5 studies the verdict rests on, `python3 -I $S/citing.py --doi <DOI>` lists the later
   works that cite them, with replications, failures and critiques flagged first (Wohlin 2014). A flag is a guess
   from the title: read the abstract before counting it.
5. For each study: design, sample (size, language, setting), the key number (effect size or agreement between
   coders), limits. Say when you only read the abstract. Each study becomes one row of the evidence table.
6. **Independence:** `python3 -I $S/independence.py <DOI> <DOI> ...` on the studies kept groups those that share
   authors; check by hand whether groups share a dataset or sample. Count each group once.

Every script ends with a "Coverage" line: the databases that answered and the ones that refused. Keep the lines;
the report needs them.

## Evidence table
One row per study the verdict rests on. The first six columns are the same in every table this plugin makes for
sources. The next five describe the study (population, intervention, comparison, outcome, setting: Robinson et
al. 2011), in plain words.

| Column | What goes in it |
|---|---|
| Citation | authors, year, title, venue |
| DOI | the DOI itself; "none" when the work has none. Never the address of a page or of a copy |
| Verified | how the study and its DOI were confirmed, naming the databases; "not verified" when nobody looked |
| Read | full text, part of the text, abstract only, or title only |
| What it says | the finding in one sentence, from what was read |
| Open copy | yes, no or unknown, as the search line shows it |
| Population | who or what was studied, and how many |
| What was varied | the intervention, exposure or condition that differs between groups or cases |
| Compared with | the comparison or control; "none" when the study has no comparison |
| What was measured | the outcome and the instrument that measured it |
| Setting | where and how: country, language, lab or field, the task or the material |
| Design | meta-analysis, experiment, survey, corpus study, case study … |
| Key number | the effect size or agreement as the source states it, with its page |
| Side | for, against or mixed, towards the claim |
| Group | the independent group the study belongs to (step 6) |

- A cell says what the source says. Write "not stated" when the part you read does not say it. Never fill a cell
  from what such studies usually do.
- **Read** is per study. A row filled from an abstract says "abstract only" and its key number has no page. A
  study known by title only has "not read" from "What it says" to "Key number".
- **Verified** is per study too. A DOI copied from a preprint's record or recalled from memory is "not verified"
  until a database or the DOI registry returns that title for it (`search.py --doi <DOI> --db all`).
- No cell contains a `|`. A link to a note is written `[[note-name]]`, without an alias.
- A new column goes at the end, after Group.
- Rows an agent returned are copied as they are. Do not retype, shorten or reword a cell or the verdict.

## Report
- **Verdict:** supported / mixed / not supported / not studied, and how close the evidence is to the project's
  setting. Give the count as independent groups ("6 studies from 3 groups"), not papers.
- **Searched:** the queries for and against the claim, the studies followed forward, and the databases that
  answered (the Coverage lines).
- **Studies,** strongest first: the evidence table. It carries what this report always gave (citation, DOI,
  design and sample, key number, open or closed, group) and adds how each study was verified, how much of it was
  read, and what it varied, compared and measured.
- **Against:** replications that failed, critiques, null results, and what they found; "none found" when the
  search for them came back empty.
- **Datasets** the project could test itself against.
- **Not measured yet:** the combinations of population, what was varied and what was measured for which this
  search found no study. Say "none found by this search", never "does not exist". Why a combination is empty,
  and whether it matters, is interpretation and is left out (see "Other Poiesis plugins" in `SKILL.md`).

## Save the table
Save the table as `research/maps/<date>-<claim>.md`, from `templates/evidence-map.md`: the claim, the date, the
searches with their Coverage lines, the table, and the combinations with no study found. Add one line to
`research/README.md`. The map is what an interpretation tool reads, so it has to stand without the conversation.

## Add
Studies the user keeps are added like literature (`playbooks/literature.md`, "Add"), with the key number and its
page in the note.
