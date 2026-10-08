#!/usr/bin/env python3
"""Merge vllm bench results + GPU samples + host facts into results/profile.json and results/PROFILE.md.

Usage: python3 build_profile.py [results_dir]
Optional: results_dir/prices.json -> {"H100_SXM": 2.69, "A100_80GB": 1.19, ...}
          (USD per GPU-hour, copied from Runpod pricing at run time)
"""
import csv, glob, json, os, re, sys
from statistics import mean

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
prices_path = os.path.join(root, "prices.json")
prices = json.load(open(prices_path)) if os.path.exists(prices_path) else {}


def metric(txt, name):
    m = re.search(r"^" + re.escape(name) + r"(?:\{[^}]*\})?\s+([0-9.eE+-]+)\s*$", txt, re.M)
    return float(m.group(1)) if m else None


def read(path):
    return open(path).read() if os.path.exists(path) else ""


rows = []
for gpu_dir in sorted(glob.glob(os.path.join(root, "*"))):
    if not os.path.isdir(gpu_dir):
        continue
    gpu = os.path.basename(gpu_dir)
    host_path = os.path.join(gpu_dir, "host.json")
    host = json.load(open(host_path)) if os.path.exists(host_path) else {}
    g0 = (host.get("gpus") or [{}])[0]
    env = host.get("runpod_env", {})
    for res in sorted(glob.glob(os.path.join(gpu_dir, "*_rate*.json"))):
        r = json.load(open(res))
        base = res[:-5]
        samples = list(csv.DictReader(open(base + ".gpu.csv"))) if os.path.exists(base + ".gpu.csv") else []

        def col(prefix):
            vals = []
            for s in samples:
                for k, v in s.items():
                    if k and k.strip().startswith(prefix):
                        try:
                            vals.append(float(v))
                        except (TypeError, ValueError):
                            pass
            return vals

        util, power, clock, temp = col("utilization.gpu"), col("power.draw"), (col("clocks.sm") or col("clocks.current.sm")), col("temperature.gpu")
        throttled = sum(1 for s in samples if any(("throttle" in (k or "") or "event_reasons" in (k or "")) and (v or "").strip() == "Active" for k, v in s.items()))
        before, after = read(base + ".metrics_before.txt"), read(base + ".metrics_after.txt")
        preempt = (metric(after, "vllm:num_preemptions_total") or 0) - (metric(before, "vllm:num_preemptions_total") or 0)
        # Share of prompt tokens served from the prefix cache during this run. A fixed bench seed repeats
        # the same prompts at every rate, so a GPU with a large KV cache can serve later runs from cache.
        dq = (metric(after, "vllm:prefix_cache_queries_total") or 0) - (metric(before, "vllm:prefix_cache_queries_total") or 0)
        dh = (metric(after, "vllm:prefix_cache_hits_total") or 0) - (metric(before, "vllm:prefix_cache_hits_total") or 0)
        prefix_hit = round(dh / dq, 3) if dq > 0 else None
        out_tps = r.get("output_throughput")
        price = prices.get(gpu)
        rows.append({
            "gpu_label": gpu, "gpu_name": g0.get("name"), "gpu_uuid": g0.get("uuid"),
            "pcie": f"gen{g0.get('pcie_gen')}x{g0.get('pcie_width')}" if g0 else None,
            "datacenter": env.get("RUNPOD_DC_ID"), "host": env.get("RUNPOD_POD_HOSTNAME"),
            "use_case": r.get("use_case"), "rate_req_s": float(r["rate"]) if r.get("rate") is not None else r.get("request_rate"),
            "input_len": r.get("input_len"), "output_len": r.get("output_len"),
            "completed": r.get("completed"), "duration_s": r.get("duration"),
            "request_throughput": r.get("request_throughput"), "goodput_req_s": r.get("request_goodput"),
            "output_tok_s": out_tps, "total_tok_s": r.get("total_token_throughput"),
            "ttft_p50_ms": r.get("median_ttft_ms"), "ttft_p99_ms": r.get("p99_ttft_ms"),
            "tpot_p50_ms": r.get("median_tpot_ms"), "tpot_p99_ms": r.get("p99_tpot_ms"),
            "e2e_p50_ms": r.get("median_e2el_ms"), "e2e_p99_ms": r.get("p99_e2el_ms"),
            "gpu_util_mean": round(mean(util), 1) if util else None,
            "power_w_mean": round(mean(power), 1) if power else None,
            "sm_clock_mean": round(mean(clock)) if clock else None,
            "temp_max": max(temp) if temp else None,
            "throttle_samples": throttled, "samples": len(samples),
            "preemptions": preempt, "prefix_cache_hit_rate": prefix_hit,
            "usd_per_gpu_hour": price,
            "usd_per_1m_output_tok": round(price / 3600 / out_tps * 1e6, 4) if price and out_tps else None,
        })

