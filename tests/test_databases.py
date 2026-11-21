"""Crossref, Europe PMC and arXiv as providers, and the scripts when OpenAlex or Semantic Scholar refuses.

The fixtures are answers these databases gave on 2026-11-21, trimmed, with abstracts shortened (tests/README.md).
"""
import json
import unittest
import xml.etree.ElementTree as ET

from helpers import Answer, LayerCase, fixture, sc

import citing  # noqa: E402
import copies  # noqa: E402
import foundations  # noqa: E402
import independence  # noqa: E402
import search  # noqa: E402

SPENT = Answer('{"reason": "daily_budget"}', 429, {"Retry-After": "13036"})
BUSY = Answer("", 429)


class Normalizing(unittest.TestCase):
    def test_crossref_record(self):
        w = sc.norm_crossref(json.loads(fixture("crossref-work-beel-2025.json"))["message"])
        self.assertEqual(w["title"], "Evaluating Sakana's AI Scientist: Bold Claims, Mixed Results, and a Promising Future?")
        self.assertEqual((w["year"], w["doi"], w["venue"]), (2025, "10.1145/3769733.3769747", "ACM SIGIR Forum"))
        self.assertEqual(w["authors"], ["Joeran Beel", "Min-Yen Kan", "Moritz Baumgart"])
        self.assertEqual(w["cited_crossref"], 7)
        self.assertEqual(w["abstract"], "Shortened for the test fixture. Artificial Research Intelligence (ARI).")  # tags removed
        self.assertEqual((w["oa_status"], w["license"]), ("unknown", None))  # Crossref does not say whether a copy is open
        self.assertEqual(set(w), set(sc.empty()))

    def test_crossref_record_with_a_creative_commons_licence(self):
        w = sc.norm_crossref(json.loads(fixture("crossref-work-wu-2025.json"))["message"])
        self.assertEqual((w["oa_status"], w["license"]), ("open", "cc-by-nc-nd"))

    def test_crossref_titles_lose_their_entities(self):
        self.assertEqual(sc.norm_crossref({"title": ["Evidence &amp; Gap Maps"]})["title"], "Evidence & Gap Maps")

    def test_europe_pmc_record(self):
        w = sc.norm_epmc(json.loads(fixture("epmc-doi-robinson-2011.json"))["resultList"]["result"][0])
        self.assertEqual(w["title"], "Development of a framework to identify research gaps from systematic reviews")  # no final period
        self.assertEqual((w["year"], w["doi"], w["epmc"]), (2011, "10.1016/j.jclinepi.2011.06.009", "MED/21937195"))
        self.assertEqual(w["authors"][0], "Karen A Robinson")
        self.assertEqual(w["abstract"], "Objective Shortened for the test fixture. Results Shortened for the test fixture.")
        self.assertEqual((w["oa_status"], w["oa_pdf"]), ("unknown", None))
        self.assertEqual(set(w), set(sc.empty()))

    def test_europe_pmc_open_record_has_its_pdf(self):
        w = sc.norm_epmc(json.loads(fixture("epmc-doi-wu-2025.json"))["resultList"]["result"][0])
        self.assertEqual((w["oa_status"], w["license"]), ("open", "cc-by-nc-nd"))
        self.assertEqual(w["oa_pdf"], "https://europepmc.org/articles/PMC12003634?pdf=render")

    def test_europe_pmc_citing_work_has_fewer_fields(self):
        w = sc.norm_epmc(json.loads(fixture("epmc-citations.json"))["citationList"]["citation"][0])
        self.assertEqual((w["year"], w["doi"], w["cited_epmc"]), (2026, None, 0))
        self.assertEqual(w["authors"], ["Larsen JS", "Pedersen S", "Liniger J"])

    def test_arxiv_entry_keeps_the_typed_doi_apart_from_the_registered_one(self):
        entry = ET.fromstring(fixture("arxiv-query-beel-2025.xml")).find("a:entry", sc.ATOM)
        w = sc.norm_arxiv(entry)
        self.assertEqual((w["arxiv"], w["year"], w["type"]), ("2502.14297", 2025, "preprint"))
        self.assertEqual(w["doi"], "10.48550/arxiv.2502.14297")
        # As arXiv returned it on 2026-11-21: the last digit of the registered DOI (…3769747) is missing.
        self.assertEqual(w["doi_published"], "10.1145/3769733.376974")
        self.assertEqual(w["oa_pdf"], "https://arxiv.org/pdf/2502.14297")
        self.assertEqual(set(w), set(sc.empty()))

    def test_openalex_and_semantic_scholar_records_are_read_as_before(self):
        w = sc.norm_openalex(json.loads(fixture("openalex-work-liu-2024.json")))
        self.assertEqual((w["year"], w["doi"], w["oa_status"]), (2024, "10.1007/s11192-023-04917-w", "green"))
        self.assertEqual(w["oa_pdf"], "https://arxiv.org/pdf/2312.05524")
        s = sc.norm_s2(json.loads(fixture("s2-paper-hiltunen-2008.json")))
        self.assertEqual((s["title"], s["year"], s["doi"], s["oa_pdf"]), ("The future sign and its three dimensions", 2008, "10.1016/j.futures.2007.08.021", None))

    def test_a_merged_work_shows_each_database_count_and_fills_an_unknown_copy(self):
        a = {**sc.empty(), "title": "T", "year": 2020, "doi": "10.1/x", "cited_crossref": 5, "oa_status": "unknown", "authors": ["A B"]}
        b = {**sc.empty(), "title": "T", "year": 2020, "doi": "10.1/x", "cited_epmc": 3, "oa_status": "open"}
        merged = sc.merge_all([a, b])
        self.assertEqual(len(merged), 1)
        self.assertEqual(sc.cites(merged[0]), "cited CR 5 · EPMC 3")
        self.assertEqual(merged[0]["oa_status"], "open")
        self.assertIn("| open copy unknown |", sc.brief(a))
        self.assertEqual(sc.most_cited(merged[0]), 5)

    def test_arxiv_query_keeps_phrases_and_drops_operators(self):
        self.assertEqual(sc.arxiv_query('"lateral reading" AND credibility'), 'all:"lateral reading" AND all:credibility')
        self.assertEqual(sc.arxiv_query("(quantum OR qubit) computing"), "all:quantum AND all:qubit AND all:computing")

    def test_a_feed_with_a_doctype_is_not_parsed(self):
        self.assertFalse(sc._is_feed('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><feed></feed>'))
        self.assertTrue(sc._is_feed(fixture("arxiv-query-beel-2025.xml")))


