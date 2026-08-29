#!/usr/bin/env python3
"""Launch a Pod for the lab, cheaply and with the cost stated up front.

실습용 Pod 를 기동한다. 저렴하게, 그리고 비용을 먼저 밝히고.

    python launch.py                          # CPU-only Pod, the cheapest way in
    python launch.py --gpu "NVIDIA RTX A4000" # attach a GPU
    python launch.py --dry-run                # show what it would do, create nothing

Defaults to CPU because this lab is about launching, connecting and tearing
down — none of which needs a GPU. Add one when you have something to run on it.
이 실습의 주제는 기동·접속·정리이고 그중 어느 것도 GPU 를 필요로 하지 않으므로
기본값을 CPU 로 두었다. GPU 는 실제로 돌릴 것이 생겼을 때 붙인다.
"""

import argparse
import sys

from common import POD_ID_FILE, client, confirm, describe, running_pods

DEFAULT_IMAGE = "runpod/pytorch:1.0.7-cu1281-torch291-ubuntu2404"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", default="hol-pod-01")
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument(
        "--gpu",
        default=None,
        help="GPU type id, e.g. 'NVIDIA RTX A4000'. Omitted means a CPU-only Pod. "
             "/ GPU 타입 ID. 생략하면 CPU 전용 Pod.",
    )
    ap.add_argument("--gpu-count", type=int, default=1)
    ap.add_argument(
        "--volume-gb", type=int, default=10,
        help="Volume disk size. Survives stop, dies on terminate. "
             "/ 볼륨 디스크 크기. 중지 시 유지, 삭제 시 소멸.",
    )
    ap.add_argument("--disk-gb", type=int, default=10, help="Container (scratch) disk.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    runpod = client()

    # Refuse to stack Pods by accident. The most expensive mistake in this lab
    # is not a wrong flag, it is forgetting one is already up.
    # 실수로 Pod 를 쌓지 않도록 막는다. 이 실습에서 가장 비싼 실수는 잘못된 플래그가
    # 아니라, 이미 하나가 떠 있다는 사실을 잊는 것이다.
    existing = running_pods(runpod)
    if existing:
        print("A Pod is already running. / 이미 실행 중인 Pod 가 있습니다.\n")
        for p in existing:
            print("  " + describe(p).replace("\n", "\n  "))
        print("\nTerminate it first: python teardown.py")
        print("먼저 정리하세요: python teardown.py")
        return 1

    # Validate the GPU id before asking for confirmation, so a typo fails here
    # rather than after you have agreed to spend money.
    # 확인을 받기 전에 GPU ID 를 검증한다. 오타라면 돈을 쓰겠다고 answer 한 뒤가
    # 아니라 이 지점에서 실패해야 한다.
    if args.gpu:
        try:
            runpod.get_gpu(args.gpu)
        except Exception as exc:  # noqa: BLE001 — surface whatever the API said
            print(f"Unknown GPU type {args.gpu!r}: {exc}")
            print("List valid ids with: python -c \"import runpod, os; "
                  "runpod.api_key=os.environ['RUNPOD_API_KEY']; "
                  "print([g['id'] for g in runpod.get_gpus()])\"")
            return 1

    kind = f"{args.gpu} x{args.gpu_count}" if args.gpu else "CPU only / CPU 전용"
    print("About to create a Pod / 아래 Pod 를 생성합니다:")
    print(f"    name    {args.name}")
    print(f"    image   {args.image}")
    print(f"    compute {kind}")
    print(f"    disks   container {args.disk_gb}GB, volume {args.volume_gb}GB at /workspace")
    print()
    print("Billing starts when it boots and continues until you terminate it,")
    print("whether or not you are using it.")
    print("기동 시점부터 삭제할 때까지, 사용 여부와 무관하게 과금됩니다.")
    print()

    if args.dry_run:
        print("--dry-run: nothing created. / 아무것도 생성하지 않았습니다.")
        return 0

    if not confirm("Create it?  / 생성할까요?"):
        print("Cancelled. / 취소했습니다.")
        return 1

    pod = runpod.create_pod(
        name=args.name,
        image_name=args.image,
        gpu_type_id=args.gpu,          # None -> CPU-only Pod
        gpu_count=args.gpu_count if args.gpu else 1,
        container_disk_in_gb=args.disk_gb,
        volume_in_gb=args.volume_gb,
        # The SDK defaults this to /runpod-volume, while the console defaults to
        # /workspace. Pin it so the path matches every doc and lab.
        # SDK 기본값은 /runpod-volume, 콘솔 기본값은 /workspace 다.
        # 모든 문서와 실습에서 경로가 일치하도록 고정한다.
        volume_mount_path="/workspace",
        start_ssh=True,
        ports="22/tcp,8888/http",
    )

    pod_id = pod.get("id")
    POD_ID_FILE.write_text(pod_id + "\n")
    print(f"\nCreated {pod_id}  (recorded in {POD_ID_FILE.name})")
    print(f"생성됨 {pod_id}  ({POD_ID_FILE.name} 에 기록)")
    print("\nNext / 다음:")
    print("    python status.py     # connection details and cost / 접속 정보와 비용")
    print("    python teardown.py   # when finished / 끝나면")
    return 0


if __name__ == "__main__":
    sys.exit(main())
