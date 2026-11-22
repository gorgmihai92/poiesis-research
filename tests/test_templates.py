"""The properties block at the top of each template (2.6.0): what it holds, the rules it keeps, and that the
scripts read a note with it as they read one without it. No network."""
import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

import library  # noqa: E402
import signals  # noqa: E402
import verify_quotes as vq  # noqa: E402

TEMPLATES = ROOT / "plugins" / "poiesis-research" / "skills" / "research" / "templates"
COMMON = ["type", "plugin", "date", "topic"]
ONE_OBJECT = COMMON + ["id", "status", "from"]
KEYS = {"note.md": ONE_OBJECT, "signal.md": ONE_OBJECT, "evidence-map.md": ONE_OBJECT, "funding.md": ONE_OBJECT,
        "research.config.md": COMMON}


def block_of(text: str) -> list[str]:
    """The lines between the first line `---` and the next `---`, or [] when the text has no such block."""
    lines = text.split("\n")
    if lines[0] != "---" or "---" not in lines[1:]:
        return []
    return lines[1 : lines.index("---", 1)]


class TheBlock(unittest.TestCase):
    def test_every_template_starts_with_one(self):
        self.assertEqual(sorted(p.name for p in TEMPLATES.glob("*.md")), sorted(KEYS))
        for name, keys in KEYS.items():
            block = block_of((TEMPLATES / name).read_text(encoding="utf-8"))
            self.assertTrue(block, name)
            self.assertEqual([l.split(":", 1)[0] for l in block if not l.startswith(" ")], keys, name)
            self.assertIn("plugin: poiesis-research", block, name)

    def test_it_keeps_the_rules_the_other_plugins_need(self):
        """No line a heading reader takes for a title, no link outside quotes, and each list item one quoted link."""
        for name in KEYS:
            for line in block_of((TEMPLATES / name).read_text(encoding="utf-8")):
                self.assertFalse(line.lstrip().startswith("#"), f"{name}: {line}")
                if line.startswith(" "):
                    self.assertRegex(line, r'^  - "\[\[[^\]|]+\]\]"$', name)
                else:
                    self.assertRegex(line, r'^[a-z]+:(?: (?:"[^"]*"|\[\]|<[^:"]*>|[a-z-]+))?$', f"{name}: {line}")

    def test_the_label_lines_are_still_there(self):
        """The block is a copy: the lines the scripts read stay in the template."""
        for name, label in (("note.md", "- **Read:**"), ("signal.md", "- **Id:** SG-"), ("evidence-map.md", "- **Verdict:**"),
                            ("funding.md", "- **Status:**")):
            self.assertIn(label, (TEMPLATES / name).read_text(encoding="utf-8"), name)


FILLED = """---
type: source-note
plugin: poiesis-research
date: 2026-11-22
topic: "methods"
id: "example-2025-note"
status: "part of the text"
from:
  - "[[IN-001]]"
---
"""
NOTE = """# A test note (Example, 2025)

- **Source:** a note written for the tests · https://doi.org/10.1234/example.2025
- **Read:** part of the text: p. 2–4 · 2026-11-22

## Quotes
- "web search helps" (p. 1)
"""


class ReadTheSame(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.notes = self.root / "research" / "notes"
        self.notes.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_library_lists_a_note_with_properties_as_one_without(self):
        path = self.notes / "example-2025-note.md"
        path.write_text(NOTE, encoding="utf-8")
        without = library.read_note(path, self.root)
        path.write_text(FILLED + NOTE, encoding="utf-8")
        self.assertEqual(library.read_note(path, self.root), without)
        self.assertEqual(without["read"], "part of the text")

    def test_the_next_signal_id_is_counted_the_same(self):
        signal = (TEMPLATES / "signal.md").read_text(encoding="utf-8")
        body = signal[signal.index("\n---\n") + 5 :].replace("SG-<number from `signals.py --next-id research/signals`>", "SG-004")
        folder = self.root / "research" / "signals"
        folder.mkdir(parents=True)
        (folder / "2026-11-22-a.md").write_text(body, encoding="utf-8")
        without = signals.next_id(folder)
        (folder / "2026-11-22-a.md").write_text('---\ntype: signal\nid: "SG-004"\n---\n' + body, encoding="utf-8")
        self.assertEqual(signals.next_id(folder), without)
        self.assertEqual(without, "SG-005")

    def test_a_report_s_references_check_the_same_with_properties(self):
        (self.notes / "example-2025-note.md").write_text(FILLED + NOTE, encoding="utf-8")
        report = self.root / "report.md"
        outputs = []
        for text in ("See [[example-2025-note]].\n", FILLED + "See [[example-2025-note]].\n"):
            report.write_text(text, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = vq.check_references(report, self.notes, None)
            outputs.append((code, out.getvalue()))
        self.assertEqual(outputs[1], outputs[0])
        self.assertEqual(outputs[0][0], 0, outputs[0][1])


if __name__ == "__main__":
    unittest.main()