class Fallbacks(LayerCase):
    def test_fallback_search_asks_until_enough_databases_answered(self):
        net = self.use([("api.crossref.org", Answer(fixture("crossref-query.json"))), ("ebi.ac.uk", Answer(fixture("epmc-doi-wu-2025.json")))])
        self.assertEqual(len(sc.fallback_search("lateral reading", need=1)), 3)
        self.assertEqual(net.count("ebi.ac.uk"), 0)
        self.assertEqual(len(sc.fallback_search("lateral reading two", need=2)), 4)
        self.assertEqual(net.count("ebi.ac.uk"), 1)

    def test_fallback_search_skips_a_database_that_refuses(self):
        self.use([("api.crossref.org", Answer("", 403)), ("ebi.ac.uk", Answer(fixture("epmc-doi-wu-2025.json")))])
        works = sc.fallback_search("x", need=1)
        self.assertEqual([w["epmc"] for w in works], ["MED/40240349"])
        self.assertIn("Crossref refused (HTTP 403", sc.coverage_line())

    def test_an_arxiv_doi_is_asked_from_arxiv_first(self):
        net = self.use([("export.arxiv.org", Answer(fixture("arxiv-query-beel-2025.xml")))])
        w = sc.fallback_doi("10.48550/arXiv.2502.14297")
        self.assertEqual(w["arxiv"], "2502.14297")
        self.assertIn("id_list=2502.14297", net.calls[0])

    def test_works_by_doi_uses_the_other_databases_when_openalex_refuses(self):
        self.use([("api.openalex.org", SPENT), ("api.crossref.org", Answer(fixture("crossref-work-beel-2025.json")))])
        works = sc.works_by_doi(["10.1145/3769733.3769747"])
        self.assertEqual([w["crossref"] for w in works], ["10.1145/3769733.3769747"])


