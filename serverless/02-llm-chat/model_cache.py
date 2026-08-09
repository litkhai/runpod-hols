"""Locate a model in Runpod's cached-model store.

Runpod 의 모델 캐시에서 모델 경로를 찾는다.

Deliberately dependency-free — no torch, no transformers. That keeps this
importable (and unit-testable) on a laptop without installing several GB of
CUDA wheels, and it lets handler.py resolve the cache *before* importing
transformers, which matters because the offline env vars are only read at
import time.

의도적으로 의존성이 없다. torch 도 transformers 도 쓰지 않는다.
수 GB 짜리 CUDA 휠을 설치하지 않고도 노트북에서 import 하고 테스트할 수 있고,
handler.py 가 transformers 를 import 하기 *전에* 캐시를 확인할 수 있다.
오프라인 환경변수는 import 시점에만 읽히므로 이 순서가 중요하다.
"""

import os

# Where Runpod places cached models. Overridable so the resolver can be
# pointed at a fixture directory in tests.
# Runpod 이 캐시된 모델을 두는 위치. 테스트에서 픽스처 디렉토리를 가리킬 수 있도록
# 환경변수로 덮어쓸 수 있게 했다.
DEFAULT_CACHE_ROOT = os.environ.get(
    "RUNPOD_HF_CACHE_ROOT", "/runpod-volume/huggingface-cache/hub"
)


def snapshot_path(model_id: str, cache_root: str = None):
    """Return the local snapshot directory for `model_id`, or None.

    `model_id` 에 해당하는 로컬 스냅샷 디렉토리를 반환한다. 없으면 None.

    Returning None rather than raising is the point: the caller can fall back
    to downloading from the Hub, which is what makes local testing possible.
    Runpod's own example raises here, so its handler cannot run off-platform.

    예외를 던지지 않고 None 을 반환하는 것이 핵심이다. 호출자가 Hub 다운로드로
    폴백할 수 있어 로컬 테스트가 가능해진다. Runpod 공식 예제는 여기서 예외를
    던지기 때문에 플랫폼 밖에서는 핸들러가 실행되지 않는다.

    Layout, per Hugging Face cache conventions:
    Hugging Face 캐시 규약에 따른 구조:
        <root>/models--<org>--<name>/refs/main        -> snapshot hash
        <root>/models--<org>--<name>/snapshots/<hash>/ -> the files
    """
    if not model_id or "/" not in model_id:
        raise ValueError(
            f"model_id must look like 'org/name', got {model_id!r} "
            f"/ model_id 는 'org/name' 형식이어야 한다"
        )

    root = cache_root or DEFAULT_CACHE_ROOT
    org, name = model_id.split("/", 1)
    model_root = os.path.join(root, f"models--{org}--{name}")
    snapshots_dir = os.path.join(model_root, "snapshots")

    # Preferred: follow refs/main to the exact revision.
    # 우선 경로: refs/main 이 가리키는 정확한 리비전을 따라간다.
    refs_main = os.path.join(model_root, "refs", "main")
    if os.path.isfile(refs_main):
        with open(refs_main, "r") as fh:
            revision = fh.read().strip()
        candidate = os.path.join(snapshots_dir, revision)
        if os.path.isdir(candidate):
            return candidate

    # Fallback: refs/main missing or dangling — take a snapshot that exists.
    # Sorted so the choice is at least deterministic across workers.
    #
    # 폴백: refs/main 이 없거나 깨졌을 때 실제로 존재하는 스냅샷을 쓴다.
    # 워커마다 같은 선택을 하도록 정렬한다.
    if os.path.isdir(snapshots_dir):
        found = sorted(
            d for d in os.listdir(snapshots_dir)
            if os.path.isdir(os.path.join(snapshots_dir, d))
        )
        if found:
            return os.path.join(snapshots_dir, found[0])

    return None
