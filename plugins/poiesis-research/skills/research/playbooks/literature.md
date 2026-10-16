# Literature

What has been written on a topic: the field's founding works, the current methods, the best sources for a need.

## Find
1. Say the question in one line, and what the answer will be used for.
2. **Founding works first**, from the field's own citations, not from keywords (co-citation, Small 1973; starting
   from reference lists, Wohlin 2014):
   `python3 -I $S/foundations.py "<topic>"` reads the bibliographies of the most-cited works on the topic and
   lists the works they all cite. Try two or three wordings; if it warns that the seeds drifted, use the field's own
   term. Old books are indexed poorly: add the classics handbooks name, marked "from the literature".
3. **Current work:** `python3 -I $S/search.py "<query>" --sort cited --brief`, and the same by relevance. Each
   line shows citations, the evidence kind (review / empirical / analytical) and whether an open copy exists.
4. **Google Scholar** (optional, the widest coverage: 88% of citations vs 60% or less elsewhere, most in the
   humanities and older works; Martín-Martín et al. 2021): it can only be searched by hand. If the user exports
   results from Publish or Perish as CSV, combine them: `python3 -I $S/scholar_import.py export.csv`.

## Report
Two groups, founding works and current methods. For each source: citation, why it matters (citations, who cites
it), evidence kind, open or closed, what it would change. Then ask which ones to add.

## Add
1. **Copy:** `python3 -I $S/copies.py --doi <DOI> --download <temp folder>` saves the open copy when there is
   one; otherwise the user gets one (see `rules.md`). Move it to `research/papers/<section>/<slug>.pdf`
   (`firstauthor-year-short-title`).
2. **Text:** `python3 -I $S/extract_text.py <pdf>` writes the text next to it, with `[p. N]` page markers.
3. **Note:** write `research/notes/<section>/<slug>.md` from `templates/note.md`. Every claim has a page.
4. **Verify:** `python3 -I $S/verify_citations.py research/notes` checks that every DOI exists and matches its note.
5. **Index:** one line in `research/README.md` under its section.

## Use
When a decision rests on a source, cite the note and page where the decision is recorded. If no source supports
something, say so: it is a product decision, not a research finding.
