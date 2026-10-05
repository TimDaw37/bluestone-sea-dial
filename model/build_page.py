#!/usr/bin/env python3
"""docs/app.html is the page body (as published as a claude.ai artifact); wrap it as docs/index.html for GitHub Pages."""
from pathlib import Path
d = Path(__file__).resolve().parent.parent / "docs"
body = (d / "app.html").read_text()
(d / "index.html").write_text('<!doctype html>\n<html lang="en-GB"><head><meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    '<meta name="description" content="Least-cost sensitivity model: at what cost of water travel does a Preseli to Stonehenge route take the sea?">\n'
    '</head><body>\n' + body + '\n</body></html>\n')
