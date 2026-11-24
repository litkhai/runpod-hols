#!/usr/bin/env python3
"""Verify the Runpod API key actually works, and show what it can see.

Runpod API 키가 실제로 동작하는지 확인하고, 무엇을 조회할 수 있는지 보여준다.

Read-only REST v2 calls (api.runpod.io/v2) — nothing is created, so nothing is billed.
A scoped key that lacks one of the scopes gets 403 for that call only; the script prints
the API's reason (which names the missing scope) and carries on (#103).
REST v2 읽기 호출만 한다. 생성하는 리소스가 없으므로 과금되지 않는다. scoped 키에 어떤
범위가 없으면 그 호출만 403 이 되고, 스크립트는 API 가 알려준 빠진 범위를 출력한 뒤 계속한다.

Usage / 사용법:
    python3 setup/verify-auth.py

Standard library only. Until 2026-11-24 this used the runpod SDK, whose get_user() goes
through GraphQL — a scoped key with GraphQL set to None fails there.
표준 라이브러리만 쓴다. 이전에는 runpod SDK 의 get_user() (GraphQL) 를 썼는데, GraphQL 을
None 으로 둔 scoped 키는 거기서 실패한다.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REST = "https://api.runpod.io/v2"


def load_dotenv() -> None:
    """Read .env at the repo root. Avoids a python-dotenv dependency.

    저장소 루트의 .env 를 읽는다. python-dotenv 의존성을 피하기 위함.
    """
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        # Do not clobber a value already exported in the shell.
        # 셸에서 이미 export 한 값은 덮어쓰지 않는다.
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def get(path: str, api_key: str):
    """Return (status, body): parsed JSON on 2xx, the API's error detail otherwise."""
    req = urllib.request.Request(REST + path, headers={
        "Authorization": "Bearer " + api_key,
        # Cloudflare in front of the API rejects the default Python-urllib agent (error 1010).
        # API 앞단의 Cloudflare 가 기본 Python-urllib 에이전트를 거부한다 (error 1010).
        "User-Agent": "runpod-hols-setup/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read()).get("detail", "")
        except ValueError:
            return e.code, ""


def main() -> int:
    load_dotenv()

    api_key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not api_key:
        print("RUNPOD_API_KEY is not set. / RUNPOD_API_KEY 가 설정되지 않았습니다.")
        print("  1. Issue a key at https://console.runpod.io/user/credentials")
        print("  2. ./setup/init-env.sh")
        return 1

    # 1. Who am I? Also the cheapest way to prove the key is valid (scope account:read).
    #    나는 누구인가. 키 유효성을 확인하는 가장 가벼운 방법이기도 하다 (account:read).
    status, me = get("/account", api_key)
    if status == 401:
        print("Authentication failed. / 인증에 실패했습니다.")
        print("Check that the key is correct and not revoked.")
        print("키가 올바른지, 폐기되지 않았는지 확인하세요.")
        return 1
    print("Authenticated. / 인증 성공.")
    print(f"  account: {me.get('id')}" if status == 200 else f"  account: {status} {me}")

    # 2. GPU catalogue — confirms read access to the resource APIs (catalog:read).
    #    GPU 목록 — 리소스 API 읽기 권한을 확인한다 (catalog:read).
    status, body = get("/catalog/gpus", api_key)
    if status == 200:
        gpus = body.get("gpus", [])
        print(f"\nGPU types visible / 조회 가능한 GPU 타입: {len(gpus)}")
        for gpu in gpus[:5]:
            print(f"  - {gpu.get('id')}  ({gpu.get('name')})")
        if len(gpus) > 5:
            print(f"  … and {len(gpus) - 5} more / 외 {len(gpus) - 5}개")
    else:
        print(f"\nCould not list GPUs. / GPU 목록 조회 실패: {status} {body}")

    # 3. Existing resources — a reminder of anything already costing money (pods:read, serverless:read).
    #    기존 리소스 — 이미 비용이 나가고 있는 것이 있는지 확인.
    status, body = get("/pods", api_key)
    if status == 200:
        pods = body.get("pods", [])
        running = [p for p in pods if p.get("status") == "RUNNING"]
        print(f"\nPods / 파드: {len(pods)} total, {len(running)} running / 전체 {len(pods)}개, 실행 중 {len(running)}개")
        for pod in running:
            print(f"  ! RUNNING — {pod.get('name')} ({pod.get('id')}) — being billed / 과금 중")
        if running:
            print("  Stop or terminate what you are not using. / 사용하지 않는 것은 중지하거나 삭제하세요.")
    else:
        print(f"\nCould not list pods. / 파드 목록 조회 실패: {status} {body}")

    status, body = get("/serverless", api_key)
    if status == 200:
        eps = body.get("endpoints", [])
        active = [e for e in eps if (e.get("workers") or {}).get("min")]
        print(f"\nServerless endpoints / 엔드포인트: {len(eps)}, with active workers / 활성 워커 있음: {len(active)}")
        for ep in active:
            print(f"  ! workers.min {ep['workers']['min']} — {ep.get('name')} ({ep.get('id')}) — billed while idle / 유휴 중에도 과금")
    else:
        print(f"\nCould not list endpoints. / 엔드포인트 목록 조회 실패: {status} {body}")

    print("\nReady. / 준비 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
