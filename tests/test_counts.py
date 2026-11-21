"""counts.py: the share calculation, the files it saves, and replaying recorded answers.

The recordings in tests/recordings were made on 2026-11-21 with no OpenAlex key. The expected CSV files are what
that live run saved; a replay must give the same bytes, today and on any later day. recordings/counts-epmc is the
exception: synthetic, for the test (written on 2026-11-26, counts that stand for nothing), and expected/counts-epmc.csv
is what counts.py saves from it.
"""
import csv
import json
import os
import unittest
from pathlib import Path

from helpers import RECORDINGS, Answer, LayerCase, sc

import counts  # noqa: E402

EXPECTED = Path(__file__).resolve().parent / "expected"
SERIES = ['"solid-state battery"', '"quantum computing" OR "quantum computer"', "--label", "Solid-state batteries", "--label", "Quantum computing",
          "--from", "2015", "--to", "2026"]


def lab_fixtures() -> Path | None:
    """The trend-scan files of the Poiesis Lab notebook, which live outside this repository."""
    for root in (os.environ.get("POIESIS_LAB"), Path.home() / "Poiesis Lab"):
        if root and (Path(root) / "fixtures" / "trend-scan" / "openalex.json").is_file():
            return Path(root) / "fixtures" / "trend-scan"
    return None


class Shares(unittest.TestCase):
    def test_a_share_is_works_per_100_000_of_the_base(self):
        s = counts.share(counts.Counts(["article"], {2024: 50, 2025: 75}), counts.Counts(["article"], {2024: 1_000_000, 2025: 1_000_000}))
        self.assertEqual(s, {2024: 5.0, 2025: 7.5})

    def test_a_share_with_different_types_on_the_two_sides_is_refused(self):
        typed = counts.Counts(["article", "review", "preprint"], {2025: 4082})
        everything = counts.Counts(counts.ALL, {2025: 14226691})
        with self.assertRaises(ValueError) as c:
            counts.share(typed, everything)
        self.assertIn("same document types on both sides", str(c.exception))

    def test_the_order_of_the_types_does_not_matter(self):
        a = counts.Counts(["review", "article"], {2025: 1})
        b = counts.Counts(["article", "review"], {2025: 100000})
        self.assertEqual(counts.share(a, b), {2025: 1.0})

    def test_a_year_missing_from_the_series_counts_zero_and_an_empty_base_gives_no_share(self):
        s = counts.share(counts.Counts(counts.ALL, {2024: 3}), counts.Counts(counts.ALL, {2023: 10, 2024: 0}))
        self.assertEqual(s, {2023: 0.0, 2024: None})

    def test_select_adds_the_chosen_types_or_all_of_them(self):
        table = {2025: {"article": 10, "review": 2, "dataset": 30}}
        self.assertEqual(counts.select(table, ("article", "review"), range(2024, 2026)).by_year, {2024: 0, 2025: 12})
        self.assertEqual(counts.select(table, counts.ALL, range(2025, 2026)).by_year, {2025: 42})

    def test_the_year_being_fetched_is_partial(self):
        self.assertTrue(counts.is_partial(2026, "2026-11-17T20:24:00Z"))
        self.assertFalse(counts.is_partial(2025, "2026-11-17T20:24:00Z"))
        self.assertTrue(counts.is_partial(2027, "2026-11-17"))

    def test_the_lab_trend_scan_shares_are_reproduced_for_every_area_and_year(self):
        """Fed the counts the lab recorded on 2026-11-17, the calculation gives the published `share` (articles,
        reviews and preprints on both sides) and `share_all` (every type on both sides)."""
        folder = lab_fixtures()
        if folder is None:
            self.skipTest("the Poiesis Lab notebook is not on this machine: set POIESIS_LAB to its folder")
        data = json.loads((folder / "openalex.json").read_text(encoding="utf-8"))
        published = json.loads((folder / "series.json").read_text(encoding="utf-8"))["rows"]
        typed = ("article", "review", "preprint")  # what the run's second pass counted: type:article|review|preprint
        shares = {}
        for area, s in data["series"].items():
            shares[area] = (counts.share(counts.Counts(typed, s["typed"]), counts.Counts(typed, data["total"]["typed"])),
                            counts.share(counts.Counts(counts.ALL, s["broad"]), counts.Counts(counts.ALL, data["total"]["all"])))
        self.assertEqual(len(published), 85)  # 5 areas, 2010 to 2026
        checked = 0
        for row in published:
            share, share_all = shares[row["area_id"]]
            self.assertEqual(round(share[row["year"]], 2), row["share"], f"share, {row['area_id']} {row['year']}")
            self.assertEqual(round(share_all[row["year"]], 2), row["share_all"], f"share_all, {row['area_id']} {row['year']}")
            self.assertEqual(counts.is_partial(row["year"], data["fetched"]), row["partial"], f"partial, {row['area_id']} {row['year']}")
            checked += 1
        self.assertEqual(checked, 85)
        # The same data shows why the rule exists: with every type in the base, solid-state batteries fall in 2025.
        ssb, ssb_all = shares["ssb"]
        self.assertGreater(ssb[2025], ssb[2024])
        self.assertLess(ssb_all[2025], ssb_all[2024])


