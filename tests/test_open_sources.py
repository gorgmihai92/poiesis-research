"""DOAJ, OSF Preprints, Zenodo and CORE: their records, search.py and counts.py on recorded answers, and CORE's key.

The recordings in recordings/open-sources, counts-doaj and counts-zenodo were made on 2026-11-22 with no key and
trimmed with tests/trim_recordings.py. CORE's fixture is one keyless answer of the same day, trimmed by hand: CORE
is asked only with a key, and no key was available to record with (tests/README.md).
"""
import json
import os
import unittest
from pathlib import Path

from helpers import RECORDINGS, Answer, LayerCase, fixture, sc

import counts  # noqa: E402
import search  # noqa: E402

EXPECTED = Path(__file__).resolve().parent / "expected"
OPEN = RECORDINGS / "open-sources"
KEY = "CORE-SECRET-123/abc+def"


def recorded(prefix: str) -> dict:
    """The body of the one recording in recordings/open-sources whose name starts with `prefix`."""
    (path,) = OPEN.glob(f"{prefix}-*.json")
    return json.loads(json.loads(path.read_text(encoding="utf-8"))["body"])


class Records(unittest.TestCase):
    def test_a_doaj_article_is_an_open_copy_and_its_doi_is_the_landing_page(self):
        first, second, _ = [sc.norm_doaj(r) for r in recorded("doaj.org")["results"]]
        self.assertEqual((first["title"], first["year"], first["venue"][:30], first["type"]), ("Monumento de Vanguardia", 2021, "Anales del Instituto de Arte A", "article"))
        self.assertEqual((first["doi"], first["oa_status"], first["landing"]), (None, "open", "https://www.iaa.fadu.uba.ar/ojs/index.php/anales/article/view/78"))
        self.assertEqual(second["doi"], "10.6209/jories.202603_71(1).0009")
        self.assertEqual(second["landing"], "https://doi.org/10.6209/jories.202603_71(1).0009")
        self.assertTrue(first["doaj"])

    def test_doaj_authors_and_abstract_are_read_when_the_answer_has_them(self):
        w = sc.norm_doaj({"id": "x", "bibjson": {"title": "A <i>title</i>", "year": "2024", "author": [{"name": "A. Author"}, {"affiliation": "no name"}],
                                                 "abstract": "\nSome words.\n", "identifier": [{"type": "DOI", "id": "https://doi.org/10.1/ABC"}]}})
        self.assertEqual((w["title"], w["authors"], w["abstract"], w["doi"]), ("A title", ["A. Author"], "Some words.", "10.1/abc"))

    def test_an_osf_preprint_keeps_its_own_doi_apart_from_the_published_one(self):
        w = sc.norm_osf(recorded("api.osf.io")["data"][0])
        self.assertEqual((w["year"], w["venue"], w["type"], w["oa_status"]), (2026, "OSF Preprints (socarxiv)", "preprint", "green"))
        self.assertEqual((w["doi"], w["doi_published"], w["landing"]), ("10.31235/osf.io/jdytw_v1", None, "https://osf.io/preprints/socarxiv/jdytw_v1/"))
        self.assertEqual(w["authors"], [])  # not in the list answer
        self.assertEqual(sc.norm_osf({"attributes": {"title": "T", "date_created": "2019-01-02", "doi": "10.9/Pub"}})["doi_published"], "10.9/pub")

    def test_a_zenodo_record_says_its_type_licence_and_access(self):
        w = sc.norm_zenodo(recorded("zenodo.org")["hits"]["hits"][0])
        self.assertEqual((w["title"][:30], w["year"], w["doi"], w["oa_status"]), ("Anthropology Of, For, And With", 2014, "10.5281/zenodo.1172837", "open"))
        self.assertTrue(w["landing"].startswith("https://zenodo.org/records/"), w["landing"])
        self.assertTrue(w["type"] and w["license"])
        closed = sc.norm_zenodo({"metadata": {"title": "T", "access_right": "restricted", "creators": [{"name": "Person, A."}]}})
        self.assertEqual((closed["oa_status"], closed["authors"], closed["venue"]), ("closed", ["Person, A."], "Zenodo"))

    def test_a_core_work_without_a_download_link_has_an_unknown_copy(self):
        w = sc.norm_core(json.loads(fixture("core-search-design-anthropology.json"))["results"][0])
        self.assertEqual((w["title"], w["year"], w["doi"], w["venue"]), ("Design Anthropology", 2016, "10.1111/gena.12013", "Wiley"))
        self.assertEqual((w["oa_pdf"], w["oa_status"], w["landing"], w["core"]), (None, "unknown", "https://core.ac.uk/works/111457555", 111457555))
        self.assertEqual(sc.norm_core({"title": "T", "downloadUrl": "https://core.ac.uk/download/1.pdf"})["oa_status"], "open")

    def test_words_side_by_side_are_joined_with_and_for_zenodo(self):
        self.assertEqual(sc.and_join("design anthropology"), "design AND anthropology")
        self.assertEqual(sc.and_join('"design anthropology" OR ethnography'), '"design anthropology" OR ethnography')
        self.assertEqual(sc.and_join("(craft OR making) ritual"), "( craft OR making ) AND ritual")
        self.assertEqual(sc.and_join('title:"x y" z'), 'title:"x y" AND z')
        self.assertEqual(sc.and_join("ritual publication_date:[2020-01-01 TO 2020-12-31]"), "ritual AND publication_date:[2020-01-01 TO 2020-12-31]")
        self.assertEqual(sc.and_join("title:(design anthropology) ritual"), "title:( design AND anthropology ) AND ritual")
        self.assertEqual(sc.and_join('"design anthropology"~3 craft'), '"design anthropology"~3 AND craft')
        self.assertEqual(sc.and_join('"a b"^2 c'), '"a b"^2 AND c')
        self.assertEqual(sc.and_join("craft and ritual"), "craft AND and AND ritual")  # a lowercase "and" is a word in Zenodo's syntax

    def test_each_host_is_paced_as_its_documentation_asks(self):
        self.assertEqual([sc.pace_seconds(h) for h in ("doaj.org", "api.osf.io", "zenodo.org", "api.core.ac.uk")], [0.55, 36.5, 2.1, 6.1])
        self.assertEqual([sc.DATABASES[h] for h in ("doaj.org", "api.osf.io", "zenodo.org", "api.core.ac.uk")], ["DOAJ", "OSF Preprints", "Zenodo", "CORE"])


