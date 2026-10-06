#!/usr/bin/env bash
# Sample GPU telemetry once per second to CSV until killed. Used by run_sweep.sh.
# Usage: ./sample_gpu.sh out.csv
# Newer drivers renamed clocks_throttle_reasons.* to clocks_event_reasons.*; use whichever this driver lists.
OUT=${1:-gpu_samples.csv}
R=clocks_throttle_reasons
nvidia-smi --help-query-gpu 2>/dev/null | grep -q 'clocks_event_reasons\.hw_slowdown' && R=clocks_event_reasons
exec nvidia-smi \
  --query-gpu=timestamp,index,utilization.gpu,utilization.memory,power.draw,clocks.sm,temperature.gpu,$R.hw_slowdown,$R.hw_thermal_slowdown,$R.sw_thermal_slowdown,$R.sw_power_cap \
  --format=csv,nounits -l 1 > "$OUT"
