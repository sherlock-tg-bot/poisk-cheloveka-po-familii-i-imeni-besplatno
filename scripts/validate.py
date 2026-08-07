#!/usr/bin/env python3
"""Validate the repository's content contract without third-party packages."""
from html.parser import HTMLParser
from pathlib import Path
import re
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(name):
    path = ROOT / name
    if not path.is_file():
        errors.append(f"missing file: {name}")
        return ""
    return path.read_text(encoding="utf-8")

try:
    metadata = json.loads(read("metadata.json"))
except (json.JSONDecodeError, TypeError):
    metadata = {}
    errors.append("metadata.json is not valid JSON")

keyword = metadata.get("keyword", "")
target = metadata.get("target_url", "")
if not keyword or not target:
    errors.append("metadata.json must define keyword and target_url")

readme = read("README.md")
faq = read("FAQ.md")
security = read("SECURITY.md")
html = read("index.html")
workflow = read(".github/workflows/validate.yml")
validator = read("scripts/validate.py")

if keyword and not readme.startswith(f"# {keyword}"):
    errors.append("README H1 must start with the exact keyword")
if target:
    if readme.count(target) < 3:
        errors.append("target_url must appear at least three times in README")
    if target not in html:
        errors.append("target_url must appear in index.html")
for name, content in (("README.md", readme), ("FAQ.md", faq), ("SECURITY.md", security)):
    if re.search(r"https?://(?:www\.)?(?:sherlockbot\.is|glazboga\.is|t\.me|telegram\.me)(?:[/?)\"']|$)", content):
        errors.append(f"{name} contains a forbidden direct CTA URL")
if "Открыть в Telegram" not in readme or "Открыть в Telegram" not in html:
    errors.append("CTA text must be present in README and index.html")
for forbidden in ("гарантирует", "анонимност", "в реальном времени", "за пять секунд"):
    if forbidden.lower() in (readme + faq + security + html).lower():
        errors.append(f"forbidden promise or unsafe claim: {forbidden}")
if "python3 scripts/validate.py" not in workflow or "Content validation" not in workflow:
    errors.append("workflow must be named Content validation and run the validator")

class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.h1 = []; self.hrefs = []; self.has_title = False; self.in_h1 = False; self.errors = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1": self.in_h1 = True
        if tag == "title": self.has_title = True
        if tag == "a" and "href" in attrs: self.hrefs.append(attrs["href"])
    def handle_endtag(self, tag):
        if tag == "h1": self.in_h1 = False
    def handle_data(self, data):
        if self.in_h1: self.h1.append(data)

parser = DocumentParser()
try: parser.feed(html)
except Exception as exc: errors.append(f"index.html parse error: {exc}")
if not parser.h1: errors.append("index.html must contain an H1")
if keyword and keyword not in "".join(parser.h1):
    errors.append("index.html must contain the exact keyword in H1 text")
if not parser.has_title: errors.append("index.html must contain a title")
if target and target not in parser.hrefs: errors.append("CTA href missing from index.html")
if len([line for line in faq.splitlines() if line.startswith("## ")]) < 4:
    errors.append("FAQ.md must contain at least four questions")
if not validator: errors.append("validator is empty")

if errors:
    print("Validation failed:")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)
print("Validation passed: required files, keyword, CTA, safety rules, FAQ, and HTML are valid.")
