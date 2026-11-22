"""verify_quotes.py: quotes looked for in a source's extracted text, and a report's references looked for in the
notes. No network."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, SCRIPTS

import verify_quotes as vq  # noqa: E402

TEST_NOTE = Path(__file__).resolve().parent / "texts" / "notes" / "walters-quotes.md"

# What extract_text.py gives for a two-column PDF: ligatures, words cut at line ends, letters spaced out, a
# sentence that runs onto the next page, a footnote number glued to a word.
TEXT = """[p. 1]
Our ﬁndings reveal that between 50%
and 90% of responses are not fully suppor-
ted by the sources they cite.
T h e  s e c o n d  r e s u l t is that web search helps.
The measure is statement-level sup-
port, and it starts on this page and

[p. 2]
ends on the next one. The system marked all twelve ideas as novel15, despite
some being well documented. Models “often answer wrongly” when asked.

[p. 3]
Nothing relevant here.
"""


def run(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["verify_quotes.py", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = vq.main()
            except SystemExit as e:
                code = e.code
    finally:
        sys.argv = saved
    return code, out.getvalue()


class TheTestNote(unittest.TestCase):
    def test_two_true_quotes_are_found_and_the_false_one_is_not(self):
        code, out = run([str(TEST_NOTE)])
        lines = out.strip().splitlines()
        self.assertTrue(lines[0].startswith("FOUND      walters-quotes.md · line 11 · p. 1 · "), lines[0])
        self.assertTrue(lines[1].startswith("FOUND      walters-quotes.md · line 12 · p. 1 · "), lines[1])
        self.assertTrue(lines[2].startswith("NOT FOUND  walters-quotes.md · line 13 · not in the source's text"), lines[2])
        self.assertTrue(lines[3].startswith("WRONG PAGE walters-quotes.md · line 14 · cited p. 4, found on p. 1"), lines[3])
        self.assertEqual(lines[-1], "FOUND: 2 · NOT FOUND: 1 · WRONG PAGE: 1")
        self.assertEqual(code, 1)

    def test_it_runs_as_the_playbook_runs_it(self):
        done = subprocess.run([sys.executable, "-I", str(SCRIPTS / "verify_quotes.py"), str(TEST_NOTE)], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(done.returncode, 1)
        self.assertIn("FOUND: 2 · NOT FOUND: 1 · WRONG PAGE: 1", done.stdout)

    def test_the_repository_s_own_notes_pass(self):
        code, out = run([str(ROOT / "research" / "notes")])
        self.assertEqual(code, 0, out)
        self.assertNotIn("NOT FOUND", out)
        self.assertNotIn("WRONG PAGE", out)
        self.assertIn("FOUND      walters-2023-fabricated-citations.md", out)  # its text is in the repository
        self.assertIn("FOUND      murad-2016-new-evidence-pyramid.md", out)


class Matching(unittest.TestCase):
    def setUp(self):
        self.pages = vq.pages_of(TEXT)

    def test_ligatures_line_breaks_and_spaced_letters_do_not_hide_a_quote(self):
        self.assertEqual(vq.find("Our findings reveal that between 50% and 90% of responses are not fully supported", self.pages, (1, 1)), ("FOUND", "p. 1"))
        self.assertEqual(vq.find("The second result is that web search helps", self.pages, (1, 1)), ("FOUND", "p. 1"))
        self.assertEqual(vq.find("statement-level support", self.pages, (1, 1)), ("FOUND", "p. 1"))

    def test_a_changed_number_or_word_is_not_found(self):
        self.assertEqual(vq.find("between 50% and 80% of responses", self.pages, (1, 1))[0], "NOT FOUND")
        self.assertEqual(vq.find("responses are fully supported by the sources", self.pages, (1, 1))[0], "NOT FOUND")
        self.assertEqual(vq.find("marked all ten ideas as novel", self.pages, (2, 2))[0], "NOT FOUND")

    def test_a_quote_that_runs_onto_the_next_page_is_found_from_its_first_page(self):
        self.assertEqual(vq.find("it starts on this page and ends on the next one", self.pages, (1, 1)), ("FOUND", "p. 1"))
        self.assertEqual(vq.find("it starts on this page and ends on the next one", self.pages, None), ("FOUND", "p. 1–2"))

    def test_an_elided_quote_wholly_on_the_next_page_is_the_wrong_page(self):
        """Found by the second review: the quote's first words also stand on the cited page."""
        pages = vq.pages_of("[p. 4]\nWe find the same in the pilot. Nothing else.\n[p. 5]\nWe find that the effect was 37 percent larger in the second cohort.\n[p. 6]\nEnd.\n")
        self.assertEqual(vq.find("We find … the effect was 37 percent larger", pages, (4, 4)), ("WRONG PAGE", "cited p. 4, found on p. 5"))
        self.assertEqual(vq.find("We find … the effect was 37 percent larger", pages, (5, 5)), ("FOUND", "p. 5"))
        self.assertEqual(vq.find("We find the same … Nothing else", pages, (4, 4)), ("FOUND", "p. 4"))

    def test_an_elided_quote_on_the_cited_page_is_found_there_when_the_next_page_has_it_too(self):
        """Found by the re-check: a tighter reading on the next page made a right citation the wrong page."""
        pages = vq.pages_of("[p. 4]\nWe find that in the first cohort the effect was small.\n[p. 5]\nWe find the effect was small in the second cohort too.\n")
        self.assertEqual(vq.find("We find … the effect was small", pages, (4, 4)), ("FOUND", "p. 4"))
        self.assertEqual(vq.find("We find … the effect was small", pages, (5, 5)), ("FOUND", "p. 5"))

    def test_a_quote_that_runs_on_from_the_cited_page_is_found_there_even_if_repeated_elsewhere(self):
        """Seen on random texts by the second review: the same words stood whole on a later page."""
        pages = vq.pages_of("[p. 3]\nin find kelp the that\n[p. 4]\nmoral the in kelp in\n[p. 6]\nlarger x9 was that moral\n")
        self.assertEqual(vq.find("that moral", pages, (3, 3))[:1], ("FOUND",))
        self.assertEqual(vq.find("that moral", pages, (6, 6))[1].split(" (")[0], "p. 6")

    def test_an_elided_quote_in_a_long_text_is_checked_quickly(self):
        import time
        text = "[p. 1]\n" + "\n".join(f"[p. {n}]\n" + "the cat sat on the mat and the dog lay down. " * 60 for n in range(2, 400)) + "\n[p. 400]\nthe method works.\n"
        pages = vq.pages_of(text)
        started = time.perf_counter()
        self.assertEqual(vq.find("the … the method works", pages, (3, 3)), ("WRONG PAGE", "cited p. 3, found on p. 399–400"))  # its first word ends p. 399
        self.assertLess(time.perf_counter() - started, 1.0)

    def test_a_quote_that_runs_past_the_next_page_names_the_pages_it_is_on(self):
        pages = vq.pages_of("[p. 4]\nThe quote starts on this page and\n[p. 5]\n\n[p. 6]\ncontinues after a page with a figure only.\n")
        quote = "The quote starts on this page and continues after a page with a figure only"
        self.assertEqual(vq.find(quote, pages, (4, 4)), ("WRONG PAGE", "cited p. 4, found on p. 4–6"))
        self.assertEqual(vq.find(quote, pages, (4, 6)), ("FOUND", "p. 4–6"))
        self.assertEqual(vq.find(quote, pages, None), ("FOUND", "p. 4–6"))

    def test_a_quote_wholly_on_the_page_after_the_cited_one_is_the_wrong_page(self):
        """Found by the lab's review of 2026-11-21: one page early was accepted as FOUND."""
        self.assertEqual(vq.find("Nothing relevant here", self.pages, (2, 2)), ("WRONG PAGE", "cited p. 2, found on p. 3"))
        self.assertEqual(vq.find("Nothing relevant here", self.pages, (1, 2)), ("WRONG PAGE", "cited p. 1–2, found on p. 3"))
        self.assertEqual(vq.find("Nothing relevant here", self.pages, (3, 3))[0], "FOUND")
        # A quote that starts on the cited page and ends on the next is still found there.
        self.assertEqual(vq.find("it starts on this page and ends on the next one", self.pages, (1, 1)), ("FOUND", "p. 1"))
        self.assertEqual(vq.find("it starts on this page and ends on the next one", self.pages, (2, 2))[0], "WRONG PAGE")

    def test_the_lab_review_s_case_one_page_early(self):
        pages = vq.pages_of("[p. 4]\nNothing relevant is written on this page at all.\n[p. 5]\nThe effect was 37 percent larger in the second "
                            "cohort than in the first.\n[p. 6]\nEnd.\n")
        quote = "The effect was 37 percent larger in the second cohort"
        self.assertEqual(vq.find(quote, pages, (4, 4)), ("WRONG PAGE", "cited p. 4, found on p. 5"))
        self.assertEqual(vq.find(quote, pages, (5, 5)), ("FOUND", "p. 5"))
        self.assertEqual(vq.find(quote, pages, (4, 5)), ("FOUND", "p. 4–5"))
        self.assertEqual(vq.find(quote, pages, (3, 3)), ("WRONG PAGE", "cited p. 3, found on p. 5"))
        self.assertEqual(vq.find(quote, pages, (6, 6)), ("WRONG PAGE", "cited p. 6, found on p. 5"))

    def test_the_wrong_page_is_reported_with_the_right_one(self):
        self.assertEqual(vq.find("The system marked all twelve ideas as novel", self.pages, (3, 3)), ("WRONG PAGE", "cited p. 3, found on p. 2"))

    def test_an_ellipsis_asks_for_every_part_in_order(self):
        self.assertEqual(vq.find("Our findings reveal … not fully supported by the sources", self.pages, (1, 1))[0], "FOUND")
        self.assertEqual(vq.find("not fully supported [...] Our findings reveal", self.pages, (1, 1))[0], "NOT FOUND")

    def test_a_footnote_number_inside_a_quote_makes_it_not_found(self):
        # "novel15, despite": the check is strict on digits, so this asks a person to look. A wrong number would
        # otherwise pass.
        self.assertEqual(vq.find("as novel, despite some being well documented", self.pages, (2, 2))[0], "NOT FOUND")

    def test_a_very_short_quote_is_flagged_as_a_weak_check(self):
        self.assertEqual(vq.find("web search helps", self.pages, (1, 1)), ("FOUND", "p. 1 (short: 14 letters, a weak check)"))

    def test_curly_quotes_and_a_page_range_are_read(self):
        note = '## Quotes\n- “often answer wrongly” (pp. 2–3)\n- "no page given here"\n* «alt marks» (p. 7)\nA line "with a quote" inside is not a quote line.\n'
        self.assertEqual(vq.quotes_of(note), [(2, "often answer wrongly", (2, 3)), (3, "no page given here", None), (4, "alt marks", (7, 7))])

    def test_a_page_range_written_short_is_read_as_the_range_it_means(self):
        """Found by the second review: (pp. 249–51) was read as pages 249 to 51."""
        self.assertEqual(vq.quotes_of('- "a future sign has three dimensions" (pp. 249–51)\n- "another one" (p. 1198-9)\n- "a third" (pp. 12–14)\n'),
                         [(1, "a future sign has three dimensions", (249, 251)), (2, "another one", (1198, 1199)), (3, "a third", (12, 14))])

    def test_a_text_without_page_markers_is_searched_whole(self):
        pages = vq.pages_of("systematic reviews are a lens through which evidence is viewed (applied)")
        self.assertEqual(vq.find("a lens through which evidence is viewed", pages, None), ("FOUND", "the text has no page markers"))
        self.assertEqual(vq.find("a lens through which evidence is viewed", pages, (4, 4)), ("FOUND", "the text has no page markers"))


