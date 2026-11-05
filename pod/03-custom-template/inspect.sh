#!/usr/bin/env bash
# Run inside the Pod. Prints what the template put in the environment without
# printing any secret: plain values in full, secrets as a hash or a length.
# Pod 안에서 실행. 비밀 값은 출력하지 않는다. 일반 값은 그대로, 시크릿은 해시나 길이로.
h() { printf '%s' "$1" | sha256sum | cut -c1-16; }
pid1() { tr '\0' '\n' < /proc/1/environ | sed -n "s/^$1=//p"; }
hashed() { if [ -n "$1" ]; then echo "sha256[:16] $(h "$1")"; else echo "<unset>"; fi; }
echo "GREETING        this shell: ${GREETING:-<unset>}"
echo "GREETING        PID 1:      $(pid1 GREETING)"
echo "DEMO_SECRET     this shell: $(hashed "${DEMO_SECRET:-}")"
echo "DEMO_SECRET     PID 1:      $(hashed "$(pid1 DEMO_SECRET)")"
echo "RUNPOD_* names, PID 1: $(tr '\0' '\n' < /proc/1/environ | grep -o '^RUNPOD_[A-Z0-9_]*' | sort | tr '\n' ' ')"
k=$(pid1 RUNPOD_API_KEY); if [ -n "$k" ]; then echo "RUNPOD_API_KEY  PID 1:      present, ${#k} chars"; else echo "RUNPOD_API_KEY  PID 1:      <unset>"; fi
for f in /etc/rp_environment /root/.bashrc; do [ -f "$f" ] && echo "$f: $(grep -c . "$f") lines, mentions GREETING: $(grep -c GREETING "$f")"; done
