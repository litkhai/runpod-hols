#!/usr/bin/env bash
# Interactively create the repo .env. Secrets are read with echo disabled, so
# the key never appears on screen or in your shell history.
# 대화형으로 저장소 .env 를 만든다. 비밀값은 화면 출력을 끈 채 입력받으므로
# 키가 화면에도 셸 히스토리에도 남지 않는다.
#
# Usage / 사용법:  ./setup/init-env.sh
#
# Safe to re-run — existing values are offered as defaults and the previous
# file is backed up before being replaced.
# 여러 번 실행해도 안전하다. 기존 값을 기본값으로 제시하고,
# 파일을 교체하기 전에 이전 파일을 백업한다.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"

green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }
amber() { printf '\033[33m%s\033[0m' "$1"; }
dim()   { printf '\033[2m%s\033[0m' "$1"; }

# Refuse to run without a terminal — otherwise the prompts silently read EOF
# and we would write an empty .env.
# 터미널이 없으면 실행하지 않는다. 프롬프트가 조용히 EOF 를 읽어
# 빈 .env 를 써버리기 때문이다.
if [ ! -t 0 ]; then
  echo "$(red 'This script needs an interactive terminal. / 대화형 터미널이 필요합니다.')" >&2
  exit 1
fi

# current_value <KEY> — read a value out of the existing .env, if any.
# 기존 .env 에서 값을 읽어온다.
current_value() {
  [ -f "$ENV_FILE" ] || return 0
  sed -n "s/^$1=//p" "$ENV_FILE" | head -1 | sed 's/^["'\'']//; s/["'\'']$//'
}

# trim <value> — drop leading/trailing whitespace. Pasting a key often drags
# along a stray space or newline, which is not worth failing over.
# 앞뒤 공백을 제거한다. 키를 붙여넣을 때 공백이나 개행이 딸려오는 일이 흔한데,
# 그것 때문에 실패시킬 이유는 없다.
trim() {
  local v="$1"
  v="${v#"${v%%[![:space:]]*}"}"
  v="${v%"${v##*[![:space:]]}"}"
  printf '%s' "$v"
}

# mask <value> — show enough to recognise the value, not enough to leak it.
# 값을 식별할 수 있을 정도만 보여주고 전체는 노출하지 않는다.
mask() {
  local v="$1" n=${#1}
  if [ "$n" -le 8 ]; then printf '••••'; else printf '••••••••%s' "${v: -4}"; fi
}

# These are called as "$(ask_... )", so stdout IS the return value. Every
# prompt must go to stderr, or the prompt text ends up inside the answer.
# 이 함수들은 "$(ask_... )" 로 호출되므로 stdout 이 곧 반환값이다.
# 프롬프트는 반드시 stderr 로 내보내야 한다. 안 그러면 프롬프트 문구가 값에 섞인다.

# ask_secret <KEY> <label> — hidden input, keeps the existing value on Enter.
# 숨김 입력. 그냥 Enter 를 치면 기존 값을 유지한다.
ask_secret() {
  local key="$1" label="$2" existing input
  existing="$(current_value "$key")"

  printf '%s\n' "$label" >&2
  if [ -n "$existing" ]; then
    printf '  %s\n' "$(dim "current / 현재: $(mask "$existing")  — Enter to keep / 유지하려면 Enter")" >&2
  fi

  # -s hides the input, -r keeps backslashes literal, and -p prints the prompt
  # only after echo is already off. Printing the prompt separately would leave
  # a window in which a fast paste lands while the terminal still echoes.
  #
  # -s 는 입력을 숨기고, -r 은 백슬래시를 그대로 두며, -p 는 에코를 끈 뒤에
  # 프롬프트를 출력한다. 프롬프트를 따로 출력하면 에코가 꺼지기 전에
  # 빠른 붙여넣기가 들어와 값이 노출될 틈이 생긴다.
  read -rsp "  > " input
  echo >&2

  if [ -z "$input" ]; then printf '%s' "$existing"; else printf '%s' "$input"; fi
}

# ask_plain <KEY> <label> — visible input, keeps the existing value on Enter.
# 일반 입력. 그냥 Enter 를 치면 기존 값을 유지한다.
ask_plain() {
  local key="$1" label="$2" existing input
  existing="$(current_value "$key")"

  if [ -n "$existing" ]; then
    printf '%s\n  %s ' "$label" "$(dim "current / 현재: $existing  — Enter to keep / 유지하려면 Enter:")" >&2
  else
    printf '%s\n  ' "$label" >&2
  fi

  read -r input
  if [ -z "$input" ]; then printf '%s' "$existing"; else printf '%s' "$input"; fi
}

echo
echo "Runpod HOL — create .env / .env 생성"
echo
echo "  Values are written to $(dim "$ENV_FILE") with 0600 permissions."
echo "  값은 $(dim "$ENV_FILE") 에 0600 권한으로 저장됩니다."
echo "  This file is gitignored. / 이 파일은 gitignore 돼 있습니다."
echo

# --- 1. API key ------------------------------------------------------------

cat <<'TXT'
1) RUNPOD_API_KEY

   Create one at https://console.runpod.io/user/settings → API Keys.
   https://console.runpod.io/user/settings 의 API Keys 에서 생성합니다.

   Runpod shows the key only once and does not store it — copy it into a
   password manager before pasting it here.
   Runpod 은 키를 한 번만 보여주고 저장하지 않습니다.
   여기 붙여넣기 전에 비밀번호 관리자에 먼저 저장하세요.

   Permission levels / 권한 등급:
     Read Only   verify-auth.py and browsing / 조회 실습에 충분
     All         creating Pods, endpoints, volumes / 리소스 생성에 필요
   You can edit a key's permissions later without reissuing it.
   권한은 나중에 재발급 없이 수정할 수 있습니다.

TXT

API_KEY="$(trim "$(ask_secret RUNPOD_API_KEY "   Paste your API key (hidden) / API 키 붙여넣기 (화면에 표시되지 않음):")")"

if [ -z "$API_KEY" ]; then
  echo "  $(amber 'No key entered. / 키를 입력하지 않았습니다.') You can add it to .env later. / 나중에 .env 에 직접 넣어도 됩니다."
elif printf '%s' "$API_KEY" | grep -q '[[:space:]]'; then
  # Whitespace survived trimming, so it is inside the value — that is a bad
  # paste, not a stray newline.
  # 다듬은 뒤에도 공백이 남았다면 값 내부에 있다는 뜻이다. 잘못 붙여넣은 것이다.
  echo "  $(red 'The key contains whitespace inside it — check the paste. / 키 내부에 공백이 있습니다. 붙여넣기를 확인하세요.')"
  exit 1
else
  echo "  $(green 'Recorded') $(dim "($(mask "$API_KEY"))")"
fi
echo

# --- 2. Endpoint ID --------------------------------------------------------

cat <<'TXT'
2) RUNPOD_ENDPOINT_ID   (optional / 선택)

   Fill this in after you deploy a Serverless endpoint. Leave blank for now.
   Serverless 엔드포인트를 배포한 뒤에 채우면 됩니다. 지금은 비워둬도 됩니다.

