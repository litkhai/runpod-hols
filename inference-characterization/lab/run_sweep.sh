#!/usr/bin/env bash
# Run the use-case x request-rate sweep against a vLLM server running on this host.
# Requires: vllm installed (provides `vllm bench serve`), server listening on $PORT, nvidia-smi, curl.
# Usage: GPU_LABEL=H100_SXM MODEL=Qwen/Qwen2.5-7B-Instruct ./run_sweep.sh [use_case ...]
set -euo pipefail
GPU_LABEL=${GPU_LABEL:?set GPU_LABEL, e.g. H100_SXM or A100_80GB_community}
MODEL=${MODEL:-Qwen/Qwen2.5-7B-Instruct}
PORT=${PORT:-8000}
DIR=$(cd "$(dirname "$0")" && pwd)
RESULTS=${RESULTS:-$DIR/results/$GPU_LABEL}
mkdir -p "$RESULTS"

curl -sf "localhost:$PORT/v1/models" >/dev/null || { echo "vLLM server not reachable on port $PORT"; exit 1; }
"$DIR/capture_host.sh" "$RESULTS/host.json" >/dev/null

CASES=("$@")
if [ ${#CASES[@]} -eq 0 ]; then
  read -r -a CASES <<<"$(python3 -c "import json;print(' '.join(json.load(open('$DIR/use_cases.json'))))")"
fi

# --ignore-eos is explicit although vLLM 0.31.0 already forces it for the random dataset
# (vllm/benchmarks/serve.py), so every request generates exactly output_len tokens.

# Warm-up so the first measured run does not include CUDA-graph capture or allocator warm-up.
vllm bench serve --backend vllm --model "$MODEL" --host 127.0.0.1 --port "$PORT" \
  --dataset-name random --random-input-len 256 --random-output-len 64 --num-prompts 32 --request-rate inf >/dev/null 2>&1 || true

for uc in "${CASES[@]}"; do
  read -r IN OUTL N SLO <<<"$(python3 -c "import json;c=json.load(open('$DIR/use_cases.json'))['$uc'];print(c['input_len'],c['output_len'],c['num_prompts'],c['slo'])")"
  # RATES (e.g. "1") overrides the list in use_cases.json for a minimal functional run.
  RATES=${RATES_OVERRIDE:-$(python3 -c "import json;print(' '.join(map(str,json.load(open('$DIR/use_cases.json'))['$uc']['rates'])))")}
  for r in $RATES; do
    tag="${uc}_rate${r}"
    # A different seed per run: with one fixed seed every rate repeats the same random prompts, and a GPU
    # with a large KV cache serves later runs from its prefix cache instead of doing the prefill.
    SEED=$(printf '%s' "$GPU_LABEL-$tag" | cksum | cut -d' ' -f1)
    echo "=== $GPU_LABEL / $uc / rate=$r req/s (in=$IN out=$OUTL n=$N slo=$SLO)"
    curl -s "localhost:$PORT/metrics" > "$RESULTS/${tag}.metrics_before.txt"
    "$DIR/sample_gpu.sh" "$RESULTS/${tag}.gpu.csv" & SAMPLER=$!
    trap 'kill "$SAMPLER" 2>/dev/null || true' EXIT
    # shellcheck disable=SC2086  # $SLO is intentionally word-split into "ttft:1000 tpot:50"
    vllm bench serve --backend vllm --model "$MODEL" --host 127.0.0.1 --port "$PORT" \
      --dataset-name random --random-input-len "$IN" --random-output-len "$OUTL" \
      --num-prompts "$N" --request-rate "$r" --ignore-eos --seed "$SEED" --goodput $SLO \
      --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,90,99 \
      --save-result --result-dir "$RESULTS" --result-filename "${tag}.json" \
      --metadata gpu="$GPU_LABEL" use_case="$uc" rate="$r" input_len="$IN" output_len="$OUTL" \
      2>&1 | tee "$RESULTS/${tag}.log"
    kill "$SAMPLER" 2>/dev/null || true
    curl -s "localhost:$PORT/metrics" > "$RESULTS/${tag}.metrics_after.txt"
  done
done
echo "done -> $RESULTS"
