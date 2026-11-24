# Tests

Tests for the scripts in `plugins/poiesis-research/skills/research/scripts`. They need Python 3 only and never use
the network: a fake network serves canned answers, and `counts.py` replays recorded ones.

```
python3 -I -m unittest discover -s tests
```

This folder is not part of the plugin, so it is not installed with it.

| File | What it checks |
|---|---|
| `test_request_layer.py` | the request layer in `scholarly.py`: cache, pacing per host, the OpenAlex budget, refusals, record and replay, the Coverage line |
| `test_databases.py` | Crossref, Europe PMC and arXiv records, and each script when OpenAlex or Semantic Scholar refuses |
| `test_counts.py` | the share calculation against the lab's recorded run, and `counts.py` replaying recorded answers |
| `test_verify_quotes.py` | quotes found and not found in a source's text, and references with no note |
| `test_verify_citations.py` | which DOI a note is read as having (from its Source line: bare, after `doi.org/`, a publisher's `/doi/` or `doi:`), that the three scripts read DOIs alike, and the exit code, with the registry replaced by canned titles |
| `test_signals.py`, `test_library.py` | the signal sources and the library listing, on recorded answers |
| `test_open_sources.py` | DOAJ, OSF Preprints, Zenodo and CORE: their records, `search.py` and `counts.py` on recorded answers, CORE skipped without a key, and CORE's key kept out of every file and output |

## Fixtures and recordings

- `fixtures/` holds answers the databases gave on 2026-11-21, trimmed to the fields the scripts read. Abstracts
  are replaced by "Shortened for the test fixture.", because an abstract belongs to its authors or publisher.
  Everything else is as returned, including the arXiv record whose typed DOI lacks its last digit.
- `recordings/` holds whole answers saved by `counts.py --record` and `signals.py --record`, one file per request,
  with the address it was asked at (never a key) and the date. `--replay` reads them back.
- `texts/` holds a short text and notes written for the quote tests.
- `recordings/counts-epmc` is synthetic, for the test: eight answers written on 2026-11-26 in the shape Europe PMC
  answers, each marked `"synthetic"`. Their counts stand for nothing, and `expected/counts-epmc.csv` is what
  `counts.py --replay` saves from them.
- `recordings/open-sources`, `counts-doaj` and `counts-zenodo` were made on 2026-11-22 with no key, one small request
  each (and four per database for the counts), and trimmed. `fixtures/core-search-design-anthropology.json` is one
  keyless CORE answer of the same day, trimmed by hand: CORE is asked only with a key, and none was available.

The share test also reads `fixtures/trend-scan/` in the Poiesis Lab notebook, which is outside this repository. It
looks in the folder `POIESIS_LAB` names, then in `~/Poiesis Lab`. Where neither holds the notebook, that one test is
skipped and says so.
