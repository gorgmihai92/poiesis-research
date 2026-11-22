# Prior art

Before anything is called new (an idea, a method, a concept, an interface), find the nearest work that exists and
say what differs. The answer is a list of neighbours. It is never the word "new".

## Read first
`beel-2025-ai-scientist-novelty` in `research/notes` of the plugin's repository, read in full. A system checked
novelty by keyword search, took "no clear match" to mean "new", and marked 12 of 12 ideas as new; four were known
techniques. It is one system on one topic: it shows how the mistake happens, not how often.

## Before searching
Describe the thing in three lines, without its name:
- **What it does:** the mechanism.
- **What for:** the problem it answers or the use it has.
- **Where:** the setting, the users or the material.

A name someone just coined finds nothing. The mechanism finds neighbours.

## Find
1. **Wordings.** For each of the three lines write at least three: the field's own terms, the terms of a
   neighbouring field where the same mechanism may have another name, and the plain description. Ask what
   someone who built this ten years ago would have called it.
2. **Search every wording in more than one database:**
   `python3 -I $S/search.py "<wording>" --db all --brief`, by relevance, and again with `--sort cited`.
   `--db all` asks OpenAlex, Semantic Scholar, Crossref, Europe PMC, arXiv, DOAJ, Zenodo and CORE (CORE only with
   `CORE_API_KEY`); the Coverage line says which answered. OSF Preprints only when named (`--db osf`), with a
   short wording: it matches titles only. A wording that returns nothing is written down too.
3. **Follow the closest ones.** `python3 -I $S/citing.py --doi <DOI>` shows later work built on a neighbour.
   `python3 -I $S/foundations.py --doi <DOI> --doi <DOI>` shows what the neighbours cite in common: the field the
   thing belongs to, whatever it is called there.
4. **Outside the scholarly databases** when the thing is a product, a tool or a pattern: search the web for
   products, standards and code repositories, and find out who is behind each source (`rules.md`,
   "Non-academic sources"). No script here searches patents: say so under "Not checked".
5. **Read before listing.** Read at least the abstract of each candidate, and say how much you read. A title that
   sounds close is a lead, not a neighbour.

## Report
- **Nearest existing work,** closest first, one row each: citation · DOI · what it does · what is the same ·
  what differs · read (full text, abstract or title only). Three to seven neighbours are usually enough; if there
  are fewer than three, say how many wordings and databases that rests on.
- **What differs,** in one line per neighbour: the mechanism, the use or the setting. Say which of the three is
  the same and which is not.
- **Searched:** every wording, the databases that answered (the Coverage lines) and the date.
- **The words that are allowed:** "no closer work was found in <databases> with <wordings> on <date>". Not
  "new", "novel", "the first" or "nobody has": a search that finds nothing is not a finding that nothing exists.
- **Not checked:** for example patents, sources not in English, products with no paper.

## Save
When the user keeps the result, save it as `research/maps/<date>-prior-art-<name>.md` with the three lines, the
table, the searches and "Not checked". Neighbours the user keeps are added like literature
(`playbooks/literature.md`, "Add"). Add one line to `research/README.md`.
