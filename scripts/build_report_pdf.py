"""Render docs/REPORT.md to docs/Bayesian_Study_Planner_Report.pdf.

Needs the `markdown` package (pip install markdown) and Microsoft Edge or Google Chrome,
which does the HTML -> PDF step in headless mode.

    python scripts/build_report_pdf.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SOURCE = DOCS / "REPORT.md"
OUTPUT = DOCS / "Bayesian_Study_Planner_Report.pdf"

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
BROWSER_COMMANDS = ["google-chrome", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"]

CSS = """
@page { size: Letter; margin: 18mm 17mm; }
body { font-family: "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d2320; }
h1 { font-size: 22pt; margin: 0 0 2mm; }
h2 { font-size: 15pt; margin: 8mm 0 2mm; border-bottom: 1px solid #c9d0cb; padding-bottom: 1mm; break-after: avoid; }
h3 { font-size: 12pt; margin: 5mm 0 1.5mm; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #eef1ee; padding: 0 2px; border-radius: 2px; }
pre { background: #eef1ee; padding: 3mm; border-radius: 3px; overflow-wrap: anywhere; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 3mm 0; font-size: 9.5pt; break-inside: avoid; }
th, td { border: 1px solid #c9d0cb; padding: 1.2mm 2mm; text-align: left; vertical-align: top; }
th { background: #e4eae5; }
img { max-width: 100%; max-height: 120mm; display: block; margin: 3mm auto 1mm; break-inside: avoid; }
a { color: #234b36; }
"""


def find_browser() -> str:
    for path in BROWSERS:
        if Path(path).exists():
            return path
    for name in BROWSER_COMMANDS:
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("Edge or Chrome not found. Install one, or open docs/REPORT.md in a Markdown viewer and print to PDF.")


def main() -> None:
    body = markdown.markdown(SOURCE.read_text(encoding="utf-8"), extensions=["tables", "fenced_code", "sane_lists"])
    html = (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Bayesian Study Planner - COSC 329 Report</title>'
        f'<base href="{DOCS.as_uri()}/"><style>{CSS}</style></head><body>{body}</body></html>'
    )
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "report.html"
        page.write_text(html, encoding="utf-8")
        OUTPUT.unlink(missing_ok=True)
        subprocess.run(
            [find_browser(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={Path(tmp) / 'profile'}", f"--print-to-pdf={OUTPUT}", page.as_uri()],
            check=True, capture_output=True, timeout=120,
        )
    if not OUTPUT.exists():
        raise SystemExit("The browser did not produce a PDF.")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
