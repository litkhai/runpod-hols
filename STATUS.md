# STATUS.md

Updated 2026-10-11.

## Tracks

| Track | Run against a real account? |
|---|---|
| [`setup/`](./setup) | Yes |
| [`serverless/01-hello-worker`](./serverless/01-hello-worker) | **Yes** — deployed, called, measured; re-run on SDK 1.12.0 |
| [`serverless/02-llm-chat`](./serverless/02-llm-chat) | **Yes** — built by the console, deployed, called and measured 2026-10-11 on RTX A5000 and RTX PRO 6000 Blackwell MIG 1g.24gb with the CUDA 12.8 image; cache path settled (docs layout) |
| [`pod/01-launch-connect`](./pod/01-launch-connect) | No — `--dry-run` only, no Pod ever launched ([#13](https://github.com/litkhai/runpod-hols/issues/13)) |
| [`terraform/01-endpoint`](./terraform/01-endpoint) | Partly — `apply` and `destroy` run 2026-10-11 with two provider workarounds; serving a request not run ([#11](https://github.com/litkhai/runpod-hols/issues/11)) |
| [`terraform/02-pod`](./terraform/02-pod) | No — `plan` only ([#12](https://github.com/litkhai/runpod-hols/issues/12)) |
| [`cluster/`](./cluster) | No — README only, deferred on cost ([#19](https://github.com/litkhai/runpod-hols/issues/19)) |
| [`inference-characterization/`](./inference-characterization) | **Yes** — Pod sweeps on Secure Cloud GPU types, Serverless cold-start probes with worker logs, 2026-10-06/07; Community Cloud Pod never reachable over SSH; per-run seed not re-run ([#6](https://github.com/litkhai/runpod-hols/issues/6)); review follow-up tests T2/T3/T5/T7/T11 done 2026-10-07, T1/T4/T6/T8–T10 open ([#8](https://github.com/litkhai/runpod-hols/issues/8)) |
| [`sdk/`](./sdk) | Source read at 1.11.0 and 1.12.0; client exercised live |
| [`gpu-topology/`](./gpu-topology) | Catalogue and OpenAPI queried live; hardware claims unrun ([#14](https://github.com/litkhai/runpod-hols/issues/14)) |
| [`docs/`](./docs) | <https://runpod.litkhai.dev> |

## CI

`checks` on pull requests: `docs` (`scripts/check-docs.py`), `syntax`, `secrets`
(gitleaks with `.gitleaks.toml`, full history), `hygiene`. The same checks run
on staged files in `.githooks/pre-commit` — enable it once per clone with
`git config core.hooksPath .githooks`. `pages.yml` deploys `docs/` on push to `main`.

## Account

| Endpoint | ID | Part of a lab? |
|---|---|---|
| `01-hello-world` | `ku3jultxavac2v` | Lab 01 |
| `vLLM v2.22.5` | `56snfp0y0lh5qc` | No — earlier exploration with Runpod's prebuilt vLLM worker |
| `02-llm-chat` | `3xiuyqtrh6r0zl` | Lab 02 — built from `main` by the console, minimum CUDA 12.8 |

All three scale to zero; `currentSpendPerHr` was `0` on 2026-10-11. `vLLM v2.22.5`
has `workersMax` 0 on that date, so it serves nothing until raised.

> `Endpoint.health()` reports worker slots even when nothing is billing. It is
> not a spend signal — query `myself { currentSpendPerHr }` for that.

## Open work

Tracked as issues — [all open](https://github.com/litkhai/runpod-hols/issues) ·
[needs a re-run](https://github.com/litkhai/runpod-hols/issues?q=is%3Aopen+label%3Are-verify) ·
[new labs](https://github.com/litkhai/runpod-hols/issues?q=is%3Aopen+label%3Aenhancement).

- Re-verify: [#11](https://github.com/litkhai/runpod-hols/issues/11) [#12](https://github.com/litkhai/runpod-hols/issues/12) Terraform
  `apply` · [#13](https://github.com/litkhai/runpod-hols/issues/13) Pod launch · [#14](https://github.com/litkhai/runpod-hols/issues/14) GPU topology on hardware ·
  [#6](https://github.com/litkhai/runpod-hols/issues/6) [#8](https://github.com/litkhai/runpod-hols/issues/8) inference-characterization follow-ups.
- New labs: [#15](https://github.com/litkhai/runpod-hols/issues/15) `serverless/03-vllm-endpoint` · [#16](https://github.com/litkhai/runpod-hols/issues/16) `pod/02-storage` ·
  [#17](https://github.com/litkhai/runpod-hols/issues/17) `pod/03-custom-template` · [#18](https://github.com/litkhai/runpod-hols/issues/18) `pod/04-pod-to-serverless` ·
  [#19](https://github.com/litkhai/runpod-hols/issues/19) the cluster track.
- Lab fixes: [#22](https://github.com/litkhai/runpod-hols/issues/22) Lab 02 `top_p` warning on greedy requests.