class SearchReplay(LayerCase):
    def replay(self, argv: list[str]) -> tuple[int, str, str]:
        sc.configure(replay=OPEN)
        net = self.use([])  # any request to the network fails the test
        result = self.run_script(search, argv)
        self.assertEqual(net.calls, [])
        return result

    def rows(self, out: str) -> list[str]:
        return [x for x in out.splitlines() if x.startswith("- ")]

    def test_doaj_rows_have_the_same_shape_as_the_other_databases(self):
        code, out, err = self.replay(["design anthropology", "--db", "doaj", "--limit", "3", "--brief"])
        self.assertEqual((code, err), (0, ""))
        rows = self.rows(out)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], "- Monumento de Vanguardia (2021) |  | no citation count | unknown | open | -")
        self.assertIn("Coverage (2026-11-22): DOAJ answered (1 request, of which 1 from a recording).", out)

    def test_osf_rows_from_a_title_search(self):
        code, out, _ = self.replay(["anthropology", "--db", "osf", "--limit", "2", "--brief"])
        rows = self.rows(out)
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0].startswith("- Toward an anthropology of AI agents"), rows[0])
        self.assertTrue(rows[0].endswith("| open | 10.31235/osf.io/jdytw_v1"), rows[0])
        self.assertIn("OSF Preprints answered (1 request, of which 1 from a recording)", out)

    def test_zenodo_rows_and_json(self):
        code, out, err = self.replay(["design anthropology", "--db", "zenodo", "--limit", "3", "--json"])
        works = json.loads(out)
        self.assertEqual([w["doi"] for w in works], ["10.5281/zenodo.1172837", "10.5281/zenodo.14636662", "10.5281/zenodo.4518998"])
        self.assertTrue(all(w["zenodo"] and w["oa_status"] == "open" for w in works))
        self.assertIn("Zenodo answered (1 request, of which 1 from a recording)", err)

    def test_a_doi_is_not_looked_up_in_the_open_sources(self):
        code, _, err = self.run_script(search, ["--doi", "10.1/x", "--db", "zenodo"])
        self.assertEqual(code, 2)
        self.assertIn("searched by query", err)


