#!/usr/bin/env python3
"""Verify the Runpod API key actually works, and show what it can see.

Runpod API 키가 실제로 동작하는지 확인하고, 무엇을 조회할 수 있는지 보여준다.

This makes three read-only calls — nothing is created, so nothing is billed.
읽기 전용 호출 세 건만 수행한다. 생성하는 리소스가 없으므로 과금되지 않는다.

Usage / 사용법:
    python setup/verify-auth.py

Requires the runpod SDK. If you have not installed it yet:
runpod SDK 가 필요하다. 아직 설치하지 않았다면:
    uv venv --python 3.11 .venv
    uv pip install --python .venv/bin/python runpod
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


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


def main() -> int:
    load_dotenv()

    api_key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not api_key:
        print("RUNPOD_API_KEY is not set. / RUNPOD_API_KEY 가 설정되지 않았습니다.")
        print("  1. Issue a key at https://console.runpod.io/user/settings")
        print("  2. cp .env.example .env  and fill it in / 를 실행하고 값을 채우세요")
        return 1

    try:
        import runpod
    except ImportError:
        print("The runpod SDK is not installed. / runpod SDK 가 설치되지 않았습니다.")
        print("  uv venv --python 3.11 .venv")
        print("  uv pip install --python .venv/bin/python runpod")
        return 1

    runpod.api_key = api_key

    # 1. Who am I? Also the cheapest way to prove the key is valid.
    #    나는 누구인가. 키 유효성을 확인하는 가장 가벼운 방법이기도 하다.
    try:
        user = runpod.get_user()
    except Exception as exc:  # noqa: BLE001 - surface whatever the API said
        print(f"Authentication failed. / 인증에 실패했습니다.\n  {exc}")
        print("\nCheck that the key is correct and not revoked.")
        print("키가 올바른지, 폐기되지 않았는지 확인하세요.")
        return 1

    print("Authenticated. / 인증 성공.")
    # The user payload shape varies by API version, so print defensively.
    # 사용자 응답 형태는 API 버전에 따라 달라지므로 방어적으로 출력한다.
    for field in ("id", "email", "currentSpendPerHr"):
        if isinstance(user, dict) and field in user:
            print(f"  {field}: {user[field]}")

    # 2. GPU catalogue — confirms read access to the resource APIs.
    #    GPU 목록 — 리소스 API 읽기 권한을 확인한다.
    try:
        gpus = runpod.get_gpus()
        print(f"\nGPU types visible / 조회 가능한 GPU 타입: {len(gpus)}")
        for gpu in gpus[:5]:
            print(f"  - {gpu.get('id')}  ({gpu.get('displayName')})")
        if len(gpus) > 5:
            print(f"  … and {len(gpus) - 5} more / 외 {len(gpus) - 5}개")
    except Exception as exc:  # noqa: BLE001
        print(f"\nCould not list GPUs. / GPU 목록 조회 실패: {exc}")

    # 3. Existing resources — a reminder of anything already costing money.
    #    기존 리소스 — 이미 비용이 나가고 있는 것이 있는지 확인.
    try:
        pods = runpod.get_pods()
        running = [p for p in pods if p.get("desiredStatus") == "RUNNING"]
        print(f"\nPods / 파드: {len(pods)} total, {len(running)} running / 전체 {len(pods)}개, 실행 중 {len(running)}개")
        for pod in running:
            print(f"  ! RUNNING — {pod.get('name')} ({pod.get('id')}) — being billed / 과금 중")
        if running:
            print("  Stop or terminate what you are not using. / 사용하지 않는 것은 중지하거나 삭제하세요.")
    except Exception as exc:  # noqa: BLE001
        print(f"\nCould not list pods. / 파드 목록 조회 실패: {exc}")

    print("\nReady. / 준비 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
