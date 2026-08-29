#!/usr/bin/env python3
"""Show every Pod on the account, what it costs, and how to reach it.

계정의 모든 Pod, 각각의 비용, 그리고 접속 방법을 보여준다.

    python status.py

Read-only. Safe to run as often as you like.
읽기 전용이다. 얼마든지 반복 실행해도 된다.
"""

import sys

from common import client, describe, ssh_target


def main() -> int:
    runpod = client()
    pods = runpod.get_pods()

    if not pods:
        print("No Pods. Nothing is costing you anything.")
        print("Pod 가 없습니다. 과금되는 것이 없습니다.")
        return 0

    running = [p for p in pods if p.get("desiredStatus") == "RUNNING"]
    stopped = [p for p in pods if p.get("desiredStatus") != "RUNNING"]

    if running:
        print(f"RUNNING — billing now / 과금 중  ({len(running)})\n")
        for p in running:
            print("  " + describe(p).replace("\n", "\n  "))
            target = ssh_target(p)
            if target:
                ip, port = target
                print(f"    ssh      ssh root@{ip} -p {port} -i ~/.ssh/id_ed25519")
            else:
                # Ports take a moment to appear after boot; it is not an error.
                # 기동 직후에는 포트가 아직 안 뜬다. 오류가 아니다.
                print("    ssh      not ready yet — rerun in a moment "
                      "/ 아직 준비 안 됨. 잠시 후 다시 실행")
            print()

    if stopped:
        print(f"STOPPED — GPU released, volume storage still billed "
              f"/ GPU 반납, 볼륨 스토리지는 계속 과금  ({len(stopped)})\n")
        for p in stopped:
            print("  " + describe(p).replace("\n", "\n  ") + "\n")

    total = sum(float(p.get("costPerHr") or 0) for p in running)
    if total:
        print(f"Combined rate / 합계 요율: ${total:.4f}/hr  "
              f"= ${total * 24:.2f}/day if left running / 그대로 두면 하루")
        print("Terminate what you are not using: python teardown.py")
        print("사용하지 않는 것은 삭제하세요: python teardown.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
