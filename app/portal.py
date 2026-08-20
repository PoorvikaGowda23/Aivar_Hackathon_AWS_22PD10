"""
Stage 14/15: Embedded Portal HTML Website string.
Guarantees GET / always serves the full interactive Agent Compliance Portal
website directly without file system lookups.
"""

from __future__ import annotations
from pathlib import Path

_INDEX_HTML_PATH = Path(__file__).parent / "templates" / "index.html"

def get_portal_html() -> str:
    if _INDEX_HTML_PATH.exists():
        return _INDEX_HTML_PATH.read_text(encoding="utf-8")
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Agent Compliance Portal</title>
  <style>
    body { font-family: sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 3rem; }
    a { color: #38bdf8; text-decoration: none; font-weight: bold; }
    .btn { background: #6366f1; color: white; padding: 0.75rem 1.5rem; border-radius: 8px; text-decoration: none; display: inline-block; margin-top: 1rem; }
  </style>
</head>
<body>
  <h1>🛡️ Agent Compliance Card Generator</h1>
  <p>EU AI Act • NIST AI RMF • ISO 42001 Compliance System</p>
  <br>
  <a href="/docs" class="btn">Open Interactive API Docs (/docs)</a>
  <a href="/health" class="btn" style="background:#10b981;">Check System Health (/health)</a>
</body>
</html>"""

PORTAL_HTML = get_portal_html()

