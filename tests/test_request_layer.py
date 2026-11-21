"""The request layer in scholarly.py: cache, pacing, budget, refusals, record and replay, the Coverage line."""
import json
import os
import time
import unittest
import urllib.error

from helpers import Answer, LayerCase, sc

OA = "https://api.openalex.org/works"
BUDGET = {"x-ratelimit-remaining-usd": "0.0963", "x-ratelimit-limit-usd": "0.1", "x-ratelimit-cost-usd": "0.0001", "x-ratelimit-reset": "13036"}


class Cache(LayerCase):
    def test_second_request_is_answered_from_disk(self):
        net = self.use([("api.openalex.org", Answer('{"results": [1]}'))])
        self.assertEqual(sc.get(f"{OA}?filter=doi:10.1/x"), {"results": [1]})
        self.assertEqual(sc.get(f"{OA}?filter=doi:10.1/x"), {"results": [1]})
        self.assertEqual(len(net.calls), 1)
        self.assertEqual([e["how"] for e in sc.LAYER.events], ["network", "cache"])

    def test_the_answer_is_on_disk_before_the_run_ends(self):
        self.use([("api.openalex.org", Answer('{"results": [1]}'))])
        sc.get(f"{OA}?filter=doi:10.1/x")
        files = list((self.tmp / "cache" / "api.openalex.org").glob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertEqual(json.loads(files[0].read_text())["body"], '{"results": [1]}')

    def test_keys_and_email_are_never_written_or_part_of_the_cache_key(self):
        net = self.use([("api.openalex.org", Answer('{"ok": true}'))])
        sc.get(f"{OA}?search=x&api_key=SECRET-ONE&mailto=someone%40example.org")
        sc.get(f"{OA}?search=x&api_key=SECRET-TWO")  # another key, the same request
        self.assertEqual(len(net.calls), 1)
        stored = "".join(f.read_text() for f in (self.tmp / "cache").rglob("*.json"))
        for secret in ("SECRET-ONE", "SECRET-TWO", "someone", "mailto", "api_key"):
            self.assertNotIn(secret, stored)

    def test_fresh_asks_again_and_rewrites_the_cache(self):
        net = self.use([("api.openalex.org", [Answer('{"n": 1}'), Answer('{"n": 2}')])])
        sc.get(f"{OA}?filter=a")
        sc.configure(fresh=True)
        self.assertEqual(sc.get(f"{OA}?filter=a"), {"n": 2})
        sc.configure(fresh=False)
        self.assertEqual(sc.get(f"{OA}?filter=a"), {"n": 2})
        self.assertEqual(len(net.calls), 2)

    def test_an_answer_older_than_a_day_is_asked_again(self):
        net = self.use([("api.openalex.org", [Answer('{"n": 1}'), Answer('{"n": 2}')])])
        sc.get(f"{OA}?filter=a")
        path = next((self.tmp / "cache" / "api.openalex.org").glob("*.json"))
        entry = json.loads(path.read_text())
        entry["fetched"] = "2020-01-01T00:00:00Z"
        path.write_text(json.dumps(entry))
        self.assertEqual(sc.get(f"{OA}?filter=a"), {"n": 2})
        self.assertEqual(len(net.calls), 2)

    def test_not_found_is_an_answer_and_is_cached(self):
        net = self.use([("api.openalex.org", Answer("", 404))])
        self.assertEqual(sc.get(f"{OA}/doi:10.1/none"), {})
        self.assertEqual(sc.get(f"{OA}/doi:10.1/none"), {})
        self.assertEqual(len(net.calls), 1)
        self.assertFalse(sc.refused("OpenAlex"))

    def test_post_is_cached_by_its_body(self):
        net = self.use([("semanticscholar", Answer("[]"))])
        url = "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title"
        sc.post(url, {"ids": ["DOI:10.1/a"]})
        sc.post(url, {"ids": ["DOI:10.1/a"]})
        sc.post(url, {"ids": ["DOI:10.1/b"]})
        self.assertEqual(len(net.calls), 2)

    def test_the_cache_can_be_turned_off(self):
        net = self.use([("api.openalex.org", Answer("{}"))])
        sc.configure(cache_dir=None)
        sc.get(f"{OA}?filter=a")
        sc.get(f"{OA}?filter=a")
        self.assertEqual(len(net.calls), 2)
        self.assertFalse((self.tmp / "cache").exists())


class Secrets(LayerCase):
    """Found by the lab's review of 2026-11-21: keys were taken out of the address only."""

    def test_a_key_the_answer_repeats_is_not_stored_or_returned(self):
        key = "SECRET+KEY/123"  # as it is, and as an address carries it: SECRET%2BKEY%2F123
        echo = Answer(json.dumps({"meta": {"url": "/works?filter=a&api_key=SECRET%2BKEY%2F123", "note": f"your key is {key}"}, "results": [1]}))
        self.use([("api.openalex.org", echo)])
        sc.configure(record=self.tmp / "rec")
        got = sc.get(f"{OA}?filter=a&api_key=SECRET%2BKEY%2F123")
        self.assertEqual(got["results"], [1])
        stored = json.dumps(got) + "".join(f.read_text() for f in list((self.tmp / "cache").rglob("*.json")) + list((self.tmp / "rec").glob("*.json")))
        for form in (key, "SECRET%2BKEY%2F123", "SECRET"):
            self.assertNotIn(form, stored)
        self.assertIn("REDACTED", stored)

    def test_a_key_from_the_environment_that_travels_in_a_header_is_scrubbed_too(self):
        os.environ["S2_API_KEY"] = "S2-SECRET-999"
        try:
            self.use([("semanticscholar", Answer(json.dumps({"message": "your key S2-SECRET-999 is fine", "data": []})))])
            sc.configure(record=self.tmp / "rec")
            got = sc.s2_get("/paper/search", {"query": "x"})
            self.assertNotIn("S2-SECRET-999", json.dumps(got))
            stored = "".join(f.read_text() for f in list((self.tmp / "cache").rglob("*.json")) + list((self.tmp / "rec").glob("*.json")))
            self.assertNotIn("S2-SECRET-999", stored)
        finally:
            del os.environ["S2_API_KEY"]

    def test_an_answer_with_no_secret_in_it_is_kept_as_it_came(self):
        body = '{"results": [{"title": "a  title with  two spaces", "n": 1.50}]}'
        self.use([("api.openalex.org", Answer(body))])
        sc.get(f"{OA}?filter=a")
        entry = json.loads(next((self.tmp / "cache" / "api.openalex.org").glob("*.json")).read_text())
        self.assertEqual(entry["body"], body)


class ClearingTheCache(LayerCase):
    """Found by the same review: --clear removed the whole folder, with whatever else was in it."""

    def clear(self) -> str:
        import contextlib
        import io
        import sys
        out = io.StringIO()
        saved = sys.argv
        sys.argv = ["scholarly.py", "cache", "--clear"]
        try:
            with contextlib.redirect_stdout(out):
                sc.main()
        finally:
            sys.argv = saved
        return out.getvalue()

    def test_clearing_removes_the_answers_and_leaves_other_files_alone(self):
        self.use([("api.openalex.org", Answer("{}", head=BUDGET)), ("api.crossref.org", Answer('{"message": {}}'))])
        sc.get(f"{OA}?filter=a")
        sc.get("https://api.crossref.org/works/10.1/x")
        cache = self.tmp / "cache"
        (cache / "my-notes.txt").write_text("not the cache's", encoding="utf-8")
        (cache / "mine").mkdir()
        (cache / "mine" / "keep.json").write_text("{}", encoding="utf-8")
        (cache / "api.openalex.org" / "something-else.json").write_text("{}", encoding="utf-8")
        said = self.clear()
        self.assertEqual((cache / "my-notes.txt").read_text(encoding="utf-8"), "not the cache's")
        self.assertTrue((cache / "mine" / "keep.json").is_file())
        self.assertTrue((cache / "api.openalex.org" / "something-else.json").is_file())  # not a name the cache gives
        left = sorted(str(f.relative_to(cache)) for f in cache.rglob("*") if f.is_file())
        self.assertEqual(left, ["api.openalex.org/something-else.json", "mine/keep.json", "my-notes.txt"])
        self.assertFalse((cache / "api.crossref.org").exists())  # a folder the cache emptied is removed
        self.assertIn("Cleared 2 answers", said)
        self.assertIn("3 other files in the folder were left alone", said)

    def test_after_clearing_the_next_request_asks_again(self):
        net = self.use([("api.openalex.org", Answer("{}"))])
        sc.get(f"{OA}?filter=a")
        self.clear()
        sc.get(f"{OA}?filter=a")
        self.assertEqual(len(net.calls), 2)


class Refusals(LayerCase):
    def test_a_short_rate_limit_is_waited_out(self):
        self.use([("api.openalex.org", [Answer("", 429, {"Retry-After": "2"}), Answer('{"ok": 1}')])])
        self.assertEqual(sc.get(f"{OA}?filter=a"), {"ok": 1})
        self.assertIn(2.0, self.sleeps)
        self.assertFalse(sc.refused("OpenAlex"))

    def test_a_spent_daily_budget_stops_at_once_and_says_when_it_resets(self):
        self.use([("api.openalex.org", Answer('{"reason": "daily_budget"}', 429, {"Retry-After": "13036"}))])
        with self.assertRaises(sc.BudgetExhausted) as c:
            sc.get(f"{OA}?search=x")
        self.assertIn("resets in 3h37m", str(c.exception))
        self.assertIn("OPENALEX_API_KEY", str(c.exception))
        self.assertEqual(self.sleeps, [])  # no waiting for a budget that comes back in hours
        self.assertTrue(sc.refused("OpenAlex"))

    def test_after_the_budget_is_spent_paid_requests_are_not_sent_and_free_ones_are(self):
        net = self.use([("search=x", Answer('{"reason": "daily_budget"}', 429, {"Retry-After": "13036"})), ("doi:10.1/a", Answer('{"id": "W1"}'))])
        with self.assertRaises(sc.BudgetExhausted):
            sc.get(f"{OA}?search=x")
        with self.assertRaises(sc.BudgetExhausted):
            sc.get(f"{OA}?search=y")  # would cost $0.001: refused here, never sent
        self.assertEqual(net.count("search=y"), 0)
        self.assertEqual(sc.get(f"{OA}/doi:10.1/a"), {"id": "W1"})  # one record by DOI is free

    def test_another_process_learns_the_budget_from_the_shared_folder(self):
        self.use([("api.openalex.org", Answer("{}", head={**BUDGET, "x-ratelimit-remaining-usd": "0.0002"}))])
        sc.get(f"{OA}?filter=a")
        sc.LAYER.budget.clear()  # what a second process starts with
        net = self.use([])
        with self.assertRaises(sc.BudgetExhausted):
            sc.get(f"{OA}?search=z")
        self.assertEqual(net.calls, [])

    def test_a_request_that_needs_a_key_says_so(self):
        self.use([("cursor=abc", Answer('{"error": "API key required for cursor paging"}', 401))])
        with self.assertRaises(sc.NeedsKey) as c:
            sc.get(f"{OA}?group_by=primary_topic.id&cursor=abc")
        self.assertIn("OPENALEX_API_KEY", str(c.exception))

    def test_an_anti_bot_page_is_a_refusal_and_is_not_cached(self):
        net = self.use([("api.crossref.org", Answer("<html><title>Just a moment...</title></html>"))])
        for _ in range(2):
            with self.assertRaises(sc.Refused):
                sc.get("https://api.crossref.org/works?query.bibliographic=x")
        self.assertEqual(len(net.calls), 2)
        self.assertEqual(list((self.tmp / "cache").rglob("api.crossref.org/*.json")), [])

    def test_a_server_error_is_retried_then_raised(self):
        net = self.use([("api.crossref.org", Answer("", 503))])
        with self.assertRaises(urllib.error.HTTPError):
            sc.get("https://api.crossref.org/works?query.bibliographic=x", tries=3)
        self.assertEqual(len(net.calls), 3)
        self.assertTrue(sc.refused("Crossref"))

    def test_ask_turns_a_refusal_into_none(self):
        self.use([("api.crossref.org", Answer("", 503))])
        self.assertIsNone(sc.ask(sc.get, "https://api.crossref.org/works?query.bibliographic=x", tries=1))


class Budget(LayerCase):
    def test_the_remaining_budget_is_read_from_the_headers(self):
        self.use([("api.openalex.org", Answer("{}", head=BUDGET))])
        sc.get(f"{OA}?filter=a")
        seen = sc.budget()
        self.assertAlmostEqual(seen["remaining"], 0.0963)
        self.assertAlmostEqual(seen["limit"], 0.1)
        self.assertAlmostEqual(seen["reset_at"] - time.time(), 13036, delta=5)
        self.assertIn("OpenAlex budget left: $0.0963 of $0.10 a day.", sc.coverage_line())

    def test_what_a_request_costs_follows_the_documentation(self):
        self.assertEqual(sc.openalex_cost(f"{OA}/doi:10.1007/s11192-023-04917-w"), 0.0)
        self.assertEqual(sc.openalex_cost(f"{OA}?filter=publication_year:2024&group_by=type"), 0.0001)
        self.assertEqual(sc.openalex_cost(f"{OA}?search=kelp"), 0.001)
        self.assertEqual(sc.openalex_cost(f"{OA}?filter=title_and_abstract.search:kelp,type:article&group_by=publication_year"), 0.001)

    def test_no_email_is_sent_even_when_one_is_in_the_environment(self):
        os.environ["OPENALEX_MAILTO"] = "someone@example.org"
        try:
            net = self.use([("api.openalex.org", Answer('{"results": []}'))])
            sc.openalex_search("kelp")
            self.assertNotIn("mailto", net.calls[0])
            self.assertNotIn("someone", net.calls[0] + json.dumps(net.sent[0]))
        finally:
            del os.environ["OPENALEX_MAILTO"]


class Pacing(LayerCase):
    def test_the_gap_per_host_is_what_its_documentation_asks(self):
        self.assertEqual(sc.pace_seconds("export.arxiv.org"), 3.1)  # one request every three seconds
        self.assertEqual(sc.pace_seconds("api.crossref.org", "https://api.crossref.org/works?query.bibliographic=x"), 1.05)
        self.assertEqual(sc.pace_seconds("api.crossref.org", "https://api.crossref.org/works/10.1/x"), 0.25)
        self.assertEqual(sc.pace_seconds("api.openalex.org", f"{OA}?filter=type:article"), 0.2)
        broad = f"{OA}?search=a OR b OR c OR d OR e OR f OR g"
        self.assertEqual(sc.pace_seconds("api.openalex.org", broad), 1.1)
        wide = f"{OA}?filter=primary_topic.id:" + "|".join(f"T{i}" for i in range(12))
        self.assertEqual(sc.pace_seconds("api.openalex.org", wide), 1.1)

    def test_two_requests_to_one_host_are_spaced(self):
        self.use([("export.arxiv.org", Answer("<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>"))])
        sc.get_text("https://export.arxiv.org/api/query?id_list=1")
        self.assertEqual(self.sleeps, [])
        sc.get_text("https://export.arxiv.org/api/query?id_list=2")
        self.assertEqual(len(self.sleeps), 1)
        self.assertGreater(self.sleeps[0], 2.5)
        self.assertLessEqual(self.sleeps[0], 3.1)

    def test_an_answer_from_the_cache_does_not_wait(self):
        self.use([("export.arxiv.org", Answer("<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>"))])
        sc.get_text("https://export.arxiv.org/api/query?id_list=1")
        sc.get_text("https://export.arxiv.org/api/query?id_list=1")
        self.assertEqual(self.sleeps, [])


class RecordAndReplay(LayerCase):
    def test_a_recording_answers_without_the_network(self):
        net = self.use([("api.openalex.org", Answer('{"n": 1}', head=BUDGET))])
        sc.configure(record=self.tmp / "rec")
        sc.get(f"{OA}?filter=a&api_key=SECRET")
        recorded = list((self.tmp / "rec").glob("*.json"))
        self.assertEqual(len(recorded), 1)
        self.assertNotIn("SECRET", recorded[0].read_text())

        sc.LAYER = sc._Layer()
        sc.configure(cache_dir=self.tmp / "other-cache", replay=self.tmp / "rec")
        net = self.use([])
        self.assertEqual(sc.get(f"{OA}?filter=a"), {"n": 1})
        self.assertEqual(net.calls, [])
        self.assertEqual(sc.LAYER.events[-1]["how"], "replay")
        self.assertEqual(sc.last_fetched(), json.loads(recorded[0].read_text())["fetched"])

    def test_replay_never_falls_back_to_the_network(self):
        sc.configure(replay=self.tmp / "empty")
        net = self.use([("api.openalex.org", Answer("{}"))])
        with self.assertRaises(sc.ReplayMissing):
            sc.get(f"{OA}?filter=never-recorded")
        self.assertEqual(net.calls, [])

    def test_recording_also_keeps_what_the_cache_answered(self):
        self.use([("api.openalex.org", Answer('{"n": 1}'))])
        sc.get(f"{OA}?filter=a")
        sc.configure(record=self.tmp / "rec")
        sc.get(f"{OA}?filter=a")
        self.assertEqual(len(list((self.tmp / "rec").glob("*.json"))), 1)


class Coverage(LayerCase):
    def test_the_line_names_who_answered_who_refused_and_what_was_cached(self):
        self.use([("api.openalex.org", Answer("{}", head=BUDGET)), ("semanticscholar", Answer("", 429)), ("api.crossref.org", Answer('{"message": {"items": []}}'))])
        sc.get(f"{OA}?filter=a")
        sc.get(f"{OA}?filter=a")
        sc.get(f"{OA}?filter=b")
        self.assertIsNone(sc.ask(sc.get, "https://api.semanticscholar.org/graph/v1/paper/search?query=x", tries=1))
        sc.get("https://api.crossref.org/works?query.bibliographic=x")
        line = sc.coverage_line()
        self.assertRegex(line, r"^Coverage \(\d{4}-\d{2}-\d{2}\): ")
        self.assertIn("OpenAlex answered (3 requests, of which 1 from the cache)", line)
        self.assertIn("Semantic Scholar refused (HTTP 429", line)
        self.assertIn("Crossref answered (1 request)", line)

    def test_nothing_asked_means_no_line(self):
        self.assertEqual(sc.coverage_line(), "")

    def test_a_database_that_answered_and_then_refused_is_said_to_have_done_both(self):
        self.use([("filter=a", Answer("{}")), ("search=x", Answer('{"reason": "daily_budget"}', 429, {"Retry-After": "9000"}))])
        sc.get(f"{OA}?filter=a")
        with self.assertRaises(sc.BudgetExhausted):
            sc.get(f"{OA}?search=x")
        self.assertIn("OpenAlex answered (1 request) and refused (daily budget used up)", sc.coverage_line())


if __name__ == "__main__":
    unittest.main()
