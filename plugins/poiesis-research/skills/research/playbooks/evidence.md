# Evidence

Whether data support a claim. Not what theorists argue (that is literature), but what was measured.

## Find
1. Turn the claim into testable questions: what is measured, on what, compared with what.
2. Search empirical work first:
   `python3 -I $S/search.py "<concept> meta-analysis" --sort cited --brief`, then the same with "experiment",
   "validation reliability", "dataset". Each line has a first guess of the evidence kind; confirm it from the
   abstract.
3. For each study: design, sample (size, language, setting), the key number (effect size or agreement between
   coders), limits. Say when you only read the abstract.

## Report
- **Verdict:** supported / mixed / not supported / not studied, and how close the evidence is to the project's
  setting.
- **Studies,** strongest first: citation · DOI · design and sample · key number · open or closed.
- **Datasets** the project could test itself against.
- **Not measured yet:** what no study covers.

## Add
Studies the user keeps are added like literature (`playbooks/literature.md`, "Add"), with the key number and its
page in the note.
