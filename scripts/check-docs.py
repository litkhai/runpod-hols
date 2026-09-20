#!/usr/bin/env python3
"""Check the documentation conventions this repository relies on.

Run from anywhere:

    python3 scripts/check-docs.py          # report and exit non-zero on failure
    python3 scripts/check-docs.py -v       # also list what passed

Every check here exists because something actually broke. See AGENTS.md.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "_site", "node_modules", ".venv", ".jekyll-cache"}

# Liquid runs before Markdown, so `{{ '/x/' | relative_url }}` contributes a
# pipe to the source that never reaches the rendered table. Strip Liquid before
# counting columns or four tables read as ragged when they are fine.
LIQUID = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

failures: list[str] = []
passes: list[str] = []


def fail(path, msg):
    failures.append(f"{path}: {msg}")


def ok(msg):
    passes.append(msg)


def md_files():
    for p in sorted(ROOT.rglob("*.md")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def rel(p):
    return p.relative_to(ROOT).as_posix()


# --------------------------------------------------------------------------
# 1. Bilingual structure
#
# Every README and site page carries a full English section and a full Korean
# one. Sections are meant to mirror each other, so an unequal heading count
# means one language is missing something the other has.
# --------------------------------------------------------------------------
def check_bilingual():
    # Anchored to line start: prose that merely mentions `## English` in
    # backticks — AGENTS.md describing this very convention — is not a section.
    marker = re.compile(r"^## (?:English|한국어)\s*$", re.M)

    checked = 0
    for p in md_files():
        raw = p.read_text()
        if not marker.search(raw):
            continue
        text = LIQUID.sub("X", raw)
        parts = re.split(r"^## (English|한국어)\s*$", text, flags=re.M)
        if len(parts) < 5:
            fail(rel(p), "has one language section but not the other")
            continue
        en, ko = parts[2], parts[4]
        checked += 1

        for level in (2, 3):
            pat = re.compile(r"^#{%d} (?!English|한국어)(.+)$" % level, re.M)
            a, b = pat.findall(en), pat.findall(ko)
            if len(a) != len(b):
                fail(rel(p), f"h{level} count differs: {len(a)} EN vs {len(b)} KO")

        for name, half in (("EN", en), ("KO", ko)):
            if half.count("```") % 2:
                fail(rel(p), f"[{name}] unbalanced code fence")
            run = []
            for line in half.split("\n"):
                if line.strip().startswith("|"):
                    run.append(line.count("|"))
                else:
                    if len(set(run)) > 1:
                        fail(rel(p), f"[{name}] table with inconsistent columns {sorted(set(run))}")
                    run = []
    ok(f"bilingual structure: {checked} files")


# --------------------------------------------------------------------------
# 2. Site pages
#
# Each page in docs/ wraps its two languages in `.lang` blocks that the toggle
# shows and hides. A missing or unbalanced block leaves content stranded in a
# hidden div.
# --------------------------------------------------------------------------
def check_site_pages():
    checked = 0
    for p in sorted((ROOT / "docs").glob("*.md")):
        text = p.read_text()
        if not text.startswith("---"):
            fail(rel(p), "missing YAML front matter")
            continue
        front = text.split("---", 2)[1]
        if "layout: null" in front:          # redirect stub, no content of its own
            continue
        checked += 1
        for key in ("layout:", "title:", "permalink:"):
            if key not in front:
                fail(rel(p), f"front matter missing `{key}`")

        langs = re.findall(r'<div class="lang" data-lang="(\w+)"', text)
        if langs != ["en", "ko"]:
            fail(rel(p), f"expected one en and one ko .lang block, found {langs}")

        depth = 0
        for m in re.finditer(r"<div\b[^>]*>|</div>", text):
            depth += 1 if m.group().startswith("<div") else -1
            if depth < 0:
                fail(rel(p), "a </div> closes more than was opened")
                break
        if depth > 0:
            fail(rel(p), f"{depth} unclosed <div>")
    ok(f"site pages: {checked} files")


# --------------------------------------------------------------------------
# 3. Navigation
#
# Every nav entry must resolve to a real page, and every content page must be
# reachable. A page moved without updating _config.yml 404s silently.
# --------------------------------------------------------------------------
def check_nav():
    config = (ROOT / "docs" / "_config.yml").read_text()
    nav_block = config.split("nav:", 1)[1]
    nav_urls = re.findall(r"url:\s*(\S+?)\s*[,}]", nav_block)
    nav_parents = set(re.findall(r"parent:\s*([^,}]+?)\s*[,}]", nav_block))
    nav_titles = set(t.strip() for t in re.findall(r"title:\s*([^,}]+?)\s*[,}]", nav_block))

    permalinks = {}
    for p in sorted((ROOT / "docs").glob("*.md")):
        m = re.search(r"^permalink:\s*(\S+)", p.read_text(), re.M)
        if m:
            permalinks[m.group(1)] = p

    for url in nav_urls:
        if url not in permalinks:
            fail("docs/_config.yml", f"nav points at `{url}` but no page has that permalink")

    for url, p in permalinks.items():
        if url in nav_urls:
            continue
        if "layout: null" in p.read_text():   # redirect stubs are deliberately unlisted
            continue
        fail(rel(p), f"permalink `{url}` is not in the nav and is not a redirect stub")

    for parent in nav_parents:
        if parent not in nav_titles:
            fail("docs/_config.yml", f"`parent: {parent}` names an item that does not exist")

    ok(f"nav: {len(nav_urls)} entries, {len(permalinks)} pages")


# --------------------------------------------------------------------------
# 4. Internal links
#
# Relative links between repo documents break silently when a file moves.
# --------------------------------------------------------------------------
def check_internal_links():
    count = 0
    for p in md_files():
        for target in re.findall(r"\]\((\.{1,2}/[^)\s#]+)", p.read_text()):
            count += 1
            resolved = (p.parent / target).resolve()
            if not resolved.exists():
                fail(rel(p), f"link to `{target}` does not resolve")
    ok(f"internal links: {count} checked")


# --------------------------------------------------------------------------
# 5. Secrets
#
# .env holds a live API key. It must never be tracked.
# --------------------------------------------------------------------------
def check_secrets():
    try:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        ok("secrets: skipped, git unavailable")
        return

    for name in tracked:
        if Path(name).name in {".env", ".env.bak"}:
            fail(name, "a secrets file is tracked by git")

    env = ROOT / ".env"
    if env.exists():
        mode = oct(env.stat().st_mode)[-3:]
        if mode != "600":
            fail(".env", f"mode is {mode}, expected 600")
    ok(f"secrets: {len(tracked)} tracked files scanned")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true", help="list checks that passed")
    args = ap.parse_args()

    for check in (check_bilingual, check_site_pages, check_nav,
                  check_internal_links, check_secrets):
        check()

    if args.verbose:
        for line in passes:
            print(f"  ok    {line}")

    if failures:
        print(f"\n{len(failures)} problem(s):\n", file=sys.stderr)
        for line in failures:
            print(f"  FAIL  {line}", file=sys.stderr)
        return 1

    print(f"All checks passed ({len(passes)} groups).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