# Cost at SLO: per (gpu, use case), the highest swept rate where at least SLO_ATTAIN of requests
# met the SLO (goodput / request throughput). Below saturation, output tok/s only tracks the offered
# rate, so the per-row $/1M is not a cost at SLO.
ATTAIN = float(os.environ.get("SLO_ATTAIN", "0.9"))
at_slo = {}
for x in rows:
    rt, gp = x["request_throughput"], x["goodput_req_s"]
    x["slo_attainment"] = round(gp / rt, 3) if rt and gp is not None else None
    if x["slo_attainment"] is None or x["slo_attainment"] < ATTAIN:
        continue
    k = (x["gpu_label"], x["use_case"])
    if k not in at_slo or float(x["rate_req_s"] or 0) > float(at_slo[k]["rate_req_s"] or 0):
        at_slo[k] = x

json.dump({"slo_attainment_threshold": ATTAIN, "rows": rows,
           "cost_at_slo": [{"gpu_label": g, "use_case": u, "rate_req_s": x["rate_req_s"],
                            "output_tok_s": x["output_tok_s"], "slo_attainment": x["slo_attainment"],
                            "usd_per_1m_output_tok": x["usd_per_1m_output_tok"]}
                           for (g, u), x in sorted(at_slo.items())]},
          open(os.path.join(root, "profile.json"), "w"), indent=2)


def f(v, d=0):
    if v is None:
        return "-"
    return f"{v:.{d}f}" if isinstance(v, (int, float)) else str(v)


hdr = ["gpu", "use_case", "rate", "out tok/s", "goodput req/s", "TTFT p50/p99 ms", "TPOT p50/p99 ms",
       "e2e p99 ms", "GPU util %", "W", "throttle", "preempt", "prefix hit", "$/1M out tok"]
lines = ["# Hardware sensitivity profile", "", "| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
for x in sorted(rows, key=lambda x: (x["use_case"] or "", float(x["rate_req_s"] or 0), x["gpu_label"])):
    lines.append("| " + " | ".join([
        x["gpu_label"], f(x["use_case"]), f"{x['rate_req_s']:g}" if x["rate_req_s"] is not None else "-", f(x["output_tok_s"]), f(x["goodput_req_s"], 2),
        f"{f(x['ttft_p50_ms'])}/{f(x['ttft_p99_ms'])}", f"{f(x['tpot_p50_ms'], 1)}/{f(x['tpot_p99_ms'], 1)}",
        f(x["e2e_p99_ms"]), f(x["gpu_util_mean"]), f(x["power_w_mean"]),
        f"{x['throttle_samples']}/{x['samples']}", f(x["preemptions"]),
        f"{x['prefix_cache_hit_rate']:.0%}" if x["prefix_cache_hit_rate"] is not None else "-", f(x["usd_per_1m_output_tok"], 3),
    ]) + " |")
lines += ["", "`prefix hit` is the share of prompt tokens served from vLLM's prefix cache in that run. Runs with a high share did little prefill work, so their latency and throughput are not comparable with runs near 0%.",
          "", f"## Cost at SLO (highest swept rate with SLO attainment >= {ATTAIN:.0%})", "",
          "| use_case | gpu | rate | out tok/s | attainment | $/1M out tok |", "|---|---|---|---|---|---|"]
for (g, u), x in sorted(at_slo.items(), key=lambda kv: (kv[0][1], kv[1]["usd_per_1m_output_tok"] or 1e9)):
    lines.append(f"| {u} | {g} | {x['rate_req_s']:g} | {f(x['output_tok_s'])} | {f(x['slo_attainment'], 2)} | {f(x['usd_per_1m_output_tok'], 3)} |")
lines += ["", "Pairs missing here never reached the threshold at any swept rate, or have no price in `prices.json`.",
          "",
          "Rows are sorted by use case and request rate so the same operating point can be compared across GPUs.",
          "Host facts per GPU label are in `<gpu_label>/host.json`. `throttle` counts 1-second samples with any active throttle reason."]
open(os.path.join(root, "PROFILE.md"), "w").write("\n".join(lines) + "\n")
print(f"{len(rows)} rows -> {os.path.join(root, 'profile.json')} and PROFILE.md")
