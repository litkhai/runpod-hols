#!/usr/bin/env bash
# Parse-check every tracked shell, Python, YAML and JSON file.
# Run from anywhere:  ./.github/scripts/check_syntax.sh
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"
failed=0
err="$(mktemp)"
trap 'rm -f "$err"' EXIT

echo "--- shell (bash -n)"
while IFS= read -r f; do
    if ! bash -n "$f" 2>"$err"; then
        echo "  FAIL $f"; sed 's/^/        /' "$err"; failed=1
    fi
done < <(git ls-files '*.sh' '.githooks/*')
echo "    $(git ls-files '*.sh' '.githooks/*' | wc -l | tr -d ' ') files"

echo "--- python (py_compile)"
while IFS= read -r f; do
    if ! python3 -m py_compile "$f" 2>"$err"; then
        echo "  FAIL $f"; sed 's/^/        /' "$err"; failed=1
    fi
done < <(git ls-files '*.py')
echo "    $(git ls-files '*.py' | wc -l | tr -d ' ') files"
find . -name __pycache__ -type d -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true

echo "--- yaml (safe_load)"
while IFS= read -r f; do
    if ! python3 -c "import sys,yaml; list(yaml.safe_load_all(open(sys.argv[1])))" "$f" 2>"$err"; then
        echo "  FAIL $f"; sed 's/^/        /' "$err"; failed=1
    fi
done < <(git ls-files '*.yml' '*.yaml')
echo "    $(git ls-files '*.yml' '*.yaml' | wc -l | tr -d ' ') files"

echo "--- json (json.load; .jsonl line by line)"
while IFS= read -r f; do
    if ! python3 -c "
import json, sys
p = sys.argv[1]
with open(p) as fh:
    if p.endswith('.jsonl'):
        for n, line in enumerate(fh, 1):
            if line.strip():
                json.loads(line)
    else:
        json.load(fh)
" "$f" 2>"$err"; then
        echo "  FAIL $f"; tail -1 "$err" | sed 's/^/        /'; failed=1
    fi
done < <(git ls-files '*.json' '*.jsonl')
echo "    $(git ls-files '*.json' '*.jsonl' | wc -l | tr -d ' ') files"

[ "$failed" -eq 0 ] && echo "OK: all files parse"
exit "$failed"