class Queries(unittest.TestCase):
    def test_a_search_is_asked_in_titles_and_abstracts_and_within_the_base_when_there_is_one(self):
        self.assertEqual(counts.search_filter('"heat stroke"', None), 'title_and_abstract.search:"heat stroke"')
        self.assertEqual(counts.search_filter('"heat stroke"', "heat OR temperature"), 'title_and_abstract.search:(heat OR temperature) AND ("heat stroke")')

    def test_a_europe_pmc_query_is_built_from_plain_words_or_used_as_written(self):
        self.assertEqual(counts.epmc_query('"heat stroke" OR dehydration'), 'TITLE_ABS:"heat stroke" OR TITLE_ABS:dehydration')
        self.assertEqual(counts.epmc_query("(heat OR temperature) AND athletes"), "( TITLE_ABS:heat OR TITLE_ABS:temperature ) AND TITLE_ABS:athletes")
        self.assertEqual(counts.epmc_query('TITLE_ABS:"heat" AND SRC:MED'), 'TITLE_ABS:"heat" AND SRC:MED')

    def test_a_topic_id_is_read_from_an_id_or_an_address(self):
        self.assertEqual(counts.topic_id("https://openalex.org/T10001"), "T10001")
        self.assertEqual(counts.topic_id("t10200"), "T10200")
        with self.assertRaises(SystemExit):
            counts.topic_id("quantum computing")


