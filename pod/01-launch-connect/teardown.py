#!/usr/bin/env python3
"""Terminate the Pod this lab created, or every Pod on the account.

이 실습이 만든 Pod 를 삭제한다. 또는 계정의 모든 Pod 를.

    python teardown.py            # the Pod recorded by launch.py
    python teardown.py --all      # every Pod, whoever created it
    python teardown.py --stop     # stop instead of terminate (keeps the volume)

Terminate removes the Pod and its volume disk. Stop releases the GPU but keeps
the volume — and keeps billing you for that storage.
Terminate 는 Pod 와 볼륨 디스크를 함께 제거한다. Stop 은 GPU 만 반납하고 볼륨을
유지하며, 그 스토리지 비용은 계속 나간다.
"""

import argparse
import sys

from common import POD_ID_FILE, client, confirm, describe


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                    help="Every Pod on the account. / 계정의 모든 Pod.")
    ap.add_argument("--stop", action="store_true",
                    help="Stop rather than terminate. Volume survives and keeps "
                         "billing. / 삭제 대신 중지. 볼륨은 남고 과금도 계속된다.")
    ap.add_argument("--yes", action="store_true",
                    help="Skip the prompt. For scripted cleanup. "
                         "/ 확인 생략. 스크립트 정리용.")
    args = ap.parse_args()

    runpod = client()
    pods = runpod.get_pods()

    if args.all:
        targets = pods
    else:
        if not POD_ID_FILE.exists():
            print(f"No {POD_ID_FILE.name} — launch.py has not recorded a Pod here.")
            print(f"{POD_ID_FILE.name} 이 없습니다. launch.py 가 기록한 Pod 가 없습니다.")
            print("Use --all to act on every Pod. / 모든 Pod 를 대상으로 하려면 --all.")
            return 1
        wanted = POD_ID_FILE.read_text().strip()
        targets = [p for p in pods if p.get("id") == wanted]
        if not targets:
            # Already gone. Clean up the stale record so the next run is quiet.
            # 이미 사라졌다. 다음 실행이 조용하도록 낡은 기록을 지운다.
            print(f"Pod {wanted} no longer exists. Clearing {POD_ID_FILE.name}.")
            print(f"Pod {wanted} 이 존재하지 않습니다. {POD_ID_FILE.name} 을 정리합니다.")
            POD_ID_FILE.unlink()
            return 0

    verb = "Stop" if args.stop else "Terminate"
    verb_ko = "중지" if args.stop else "삭제"
    print(f"{verb} the following / 다음을 {verb_ko}합니다:\n")
    for p in targets:
        print("  " + describe(p).replace("\n", "\n  ") + "\n")

    if args.stop:
        print("Volume storage keeps billing after a stop.")
        print("중지 후에도 볼륨 스토리지 비용은 계속 발생합니다.")
    else:
        print("This deletes the volume disk. Anything only in /workspace is lost.")
        print("볼륨 디스크가 삭제됩니다. /workspace 에만 있던 것은 사라집니다.")
    print()

    if not args.yes and not confirm(f"{verb}?  / {verb_ko}할까요?"):
        print("Cancelled. / 취소했습니다.")
        return 1

    for p in targets:
        pid = p.get("id")
        try:
            if args.stop:
                runpod.stop_pod(pid)
                print(f"  stopped  {pid}")
            else:
                runpod.terminate_pod(pid)
                print(f"  terminated  {pid}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED  {pid}: {exc}")

    # The record only means anything while the Pod exists.
    # 이 기록은 Pod 가 존재하는 동안에만 의미가 있다.
    if not args.stop and POD_ID_FILE.exists():
        POD_ID_FILE.unlink()

    print("\nConfirm with: python status.py")
    print("확인: python status.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