TXT

ENDPOINT_ID="$(ask_plain RUNPOD_ENDPOINT_ID "   Endpoint ID / 엔드포인트 ID:")"
echo

# --- 3. Docker username ----------------------------------------------------

cat <<'TXT'
3) DOCKER_USERNAME   (optional / 선택)

   Only needed if you build and push worker images by hand.
   Not needed when deploying through the GitHub integration.
   워커 이미지를 직접 빌드해 푸시할 때만 필요합니다.
   GitHub 연동으로 배포하면 필요 없습니다.

TXT

DOCKER_USER="$(ask_plain DOCKER_USERNAME "   Docker Hub username / Docker Hub 사용자명:")"
echo

# --- Write -----------------------------------------------------------------

if [ -f "$ENV_FILE" ]; then
  backup="$ENV_FILE.bak"
  cp "$ENV_FILE" "$backup" && chmod 600 "$backup"
  echo "  Existing .env backed up to $(dim ".env.bak") / 기존 .env 를 백업했습니다."
fi

# Write via a private temp file, then move into place, so a partially written
# .env is never readable at the final path.
# 임시 파일에 먼저 쓰고 옮긴다. 일부만 쓰인 .env 가 최종 경로에 노출되지 않도록.
tmp="$(mktemp "${TMPDIR:-/tmp}/runpod-env.XXXXXX")" || exit 1
chmod 600 "$tmp"

{
  echo "# Generated by setup/init-env.sh — do not commit."
  echo "# setup/init-env.sh 가 생성한 파일입니다. 커밋하지 마세요."
  echo
  echo "RUNPOD_API_KEY=$API_KEY"
  echo "RUNPOD_ENDPOINT_ID=$ENDPOINT_ID"
  echo "DOCKER_USERNAME=$DOCKER_USER"
} > "$tmp"

mv "$tmp" "$ENV_FILE" && chmod 600 "$ENV_FILE"

echo "  $(green 'Wrote') $ENV_FILE $(dim "(mode $(stat -f '%Lp' "$ENV_FILE" 2>/dev/null || stat -c '%a' "$ENV_FILE" 2>/dev/null))")"
echo

# --- Offer to verify -------------------------------------------------------

if [ -n "$API_KEY" ]; then
  printf 'Verify the key against the Runpod API now? / 지금 키를 검증할까요? [Y/n] '
  read -r reply
  case "$reply" in
    [Nn]*) ;;
    *)
      echo
      # Prefer a project virtualenv, fall back to whatever python is around.
      # 프로젝트 가상환경을 우선 사용하고, 없으면 시스템 python 을 쓴다.
      for py in "$REPO_ROOT/.venv/bin/python" \
                "$REPO_ROOT/serverless/01-hello-worker/.venv/bin/python" \
                python3; do
        if command -v "$py" >/dev/null 2>&1 || [ -x "$py" ]; then
          if "$py" -c "import runpod" 2>/dev/null; then
            "$py" "$REPO_ROOT/setup/verify-auth.py"
            exit $?
          fi
        fi
      done
      echo "$(amber 'The runpod SDK is not installed, so the key was not verified.')"
      echo "$(amber 'runpod SDK 가 설치돼 있지 않아 검증을 건너뛰었습니다.')"
      echo "  uv venv --python 3.11 .venv"
      echo "  uv pip install --python .venv/bin/python runpod"
      echo "  .venv/bin/python setup/verify-auth.py"
      ;;
  esac
fi

echo
echo "Next / 다음: ./setup/check-setup.sh"
