"""signals.py: one recorded scan of seven sources replayed, the window arithmetic, and what happens when a source
refuses. The recording was made on 2026-11-21 and trimmed with tests/trim_recordings.py."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from helpers import RECORDINGS, Answer, LayerCase, sc

import signals  # noqa: E402

EXPECTED = Path(__file__).resolve().parent / "expected" / "signals.txt"
SCAN = ['"brain-computer interface"', "--to", "2026-11-21", "--months", "6", "--wikipedia", "Brain–computer interface", "--hf", "EEG"]
JUDGEMENTS = ("emerging", "weak signal", "strong signal", "trend", "growing", "booming", "promising", "important", "significant", "surge", "hype")


class Window(unittest.TestCase):
    def test_months_back_keeps_the_day_or_the_month_s_last_one(self):
        self.assertEqual(signals.months_before(dt.date(2026, 11, 21), 6), dt.date(2026, 5, 21))
        self.assertEqual(signals.months_before(dt.date(2026, 8, 31), 6), dt.date(2026, 2, 28))
        self.assertEqual(signals.months_before(dt.date(2026, 1, 15), 2), dt.date(2025, 11, 15))
        self.assertEqual(signals.months_before(dt.date(2024, 3, 31), 1), dt.date(2024, 2, 29))
        self.assertEqual(signals.months_before(dt.date(2026, 12, 31), 12), dt.date(2025, 12, 31))

    def test_a_term_becomes_one_phrase(self):
        self.assertEqual(signals.phrase("brain-computer interface"), '"brain-computer interface"')
        self.assertEqual(signals.phrase('"already quoted"'), '"already quoted"')
        self.assertEqual(signals.phrase("neuromorphic"), "neuromorphic")


class NextId(unittest.TestCase):
    def test_the_next_id_is_one_more_than_the_highest_in_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertEqual(signals.next_id(folder), "SG-001")
            self.assertEqual(signals.next_id(folder / "missing"), "SG-001")
            (folder / "a.md").write_text("# A\n- **Id:** SG-001\n", encoding="utf-8")
            (folder / "b.md").write_text("# B\n- **Id:** SG-007\n- mentions SG-200 in passing\n", encoding="utf-8")
            self.assertEqual(signals.next_id(folder), "SG-008")


class Replay(LayerCase):
    def scan(self, *more: str) -> tuple[int, str, str]:
        return self.run_script(signals, [*SCAN, "--replay", str(RECORDINGS / "signals"), *more])

    def test_the_recorded_scan_gives_the_same_text_without_the_network(self):
        net = self.use([])
        code, text, err = self.scan()
        self.assertEqual((code, err, net.calls), (0, "", []))
        self.assertEqual(text, EXPECTED.read_text(encoding="utf-8"))

    def test_every_source_reports_counts_items_and_its_limits(self):
        code, text, _ = self.scan("--json")
        scan = json.loads(text)
        self.assertEqual(scan["window"], ["2026-05-21", "2026-11-21"])
        self.assertEqual(scan["asked"], "2026-11-21")
        self.assertEqual([b["source"] for b in scan["sources"]], ["arXiv", "Europe PMC", "NIH RePORTER", "OpenAIRE", "Hacker News", "Wikimedia pageviews", "Hugging Face"])
        for block in scan["sources"]:
            self.assertTrue(block["counts"], block["source"])
            self.assertTrue(block["items"], block["source"])
            self.assertTrue(block["limits"], block["source"])
            for item in block["items"]:
                self.assertRegex(item["date"], r"^\d{4}-\d{2}(-\d{2})?$", (block["source"], item))
        by = {b["source"]: b for b in scan["sources"]}
        self.assertEqual(by["arXiv"]["counts"], {"in the window": 157, "all dates": 1561})
        self.assertEqual(by["Europe PMC"]["counts"]["preprints in the window"], 48)
        self.assertEqual(by["NIH RePORTER"]["counts"]["fiscal year 2024"], 73)
        self.assertEqual(by["Hacker News"]["counts"], {"stories in the window": 14, "stories, all dates": 302})
        self.assertEqual(by["Wikimedia pageviews"]["counts"]["views in 2026-10"], 10362)
        self.assertEqual(by["Hugging Face"]["counts"]["models created in the window"], "100 or more")  # the list stops at 100
        self.assertEqual(scan["refused"], [])

    def test_the_output_reports_and_does_not_judge(self):
        _, text, _ = self.scan()
        # A title can hold any word, so the item lines are left out: the check is on the script's own words.
        own = "\n".join(line for line in text.lower().splitlines() if not line.startswith("  - "))
        for word in JUDGEMENTS:
            self.assertNotIn(word, own, word)

    def test_the_scan_is_saved_with_its_coverage_when_a_folder_is_given(self):
        code, text, _ = self.scan("--out", str(self.tmp / "signals"))
        saved = self.tmp / "signals" / "2026-11-21-brain-computer-interface.scan.json"
        self.assertTrue(saved.is_file())
        scan = json.loads(saved.read_text(encoding="utf-8"))
        self.assertIn("arXiv answered (2 requests", scan["coverage"])
        self.assertEqual(scan["script"], {"name": "signals.py", "plugin": "poiesis-research", "version": sc.VERSION})
        self.assertIn(f"Saved: {saved}", text)

    def test_wikimedia_is_not_asked_without_an_article_and_the_output_says_so(self):
        code, text, _ = self.run_script(signals, ['"brain-computer interface"', "--to", "2026-11-21", "--hf", "EEG", "--replay", str(RECORDINGS / "signals")])
        self.assertEqual(code, 0)
        self.assertIn('Not asked: Wikimedia pageviews (no article named: add --wikipedia "<title>")', text)
        self.assertIn("6 of 7 sources answered", text)
        self.assertNotIn("Wikimedia pageviews answered", text)


class Refusals(LayerCase):
    def test_a_source_that_refuses_is_named_and_the_others_still_answer(self):
        stories = Answer(json.dumps({"nbHits": 2, "hits": [{"title": "A story", "url": "https://example.org/a", "points": 5, "num_comments": 1, "created_at": "2026-10-01T00:00:00Z", "objectID": "1"}]}))
        self.use([("hn.algolia.com", stories), ("api.openaire.eu", Answer("", 429))])
        code, text, _ = self.run_script(signals, ["quantum sensing", "--to", "2026-11-21", "--sources", "hn,openaire"])
        self.assertEqual(code, 0)
        self.assertIn("stories in the window: 2", text)
        self.assertIn("OpenAIRE: refused.", text)
        self.assertIn("1 of 2 sources answered", text)
        last = text.strip().splitlines()[-1]
        self.assertIn("Hacker News answered (2 requests)", last)
        self.assertIn("OpenAIRE refused (HTTP 429", last)

    def test_an_article_title_that_does_not_exist_is_said_plainly(self):
        self.use([("wikimedia.org", Answer("", 404))])
        code, text, _ = self.run_script(signals, ["x", "--to", "2026-11-21", "--sources", "wikimedia", "--wikipedia", "No such article"])
        self.assertIn('no article with exactly this title: "No such article"', text)

    def test_an_unknown_source_is_an_error_before_anything_is_asked(self):
        net = self.use([])
        code, _, err = self.run_script(signals, ["x", "--sources", "dblp"])
        self.assertEqual((code, net.calls), (2, []))
        self.assertIn("unknown source: dblp", err)

    def test_nothing_personal_is_sent(self):
        net = self.use([("hn.algolia.com", Answer(json.dumps({"nbHits": 0, "hits": []})))])
        self.run_script(signals, ["x", "--to", "2026-11-21", "--sources", "hn"])
        for sent in net.sent:
            self.assertEqual(sent.get("User-agent"), "paper-research-skill/1.1")
            self.assertFalse([k for k in sent if k.lower() in ("from", "authorization", "cookie")])


if __name__ == "__main__":
    unittest.main()
