# Web of Science Core Collection's coverage expansion: the forgotten Arts & Humanities Citation Index? (Liu, Ni & Hu, 2024)

- **Source:** Scientometrics 129(2): 933–955 · https://doi.org/10.1007/s11192-023-04917-w (accepted manuscript,
  arXiv:2312.05524; pages = PDF pages)
- **File:** `../papers/liu-2024-web-science-core-collections.pdf` (local only)
- **Licence:** arXiv non-exclusive licence: local only.
- **Evidence:** empirical · yearly publication counts in three Web of Science citation indexes, 2001–2020,
  collected on 15 October 2021 (p. 3).
- **Read:** the abstract, introduction, data and indicators (p. 2–5) and the main findings, discussion and first
  lines of the limitations (p. 18–20), on 2026-11-21. Not read: the results sections (p. 6–17) and the rest of the
  limitations.

## What it says
- Growth in a field's publication counts can be an artefact of the growth of the database itself (p. 2, 19).
- The result changes with the document types counted. Counting all document types, yearly volume in the Arts &
  Humanities Citation Index stayed about flat from 2001 to 2020; counting only citable items, it rose slightly
  (p. 18).
- Two databases gave different pictures of the same field: arts and humanities publications in Scopus grew 392%
  from 2001 to 2020, while the count in the Arts & Humanities Citation Index nearly stalled (p. 19).
- The authors name no gold standard that says which database is right (p. 20).

## What it means for the plugin
- A yearly count describes the database and the field together. `counts.py` saves the count with the database,
  the date and the document types, and `playbooks/trends.md` asks for a second database where one answers.
- The types counted change the result. A share uses the same types above and below the line, and the series
  records which.
- The study is on Web of Science, not on OpenAlex. It supports the caution by analogy; what OpenAlex documents
  about itself is in the OpenAlex note.

## Quotes
- "the growth of research output may also be an artifact caused by the expansion of the used database itself" (p. 2)
