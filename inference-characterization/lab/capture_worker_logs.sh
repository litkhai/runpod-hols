#!/usr/bin/env bash
# Every 20 s, merge the logs (system + container) of every worker on a Serverless endpoint into
# OUT/<workerId>.jsonl, and save the worker list. Container logs disappear when the container is
# removed, so the window for capturing a cold start is the cold start itself.
# Usage: ./capture_worker_logs.sh <endpoint_id> <out_dir>      (stops when the endpoint is gone)
# API: GET /v2/serverless/{id}/workers and /v2/serverless/{id}/workers/{workerId}/logs (SSE),
# docs.runpod.io/api-reference-v2, read 2026-10-07.
EP=${1:?endpoint id}; OUT=${2:?out dir}; mkdir -p "$OUT"
DIR=$(cd "$(dirname "$0")" && pwd)
[ -n "${RUNPOD_API_KEY:-}" ] || { set -a; . "$DIR/../../.env"; set +a; }
H=(-H "Authorization: Bearer $RUNPOD_API_KEY" -H 'User-Agent: runpod-hols-inference-characterization/1.0')
while true; do
  j=$(curl -s --max-time 20 "${H[@]}" "https://api.runpod.io/v2/serverless/$EP/workers") || true
  grep -q '"workers"' <<<"$j" || { echo "$(date +%T) endpoint gone or unreadable"; break; }
  echo "$j" > "$OUT/workers_$(date +%H%M%S).json"
  for w in $(python3 -c 'import json,sys;print(" ".join(x["id"] for x in json.load(sys.stdin)["workers"]))' <<<"$j"); do
    curl -s -N --max-time 10 "${H[@]}" "https://api.runpod.io/v2/serverless/$EP/workers/$w/logs?tail=5000" \
      | sed -n 's/^data: //p' | python3 -c '
import json, os, sys
p = sys.argv[1]; seen = set(); rows = []
if os.path.exists(p):
    for l in open(p):
        if l.strip():
            r = json.loads(l); seen.add((r.get("ts"), r.get("source"), r.get("line"))); rows.append(r)
for l in sys.stdin:
    if l.strip().startswith("{"):
        r = json.loads(l); k = (r.get("ts"), r.get("source"), r.get("line"))
        if k not in seen:
            seen.add(k); rows.append(r)
rows.sort(key=lambda r: r.get("ts") or "")
open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows))
' "$OUT/$w.jsonl"
  done
  echo "$(date +%T) $(for f in "$OUT"/*.jsonl; do printf '%s=%s ' "$(basename "$f" .jsonl)" "$(wc -l < "$f")"; done)"
  sleep 20
done