class CoreKey(LayerCase):
    def test_without_a_key_core_is_not_asked_and_coverage_names_it(self):
        net = self.use([])
        code, out, _ = self.run_script(search, ["design anthropology", "--db", "core", "--brief"])
        self.assertEqual((code, net.calls), (0, []))
        self.assertIn("No results.", out)
        self.assertIn("CORE refused (not asked: no key, set CORE_API_KEY (free: https://core.ac.uk/services/api))", out.splitlines()[-1])

    def test_db_all_asks_every_database_but_osf_and_names_core_when_it_has_no_key(self):
        empty = Answer(json.dumps({}))
        net = self.use([("api.openalex.org", Answer(json.dumps({"results": []}))), ("semanticscholar", Answer(json.dumps({"data": []}))),
                        ("api.crossref.org", Answer(json.dumps({"message": {"items": []}}))), ("ebi.ac.uk", Answer(json.dumps({"resultList": {"result": []}}))),
                        ("export.arxiv.org", Answer('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')),
                        ("doaj.org", empty), ("api.osf.io", empty), ("zenodo.org", empty)])
        code, out, _ = self.run_script(search, ["design anthropology", "--db", "all", "--brief"])
        self.assertEqual(code, 0)
        for host in ("doaj.org", "zenodo.org"):
            self.assertEqual(net.count(host), 1, host)
        self.assertEqual((net.count("core.ac.uk"), net.count("api.osf.io")), (0, 0))  # OSF only when named
        line = out.splitlines()[-1]
        self.assertNotIn("OSF", line)
        for name in ("OpenAlex", "Semantic Scholar", "Crossref", "Europe PMC", "arXiv", "DOAJ", "Zenodo"):
            self.assertIn(f"{name} answered (1 request)", line)
        self.assertIn("CORE refused (not asked: no key", line)

    def test_with_a_key_it_travels_in_a_header_and_reaches_no_file_and_no_output(self):
        os.environ["CORE_API_KEY"] = f"  {KEY}\n"  # as a copied line can carry it
        body = json.loads(fixture("core-search-design-anthropology.json"))
        body["searchId"] = f"echo {KEY} and {KEY.replace('/', '%2F').replace('+', '%2B')}"  # an answer that repeats the key
        net = self.use([("api.core.ac.uk", Answer(json.dumps(body)))])
        sc.configure(record=self.tmp / "rec")
        code, out, err = self.run_script(search, ["design anthropology", "--db", "core", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(net.sent[0].get("Authorization"), f"Bearer {KEY}")
        self.assertNotIn("CORE-SECRET", net.calls[0])
        self.assertEqual(json.loads(out)[0]["doi"], "10.1111/gena.12013")
        self.assertIn("CORE answered (1 request)", err)
        stored = [p.read_text(encoding="utf-8") for p in self.tmp.rglob("*.json")]
        self.assertEqual(len(stored), 2)  # the cache and the recording
        for text in stored + [out, err]:
            self.assertNotIn("CORE-SECRET", text)
            self.assertNotIn("SECRET-123%2Fabc", text)

    def test_a_core_refusal_does_not_carry_the_key(self):
        os.environ["CORE_API_KEY"] = KEY
        net = self.use([("api.core.ac.uk", Answer(json.dumps({"message": f"key {KEY} is not valid"}), 401))])
        code, out, err = self.run_script(search, ["design anthropology", "--db", "core"])
        self.assertEqual((code, net.count("core.ac.uk")), (0, 1))  # 401 is not retried
        self.assertIn("CORE refused (HTTP 401", out)
        for text in [out, err] + [p.read_text(encoding="utf-8") for p in self.tmp.rglob("*.json")]:
            self.assertNotIn("CORE-SECRET", text)


class Requests(LayerCase):
    """How each open source is asked, and what a refusal or an odd answer does: on the fake network."""

    def test_from_year_reaches_each_source_in_its_own_syntax(self):
        os.environ["CORE_API_KEY"] = KEY
        net = self.use([("doaj.org", Answer(json.dumps({"total": 0, "results": []}))), ("zenodo.org", Answer(json.dumps({"hits": {"total": 0, "hits": []}}))),
                        ("api.core.ac.uk", Answer(json.dumps({"results": []})))])
        for name in ("doaj", "zenodo", "core"):
            sc.OPEN_SOURCES[name]('"design anthropology" ritual', 5, 2020)
        doaj, zenodo, core = net.calls
        self.assertEqual(doaj, sc.DOAJ + "%28%22design%20anthropology%22%20ritual%29%20AND%20bibjson.year%3A%5B2020%20TO%203000%5D?pageSize=5")
        self.assertIn("q=%28%22design+anthropology%22+AND+ritual%29+AND+publication_date%3A%5B2020-01-01+TO+3000-12-31%5D&size=5", zenodo)
        self.assertIn("q=%28%22design+anthropology%22+ritual%29+AND+yearPublished%3E%3D2020&limit=5", core)

    def test_osf_keeps_from_year_on_its_own_side_and_drops_quotes(self):
        data = {"data": [{"attributes": {"title": "Old", "date_published": "2018-05-01"}}, {"attributes": {"title": "New", "date_published": "2024-05-01"}}]}
        net = self.use([("api.osf.io", Answer(json.dumps(data)))])
        works = sc.osf_search('"design  anthropology"', 3, 2020)
        self.assertEqual([w["title"] for w in works], ["New"])
        self.assertTrue(net.calls[0].endswith("?filter%5Btitle%5D=design+anthropology&page%5Bsize%5D=3"), net.calls[0])

    def test_a_doaj_query_with_a_slash_a_question_mark_or_a_hash_stays_in_the_path(self):
        net = self.use([("doaj.org", Answer(json.dumps({"total": 1, "results": []})))])
        sc.doaj_search("doi:10.1234/ab?c#d%", 2)
        self.assertEqual(net.calls[0], sc.DOAJ + "doi%3A10.1234%2Fab%3Fc%23d%25?pageSize=2")

    def test_a_doaj_404_is_a_refusal_not_a_count_of_zero(self):
        self.use([("doaj.org", Answer("", 404))])
        with self.assertRaises(Exception) as caught:
            sc.doaj_count("x")
        self.assertIsInstance(caught.exception, sc.REFUSALS)
        self.assertIn("DOAJ refused (HTTP 404", sc.coverage_line())
        self.assertNotIn("DOAJ answered", sc.coverage_line())

    def test_a_zenodo_answer_without_a_count_is_refused_and_not_cached(self):
        net = self.use([("zenodo.org", [Answer(json.dumps({"hits": {"total": {}}})), Answer(json.dumps({"hits": {"total": 7}}))])])
        with self.assertRaises(sc.Refused):
            sc.zenodo_count("x")
        self.assertIn("Zenodo refused (answered with something that is not data", sc.coverage_line())
        self.assertEqual(sc.zenodo_count("x"), 7)  # asked again, not served from the cache
        self.assertEqual(net.count("zenodo.org"), 2)

    def test_a_core_document_type_given_as_a_list_is_kept_as_text(self):
        self.assertEqual(sc.norm_core({"title": "T", "documentType": ["research", "thesis"]})["type"], "research,thesis")
        self.assertEqual(sc.evidence_kind(sc.norm_core({"title": "T", "documentType": ["review"], "abstract": "a"})), "review")

    def test_oa_only_keeps_the_open_records_of_an_open_source(self):
        hits = {"hits": {"total": 2, "hits": [{"metadata": {"title": "Open one", "access_right": "open"}}, {"metadata": {"title": "Closed one", "access_right": "restricted"}}]}}
        self.use([("zenodo.org", Answer(json.dumps(hits)))])
        code, out, _ = self.run_script(search, ["x", "--db", "zenodo", "--oa-only", "--brief"])
        self.assertEqual([x.split(" (")[0] for x in out.splitlines() if x.startswith("- ")], ["- Open one"])

    def test_a_busy_zenodo_is_asked_again_and_then_refused(self):
        net = self.use([("zenodo.org", Answer("", 429))])
        self.assertIsNone(sc.ask_open("zenodo", "x"))
        self.assertEqual(net.count("zenodo.org"), 5)
        self.assertIn("Zenodo refused (HTTP 429", sc.coverage_line())

    def test_a_core_500_is_asked_again_once_only(self):
        os.environ["CORE_API_KEY"] = KEY
        net = self.use([("api.core.ac.uk", Answer(json.dumps({"message": "abstract is not a searchable field"}), 500))])
        self.assertIsNone(sc.ask_open("core", "design anthropology"))
        self.assertEqual(net.count("core.ac.uk"), 2)
        self.assertIn("CORE refused (HTTP 500", sc.coverage_line())

    def test_an_answer_of_an_unexpected_shape_is_named_and_the_run_goes_on(self):
        odd = {"hits": {"total": 1, "hits": [{"metadata": {"title": "T", "license": "cc-by-4.0", "resource_type": "dataset"}}]}}
        self.use([("zenodo.org", Answer(json.dumps(odd))), ("doaj.org", Answer(json.dumps({"total": 0, "results": []})))])
        self.assertIsNone(sc.ask_open("zenodo", "x"))
        self.assertEqual(sc.ask_open("doaj", "x"), [])
        line = sc.coverage_line()
        self.assertIn("Zenodo answered (1 request) and refused (answer not in the expected shape)", line)
        self.assertIn("DOAJ answered (1 request)", line)

    def test_a_key_with_a_line_break_inside_never_reaches_a_message(self):
        os.environ["CORE_API_KEY"] = "CORE-SECRET\n123abcdef"
        self.use([])
        sc._open = lambda req, timeout=60: (_ for _ in ()).throw(ValueError(f"Invalid header value {req.get_header('Authorization')!r}"))
        with self.assertRaises(sc.Refused) as caught:
            sc.core_search("x")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertNotIn("123abcdef", sc.coverage_line())

    def test_a_recorded_core_answer_replays_without_a_key(self):
        sc.configure(record=self.tmp / "rec")
        os.environ["CORE_API_KEY"] = KEY
        self.use([("api.core.ac.uk", Answer(fixture("core-search-design-anthropology.json")))])
        sc.core_search("design anthropology", 1)
        del os.environ["CORE_API_KEY"]
        sc.LAYER = sc._Layer()
        sc.configure(cache_dir=None, replay=self.tmp / "rec")
        net = self.use([])
        self.assertEqual([w["doi"] for w in sc.core_search("design anthropology", 1)], ["10.1111/gena.12013"])
        self.assertEqual(net.calls, [])


class CountsReplay(LayerCase):
    def counted(self, db: str) -> tuple[str, dict]:
        net = self.use([])
        code, text, err = self.run_script(counts, ['"design anthropology"', "--db", db, "--from", "2023", "--to", "2024",
                                                   "--replay", str(RECORDINGS / f"counts-{db}"), "--out", str(self.tmp / "out")])
        self.assertEqual((code, err, net.calls), (0, "", []))
        out = self.tmp / "out"
        self.assertEqual((out / "design-anthropology-2026-11-22.csv").read_bytes(), (EXPECTED / f"counts-{db}.csv").read_bytes())
        self.assertFalse((out / "design-anthropology-2026-11-22.types.csv").exists())
        return text, json.loads((out / "design-anthropology-2026-11-22.meta.json").read_text(encoding="utf-8"))

    def test_doaj_counts_one_year_at_a_time(self):
        text, meta = self.counted("doaj")
        self.assertEqual((meta["database"], meta["series"][0]["query"], meta["base"]["query"]), ("DOAJ", '("design anthropology")', "bibjson.year:<year> only"))
        self.assertIn("keywords among them", meta["search_field"])
        self.assertIn("DOAJ answered (4 requests, of which 4 from a recording)", text)

    def test_zenodo_counts_one_year_at_a_time(self):
        text, meta = self.counted("zenodo")
        self.assertEqual(meta["database"], "Zenodo")
        self.assertIn("Every resource type is counted", meta["search_field"])
        self.assertIn('- "design anthropology" · 2023: 2 (0.43) · 2024: 2 (0.31)', text)

    def test_zenodo_words_are_joined_with_and_in_a_count(self):
        net = self.use([("zenodo.org", Answer(json.dumps({"hits": {"total": 5, "hits": []}})))])
        self.run_script(counts, ["design anthropology", "--db", "zenodo", "--from", "2024", "--to", "2024", "--out", str(self.tmp / "out")])
        self.assertIn("q=%28design+AND+anthropology%29+AND+publication_date", net.calls[-1])

    def test_osf_and_core_have_no_yearly_counts(self):
        for db in ("osf", "core"):
            code, _, err = self.run_script(counts, ["x", "--db", db, "--out", str(self.tmp / "out")])
            self.assertEqual(code, 2, db)
            self.assertIn("invalid choice", err)


if __name__ == "__main__":
    unittest.main()
