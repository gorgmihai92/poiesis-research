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
        self.assertEqual(vq.find("it starts on this page and ends on the next one", self.pages, None), ("FOUND", "across two pages"))

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

    def test_an_email_address_is_not_read_as_a_citation(self):
        code, out = self.check("Write to someone@example.org about it.\n")
        self.assertEqual(code, 0, out)
        self.assertIn("0 references", out)


if __name__ == "__main__":
    unittest.main()
