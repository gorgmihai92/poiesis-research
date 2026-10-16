# Reference Coverage Analysis of OpenAlex compared to Web of Science and Scopus (Culbert et al., 2025)

- **Source:** Scientometrics (2025); preprint arXiv:2401.16359 · https://doi.org/10.48550/arXiv.2401.16359 (pages = PDF pages)
- **File:** `../papers/culbert-2025-openalex-reference-coverage.pdf`
- **Licence:** arXiv non-exclusive licence: local only.
- **Evidence:** empirical · 16.8 million recent publications indexed in all three databases (p. 1).

## What it says
- OpenAlex has average reference counts and internal coverage comparable to Web of Science and Scopus (p. 1).
- It has fewer abstracts than both, more ORCID identifiers, and similar open-access information (p. 1).
- OpenAlex changes quickly, so the trustworthiness of its data is an open question (p. 1).

## What it means for the plugin
- Supports reading seed bibliographies from OpenAlex for the founding-works step (its reference lists are as
  complete as the commercial databases' for recent work).
- Fewer abstracts means the evidence-kind guess (from title and abstract) more often has nothing to read: those
  works show "unknown" and must be classified by reading.
- Results can drift as OpenAlex changes: notes record the date of a search.

## Quotes
- "OpenAlex has average source reference numbers and internal coverage rates comparable to both Web of Science and Scopus." (p. 1)