class Replay(LayerCase):
    def run_counts(self, args: list[str], out: Path) -> tuple[int, str, str]:
        return self.run_script(counts, [*args, "--out", str(out)])

    def test_recorded_answers_give_the_same_files_twice_and_what_the_live_run_saved(self):
        first, second = self.tmp / "one", self.tmp / "two"
        for out in (first, second):
            sc.LAYER = sc._Layer()
            sc.configure(cache_dir=self.tmp / "cache")
            net = self.use([])  # any request to the network fails the test
            code, text, err = self.run_counts([*SERIES, "--replay", str(RECORDINGS / "counts-series")], out)
            self.assertEqual((code, err, net.calls), (0, "", []))
        for name in ("solid-state-batteries-2026-11-21.csv", "solid-state-batteries-2026-11-21.types.csv", "solid-state-batteries-2026-11-21.meta.json"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)
        self.assertEqual((first / "solid-state-batteries-2026-11-21.csv").read_bytes(), (EXPECTED / "counts-series.csv").read_bytes())
        self.assertEqual((first / "solid-state-batteries-2026-11-21.types.csv").read_bytes(), (EXPECTED / "counts-series.types.csv").read_bytes())
        self.assertIn("OpenAlex answered (3 requests, of which 3 from a recording)", text)
        self.assertIn("Coverage (2026-11-21)", text)  # the date the answers were fetched, not the day of the replay

    def test_the_metadata_says_what_a_reader_needs_to_trust_the_series(self):
        self.run_counts([*SERIES, "--replay", str(RECORDINGS / "counts-series")], self.tmp / "out")
        meta = json.loads((self.tmp / "out" / "solid-state-batteries-2026-11-21.meta.json").read_text())
        self.assertEqual(meta["database"], "OpenAlex")
        self.assertEqual(meta["fetched"], "2026-11-21")
        self.assertEqual(meta["partial_years"], [2026])
        self.assertEqual(meta["share"]["numerator_types"], ["article", "preprint", "review"])
        self.assertEqual(meta["share"]["numerator_types"], meta["share"]["denominator_types"])
        self.assertEqual(meta["series"][1]["search"], '"quantum computing" OR "quantum computer"')
        self.assertEqual(meta["script"]["name"], "counts.py")
        self.assertEqual(meta["script"]["version"], sc.VERSION)
        self.assertEqual(len(meta["script"]["sha256"]), 64)
        self.assertNotIn("--replay", meta["script"]["command"])  # where files are read from does not change the numbers
        self.assertTrue(meta["complete"])
        self.assertIn("Coverage (2026-11-21): OpenAlex answered", meta["coverage"])

    def test_the_rows_carry_both_shares_and_mark_the_partial_year(self):
        self.run_counts([*SERIES, "--replay", str(RECORDINGS / "counts-series")], self.tmp / "out")
        with (self.tmp / "out" / "solid-state-batteries-2026-11-21.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 24)
        r = {(x["series"], x["year"]): x for x in rows}
        self.assertEqual(r[("solid-state-batteries", "2026")]["partial"], "true")
        self.assertEqual(r[("solid-state-batteries", "2025")]["partial"], "false")
        for x in rows:  # each share is its own count over its own base, never one over the other
            self.assertAlmostEqual(float(x["share_per_100k"]), 1e5 * int(x["count"]) / int(x["base"]), places=3)
            self.assertAlmostEqual(float(x["share_all_types_per_100k"]), 1e5 * int(x["count_all_types"]) / int(x["base_all_types"]), places=3)
            self.assertLessEqual(int(x["count"]), int(x["count_all_types"]))
        # Recorded on 2026-11-21: among the same types the share rose from 2024 to 2025; among all types it fell.
        a, b = r[("solid-state-batteries", "2024")], r[("solid-state-batteries", "2025")]
        self.assertGreater(float(b["share_per_100k"]), float(a["share_per_100k"]))
        self.assertLess(float(b["share_all_types_per_100k"]), float(a["share_all_types_per_100k"]))

    def test_without_a_key_the_taxonomy_stops_after_200_topics_and_says_so(self):
        net = self.use([])
        code, text, err = self.run_counts(["--taxonomy", "--from", "2025", "--to", "2026", "--replay", str(RECORDINGS / "counts-taxonomy")], self.tmp / "out")
        self.assertEqual((code, net.calls), (2, []))  # saved, and marked incomplete
        saved = self.tmp / "out" / "taxonomy-2025-2026-2026-11-21.csv"
        self.assertEqual(saved.read_bytes(), (EXPECTED / "counts-taxonomy.csv").read_bytes())
        meta = json.loads(saved.with_name("taxonomy-2025-2026-2026-11-21.meta.json").read_text())
        self.assertFalse(meta["complete"])
        self.assertEqual(meta["topics"], {"fetched": 200, "documented": 4516})
        self.assertIn("API key required for cursor paging", meta["stopped"])
        self.assertIn("Topics: 200 of 4516 documented", text)
        self.assertIn("The topics saved are the first 200 by id, not the largest.", text)
        self.assertIn("OpenAlex answered (2 requests, of which 2 from a recording) and refused (needs a key)", text)

    def test_europe_pmc_counts_one_year_at_a_time_within_a_base(self):
        """The Europe PMC answers are synthetic, for the test: written on 2026-11-26 in the shape Europe PMC answered
        on 2026-11-21, with counts that stand for nothing."""
        code, text, _ = self.run_counts(['"heat stroke"', "--base", "heat OR temperature", "--db", "epmc", "--from", "2023", "--to", "2026",
                                         "--replay", str(RECORDINGS / "counts-epmc")], self.tmp / "out")
        self.assertEqual(code, 0)
        self.assertEqual((self.tmp / "out" / "heat-stroke-2026-11-26.csv").read_bytes(), (EXPECTED / "counts-epmc.csv").read_bytes())
        self.assertFalse((self.tmp / "out" / "heat-stroke-2026-11-26.types.csv").exists())  # Europe PMC is not split by OpenAlex's types
        self.assertIn("Europe PMC answered (8 requests", text)

    def test_a_request_missing_from_the_recording_stops_the_run_and_never_uses_the_network(self):
        net = self.use([("api.openalex.org", Answer("{}"))])
        code, text, err = self.run_counts(['"something never recorded"', "--from", "2015", "--to", "2026", "--replay", str(RECORDINGS / "counts-series")], self.tmp / "out")
        self.assertEqual((code, net.calls), (2, []))
        self.assertIn("not in the recording", err)


class StoppingHalfway(LayerCase):
    def table(self, n: int) -> Answer:
        groups = [{"key": str(y), "key_display_name": str(y), "count": n, "groups": [{"key": "https://openalex.org/types/article", "key_display_name": "article", "count": n}]}
                  for y in (2024, 2025)]
        return Answer(json.dumps({"meta": {"count": 2 * n}, "group_by": groups}), head={"x-ratelimit-remaining-usd": "0.0500", "x-ratelimit-limit-usd": "0.1", "x-ratelimit-reset": "9000"})

    def test_what_arrived_before_a_refusal_is_on_disk_and_marked_incomplete(self):
        spent = Answer('{"reason": "daily_budget"}', 429, {"Retry-After": "9000"})
        self.use([("search%3Asecond", spent), ("search%3Afirst", self.table(5)), ("api.openalex.org", self.table(1000))])
        code, text, err = self.run_script(counts, ["first", "second", "--from", "2024", "--to", "2025", "--out", str(self.tmp / "out")])
        self.assertEqual(code, 2)
        self.assertIn("Stopped: api.openalex.org: daily free budget used up", err)
        self.assertIn("2 rows are saved", err)
        name = next(f.name for f in (self.tmp / "out").glob("first-*.csv") if not f.name.endswith(".types.csv"))
        rows = (self.tmp / "out" / name).read_text().splitlines()
        self.assertEqual(len(rows), 3)  # the header and the two years of the series that arrived
        meta = json.loads(next((self.tmp / "out").glob("first-*.meta.json")).read_text())
        self.assertFalse(meta["complete"])
        self.assertIn("daily free budget used up", meta["stopped"])
        self.assertIn("OpenAlex answered (2 requests) and refused (daily budget used up)", meta["coverage"])

    def test_the_second_run_pays_only_for_what_is_missing(self):
        spent = Answer('{"reason": "daily_budget"}', 429, {"Retry-After": "9000"})
        self.use([("search%3Asecond", spent), ("search%3Afirst", self.table(5)), ("api.openalex.org", self.table(1000))])
        self.run_script(counts, ["first", "second", "--from", "2024", "--to", "2025", "--out", str(self.tmp / "out")])
        sc.LAYER = sc._Layer()
        sc.configure(cache_dir=self.tmp / "cache")
        (self.tmp / "cache" / "budget").joinpath("api.openalex.org.nokey.json").unlink()  # a new day: the budget is back
        net = self.use([("search%3Asecond", self.table(7)), ("api.openalex.org", self.table(1000))])
        code, text, err = self.run_script(counts, ["first", "second", "--from", "2024", "--to", "2025", "--out", str(self.tmp / "out")])
        self.assertEqual(code, 0)
        self.assertEqual(len(net.calls), 1)  # the base and the first series came from the cache
        self.assertIn("of which 2 from the cache", text)

    def test_an_answer_that_is_not_split_by_type_is_refused_not_read_as_zero(self):
        flat = Answer(json.dumps({"meta": {"count": 10}, "group_by": [{"key": "2025", "key_display_name": "2025", "count": 10}]}))
        self.use([("api.openalex.org", flat)])
        code, text, err = self.run_script(counts, ["anything", "--from", "2025", "--to", "2025", "--out", str(self.tmp / "out")])
        self.assertEqual(code, 2)
        self.assertIn("without the split by document type", err)
        self.assertFalse((self.tmp / "out").exists() and any((self.tmp / "out").iterdir()))

    def test_a_topic_within_a_base_is_counted_within_that_base(self):
        """Found by the lab's review of 2026-11-21: the topic was counted in all works and divided by the base."""
        net = self.use([("api.openalex.org", self.table(40))])
        code, text, err = self.run_script(counts, ["--topic", "T10001", "--label", "A topic", "--base", "heat", "--from", "2024", "--to", "2025",
                                                   "--out", str(self.tmp / "out")])
        self.assertEqual(code, 0, err)
        topic_calls = [u for u in net.calls if "primary_topic.id%3AT10001" in u]
        self.assertEqual(len(topic_calls), 1)
        self.assertIn("title_and_abstract.search%3Aheat", topic_calls[0])  # the same base as below the line
        meta = json.loads(next((self.tmp / "out").glob("*.meta.json")).read_text())
        self.assertEqual(meta["series"][0]["filter"], "primary_topic.id:T10001,title_and_abstract.search:heat")
        self.assertEqual(meta["base"]["filter"], "publication_year:2024-2025,title_and_abstract.search:heat")

    def test_a_base_with_the_taxonomy_is_refused_not_ignored(self):
        net = self.use([])
        code, text, err = self.run_script(counts, ["--taxonomy", "--base", "heat", "--from", "2025", "--to", "2025", "--out", str(self.tmp / "out")])
        self.assertEqual((code, net.calls), (2, []))
        self.assertIn("--base does not combine with --taxonomy", err)

    def test_the_metadata_does_not_say_that_quotes_turn_stemming_off(self):
        """Found by the same review: a quoted singular and its plural gave the same counts on 2026-11-21."""
        self.use([("api.openalex.org", self.table(40))])
        self.run_script(counts, ['"solid-state battery"', "--from", "2024", "--to", "2025", "--out", str(self.tmp / "out")])
        field = json.loads(next((self.tmp / "out").glob("*.meta.json")).read_text())["search_field"]
        self.assertNotIn("unless quoted", field)
        self.assertIn("stems words, inside double quotes too", field)
        self.assertIn("title_and_abstract.search", field)

    def test_the_metadata_names_the_documented_exception_to_stemming(self):
        """Seen on 2026-11-21: "theory of mind" and "theories of mind", both quoted, gave different counts."""
        self.use([("api.openalex.org", self.table(40))])
        self.run_script(counts, ['"theory of mind"', "--from", "2024", "--to", "2025", "--out", str(self.tmp / "out")])
        field = json.loads(next((self.tmp / "out").glob("*.meta.json")).read_text())["search_field"]
        self.assertIn("a short quoted phrase that holds a stop word", field)
        self.assertIn("matched as typed", field)

    def test_the_europe_pmc_metadata_says_what_was_seen_not_more(self):
        self.use([("europepmc", Answer(json.dumps({"hitCount": 7})))])
        self.run_script(counts, ["possum", "--db", "epmc", "--from", "2024", "--to", "2025", "--out", str(self.tmp / "out")])
        field = json.loads(next((self.tmp / "out").glob("*.meta.json")).read_text())["search_field"]
        self.assertNotIn("no stemming", field)  # a rule of the database that nobody read
        self.assertIn("on 2026-11-21 a singular and its plural gave different counts", field)

    def test_a_second_run_with_other_series_does_not_overwrite_the_first(self):
        self.use([("api.openalex.org", self.table(40))])
        out = self.tmp / "out"
        self.run_script(counts, ["first", "second", "--from", "2024", "--to", "2025", "--out", str(out)])
        before = {f.name: f.read_bytes() for f in out.iterdir()}
        code, text, err = self.run_script(counts, ["first", "third", "--from", "2024", "--to", "2025", "--out", str(out)])
        self.assertEqual(code, 0, err)
        for name, data in before.items():
            self.assertEqual((out / name).read_bytes(), data, name)  # the first run's files are as they were
        metas = sorted(f.name for f in out.glob("*.meta.json"))
        self.assertEqual(len(metas), 2, metas)
        searches = [[s["search"] for s in json.loads((out / m).read_text())["series"]] for m in metas]
        self.assertIn(["first", "second"], searches)
        self.assertIn(["first", "third"], searches)
        self.assertIn("kept under a new name", text)

    def test_the_same_command_again_writes_the_same_files(self):
        self.use([("api.openalex.org", self.table(40))])
        out = self.tmp / "out"
        for _ in range(2):
            code, _, err = self.run_script(counts, ["first", "second", "--from", "2024", "--to", "2025", "--out", str(out)])
            self.assertEqual(code, 0, err)
        self.assertEqual(len(list(out.glob("*.meta.json"))), 1)

    def test_a_name_the_user_gave_is_used_as_given(self):
        self.use([("api.openalex.org", self.table(40))])
        out = self.tmp / "out"
        self.run_script(counts, ["first", "--from", "2024", "--to", "2025", "--out", str(out), "--name", "mine"])
        self.run_script(counts, ["other", "--from", "2024", "--to", "2025", "--out", str(out), "--name", "mine"])
        self.assertEqual(sorted(f.name for f in out.iterdir()), ["mine.csv", "mine.meta.json", "mine.types.csv"])

    def test_types_are_openalex_s_and_are_refused_with_europe_pmc(self):
        code, text, err = self.run_script(counts, ["x", "--db", "epmc", "--types", "article", "--out", str(self.tmp / "out")])
        self.assertEqual(code, 2)  # argparse's own exit code for a wrong argument
        self.assertIn("--types names OpenAlex's document types", err)


if __name__ == "__main__":
    unittest.main()
