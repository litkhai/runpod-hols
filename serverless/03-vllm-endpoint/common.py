"""Shared helpers for the vLLM endpoint lab: .env loading, the REST API, local state.

vLLM 엔드포인트 실습 공용 헬퍼: .env 로딩, REST API, 로컬 상태.

Standard library only for the control plane; `openai` is needed by chat.py alone.
제어 쪽은 표준 라이브러리만 쓴다. `openai` 는 chat.py 에서만 필요하다.
"""

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LAB_DIR = pathlib.Path(__file__).resolve().parent

# What deploy.py created, so chat.py and teardown.py need no arguments. Gitignored.
# deploy.py 가 만든 것. chat.py 와 teardown.py 가 인자 없이 동작하도록. gitignore 대상.
STATE_FILE = LAB_DIR / ".endpoint.json"

# Field names from the published OpenAPI spec, rest.runpod.io/v1/openapi.json (read 2026-11-05).
# 필드 이름은 발행된 OpenAPI 스펙 기준 (2026-11-05 확인).
REST = "https://rest.runpod.io/v1"


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
        sys.exit("RUNPOD_API_KEY is not set. Run ./setup/init-env.sh\n"
                 "RUNPOD_API_KEY 가 설정되지 않았습니다. ./setup/init-env.sh 를 실행하세요.")
    return key


class RestError(RuntimeError):
    def __init__(self, status: int, text: str):
        super().__init__(f"{status} {text}")
        self.status, self.text = status, text


def rest(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(
        REST + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": "Bearer " + api_key(),
            "Content-Type": "application/json",
            # Cloudflare in front of the API rejects the default Python-urllib agent (error 1010).
            # API 앞단의 Cloudflare 가 기본 Python-urllib 에이전트를 거부한다 (error 1010).
            "User-Agent": "runpod-hols-vllm-endpoint/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode()
            return json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as e:
        raise RestError(e.code, f"{method} {path} -> {e.read().decode()[:500]}") from None


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
