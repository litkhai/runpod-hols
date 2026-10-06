#!/usr/bin/env bash
# Append a one-GPU Secure stock snapshot (with and without a CUDA 13 floor) every INTERVAL seconds.
# Read-only GraphQL query; nothing is created or billed.
# Usage: INTERVAL=600 COUNT=8 ./stock_snapshots.sh results/stock_snapshots.jsonl
OUT=${1:?out.jsonl}; INTERVAL=${INTERVAL:-600}; COUNT=${COUNT:-8}
DIR=$(cd "$(dirname "$0")" && pwd)
[ -n "${RUNPOD_API_KEY:-}" ] || { set -a; . "$DIR/../../.env"; set +a; }
Q='{"query":"{ gpuTypes { id cuda13: lowestPrice(input:{gpuCount:1, secureCloud:true, minCudaVersion:\"13.0\"}) { stockStatus } any: lowestPrice(input:{gpuCount:1, secureCloud:true}) { stockStatus } } }"}'
for i in $(seq 1 "$COUNT"); do
  curl -s --max-time 30 -H "Authorization: Bearer $RUNPOD_API_KEY" -H 'Content-Type: application/json' \
       -H 'User-Agent: runpod-hols-inference-characterization/1.0' -d "$Q" https://api.runpod.io/graphql \
  | python3 -c '
import json, sys, time
d = json.load(sys.stdin)
keep = ("H100", "H200", "A100", "L40", "4090", "L4", "B200")
rows = {g["id"]: [(g["cuda13"] or {}).get("stockStatus"), (g["any"] or {}).get("stockStatus")]
        for g in d["data"]["gpuTypes"] if any(k in g["id"] for k in keep)}
print(json.dumps({"queried_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "secure_1gpu_[cuda13,any]": rows}))
' >> "$OUT" && echo "$(date +%T) snapshot $i"
  [ "$i" -lt "$COUNT" ] && sleep "$INTERVAL"
done
