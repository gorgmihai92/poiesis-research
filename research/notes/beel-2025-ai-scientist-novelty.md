# Evaluating Sakana's AI Scientist: Bold Claims, Mixed Results, and a Promising Future? (Beel, Kan & Baumgart, 2025)

- **Source:** ACM SIGIR Forum 59(1): 1–20 · https://doi.org/10.1145/3769733.3769747 (preprint arXiv:2502.14297v3,
  under an earlier title; pages = PDF pages of the preprint)
- **File:** `../papers/beel-2025-evaluating-sakanas-ai-scientist.pdf` (local only)
- **Licence:** arXiv non-exclusive licence: local only.
- **Evidence:** empirical, one case · one system, one research topic (green recommender systems), one dataset,
  12 ideas (p. 4–6, 9).
- **Read:** full text of the preprint, p. 1–15, on 2026-11-21. Not read: the reference list. The journal version
  was not compared with the preprint.

## What it says
- To decide whether an idea was new, the system searched Semantic Scholar, took up to 10 results per query for up
  to 10 rounds, and marked the idea new when it found no clear match (p. 6).
- It marked all 12 ideas as new: the 10 it generated and the 2 the authors supplied. Four of them were known
  techniques, among them micro-batching for stochastic gradient descent and adaptive learning rates (p. 6).
- The authors put this down to keyword matching in place of a synthesis of the research (p. 6).
- In earlier tests the system had sometimes marked an idea as not new, so "new" was not its only answer (p. 6,
  footnote 15).
- One generated manuscript did not cite existing papers that use the same term, e-fold cross-validation, although
  they were in Semantic Scholar (p. 7).
- Limits the authors state: one dataset, one research area, fixed seed ideas and one template (p. 9).

## What it means for the plugin
- A search that finds nothing is not a finding that nothing exists. `playbooks/prior-art.md` reports the nearest
  existing works and what differs, and never the word "new" by itself.
- The search goes by what the thing does and by the field's own terms, in more than one database, and the report
  says which databases answered.
- One system on one topic: it shows how the mistake happens, not how often.

## Quotes
- "If no clear matches are found, it assigns novel=True; otherwise, it may classify the idea as non-novel." (p. 6)
- "the AI Scientist classified all 10 generated ideas and both seed ideas as novel" (p. 6)
