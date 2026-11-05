#!/usr/bin/env bash
# Run inside the Pod. `write <tag>` drops a marker in each storage tier;
# `check` lists which markers survived, and where each path is mounted.
# Pod 안에서 실행. `write <tag>` 는 각 스토리지 계층에 표식을 남기고,
# `check` 는 어떤 표식이 남았는지와 각 경로의 마운트를 보여준다.
set -u
DIRS="/root /workspace"
case "${1:-check}" in
  write)
    for d in $DIRS; do echo "$2 $(date -u +%FT%TZ)" >> "$d/hol-marker.txt"; done
    sync; echo "wrote '$2' to: $DIRS" ;;
  check)
    for d in $DIRS; do
      printf '%-11s %-28s ' "$d" "$(df --output=source,fstype "$d" | tail -1 | tr -s ' ')"
      if [ -f "$d/hol-marker.txt" ]; then tr '\n' ';' < "$d/hol-marker.txt"; echo; else echo "(no marker)"; fi
    done ;;
esac
