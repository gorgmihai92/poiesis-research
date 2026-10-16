#!/usr/bin/env python3
"""Download the open copy of each work, or say where to find it. Run with `python3 -I`.

  copies.py --doi 10.x/abc [--doi …] [--download DIR]

Open copies are those OpenAlex or Semantic Scholar know of: publisher open access, university repositories,
author manuscripts, preprints. With --download DIR the first real PDF is saved as DIR/<slug>.pdf.
When there is no open copy, the work's page is given (library, author, or purchase).
"""
import argparse
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scholarly as sc  # noqa: E402

STOP = {"the", "a", "an", "of", "and", "in", "on", "for", "to"}


def slug(w: dict) -> str:
    surname = (sc.fold((w.get("authors") or ["anon"])[0]).split() or ["anon"])[-1]
    words = [x for x in sc.fold(w.get("title", "")).split() if x not in STOP][:4]
    return "-".join([surname, str(w.get("year") or "nd"), *words])


def open_pdfs(doi: str) -> tuple[dict, list[str]]:
    raw = sc.openalex_work(doi) or {}
    w = sc.norm_openalex(raw) if raw else {**sc.empty(), "doi": doi}
    urls = [loc["pdf_url"] for loc in raw.get("locations", []) if loc.get("is_oa") and loc.get("pdf_url")]
    try:
        s2 = sc.s2_doi(doi)
        if s2 and s2.get("oa_pdf") and s2["oa_pdf"] not in urls:
            urls.append(s2["oa_pdf"])
    except Exception:
        pass  # Semantic Scholar busy: OpenAlex's locations are enough
    return w, urls


def download(urls: list[str], dest: Path) -> str | None:
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={**sc.UA, "Accept": "application/pdf"})
            with urllib.request.urlopen(req, timeout=60) as res:
                data = res.read()
        except Exception:
            continue
        if data[:5] == b"%PDF-":  # not a landing page
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return url
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--doi", action="append", required=True)
    p.add_argument("--download", type=Path, help="save open PDFs here")
    a = p.parse_args()

    got = 0
    for doi in a.doi:
        w, urls = open_pdfs(doi.removeprefix("https://doi.org/"))
        print(f"{w.get('title') or doi} ({w.get('year')})")
        if a.download and urls:
            dest = a.download / f"{slug(w)}.pdf"
            if src := download(urls, dest):
                got += 1
                print(f"  ✓ saved {dest}  ← {src}")
                continue
        if urls:
            print(f"  open copy: {urls[0]}")
        else:
            print(f"  no open copy · https://doi.org/{w.get('doi') or doi}")
    if a.download:
        print(f"\nDownloaded {got} of {len(a.doi)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
