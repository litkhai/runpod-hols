#!/usr/bin/env bash
# Capture host and GPU facts (the "platform context" a customer cannot normally see) into JSON.
# Usage: ./capture_host.sh [out.json]
set -euo pipefail
OUT=${1:-host.json}
GPU_CSV=$(nvidia-smi --query-gpu=index,name,uuid,driver_version,memory.total,pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,pcie.link.width.max,clocks.max.sm,power.limit --format=csv,noheader,nounits)
# nvidia-smi underlines the header with ANSI escapes; strip them.
TOPO=$(nvidia-smi topo -m 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' || echo "n/a")
CPU=$(lscpu | grep -E '^(Model name|Socket\(s\)|NUMA node\(s\)|CPU\(s\)|Thread\(s\) per core)' | sed 's/  */ /g' || true)
python3 - "$OUT" "$GPU_CSV" "$TOPO" "$CPU" <<'PY'
import json, os, sys, subprocess, platform
out, gpu_csv, topo, cpu = sys.argv[1:5]
cols = ["index","name","uuid","driver","mem_mib","pcie_gen","pcie_gen_max","pcie_width","pcie_width_max","sm_clock_max_mhz","power_limit_w"]
gpus = [dict(zip(cols, [x.strip() for x in line.split(",")])) for line in gpu_csv.strip().splitlines()]
cuda = subprocess.run("nvidia-smi | grep -o 'CUDA Version: [0-9.]*' | head -1", shell=True, capture_output=True, text=True).stdout.strip()
vllm = subprocess.run("python3 -c 'import vllm;print(vllm.__version__)' 2>/dev/null", shell=True, capture_output=True, text=True).stdout.strip()
# Drop credentials, and the public IP and port map: they identify the Pod, not the hardware.
# Runpod sets RUNPOD_* on the container's PID 1; an SSH session does not inherit them.
env = dict(os.environ)
try:
    for kv in open("/proc/1/environ", "rb").read().split(b"\0"):
        k, _, v = kv.decode(errors="replace").partition("=")
        if k:
            env.setdefault(k, v)
except OSError:
    pass
redact = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PUBLIC_IP", "TCP_PORT", "UDP_PORT")
host = {
  "runpod_env": {k: v for k, v in env.items() if k.startswith("RUNPOD_") and not any(s in k for s in redact)},
  "gpus": gpus,
  "nvlink_topology": topo,
  "cpu": cpu,
  "cuda": cuda,
  "vllm_version": vllm,
  "kernel": platform.release(),
}
json.dump(host, open(out, "w"), indent=2)
print(json.dumps(host, indent=2))
PY
