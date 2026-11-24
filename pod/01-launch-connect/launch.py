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
# Smallest Compute-Optimized size: 2 vCPU, 2 GB per vCPU. runpod 2.x sends the
# flavor and vCPU count from this id; the memory part is checked, not sent.
# 가장 작은 Compute-Optimized 사양: vCPU 2개, vCPU 당 2GB. runpod 2.x 는 이 id 에서
# flavor 와 vCPU 수를 보내고, 메모리 부분은 형식만 검사한다.
DEFAULT_CPU = "cpu3c-2-4"


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
        "--cpu",
        default=DEFAULT_CPU,
        help="CPU instance id <flavor>-<vcpu>-<memory GB>, used when --gpu is omitted. "
             "The API rejects a CPU Pod without one. "
             "/ CPU 인스턴스 ID. --gpu 를 생략했을 때 쓰며, 없으면 API 가 거부한다.",
    )
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
            gpu = runpod.get_gpu(args.gpu, args.gpu_count)
        except Exception as exc:  # noqa: BLE001 — surface whatever the API said
            print(f"Unknown GPU type {args.gpu!r}: {exc}")
            print("List valid ids with: python -c \"import runpod, os; "
                  "runpod.api_key=os.environ['RUNPOD_API_KEY']; "
                  "print([g['id'] for g in runpod.get_gpus()])\"")
            return 1
        # runpod 2.x reads the catalog with pod stock (include=AVAILABILITY, product=POD).
        # runpod 2.x 는 Pod 재고를 포함해 카탈로그를 읽는다.
        print(f"Stock for {args.gpu} x{args.gpu_count}: {gpu.get('availability')}  "
              f"(secure ${(gpu.get('price') or {}).get('secure')}/hr per GPU)")
        if gpu.get("availability") == "NONE":
            print("No stock right now; the create would fail. / 지금 재고가 없어 생성이 실패합니다.")

    kind = f"{args.gpu} x{args.gpu_count}" if args.gpu else f"CPU only / CPU 전용 ({args.cpu})"
    print("About to create a Pod / 아래 Pod 를 생성합니다:")
    print(f"    name    {args.name}")
    print(f"    image   {args.image}")
    print(f"    compute {kind}")
    if args.gpu:
        print(f"    disks   container {args.disk_gb}GB, volume {args.volume_gb}GB at /workspace")
    else:
        # REST v2 refuses a Pod volume on a CPU Pod, and runpod 2.x refuses
        # volume_mount_path on one before sending anything.
        # REST v2 는 CPU Pod 의 Pod 볼륨을 거부하고, runpod 2.x 는 보내기 전에
        # volume_mount_path 를 거부한다.
        print(f"    disks   container {args.disk_gb}GB; no volume disk on a CPU Pod — "
              "/workspace is on the container disk")
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
        instance_id=None if args.gpu else args.cpu,
        container_disk_in_gb=args.disk_gb,
        # A Pod volume only on a GPU Pod (see above). The SDK mounts it at
        # /runpod-volume by default, the console at /workspace; pin /workspace.
        # Pod 볼륨은 GPU Pod 에만. SDK 기본 경로는 /runpod-volume, 콘솔은 /workspace
        # 이므로 /workspace 로 고정한다.
        volume_in_gb=args.volume_gb if args.gpu else 0,
        volume_mount_path="/workspace" if args.gpu else None,
        cloud_type="SECURE",
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
