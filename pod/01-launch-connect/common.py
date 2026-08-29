"""Shared helpers for the Pod lab scripts.

Pod 실습 스크립트가 공유하는 헬퍼.

Kept dependency-light on purpose: only `runpod` and the standard library, so
these run in the same virtualenv as the Serverless labs.
의도적으로 의존성을 최소화했다. `runpod` 과 표준 라이브러리만 사용하므로
Serverless 실습과 같은 가상환경에서 실행된다.
"""

import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LAB_DIR = pathlib.Path(__file__).resolve().parent

# Where launch.py records the Pod it created, so teardown.py needs no argument.
# Gitignored — it is machine-local state, not source.
#
# launch.py 가 생성한 Pod 를 기록하는 위치. teardown.py 가 인자 없이 동작하도록.
# gitignore 대상이다. 소스가 아니라 이 머신에만 해당하는 상태다.
POD_ID_FILE = LAB_DIR / ".pod-id"


def load_env() -> None:
    """Read the repo .env without adding a python-dotenv dependency.

    python-dotenv 의존성 없이 저장소 .env 를 읽는다.
    """
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def client():
    """Return the runpod module with credentials applied, or exit with advice.

    자격 증명이 적용된 runpod 모듈을 반환한다. 없으면 안내와 함께 종료한다.
    """
    load_env()
    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not key:
        sys.exit(
            "RUNPOD_API_KEY is not set. Run ./setup/init-env.sh\n"
            "RUNPOD_API_KEY 가 설정되지 않았습니다. ./setup/init-env.sh 를 실행하세요."
        )
    try:
        import runpod
    except ImportError:
        sys.exit(
            "The runpod SDK is not installed.\n"
            "runpod SDK 가 설치되지 않았습니다.\n"
            "  uv venv --python 3.11 .venv && "
            "uv pip install --python .venv/bin/python runpod"
        )
    runpod.api_key = key
    return runpod


def confirm(question: str) -> bool:
    """Require a typed yes. Refuses to assume consent without a terminal.

    'yes' 를 직접 입력해야 통과한다. 터미널이 없으면 동의를 가정하지 않는다.

    A y/N prompt is too easy to fly through when the thing on the other side
    costs money by the minute.
    분 단위로 돈이 나가는 작업 앞에서 y/N 프롬프트는 너무 쉽게 지나쳐진다.
    """
    if not sys.stdin.isatty():
        print("Not a terminal — refusing to proceed unattended.")
        print("터미널이 아니므로 무인 실행을 거부합니다.")
        return False
    print(question)
    return input("  type 'yes' to continue / 계속하려면 'yes' 입력: ").strip() == "yes"


def running_pods(runpod) -> list:
    """Pods currently costing money. / 지금 비용이 발생 중인 Pod."""
    return [p for p in runpod.get_pods() if p.get("desiredStatus") == "RUNNING"]


def describe(pod: dict) -> str:
    """One line per Pod, with the numbers that matter.

    Pod 하나를 한 줄로. 중요한 수치만.
    """
    cost = pod.get("costPerHr") or 0
    up = pod.get("uptimeSeconds") or 0
    gpu = (pod.get("machine") or {}).get("gpuDisplayName") or "CPU only"
    spent = float(cost) * (up / 3600)
    return (
        f"{pod.get('name')}  ({pod.get('id')})\n"
        f"    status   {pod.get('desiredStatus')}   {gpu} x{pod.get('gpuCount') or 0}\n"
        f"    cost     ${cost}/hr   up {up // 60}m {up % 60}s   "
        f"≈ ${spent:.4f} so far / 현재까지\n"
        f"    volume   {pod.get('volumeInGb')}GB at {pod.get('volumeMountPath')}"
    )


def ssh_target(pod: dict):
    """Extract a public SSH endpoint from the Pod's runtime ports, if any.

    Pod 의 런타임 포트에서 공개 SSH 접속 지점을 찾는다. 없으면 None.
    """
    runtime = pod.get("runtime") or {}
    for port in runtime.get("ports") or []:
        if port.get("privatePort") == 22 and port.get("isIpPublic"):
            return port.get("ip"), port.get("publicPort")
    return None
