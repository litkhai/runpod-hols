#!/usr/bin/env python3
"""Fetch the public pages this lab cites and keep the lines it relies on, with URL and date read.

Usage: python3 collect_evidence.py [out.md]   (default: ../evidence/excerpts.md)

Only the matching lines are kept, not whole pages. Lines from a page's "Agent Instructions" block
(text addressed to AI agents, present on docs.runpod.io) are dropped; they are not documentation.
A pattern that matches nothing is reported as "no match", which means the page changed.
"""
import html, json, os, re, subprocess, sys, tempfile, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "evidence", "excerpts.md")
UA = {"User-Agent": "Mozilla/5.0 (runpod-hols inference-characterization evidence)"}

SOURCES = [
    ("Runpod docs — Choose a Pod (Secure vs Community)", "https://docs.runpod.io/pods/choose-a-pod.md",
     [r"Secure Cloud", r"Community Cloud", r"no longer accepting new hosts", r"Peer-to-peer", r"T3/T4"]),
    ("Runpod docs — Pod pricing", "https://docs.runpod.io/pods/pricing.md",
     [r"Commitment", r"Savings plans? ", r"by the second", r"per-second"]),
    ("Runpod docs — Pod migration", "https://docs.runpod.io/pods/troubleshooting/pod-migration.md",
     [r"beta", r"unavailable", r"migrate"]),
    ("Runpod API v2 — Stream serverless worker logs", "https://docs.runpod.io/api-reference-v2/serverless/stream-serverless-worker-logs.md",
     [r"/v2/serverless/\{id\}/workers/\{workerId\}/logs", r"Server-Sent Events", r"source.*container", r"Omit to include both", r"backfill", r"Maximum 5000"]),
    ("Runpod API v2 — List serverless endpoint workers", "https://docs.runpod.io/api-reference-v2/serverless/list-serverless-endpoint-workers.md",
     [r"/v2/serverless/\{id\}/workers", r"gpuTypeId", r"dataCenterId", r"startedAt", r"THROTTLED|IDLE|RUNNING"]),
    ("Runpod docs — Endpoint settings (FlashBoot, GPU priority)", "https://docs.runpod.io/serverless/endpoints/endpoint-configurations.md",
     [r"FlashBoot", r"consistent traffic", r"up to three GPU types", r"Active workers", r"Idle timeout"]),
    ("Runpod docs — Cached models", "https://docs.runpod.io/serverless/endpoints/model-caching.md",
     [r"cold start", r"cached", r"Hugging Face"]),
    ("Runpod docs — Serverless logs", "https://docs.runpod.io/serverless/development/logs.md",
     [r"retention|retain|days|hours", r"worker logs", r"container"]),
    ("Runpod Overdrive", "https://www.runpod.io/overdrive",
     [r"Same GPU", r"Tell us your workload", r"beat your baseline", r"Sub-200ms", r"Builds upon Runpod Serverless", r"vLLM"]),
    ("worker-vllm v2.28.0 release", "https://api.github.com/repos/runpod-workers/worker-vllm/releases/tags/v2.28.0",
     [r"vLLM to v0\.30\.0"]),
    ("vLLM v0.31.0 — vllm/benchmarks/serve.py", "https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/vllm/benchmarks/serve.py",
     [r"when using random datasets, default to ignoring EOS", r'"--goodput"', r'"--metadata"', r'result\[f"p\{p_word\}_', r'"output_throughput"', r'"request_goodput"']),
    ("vLLM v0.31.0 — vllm/v1/metrics/loggers.py", "https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/vllm/v1/metrics/loggers.py",
     [r'name="vllm:num_preemptions"']),
    ("PyPI — vllm 0.31.0 requires_dist", "https://pypi.org/pypi/vllm/0.31.0/json", None),
    ("Runpod REST API v1 — OpenAPI spec", "https://rest.runpod.io/v1/openapi.json", None),
]


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def text_lines(raw):
    if "<html" in raw[:2000].lower():
        raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
        raw = html.unescape(re.sub(r"<[^>]+>", "\n", raw))
    out, skip = [], False
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("> ## Agent Instructions"):
            skip = True
            continue
        if skip and (s.startswith("> ") or s == ">"):
            continue
        skip = False
        if s:
            out.append(s)
    return out


def main():
    today = time.strftime("%Y-%m-%d")
    md = ["# Evidence excerpts", "", "Lines this lab relies on, fetched by `lab/collect_evidence.py` on %s. Each block keeps only the matching lines; follow the URL for context." % today, ""]
    for title, url, pats in SOURCES:
        md += ["## %s" % title, "", "<%s> — read %s" % (url, today), ""]
        try:
            raw = fetch(url)
        except Exception as e:  # keep going: one unreachable page should not lose the rest
            md += ["Fetch failed: `%s`" % e, ""]
            continue
        if url.endswith("/json") and "pypi.org" in url:
            reqs = json.loads(raw)["info"]["requires_dist"]
            md += ["```", *[r for r in reqs if r.startswith(("torch", "nvidia"))], "```", ""]
            continue
        if url.startswith("https://api.github.com/"):
            body = json.loads(raw).get("body") or ""
            md += ["```", *[l for l in body.splitlines() if any(re.search(p, l) for p in pats)], "```", ""]
            continue
        if url.endswith("openapi.json"):
            d = json.loads(raw)
            pc = d["components"]["schemas"]["PodCreateInput"]["properties"]
            ec = d["components"]["schemas"]["EndpointCreateInput"]["properties"]
            md += ["```",
                   "paths: %d" % len(d["paths"]),
                   "PodCreateInput.allowedCudaVersions enum: %s" % pc["allowedCudaVersions"]["items"].get("enum"),
                   "PodCreateInput fields used: cloudType, gpuTypeIds, allowedCudaVersions, supportPublicIp, ports, env",
                   "EndpointCreateInput fields used: flashboot, idleTimeout, workersMin, workersMax, minCudaVersion, gpuTypeIds",
                   "Pod.portMappings: " + d["components"]["schemas"]["Pod"]["properties"]["portMappings"]["description"][:160],
                   "```", ""]
            continue
        lines = text_lines(raw)
        if url.endswith(".py"):
            hits = ["%d: %s" % (i + 1, l) for i, l in enumerate(raw.splitlines()) if any(re.search(p, l) for p in pats)]
        else:
            seen, hits = set(), []
            for l in lines:
                if any(re.search(p, l, re.I) for p in pats) and l not in seen and len(l) < 400:
                    seen.add(l)
                    hits.append(l)
        missing = [p for p in pats if not any(re.search(p, h, re.I) for h in hits)]
        md += ["```", *hits[:25], "```", ""]
        if missing:
            md += ["No match for: %s" % ", ".join("`%s`" % m for m in missing), ""]
    md += ["## NVIDIA H100 NVL product brief", "",
           "<https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/h100/PB-11773-001_v01.pdf> — read %s" % today, ""]
    try:
        pdf = os.path.join(tempfile.mkdtemp(), "pb-11773.pdf")
        req = urllib.request.Request("https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/h100/PB-11773-001_v01.pdf", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r, open(pdf, "wb") as f:
            f.write(r.read())
        txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
        block = txt[txt.find("Total board power"):txt.find("Thermal solution")]
        md += ["```", block.rstrip(), "```", ""]
    except Exception as e:
        md += ["Fetch or pdftotext failed: `%s`" % e, ""]
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    open(OUT, "w").write("\n".join(md) + "\n")
    print("->", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
