# Trends

How many works a subject has, year by year, as counts and shares. Research reports the numbers and how they were
counted. Whether a series is a trend, and what it means, is interpretation: it is not part of this playbook (see
"Other Poiesis plugins" in `SKILL.md`).

## Read first
The rules below rest on three notes in `research/notes` of the plugin's repository. Each says how much of its
source was read.
- `poiesis-lab-2026-recorded-runs`: an observation. In one recorded run a share fell only because the database
  had added other kinds of records to its base.
- `openalex-2026-api-documentation`: OpenAlex's documentation as read on 2026-11-21: what a request costs, how
  works are typed, how topics are assigned and when that changed.
- `liu-2024-database-expansion`: a study of Web of Science, read in part. A count describes the database and the
  field together.

## Count
1. **Fix the slices before looking:** the words of each series, the years, the document types and the base.
   Changing one after seeing the numbers makes a new series, saved next to the first.
2. **A search:** `python3 -I $S/counts.py '"<phrase>" OR "<phrase>"' --label "<name>" --from <year>`. One search
   per series; phrases in double quotes. It looks in titles and abstracts.
   - Within a field instead of all works: add `--base '<search for the field>'`. Every series, a topic too, is
     then counted within that field, above the line as below it.
   - A topic of the OpenAlex taxonomy: `--topic T<id>`.
   - Every topic at once: `--taxonomy --from <year>`. Past the first 200 topics OpenAlex asks for a free key
     (`OPENALEX_API_KEY`). Without one the script saves those 200, says the scan is incomplete and exits with
     code 2. They are the first 200 by id, not the largest.
3. **A second database** when one covers the subject: the same search with `--db epmc` (Europe PMC: life
   sciences first). Two databases that disagree are both reported; neither is picked.
4. **Cost:** without a key OpenAlex gives $0.10 a day to everyone on the same network. A search series costs
   $0.001 and the base $0.0001. Answers are cached for a day, so a run that stopped can be run again at no cost.

## Rules
- **The same document types above and below the line.** A share is a count per 100,000 works of the base, and
  both count the same types: by default articles, reviews and preprints (`--types`). `counts.py` computes no other
  kind of share. The saved file also holds the share among all types, so the two can be compared.
- **The partial year is marked** and never set beside a full year as if it were one.
- **A series belongs to its database and its day.** OpenAlex retypes works and reassigns topics; it replaced its
  topic classifier in October 2026. Two series fetched on different days are two series: say both dates before
  putting them side by side, and do not join them.
- **"Not found" is not "does not exist".** The Coverage line says which databases answered. A count of zero in
  one database is a count of zero in that database.
- **No judgement words.** Report "rose from 21.7 to 25.4 per 100,000", not "is booming". Growth rates, thresholds
  and what counts as unusual are interpretation.

## Report
- **Series:** for each one, the count and the share in the first and the last full year, and the partial year
  apart.
- **How it was counted:** the database, the date fetched, the document types, the search field and the base, as
  the metadata file has them.
- **What the numbers cannot show:** the database of today, not that of each year; works the database does not
  hold; words the search does not match.
- **Not checked:** for example a second database, other wordings, or the taxonomy past 200 topics.

## Save
`counts.py` writes `research/data/<name>.csv` (one row per series and year), `<name>.types.csv` (every document
type, so another choice can be recomputed without a new request) and `<name>.meta.json` (the query, the database,
the date, the types, the script and its Coverage line). The default name is the first series and the date
fetched. The same command run again writes the same files; a different command never overwrites them and gets
`-2`, `-3` and so on. Add one line per series to `research/README.md`, with the database and the date.
