#!/usr/bin/env bash
# Runs inside the Pod (started by pod_sweep.py): install vLLM, start the server, run the sweep, mark DONE.
# Usage: GPU_LABEL=... MODEL=... VLLM_VERSION=... MAX_MODEL_LEN=... ./pod_bootstrap.sh
set -uo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
cd "$DIR"
: "${GPU_LABEL:?}" "${MODEL:?}" "${VLLM_VERSION:?}"
MAX_MODEL_LEN=${MAX_MODEL_LEN:-8192}
export HF_HOME=${HF_HOME:-/root/hf}
rm -f DONE FAILED
# Keep the server log with the results even when a step fails.
fail() { echo "FAILED: $*"; echo "$*" > FAILED; mkdir -p "results/$GPU_LABEL"; [ -f vllm.log ] && cp vllm.log "results/$GPU_LABEL/vllm.log"; exit 1; }

echo "== install vllm==$VLLM_VERSION ($(date -u +%FT%TZ))"
# A venv, because the image's system Python has Debian-owned packages (PyJWT) that pip cannot
# uninstall when vLLM's resolver wants a different version.
# System pip is avoided entirely: uv comes from its standalone installer, python3 -m venv is the fallback.
if curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/.local/bin sh >/dev/null 2>&1; then
  /root/.local/bin/uv venv /root/venv --python python3 || fail "uv venv"
  /root/.local/bin/uv pip install --python /root/venv/bin/python "vllm==$VLLM_VERSION" 2>&1 | tail -3
else
  echo "uv installer failed, falling back to python3 -m venv"
  python3 -m venv /root/venv || fail "python3 -m venv"
  /root/venv/bin/python -m pip install -q "vllm==$VLLM_VERSION" 2>&1 | tail -5
fi
export PATH=/root/venv/bin:$PATH
python3 -c 'import vllm' 2>/dev/null || fail "vllm not importable from /root/venv"
python3 -c 'import vllm,torch;print("vllm",vllm.__version__,"torch",torch.__version__,"cuda",torch.version.cuda,"gpu_ok",torch.cuda.is_available())'

echo "== flag check"
HELP=$(vllm bench serve --help=all 2>/dev/null || vllm bench serve --help 2>&1)
for f in dataset-name random-input-len random-output-len request-rate goodput percentile-metrics \
         metric-percentiles save-result result-dir result-filename metadata ignore-eos seed; do
  grep -q -- "--$f" <<<"$HELP" || fail "vllm bench serve lacks --$f"
done
echo "all flags present"

echo "== serve ($(date -u +%FT%TZ))"
nohup vllm serve "$MODEL" --port 8000 --max-model-len "$MAX_MODEL_LEN" --gpu-memory-utilization 0.90 > vllm.log 2>&1 &
for _ in $(seq 1 180); do
  curl -sf localhost:8000/v1/models >/dev/null && break
  kill -0 $! 2>/dev/null || { tail -40 vllm.log; fail "vllm serve exited"; }
  sleep 5
done
curl -sf localhost:8000/v1/models >/dev/null || fail "vllm serve not ready after 15 min"
echo "ready ($(date -u +%FT%TZ))"
grep -iE 'KV cache|maximum concurrency' vllm.log | tail -3

echo "== sweep"
GPU_LABEL="$GPU_LABEL" MODEL="$MODEL" RATES_OVERRIDE="${RATES:-}" ./run_sweep.sh ${CASES:-} || fail "run_sweep.sh"
cp vllm.log "results/$GPU_LABEL/vllm.log"
date -u +%FT%TZ > DONE
echo "== DONE"