class Notes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        (self.tmp / "research" / "notes").mkdir(parents=True)
        (self.tmp / "research" / "papers").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def note(self, name: str, body: str) -> Path:
        path = self.tmp / "research" / "notes" / f"{name}.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_a_note_whose_text_is_not_here_is_not_checked_and_does_not_fail(self):
        self.note("closed-2020-paper", "# A closed paper (Someone, 2020)\n- **File:** none (reference only)\n\n## Quotes\n- \"words nobody can check here\" (p. 3)\n")
        code, out = run([str(self.tmp / "research" / "notes")])
        self.assertEqual(code, 0)
        self.assertIn("NO TEXT    closed-2020-paper.md · 1 quote not checked", out)

    def test_strict_fails_when_quotes_could_not_be_checked(self):
        """A gate that reads only the exit code must not pass notes nobody checked."""
        self.note("closed-2020-paper", "# A closed paper (Someone, 2020)\n- **File:** none (reference only)\n\n## Quotes\n- \"words nobody can check here\" (p. 3)\n")
        self.note("no-quotes-2021", "# A note with no quotes (Someone, 2021)\n")
        code, out = run([str(self.tmp / "research" / "notes")])
        self.assertEqual(code, 0)
        code, out = run([str(self.tmp / "research" / "notes"), "--strict"])
        self.assertEqual(code, 1)
        self.assertIn("NO TEXT    closed-2020-paper.md", out)
        self.assertIn("1 quote in 1 note could not be checked", out)

    def test_the_text_is_found_from_the_file_line_or_by_the_note_s_name_in_papers(self):
        (self.tmp / "research" / "papers" / "wu-2025-sources.txt").write_text(TEXT, encoding="utf-8")
        (self.tmp / "elsewhere").mkdir()
        (self.tmp / "elsewhere" / "by-name-2025.txt").write_text(TEXT, encoding="utf-8")
        self.note("wu-2025-note", "# T (Wu, 2025)\n- **File:** `../papers/wu-2025-sources.pdf`\n\n## Quotes\n- \"web search helps\" (p. 1)\n")
        self.note("by-name-2025", "# T (Name, 2025)\n\n## Quotes\n- \"web search helps\" (p. 1)\n")
        code, out = run([str(self.tmp / "research" / "notes"), "--papers", str(self.tmp / "elsewhere")])
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("FOUND "), 2)


