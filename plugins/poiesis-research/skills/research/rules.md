# Rules (every playbook)

## Honesty
- Never invent a source, page, number, date or amount. Everything comes from a search result or a page or file
  you read; anything you remember but cannot confirm is marked "unconfirmed".
- A claim taken from a source names its page; a funding detail names its official page and the date checked.
- After writing notes, run `verify_citations.py` on them: every DOI must exist and match the note's title. Asking
  a model whether its citations are correct is not a check: it often answers wrongly (Walters & Wilder 2023).
- Report what sources say, as they say it (sample, effect size, limits). One study is not a consensus; say when
  sources disagree. Interpretation is left to the user.

## Quality
Start from the kind of evidence, then move each source up or down by its own quality (Murad et al. 2016):
1. Systematic reviews and meta-analyses: a lens on the studies they combine, as good as those studies
2. Validated measures (with agreement between coders) and experiments
3. Other empirical studies (survey, corpus, case): note the sample, language and medium
4. Theory: good for definitions, not proof
5. Popular or practitioner books: the origin of an idea, not evidence that it works

Down: bias, small or unrepresentative sample, imprecise or inconsistent results, a setting unlike the project's.
Up: large, consistent effects. Also check peer review, venue and retractions. Citations measure influence, not
quality (Aksnes et al. 2019), and counts differ by database, so give each database's count (Martín-Martín et al.
2021). For funding, only the official call page counts.

## Freshness
Papers age slowly; calls do not. Every funding result carries the date it was checked, and a saved call is
checked again on its official page before anyone relies on it.

## Copies
- Open copies (open access, repositories, author manuscripts, preprints, public domain) can be downloaded and kept.
- For the rest, the user gets a copy: a library, free digital lending, asking the author, or buying it. Never
  search, link or download from shadow libraries (Sci-Hub, LibGen, Anna's Archive, Z-Library), and never extract
  books from previews.
- Closed-licence files stay local: never committed to a public repository, never shipped with a product.
- Use public APIs and official sites; Google Scholar only through the user's own export.

## Where these rules come from
Notes in `research/notes` of the plugin's repository: Walters & Wilder 2023 (fabricated
citations), Murad et al. 2016 (evidence pyramid), Aksnes et al. 2019 (citations and quality), Martín-Martín et al.
2021 (database coverage), Culbert et al. 2025 (OpenAlex references), Small 1973 (co-citation), Wohlin 2014
(snowballing). The rest (licences, legal copies, freshness of calls) are product decisions.
