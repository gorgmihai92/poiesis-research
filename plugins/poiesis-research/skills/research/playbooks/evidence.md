# Evidence

Whether data support a claim. Not what theorists argue (that is literature), but what was measured.

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
   coders), limits. Say when you only read the abstract.
6. **Independence:** `python3 -I $S/independence.py <DOI> <DOI> ...` on the studies kept groups those that share
   authors; check by hand whether groups share a dataset or sample. Count each group once.

## Report
- **Verdict:** supported / mixed / not supported / not studied, and how close the evidence is to the project's
  setting. Give the count as independent groups ("6 studies from 3 groups"), not papers.
- **Searched:** the queries for and against the claim, and the studies followed forward.
- **Studies,** strongest first: citation · DOI · design and sample · key number · open or closed · group.
- **Against:** replications that failed, critiques, null results, and what they found; "none found" when the
  search for them came back empty.
- **Datasets** the project could test itself against.
- **Not measured yet:** what no study covers.

## Add
Studies the user keeps are added like literature (`playbooks/literature.md`, "Add"), with the key number and its
page in the note.
