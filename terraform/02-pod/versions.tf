terraform {
  # 1.5.x cannot install this provider (openpgp armor error). Verified on 1.15.8.
  # Homebrew's `terraform` is frozen at 1.5.7 — use brew install hashicorp/tap/terraform
  #
  # 1.5.x 에서는 이 프로바이더 설치가 실패한다(openpgp armor 오류). 1.15.8 에서 확인.
  # Homebrew 의 `terraform` 은 1.5.7 에 멈춰 있으므로 brew install hashicorp/tap/terraform 사용.
  required_version = ">= 1.6.0"

  required_providers {
    runpod = {
      source = "runpod/runpod"

      # Exact pin — v1.0.9 ships a broken schema and fails every command.
      # See terraform/README.md for the details.
      #
      # 정확한 버전 고정 — v1.0.9 는 스키마가 깨져 모든 명령이 실패한다.
      # 자세한 내용은 terraform/README.md 참조.
      version = "= 1.0.8"
    }
  }
}
