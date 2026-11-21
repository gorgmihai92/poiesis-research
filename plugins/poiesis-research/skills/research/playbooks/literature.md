# Literature

What has been written on a topic: the field's founding works, the current methods, the best sources for a need.

## Find
1. Say the question in one line, and what the answer will be used for.
2. **Founding works first**, from the field's own citations, not from keywords (co-citation, Small 1973; starting
   from reference lists, Wohlin 2014):
   `python3 -I $S/foundations.py "<topic>"` reads the bibliographies of the most-cited works on the topic and
   lists the works they all cite. Try two or three wordings; if it warns that the seeds drifted, use the field's own
   term. Old books are indexed poorly: add the classics handbooks name, marked "from the literature".
   Founding works are old and the most likely to have been revised since: for the ones the user keeps,
   `python3 -I $S/citing.py --doi <DOI>` shows later replications and critiques.
3. **Current work:** `python3 -I $S/search.py "<query>" --sort cited --brief`, and the same by relevance. Each
   line shows citations, the evidence kind (review / empirical / analytical) and whether an open copy exists.
4. **Google Scholar** (optional, the widest coverage: 88% of citations vs 60% or less elsewhere, most in the
   humanities and older works; Martín-Martín et al. 2021): it can only be searched by hand. If the user exports
   results from Publish or Perish as CSV, combine them: `python3 -I $S/scholar_import.py export.csv`.

## Report
Two groups, founding works and current methods. For each source: citation, why it matters (citations, who cites
it), evidence kind, open or closed, what it would change. Then ask which ones to add.

As a table, one row per source, in these columns. The first six are the same in every table this plugin makes for
sources, so rows can be copied from one report to the next without retyping:

| Citation | DOI | Verified | Read | What it says | Open copy | Kind | Cited | Group |
|---|---|---|---|---|---|---|---|---|

- **DOI:** the DOI itself, or "none". Never the address of a page or of a copy.
- **Verified:** how the work and its DOI were confirmed, naming the databases; "not verified" when nobody looked.
  Language models get the DOI wrong more often than any other part of a reference, even for real papers (Chelli et
  al. 2024), and a preprint's record can carry a mistyped one.
- **Read:** full text, part of the text, abstract only, or title only. "What it says" comes only from what was
  read; for "title only" it is "not read".
- **Open copy:** yes, no or unknown. **Kind:** review, empirical or analytical. **Cited:** the count in each
  database that gave one. **Group:** founding or current.
- No cell contains a `|`. Rows an agent returned are copied as they are.

End with the Coverage line of each script: the databases that answered and the ones that refused. Before saying a
work was not found, ask every database: `python3 -I $S/search.py "<title or query>" --db all --brief`.

## Add
1. **Copy:** `python3 -I $S/copies.py --doi <DOI> --download <temp folder>` saves the open copy when there is
   one; otherwise the user gets one (see `rules.md`). Move it to `research/papers/<section>/<slug>.pdf`
   (`firstauthor-year-short-title`).
2. **Text:** `python3 -I $S/extract_text.py <pdf>` writes the text next to it, with `[p. N]` page markers.
3. **Note:** write `research/notes/<section>/<slug>.md` from `templates/note.md`. Every claim has a page; "Later
   work" lists what `citing.py` found against it, with the date checked. The **Read** line says how much of the
   source was read: full text, part of the text (which pages), abstract only, or title only.
4. **Verify:** `python3 -I $S/verify_citations.py research/notes` checks that every DOI exists and matches its note.
   `python3 -I $S/verify_quotes.py research/notes` checks that every quote is in the source's text, on the page
   given. A quote that is NOT FOUND or on the WRONG PAGE is corrected from the source or removed, never reworded
   to fit. A quote that is found shows the words are there, not that the claim built on it follows (Wu et al.
   2025).
5. **Index:** one line in `research/README.md` under its section.

## Use
When a decision rests on a source, cite the note and page where the decision is recorded. If no source supports
something, say so: it is a product decision, not a research finding.

Before a report goes out, `python3 -I $S/verify_quotes.py --references <report.md>` lists its references that
have no note in the library. A reference with no note is added, or taken out of the report.
