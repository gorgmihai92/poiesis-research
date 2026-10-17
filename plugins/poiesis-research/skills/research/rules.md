# Rules (every playbook)

## Depth
Some rules hold at every depth; the rest are defaults, scaled to what is at stake. The user picks the depth, or the
project's `research.config.md` sets it (`Depth:`); otherwise **standard**.
- **Always:** nothing invented; every claim cites its page; DOIs checked whenever notes are written; sources
  reported as they say it; who is behind a non-academic source; legal copies only.
- **Quick:** one search for the claim and one against it, from titles and abstracts; no forward citations or
  grouping.
- **Standard:** the playbook as written: searches for and against, forward citations for the 3–5 studies the verdict
  rests on, independent groups.
- **Thorough:** also forward citations for every study kept and every founding work, and full texts where an open
  copy exists.

A default may be skipped at any depth if the report says which one and why. Every report ends with **Not
checked:** what was skipped, or "nothing". These rules limit what is reported as true, never what may be explored.

## Honesty
- Never invent a source, page, number, date or amount. Everything comes from a search result or a page or file
  you read; anything you remember but cannot confirm is marked "unconfirmed".
- A claim taken from a source names its page; a funding detail names its official page and the date checked.
- After writing notes, run `verify_citations.py` on them: every DOI must exist and match the note's title. Asking
  a model whether its citations are correct is not a check: it often answers wrongly (Walters & Wilder 2023).
- Report what sources say, as they say it (sample, effect size, limits). One study is not a consensus; say when
  sources disagree. Interpretation is left to the user.
- Search for the evidence against a claim as hard as for the evidence for it, and report both (Nickerson 1998).

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

Count independent groups, not papers: studies that share authors, a dataset or a sample count once together.

## Non-academic sources
Reports, vendor surveys, blogs, documentation, standards, repositories and news can be used, but before relying on
one, find out who is behind it: leave the page and search what others say about the publisher, who funds it and
what it sells (lateral reading: fact checkers judged credibility better, in a fraction of the time, than historians
and students who stayed on the page; Wineburg & McGrew 2019). Name the publisher and its interest next to the
claim. A number from a party that profits from it is a lead, not evidence; documentation and standards count for
what they specify, not for whether it works.

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
citations), Nickerson 1998 (confirmation bias: search against the claim), Wineburg & McGrew 2019 (lateral
reading), Murad et al. 2016 (evidence pyramid), Aksnes et al. 2019 (citations and quality), Martín-Martín et al.
2021 (database coverage), Culbert et al. 2025 (OpenAlex references), Small 1973 (co-citation), Wohlin 2014
(snowballing, backward and forward). The rest (licences, legal copies, freshness of calls) are product decisions.
