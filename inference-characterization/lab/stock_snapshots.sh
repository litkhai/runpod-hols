#!/usr/bin/env bash
# Append a one-GPU Secure stock snapshot (with and without a CUDA 13 floor) every INTERVAL seconds.
# Read-only REST v2 catalog reads (#126; the October snapshots used GraphQL); nothing is created or billed.
# Values keep the GraphQL spelling (High/Medium/Low/null) so old and new snapshots compare.
# Usage: INTERVAL=600 COUNT=8 ./stock_snapshots.sh results/stock_snapshots.jsonl
OUT=${1:?out.jsonl}; INTERVAL=${INTERVAL:-600}; COUNT=${COUNT:-8}
DIR=$(cd "$(dirname "$0")" && pwd)
for i in $(seq 1 "$COUNT"); do
  python3 -c '
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
from stock_v2 import snapshot
print(json.dumps({"queried_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "secure_1gpu_[cuda13,any]": snapshot()}))
' "$DIR" >> "$OUT" && echo "$(date +%T) snapshot $i"
  [ "$i" -lt "$COUNT" ] && sleep "$INTERVAL"
done
