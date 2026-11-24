"""Shared helpers for the Pod lab scripts.

Pod 실습 스크립트가 공유하는 헬퍼.

Kept dependency-light on purpose: only `runpod` and the standard library, so
these run in the same virtualenv as the Serverless labs.
의도적으로 의존성을 최소화했다. `runpod` 과 표준 라이브러리만 사용하므로
Serverless 실습과 같은 가상환경에서 실행된다.
"""

import datetime as dt
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
            "uv pip install --python .venv/bin/python -r requirements.txt"
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


# runpod 2.x returns REST v2 Pods: `status` (PROVISIONING, STARTING, RUNNING, EXITED,
# ERROR), `cost`, `gpu`/`cpu`, `mounts`, `ssh`, `startedAt` — not 1.x's desiredStatus,
# costPerHr, volumeInGb or uptimeSeconds (read in runpod 2.4.0, api/ctl_commands.py).
# runpod 2.x 는 REST v2 Pod 객체를 돌려준다. 1.x 의 desiredStatus·costPerHr·volumeInGb·
# uptimeSeconds 가 아니라 status·cost·gpu/cpu·mounts·ssh·startedAt 이다.
BILLING = ("PROVISIONING", "STARTING", "RUNNING")


def running_pods(runpod) -> list:
    """Pods currently costing compute. / 지금 컴퓨트 비용이 발생 중인 Pod."""
    return [p for p in runpod.get_pods() if p.get("status") in BILLING]


def uptime_s(pod: dict) -> int:
    """Seconds since start, from startedAt.

    Not runtime.uptime: GET /v2/pods leaves runtime null in lists, and on 2026-11-24 a
    single-Pod GET kept reporting runtime.uptime 4 for minutes (#126).
    runtime.uptime 을 쓰지 않는다. 목록에서는 null 이고, 2026-11-24 단건 조회에서는 몇 분
    동안 4 에 머물렀다.
    """
    started = pod.get("startedAt")
    if not started or pod.get("status") != "RUNNING":
        return int((pod.get("runtime") or {}).get("uptime") or 0)
    t = dt.datetime.fromisoformat(started.replace("Z", "+00:00"))
    return max(0, int((dt.datetime.now(dt.timezone.utc) - t).total_seconds()))


def describe(pod: dict) -> str:
    """One line per Pod, with the numbers that matter.

    Pod 하나를 한 줄로. 중요한 수치만.
    """
    cost = pod.get("cost") or 0
    up = uptime_s(pod)
    g, c = pod.get("gpu") or {}, pod.get("cpu") or {}
    kind = f"{g.get('id')} x{g.get('count')}" if g else f"CPU {c.get('id')} {c.get('vcpuCount')} vCPU"
    if up:
        spent = float(cost) * (up / 3600)
        uptime = f"up {up // 60}m {up % 60}s   ≈ ${spent:.4f} so far / 현재까지"
    else:
        uptime = "not running / 실행 중 아님"
    m = pod.get("mounts") or {}
    vol = m.get("persistent") or (m.get("network") or [None])[0]
    volume = (f"{vol.get('size', 'network')}{'GB' if vol.get('size') else ' volume ' + vol.get('volumeId', '')}"
              f" at {vol.get('path')}") if vol else "none — /workspace is on the container disk / 없음"
    return (
        f"{pod.get('name')}  ({pod.get('id')})\n"
        f"    status   {pod.get('status')}   {kind}   {pod.get('dataCenterId') or ''}\n"
        f"    cost     ${cost}/hr   {uptime}\n"
        f"    volume   {volume}"
    )


def ssh_target(pod: dict):
    """The public SSH endpoint (ssh.direct), once 22/tcp is published and the Pod runs.

    공개 SSH 접속 지점 (ssh.direct). 22/tcp 가 열리고 Pod 가 실행 중일 때만 있다.
    """
    d = (pod.get("ssh") or {}).get("direct")
    return (d["host"], d["port"]) if d else None
