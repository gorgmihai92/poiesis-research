# Hallucination Rates and Reference Accuracy of ChatGPT and Bard for Systematic Reviews: Comparative Analysis (Chelli et al., 2024)

- **Source:** Journal of Medical Internet Research 26: e53164 · https://doi.org/10.2196/53164 (pages = PDF pages of
  the accepted manuscript on JMIR Preprints)
- **File:** `../papers/chelli-2024-hallucination-rates-reference-accuracy.pdf` (local only)
- **Licence:** the copy read is the accepted manuscript, © the authors: local only. OpenAlex lists the published
  article as CC BY.
- **Evidence:** empirical · 471 references returned by three language models for 11 systematic reviews on rotator
  cuff pathology (p. 11).
- **Read:** full text of the accepted manuscript (p. 7–14) and the published abstract, on 2026-11-21. Not read:
  the tables, figures and appendix. The manuscript was not compared line by line with the published article.

## What it says
- A reference counted as hallucinated when two of these three were wrong: title, first author, year (p. 10).
- Hallucinated references: 39.6% for GPT-3.5, 28.6% for GPT-4 and 91.4% for Bard (p. 11).
- Of the references the models returned, 9.4% (GPT-3.5), 13.4% (GPT-4) and 0% (Bard) were in the original reviews
  (p. 11).
- Among the real references returned by GPT-3.5 and GPT-4, the title was right in 98.8% of cases and the DOI in
  15.9% and 20.2% (p. 11).
- In none of the queries did a model ask the user to verify the references (p. 12).
- Limits the authors state: one topic, three models as they were in July 2023, and prompts that could be written
  differently (p. 11, 13).

## What it means for the plugin
- A reference in a report is checked against the library: `verify_quotes.py --references` lists the references
  that have no note, and `verify_citations.py` checks each note's DOI in the registry.
- The DOI was the field the models got wrong most often, even for papers that exist. The scouts give the DOI and
  say how it was verified; a DOI nobody looked up is marked as such.
- The rates come from 2023 models on one medical topic. They are a reason to check, not a rate for this plugin.

## Quotes
- "Articles were considered hallucinated if any two of the following information were wrong: title, first author, or year of publication." (p. 10)