class ScriptsWhenADatabaseRefuses(LayerCase):
    def test_search_fills_in_for_openalex_and_ends_with_coverage(self):
        self.use([("api.openalex.org", SPENT), ("semanticscholar", Answer(json.dumps({"data": [json.loads(fixture("s2-paper-hiltunen-2008.json"))]}))),
                  ("api.crossref.org", Answer(fixture("crossref-query.json")))])
        code, out, err = self.run_script(search, ["lateral reading", "--brief"])
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertEqual(len([x for x in lines if x.startswith("- ")]), 4)  # 1 from Semantic Scholar, 3 from Crossref
        self.assertTrue(lines[-1].startswith("Coverage ("))
        self.assertIn("OpenAlex refused (daily budget used up)", lines[-1])
        self.assertIn("Semantic Scholar answered (1 request)", lines[-1])
        self.assertIn("Crossref answered (1 request)", lines[-1])
        self.assertIn("OpenAlex unavailable", err)

    def test_search_asks_two_fallbacks_when_both_first_databases_refuse(self):
        net = self.use([("api.openalex.org", SPENT), ("semanticscholar", BUSY), ("api.crossref.org", Answer(fixture("crossref-query.json"))),
                        ("ebi.ac.uk", Answer(fixture("epmc-doi-wu-2025.json")))])
        code, out, _ = self.run_script(search, ["lateral reading", "--brief"])
        self.assertEqual((net.count("api.crossref.org"), net.count("ebi.ac.uk"), net.count("arxiv")), (1, 1, 0))
        self.assertIn("Europe PMC answered", out.strip().splitlines()[-1])

    def test_search_is_unchanged_when_both_first_databases_answer(self):
        net = self.use([("api.openalex.org", Answer(json.dumps({"results": [json.loads(fixture("openalex-work-liu-2024.json"))]}))),
                        ("semanticscholar", Answer(json.dumps({"data": []})))])
        code, out, err = self.run_script(search, ["web of science coverage", "--brief"])
        lines = out.strip().splitlines()
        self.assertEqual(lines[0], "- Web of Science Core Collection’s coverage expansion: the forgotten Arts & Humanities Citation Index? (2024) | "
                                   "Weishu Liu, Rong Ni et al. | cited OA 76 | unknown | open | 10.1007/s11192-023-04917-w")
        self.assertEqual((net.count("crossref"), net.count("ebi.ac.uk"), err), (0, 0, ""))
        self.assertEqual(len(lines), 3)  # the work, a blank line, the Coverage line

    def test_search_json_stays_valid_and_coverage_goes_to_stderr(self):
        self.use([("api.openalex.org", Answer(json.dumps({"results": [json.loads(fixture("openalex-work-liu-2024.json"))]}))), ("semanticscholar", BUSY),
                  ("api.crossref.org", Answer(fixture("crossref-query.json")))])
        code, out, err = self.run_script(search, ["web of science coverage", "--json"])
        works = json.loads(out)
        self.assertEqual(len(works), 4)
        self.assertNotIn("Coverage", out)
        self.assertIn("Coverage (", err)

    def test_search_by_doi_can_ask_every_database(self):
        net = self.use([("api.openalex.org", Answer("", 404)), ("semanticscholar", Answer("", 404)), ("api.crossref.org", Answer(fixture("crossref-work-beel-2025.json"))),
                        ("ebi.ac.uk", Answer(json.dumps({"hitCount": 0, "resultList": {"result": []}})))])
        code, out, _ = self.run_script(search, ["--doi", "10.1145/3769733.3769747", "--db", "all", "--brief"])
        self.assertIn("| cited CR 7 |", out)
        self.assertEqual(net.count("arxiv"), 0)  # arXiv is asked only for its own DOIs
        self.assertIn("Crossref answered (1 request)", out)

    def test_citing_reads_other_databases_and_says_which(self):
        cites = {"data": [{"citingPaper": {"paperId": "p1", "title": "A failed replication of the future sign", "year": 2012, "citationCount": 4, "abstract": "We failed to replicate."}}]}
        self.use([("api.openalex.org", SPENT), ("/citations", Answer(json.dumps(cites))), ("semanticscholar", Answer(fixture("s2-paper-hiltunen-2008.json"))),
                  ("ebi.ac.uk", Answer(json.dumps({"hitCount": 0, "resultList": {"result": []}})))])
        code, out, err = self.run_script(citing, ["--doi", "10.1016/j.futures.2007.08.021"])
        self.assertEqual(code, 0)
        self.assertIn("Read 1 of 219 citing works (Semantic Scholar).", out)
        self.assertIn("[replication, failed] A failed replication of the future sign (2012)", out)
        self.assertIn("the title search for replications and critiques among the citing works was not run", out)
        self.assertIn("OpenAlex refused (daily budget used up)", out.strip().splitlines()[-1])

    def test_citing_says_when_nothing_could_be_read(self):
        self.use([("api.openalex.org", SPENT), ("semanticscholar", BUSY), ("api.crossref.org", Answer("", 503)), ("ebi.ac.uk", Answer("", 503))])
        code, out, _ = self.run_script(citing, ["--doi", "10.1/none"])
        self.assertEqual(code, 1)
        self.assertIn("nothing was read", out)

    def test_copies_finds_the_open_copy_in_europe_pmc(self):
        self.use([("api.openalex.org", SPENT), ("semanticscholar", BUSY), ("ebi.ac.uk", Answer(fixture("epmc-doi-wu-2025.json"))),
                  ("api.crossref.org", Answer(fixture("crossref-work-wu-2025.json")))])
        code, out, _ = self.run_script(copies, ["--doi", "10.1038/s41467-025-58551-6"])
        self.assertIn("An automated framework for assessing how well LLMs cite relevant medical references (2025)", out)
        self.assertIn("open copy: https://europepmc.org/articles/PMC12003634?pdf=render", out)

    def test_independence_groups_authors_from_crossref(self):
        nothing = Answer(json.dumps({"hitCount": 0, "resultList": {"result": []}}))
        self.use([("api.openalex.org", SPENT), ("3769747", Answer(fixture("crossref-work-beel-2025.json"))), ("58551-6", Answer(fixture("crossref-work-wu-2025.json"))),
                  ("works/10.1/missing", Answer("", 404)), ("ebi.ac.uk", nothing)])
        code, out, _ = self.run_script(independence, ["10.1145/3769733.3769747", "10.1038/s41467-025-58551-6", "10.1/missing"])
        self.assertIn("2 studies, 2 independent groups by author.", out)
        self.assertIn("Not found in the databases that answered (check by hand): 10.1/missing", out)

    def test_foundations_counts_shared_references_from_crossref(self):
        def work(doi, title, refs):
            return json.dumps({"message": {"DOI": doi, "title": [title], "issued": {"date-parts": [[2020]]}, "is-referenced-by-count": 10,
                                           "reference": [{"DOI": r} for r in refs]}})
        query = json.dumps({"message": {"items": [{"DOI": "10.1/s1", "title": ["Framing effects one"], "is-referenced-by-count": 90},
                                                  {"DOI": "10.1/s2", "title": ["Framing effects two"], "is-referenced-by-count": 50},
                                                  {"DOI": "10.1/off", "title": ["Something else"], "is-referenced-by-count": 999}]}})
        self.use([("api.openalex.org", SPENT), ("semanticscholar", BUSY), ("query.bibliographic", Answer(query)),
                  ("works/10.1/s1", Answer(work("10.1/s1", "Framing effects one", ["10.1/found", "10.1/a"]))),
                  ("works/10.1/s2", Answer(work("10.1/s2", "Framing effects two", ["10.1/found", "10.1/b"]))),
                  ("works/10.1/found", Answer(work("10.1/found", "The founding work", [])))])
        code, out, err = self.run_script(foundations, ["framing effects", "--no-s2"])
        self.assertEqual(code, 0)
        self.assertIn("Read the bibliographies of the 2 most-cited works on the topic:", out)
        self.assertIn("- cited by 2 of 2 · The founding work (2020)", out)
        self.assertNotIn("Something else", out)  # off topic: the query words are not in its title
        self.assertIn("Note: OpenAlex did not answer", out)
        self.assertIn("read this list as a lower bound", out)


if __name__ == "__main__":
    unittest.main()
