# Rules (every playbook)

## Depth
Some rules hold at every depth; the rest are defaults, scaled to what is at stake. The user picks the depth, or the
project sets it with a `Depth:` line in its `CLAUDE.md` (read in every session, by every Poiesis plugin);
otherwise **standard**.
- **Always:** nothing invented; every claim cites its page; DOIs checked whenever notes are written; sources
  reported as they say it; who is behind a non-academic source; legal copies only; how much of each source was
  read; which databases answered; the same document types on both sides of a share; no step improvised.
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
- After writing notes, run `verify_citations.py` on them: each note's DOI, the one on its **Source** line, must
  exist and match the note's title. Asking a model whether its citations are correct is not a check: it often
  answers wrongly (Walters & Wilder 2023).
- ERROR means the registry did not answer: the notes have not passed; run the check again when it answers. UNREAD
  means a DOI on the Source line stands inside an address the script cannot read: write the DOI itself there.
- Report what sources say, as they say it (sample, effect size, limits). One study is not a consensus; say when
  sources disagree. Interpretation is left to the user.
- Search for the evidence against a claim as hard as for the evidence for it, and report both (Nickerson 1998).
- Say how much of each source was read: full text, part of the text, abstract only, or title only. "Title only"
  means the work exists; nothing more is claimed about it. A note carries it in its **Read** line and a table in
  its Read column.
- After writing notes, run `verify_quotes.py` on them: every quote must be in the source's text, on the page
  given. In one study between 50% and 90% of language models' answers were not fully supported by the sources they
  cited (Wu et al. 2025). A quote that is found shows the words are there; whether the claim follows is still
  yours to judge.
- Before a report goes out, `verify_quotes.py --references` lists its references that have no note. In one study
  three language models invented between 28.6% and 91.4% of the references they gave (Chelli et al. 2024).
- "Not found" is not "does not exist". Say what was searched and which databases answered: the Coverage line at
  the end of each script. A database that refused is named, not passed over.
- A row or a verdict that an agent returned is copied, not retyped. A verdict is written once.
- When a step has no playbook or script, stop and say what is missing. Offer an existing method used more
  narrowly, building the tool first, or skipping the step and recording it under "Not checked".

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

## Numbers
- A share counts the same document types above and below the line. In a recorded run the count of all OpenAlex
  works rose 29% in a year and the count of articles, reviews and preprints rose 18%, so a share of the second
  over the first fell without the field changing. `counts.py` computes no other kind of share.
- A partial year is marked and is not set beside a full year as if it were one.
- A series belongs to its database and its day: both are saved with it. A count describes the database and the
  field together (Liu, Ni & Hu 2024), so a second database is asked where one covers the subject.
- Report counts and shares. Growth rates, thresholds and the word "trend" are interpretation.

## Signals
A signal is what was observed: what, where, when, how visible, how widespread, with the source's own numbers and
the day they were read. It carries no adjective and no direction. What it means is interpretation and is left
out (the format follows the horizon-scanning record of the UK Futures Toolkit, which is guidance, not evidence).

## Calling something new
Before anything is called new, `playbooks/prior-art.md`: the nearest existing works and what differs. A search
that finds nothing is not a finding that nothing exists: one system that took it for one marked 12 of 12 ideas
as new, four of them known techniques (Beel, Kan & Baumgart 2025). The words "new", "novel" and "the first" are
not used; "no closer work was found in these databases with these wordings on this date" is.

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

Added in 2.4.0, each note saying how much of its source was read: Wu et al. 2025 (answers not supported by the
sources they cite; full text), Chelli et al. 2024 (invented references; full text of the accepted manuscript),
Beel, Kan & Baumgart 2025 (an empty search taken for novelty; full text of the preprint), Liu, Ni & Hu 2024
(counts and the database's own growth; part of the text), Robinson, Saldanha & Mckoy 2011 and Snilstveit et al.
2016 (the columns of the evidence table and the map; abstracts only), the UK Government Office for Science's
Futures Toolkit 2024 (the signal record; one section), the OpenAlex documentation and the access rules of the
other databases as read on 2026-11-21, and two recorded runs of the plugins (observations). Where the cache
lives, how long an answer is kept, the six-month signal window and the default document types are product
decisions.
