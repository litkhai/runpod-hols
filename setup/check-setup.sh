#!/usr/bin/env bash
# Check that the tools the labs need are present and new enough.
# 실습에 필요한 도구가 설치돼 있고 버전이 충분한지 검사한다.
#
# Usage / 사용법:  ./check-setup.sh
# Exits non-zero if a required tool is missing.
# 필수 도구가 없으면 0 이 아닌 코드로 종료한다.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
missing_required=0

green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }
amber() { printf '\033[33m%s\033[0m' "$1"; }

# report <status> <name> <detail>
report() {
  case "$1" in
    ok)   printf '  [%s] %-12s %s\n' "$(green OK)"   "$2" "$3" ;;
    warn) printf '  [%s] %-12s %s\n' "$(amber '--')" "$2" "$3" ;;
    fail) printf '  [%s] %-12s %s\n' "$(red FAIL)"   "$2" "$3" ;;
  esac
}

echo "Runpod HOL — setup check / 사전 구성 검사"
echo

# --- Required / 필수 -------------------------------------------------------
echo "Required / 필수"

# Python must be 3.10+ because runpod SDK 1.11 declares requires-python >=3.10.
# runpod SDK 1.11 이 requires-python >=3.10 이므로 Python 3.10 이상이어야 한다.
if command -v python3 >/dev/null 2>&1; then
  py_ver="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    report ok "python3" "$py_ver"
  else
    report warn "python3" "$py_ver — too old for the SDK, but uv can supply 3.11 / SDK 에는 낮지만 uv 로 3.11 사용 가능"
  fi
else
  report fail "python3" "not found / 없음"
  missing_required=1
fi

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    report ok "docker" "$(docker --version | sed 's/Docker version //')"
  else
    report warn "docker" "installed but daemon not running / 설치됐으나 데몬 미실행"
  fi
else
  report fail "docker" "not found / 없음 — https://docs.docker.com/get-docker/"
  missing_required=1
fi

echo

# --- Recommended / 권장 ----------------------------------------------------
echo "Recommended / 권장"

if command -v uv >/dev/null 2>&1; then
  report ok "uv" "$(uv --version | awk '{print $2}')"
else
  report warn "uv" "not found / 없음 — brew install uv"
fi

# The Runpod provider will not install on Terraform 1.5.x — it fails with
# "openpgp: invalid data: armor invalid". Homebrew's `terraform` formula is
# frozen at 1.5.7, so the tap version is the one that works.
#
# Runpod 프로바이더는 Terraform 1.5.x 에 설치되지 않는다
# ("openpgp: invalid data: armor invalid" 오류). Homebrew 의 `terraform` 포뮬러는
# 1.5.7 에 멈춰 있으므로 tap 버전을 써야 한다.
if command -v terraform >/dev/null 2>&1; then
  tf_ver="$(terraform version | head -1 | sed 's/Terraform v//')"
  tf_major="${tf_ver%%.*}"
  tf_rest="${tf_ver#*.}"
  tf_minor="${tf_rest%%.*}"
  if [ "$tf_major" -gt 1 ] 2>/dev/null || { [ "$tf_major" -eq 1 ] && [ "$tf_minor" -ge 6 ]; } 2>/dev/null; then
    report ok "terraform" "$tf_ver  (terraform/ track)"
  else
    report warn "terraform" "$tf_ver — too old for the Runpod provider, need 1.6+ / Runpod 프로바이더에는 부족, 1.6 이상 필요"
    printf '                    brew install hashicorp/tap/terraform\n'
  fi
else
  report warn "terraform" "not found / 없음 — brew install hashicorp/tap/terraform  (terraform/ track only)"
fi

if command -v runpodctl >/dev/null 2>&1; then
  report ok "runpodctl" "$(runpodctl version 2>&1 | head -1)"
else
  report warn "runpodctl" "not found / 없음 — brew install runpod/runpodctl/runpodctl"
fi

if command -v node >/dev/null 2>&1; then
  report ok "node" "$(node --version)  (MCP server needs 18+)"
else
  report warn "node" "not found / 없음 — needed only for the MCP server / MCP 서버에만 필요"
fi

echo

# --- Credentials / 인증 ----------------------------------------------------
echo "Credentials / 인증"

if [ -f "$REPO_ROOT/.env" ]; then
  report ok ".env" "present / 존재"
  # shellcheck disable=SC1091
  set -a; . "$REPO_ROOT/.env"; set +a
else
  report warn ".env" "not found / 없음 — cp .env.example .env"
fi

if [ -n "${RUNPOD_API_KEY:-}" ]; then
  # Never print the key itself. / 키 자체는 절대 출력하지 않는다.
  report ok "API key" "set (${#RUNPOD_API_KEY} chars) / 설정됨"
  echo
  echo "Next / 다음: python setup/verify-auth.py   # verify the key actually works / 키가 실제로 동작하는지 확인"
else
  report warn "API key" "RUNPOD_API_KEY not set / 미설정 — https://console.runpod.io/user/settings"
fi

echo

# --- Architecture note / 아키텍처 안내 -------------------------------------
if [ "$(uname -m)" = "arm64" ] && [ "$(uname -s)" = "Darwin" ]; then
  echo "$(amber 'Note / 참고'): Apple Silicon detected."
  echo "  Runpod workers run on linux/amd64 — always build with --platform linux/amd64."
  echo "  Runpod 워커는 linux/amd64 에서 동작한다. 빌드 시 항상 --platform linux/amd64 를 붙일 것."
  echo
fi

if [ "$missing_required" -ne 0 ]; then
  echo "$(red 'Some required tools are missing. / 필수 도구가 누락됐습니다.')"
  exit 1
fi

echo "$(green 'Required tools are ready. / 필수 도구가 준비됐습니다.')"
