# An automated framework for assessing how well LLMs cite relevant medical references (Wu et al., 2025)

- **Source:** Nature Communications 16: 3615 · https://doi.org/10.1038/s41467-025-58551-6 (pages = PDF pages)
- **File:** `../papers/wu-2025-automated-framework-assessing-how.pdf` (local only)
- **Licence:** CC BY-NC-ND 4.0: kept local, not committed.
- **Evidence:** empirical · seven language models, 800 medical questions, about 58,000 pairs of a statement and a
  source; the automated check was compared with three doctors (p. 1–2).
- **Read:** full text, p. 1–9, on 2026-11-21. Not read: the supplementary tables and figures.

## What it says
- Between 50% and 90% of the models' responses were not fully supported by the sources they cited, and some were
  contradicted by them (p. 1).
- With web search, GPT-4o still left about 30% of single statements unsupported (p. 1), and 55% of its responses
  were fully supported (p. 2).
- Models without web access produced a working URL 40% to 70% of the time (p. 2).
- A statement counted as supported when at least one cited source contained text that supports it (p. 7).
- The automated check agreed with the doctors' consensus 88.7% of the time; the doctors agreed with each other
  86.1% of the time (p. 2).
- The study checks whether a statement is grounded in its source, not whether the statement is true (p. 5).
- A model could score perfectly by quoting its sources word for word, so the authors say the measure is not meant
  to be used alone (p. 6).
- Limits the authors state: each automated step can add errors, and doctors themselves disagree on the task
  (p. 6). The questions are medical and the models are those of the first half of 2024 (p. 6).

## What it means for the plugin
- A citation next to a claim does not show that the source says it. `verify_quotes.py` checks the part a script
  can check: that each quote in a note is in the source's text, on the page the note gives.
- A quote that is found shows the words are in the source. It does not show that the claim built on it follows.
  That judgement stays with the reader and with the challenge step in poiesis-insight.
- The rates come from medical questions put to 2024 models. They are a reason to check, not a rate for this plugin.

## Quotes
- "between 50% and 90% of LLM responses are not fully supported, and sometimes contradicted, by the sources they cite" (p. 1)
- "we emphasize verifying whether the LLMs' generated statements are grounded in verifiable sources rather than directly assessing the correctness of each claim" (p. 5)
