# Signals

What can be observed about a subject right now, outside the settled literature: new preprints, funded projects,
models and datasets, discussion, attention. A signal here is the observation only: what, where, when, how visible,
how widespread. What it means, where it leads and how much it matters are interpretation and are not written here
(see "Other Poiesis plugins" in `SKILL.md`).

## Read first
Two notes in `research/notes` of the plugin's repository:
- `go-science-2024-futures-toolkit`: the UK Government Office for Science's toolkit, of which only the section on
  horizon scanning was read. It is practitioner guidance, not evidence that scanning works. From it: a common
  record for every scan, a link to the original, and a count per kind of source so that one kind does not crowd
  out the rest.
- `signal-sources-2026-access`: what seven open sources document and what each returned on 2026-11-21.

## Find
1. Say the subject in the phrase its own field uses, and the window (six months unless the user says otherwise).
2. **Scan:**
   `python3 -I $S/signals.py '"<phrase>"' --months 6 --wikipedia "<exact article title>" --hf "<short word>" --out research/signals`

   | Source | What it shows | What "visible" means there |
   |---|---|---|
   | arXiv | preprints submitted in the window | nothing: it gives no citations or views |
   | Europe PMC | records and preprints first published in the window | nothing for new items |
   | NIH RePORTER | projects funded, by fiscal year | the award amount |
   | OpenAIRE | funded projects and publications | the funded amount |
   | Hacker News | stories posted in the window | points and comments |
   | Wikimedia | monthly views of one Wikipedia article | the views |
   | Hugging Face | models and datasets by name | downloads and likes |

   Each source prints its own limit: one funder, one forum, one article, names only. Hugging Face reads names, so
   give it the short word people put in a model's name. Without `--wikipedia` that source is not asked.
3. **Open the original** of each item you will report, and read at least its summary. A title in a list is a
   lead. Say how much you read.
4. **Scan wider than the script** when the subject lives elsewhere: standards bodies, regulators, company
   pages, sources not in English. Web search finds them; `rules.md`, "Non-academic sources", says how to check who
   is behind each. No script here searches patents: say so under "Not checked".
5. **Count by kind of source.** If every signal comes from one kind, say so: the scan is narrow.

## What a signal is, and is not
- One signal is one observed thing: an item, or a count of items of one kind in one source over one window.
- It has a date of its own (published, posted, funded, released) and the date it was looked up.
- Its numbers are the source's numbers, with the day they were read. Points, views and downloads change daily.
- It carries no adjective and no direction. "14 stories in six months, the newest with 1 point" is a signal.
  "Growing interest" is not: it is a reading of one.
- Looking and finding nothing is reported too, with the source and the window, in the report. It is not a
  signal note.
- Sources that refused are named. A source that was not asked is not a source with nothing.

## Report
- **Signals,** one row each: what · where (source and link) · when · how visible · how widespread · kind of
  source · read (the item in full, its summary, or title and numbers only). No cell contains a `|`.
- **By kind of source:** how many signals came from each kind.
- **Coverage:** the script's Coverage line, and any source that was not asked.
- **Not checked:** for example patents, sources not in English, the originals that were not opened.

## Save
One note per signal the user keeps: `research/signals/<date>-<short-name>.md` from `templates/signal.md`. Its id
comes from `python3 -I $S/signals.py --next-id research/signals` (SG-001, SG-002 and so on: a number is never
used twice). The scan file that `--out` saved stays next to the notes; each note names it. Add one line per
signal to `research/README.md`.
