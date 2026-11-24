"""One-GPU Secure Pod stock from the REST v2 catalog, with and without a CUDA 13 floor.

REST v2 카탈로그에서 CUDA 13 하한 유무별 1-GPU Secure Pod 재고를 읽는다.

Used by stock_create_probe.py and stock_snapshots.sh (#126; the October runs used the
GraphQL lowestPrice { stockStatus } query). v2 says HIGH/MEDIUM/LOW/NONE; the values keep
the GraphQL spelling (High/Medium/Low/None) so old and new result files compare directly.
v2 값을 GraphQL 표기 (High/Medium/Low/None) 로 바꿔 10월 결과와 바로 비교되게 한다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pod_sweep import api, load_env  # noqa: E402

KEEP = ("H100", "H200", "A100", "L40", "4090", "L4", "B200")
LEGACY = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low", "NONE": None}


def snapshot() -> dict:
    load_env()
    base = "/catalog/gpus?include=AVAILABILITY&product=POD&cloud=SECURE&count=1"
    c13 = {g["id"]: LEGACY.get(g.get("availability")) for g in api("GET", base + "&minCudaVersion=13.0")["gpus"]}
    anyc = {g["id"]: LEGACY.get(g.get("availability")) for g in api("GET", base)["gpus"]}
    return {i: [c13.get(i), anyc.get(i)] for i in anyc if any(k in i for k in KEEP)}
