"""Shared helpers for the template lab: .env loading, REST calls, local state.

템플릿 실습 공용 헬퍼: .env 로딩, REST 호출, 로컬 상태.

Standard library only. Field names come from the published OpenAPI spec,
rest.runpod.io/v1/openapi.json (read 2026-11-05) — the REST API rather than
the Python SDK, whose Pod calls changed shape in 2.0 (#37).
표준 라이브러리만 사용한다. 필드 이름은 발행된 OpenAPI 스펙 기준이다. Python
SDK 는 2.0 에서 Pod 호출 형태가 바뀌었으므로 (#37) REST API 를 직접 쓴다.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LAB_DIR = pathlib.Path(__file__).resolve().parent
# Ids this lab created, so later steps and cleanup need no arguments. Gitignored.
# 이 실습이 만든 id. 이후 단계와 정리가 인자 없이 동작하도록. gitignore 대상.
STATE_FILE = LAB_DIR / ".template.json"
REST = "https://rest.runpod.io/v1"
# Secrets live only in REST API v2 (docs.runpod.io/api-reference-v2, read 2026-11-05).
# 시크릿은 REST API v2 에만 있다.
REST_V2 = "https://api.runpod.io/v2"


def api_key() -> str:
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not key:
        sys.exit("RUNPOD_API_KEY is not set. Run ./setup/init-env.sh")
    return key


def rest(method: str, path: str, body: dict | None = None, base: str = REST):
    req = urllib.request.Request(
        base + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": "Bearer " + api_key(),
            "Content-Type": "application/json",
            # Cloudflare in front of the API rejects the default Python-urllib agent (error 1010).
            "User-Agent": "runpod-hols-pod-template/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode()
            return json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:500]}")


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
