#!/usr/bin/env python3
"""Extract a PDF's text next to it (<name>.txt), with a "[p. N]" marker before each page so notes can cite
pages. Run with `python3 -I`.

  extract_text.py paper.pdf [--out paper.txt]

Uses `pdftotext -layout` when installed; otherwise pypdf, installed once into
~/.cache/paper-research/pylib (no system-wide install). Warns when the PDF looks scanned (little text).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LIB = Path.home() / ".cache" / "paper-research" / "pylib"


def with_pdftotext(pdf: Path) -> list[str] | None:
    if not shutil.which("pdftotext"):
        return None
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    return out.split("\f")


def with_pypdf(pdf: Path) -> list[str]:
    if not (LIB / "pypdf").exists():
        LIB.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", str(LIB), "pypdf"], check=True)
    sys.path.insert(0, str(LIB))
    import logging

    logging.getLogger("pypdf").setLevel(logging.ERROR)  # font-encoding notices are noise here
    from pypdf import PdfReader  # noqa: E402

    return [page.extract_text() or "" for page in PdfReader(str(pdf)).pages]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pdf", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    pdf = a.pdf.resolve()
    if pdf.read_bytes()[:5] != b"%PDF-":
        print(f"{pdf} is not a PDF", file=sys.stderr)
        return 1

    pages = with_pdftotext(pdf) or with_pypdf(pdf)
    while pages and not pages[-1].strip():
        pages.pop()
    out = a.out or pdf.with_suffix(".txt")
    out.write_text("\n\n".join(f"[p. {i}]\n{t.strip()}" for i, t in enumerate(pages, 1)) + "\n", encoding="utf-8")

    chars = sum(len(t.strip()) for t in pages)
    print(f"{out}: {len(pages)} pages, {chars} characters")
    if pages and chars / len(pages) < 200:
        print("Warning: very little text per page; the PDF may be scanned (needs OCR).", file=sys.stderr)
    print("Note: [p. N] is the PDF page; the printed page number in the journal may differ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