class References(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        notes = self.tmp / "research" / "notes"
        notes.mkdir(parents=True)
        (notes / "walters-2023-fabricated-citations.md").write_text(
            "# Fabrication and errors (Walters & Wilder, 2023)\n- **Source:** Scientific Reports · https://doi.org/10.1038/s41598-023-41032-5\n", encoding="utf-8")
        (notes / "murad-2016-new-evidence-pyramid.md").write_text("# New evidence pyramid (Murad, Asi, Alsawas & Alahdab, 2016)\n- **Source:** doi: 10.1136/ebmed-2016-110401\n", encoding="utf-8")
        self.report = self.tmp / "insights" / "2026-11-21-report.md"
        self.report.parent.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, text: str, *more: str) -> tuple[int, str]:
        self.report.write_text(text, encoding="utf-8")
        return run(["--references", str(self.report), "--notes", str(self.tmp / "research" / "notes"), *more])

    def test_every_kind_of_reference_with_a_note_passes(self):
        code, out = self.check(
            "Models fabricate citations (https://doi.org/10.1038/s41598-023-41032-5).\n"
            "See [the note](../research/notes/walters-2023-fabricated-citations.md) and [[murad-2016-new-evidence-pyramid]].\n"
            "Also doi:10.1136/EBMED-2016-110401, and Walters & Wilder (2023) again, and Murad et al. 2016.\n")
        self.assertEqual(code, 0, out)
        self.assertIn("4 references in 2026-11-21-report.md: 4 have a note, 0 do not.", out)
        self.assertNotIn("MENTION", out)

    def test_references_without_a_note_are_listed_with_their_line(self):
        code, out = self.check(
            "A claim (https://doi.org/10.1234/not-in-the-library).\n"
            "See [gone](../research/notes/smith-2020-gone.md) and [[no-such-note|shown text]].\n")
        self.assertEqual(code, 1)
        self.assertIn("NO NOTE    line 1 · doi 10.1234/not-in-the-library · no note has this DOI", out)
        self.assertIn("NO NOTE    line 2 · ../research/notes/smith-2020-gone.md · the linked note does not exist", out)
        self.assertIn("NO NOTE    line 2 · [[no-such-note]] · no note with this name", out)
        self.assertIn("3 references in 2026-11-21-report.md: 0 have a note, 3 do not.", out)

    def test_an_author_and_year_with_no_note_is_a_lead_and_does_not_fail(self):
        code, out = self.check("As Smith (2020) and Jones et al. 2019 showed in March 2021, see Table 2020.\n")
        self.assertEqual(code, 0)
        self.assertIn("MENTION    line 1 · Smith 2020 · no note with this author and year", out)
        self.assertIn("MENTION    line 1 · Jones 2019", out)
        self.assertNotIn("March", out)
        self.assertNotIn("Table", out)
        self.assertIn("2 author-year mentions to check by hand", out)

    def test_texere_citations_are_looked_up_in_the_bibliography(self):
        index = self.tmp / "Support" / "Texere" / "Bibliography"
        index.mkdir(parents=True)
        (index / "bibliography.json").write_text(json.dumps([
            {"id": "hiltunen2008future", "obsidianPath": "1. References/hiltunen2008future.md", "reading-status": "read", "DOI": "10.1016/j.futures.2007.08.021"},
            {"id": "sharpe2016three", "obsidianPath": "1. References/sharpe2016three.md", "reading-status": "unread"},
        ]), encoding="utf-8")
        code, out = self.check("A future sign has three dimensions [@hiltunen2008future, p. 249]. Three horizons [@sharpe2016three; @nobody2021made, p. 3].\n"
                               "The same paper by DOI: https://doi.org/10.1016/j.futures.2007.08.021\n")
        self.assertEqual(code, 1)
        self.assertEqual(out.count("NO NOTE"), 1)
        self.assertIn("NO NOTE    line 1 · [@nobody2021made] · not in the bibliography and no note with this name", out)
        self.assertIn("4 references in 2026-11-21-report.md: 3 have a note, 1 do not", out)
        self.assertIn("bibliography.json", out)

    def test_a_texere_link_to_a_place_in_a_pdf_is_not_a_reference_to_a_note(self):
        """Found by the lab's review of 2026-11-21: Texere's link to the PDF was listed as a reference with no note."""
        index = self.tmp / "Support" / "Texere" / "Bibliography"
        index.mkdir(parents=True)
        (index / "bibliography.json").write_text(json.dumps([{"id": "hiltunen2008future", "obsidianPath": "1. References/hiltunen2008future.md", "reading-status": "read"}]),
                                                 encoding="utf-8")
        code, out = self.check("#claim A future sign has three dimensions [@hiltunen2008future, p. 249] [[hiltunen2008future.pdf#page=4&annotation=123R|PDF]]\n"
                               "A figure: ![[figure-1.png]] and a note that is missing: [[no-such-note]].\n")
        self.assertEqual(code, 1)
        self.assertEqual(out.count("NO NOTE"), 1, out)
        self.assertIn("[[no-such-note]]", out)
        self.assertNotIn(".pdf", out)
        self.assertNotIn(".png", out)
        self.assertIn("2 references in 2026-11-21-report.md: 1 have a note, 1 do not", out)

    def test_the_lab_review_s_case_a_texere_line(self):
        index = self.tmp / "Support" / "Texere" / "Bibliography"
        index.mkdir(parents=True)
        (index / "bibliography.json").write_text(json.dumps([{"id": "smith2020", "obsidianPath": "1. References/smith2020.md", "reading-status": "read"}]), encoding="utf-8")
        code, out = self.check("# Report\n\nA claim [@smith2020, p. 4] [[smith2020.pdf#page=4&annotation=12R|PDF]].\n")
        self.assertEqual(code, 0, out)
        self.assertNotIn("NO NOTE", out)
        self.assertIn("1 references in 2026-11-21-report.md: 1 have a note, 0 do not", out)
        self.assertIn("1 link to a file that is not a note was not checked", out)

    def test_a_link_to_any_other_kind_of_file_is_not_a_reference_to_a_note(self):
        """Found by the second review: only the file types on a list were left out, and a table's escaped bar broke a link."""
        code, out = self.check("![[plot.avif]] ![[talk.webm]] ![[figure-2.TIFF]] [[book.epub]] [[refs.bib]]\n"
                               "| A claim | [[walters-2023-fabricated-citations.pdf\\|PDF]] | [[walters-2023-fabricated-citations\\|Walters]] |\n"
                               "A note that is missing: [[no-such-note]]. A link that names the note's file: [[murad-2016-new-evidence-pyramid.md]].\n")
        self.assertEqual(code, 1)
        self.assertEqual(out.count("NO NOTE"), 1, out)
        self.assertIn("[[no-such-note]]", out)
        self.assertIn("3 references in 2026-11-21-report.md: 2 have a note, 1 do not", out)
        self.assertIn("6 links to files that are not notes were not checked", out)

    def test_a_missing_note_whose_name_has_a_dot_is_still_reported(self):
        """Found by the re-check: [[Node.js]] was taken for a file and a missing note went unreported."""
        code, out = self.check("See [[Node.js]], [[openalex.org]] and [[Dr.Smith]].\n")
        self.assertEqual(code, 1)
        self.assertEqual(out.count("NO NOTE"), 3, out)
        self.assertNotIn("not checked", out)

    def test_a_note_whose_name_ends_like_a_file_is_still_looked_up(self):
        (self.tmp / "research" / "notes" / "notes-on-index.html.md").write_text("# Notes on index.html\n", encoding="utf-8")
        code, out = self.check("See [[notes-on-index.html]].\n")
        self.assertEqual(code, 0, out)
        self.assertIn("1 references in 2026-11-21-report.md: 1 have a note, 0 do not", out)
        self.assertNotIn("not checked", out)

    def test_what_is_shown_as_code_is_an_example_not_a_reference(self):
        code, out = self.check("Cite as `[@key, p. N]`, or by `https://doi.org/10.1234/example`.\n```\n[@another2020key] and [[some-note]]\n```\n")
        self.assertEqual(code, 0, out)
        self.assertIn("0 references", out)

    def test_an_email_address_is_not_read_as_a_citation(self):
        code, out = self.check("Write to someone@example.org about it.\n")
        self.assertEqual(code, 0, out)
        self.assertIn("0 references", out)


if __name__ == "__main__":
    unittest.main()
