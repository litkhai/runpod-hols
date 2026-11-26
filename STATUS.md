# STATUS.md

Updated 2026-10-20.

## Tracks

| Track | Run against a real account? |
|---|---|
| [`setup/`](./setup) | Yes |
| [`serverless/01-hello-worker`](./serverless/01-hello-worker) | **Yes** — deployed, called, measured; re-run on SDK 1.12.0 and 2.4.0 (2026-11-25) |
| [`serverless/02-llm-chat`](./serverless/02-llm-chat) | **Yes** — built by the console, deployed, called and measured 2026-10-11 on RTX A5000 and RTX PRO 6000 Blackwell MIG 1g.24gb with the CUDA 12.8 image; cache path settled (docs layout); re-run on SDK 2.4.0 2026-11-25 ([#138](https://github.com/litkhai/runpod-hols/issues/138)); PyTorch 2.15 / CUDA 13.2, transformers 5.24 run on a REST v2 endpoint 2026-11-26 ([#143](https://github.com/litkhai/runpod-hols/issues/143)); console endpoint moved to CUDA 13.2 and rebuilt: first prompt, `messages` and no-prompt served by the new image, a repeat prompt stayed queued and was cancelled; re-checked 2026-11-26: six sequential requests all served by one worker, four waited 22–66 s (one a cold start) with an idle worker listed ([#147](https://github.com/litkhai/runpod-hols/issues/147)) |
| [`serverless/03-vllm-endpoint`](./serverless/03-vllm-endpoint) | **Yes** — deployed by script, called with the OpenAI SDK and torn down 2026-11-05 on RTX 4090 (`worker-v1-vllm:v2.30.2`); first cold start 15 min, of which vLLM 77 s; first request HTTP 520; Re-run on REST v2 2026-11-24 ([#123](https://github.com/litkhai/runpod-hols/issues/123)): models after 114 s, template deleted at once; `worker-v1-vllm:v2.32.0` (vLLM 0.34.0), `openai` 3.59 run 2026-11-26 ([#143](https://github.com/litkhai/runpod-hols/issues/143)) |
| [`pod/01-launch-connect`](./pod/01-launch-connect) | **Yes** — launch, SSH, teardown run 2026-11-05 on a `cpu3c-2-4` CPU Pod with `runpod` 1.12.0; re-run 2026-11-24 on `runpod` 2.4.0 with a key without GraphQL, stacking guard and teardown checked ([#126](https://github.com/litkhai/runpod-hols/issues/126)); CPU Pods get no volume disk; JupyterLab and `--stop` not checked; image `runpod/pytorch:2.2.0` checked on an L4 2026-11-26 (SSH, CUDA, JupyterLab with `startJupyter`) ([#143](https://github.com/litkhai/runpod-hols/issues/143)) |
| [`pod/02-storage`](./pod/02-storage) | **Yes** — stop/start, terminate and re-attach, CPU Pods, run 2026-11-05 in EU-RO-1 over REST v1; first `start` after a stop refused for lack of GPUs on the host; Re-run on REST v2 2026-11-24 ([#123](https://github.com/litkhai/runpod-hols/issues/123)): same results on an L4 and CPU Pods (no RTX 4090 stock); a CPU Pod no longer gets a Pod volume request |
| [`pod/03-custom-template`](./pod/03-custom-template) | **Yes** — template with a plain and a secret env var, Pod, rotation, run 2026-11-05 on a CPU Pod; resolved secret and Pod API key sit in `/etc/rp_environment` (644); `restart` returned 500; Re-run on REST v2 2026-11-24 ([#123](https://github.com/litkhai/runpod-hols/issues/123)): v2 `restart` → 400 (no free vCPU) and the Pod left `EXITED`; `start` worked on the third try |
| [`pod/04-pod-to-serverless`](./pod/04-pod-to-serverless) | **Yes** — handler tested on an RTX 4090 Pod, served unchanged from Serverless via a shared network volume, 2026-11-05 EU-RO-1; first job `delayTime` 205 s, `runsync` returned `IN_QUEUE` at 90.9 s; Re-run on REST v2 2026-11-24 ([#123](https://github.com/litkhai/runpod-hols/issues/123)): `pip install` 219 s, first job `delayTime` 92.8 s, template deleted at once; re-run 2026-11-26 on `runpod/pytorch` 2.2.0 with `runpod` 2.4.0 on the volume: test on the Pod, two Serverless jobs, all deleted ([#148](https://github.com/litkhai/runpod-hols/issues/148)) |
| [`terraform/01-endpoint`](./terraform/01-endpoint) | **Yes** — provider 2.0.0 (REST v2): `apply`, one request on RTX 4090 and `destroy` run 2026-11-24 with Terraform 1.17.2 and a key without GraphQL; no workarounds needed; a template name used in October was refused (`endpoint template names must be unique`) ([#115](https://github.com/litkhai/runpod-hols/issues/115)) |
| [`terraform/02-pod`](./terraform/02-pod) | **Yes** — provider 2.0.0: `apply`, `plan` with no drift and `destroy` run 2026-11-24 with a Pod volume and with a network volume in EU-RO-1; `gpu_type_id` now honoured (RTX 2000 Ada); JupyterLab answered; SSH login not checked (key not on the account) ([#115](https://github.com/litkhai/runpod-hols/issues/115)); default image `runpod/pytorch:2.2.0` 2026-11-26, `validate` only ([#143](https://github.com/litkhai/runpod-hols/issues/143)) |
| [`cluster/01-pytorch-distributed`](./cluster/01-pytorch-distributed) | **Yes** — stage 1 run 2026-11-07 on 2× RTX 4090 (`SYS`, NCCL via host memory, 15.6 GB/s, DDP 0.21 scaling) and 2× A100 SXM (`NV12`, 201 GB/s, 0.91); 4× H100 SXM Pod (NV18, 356 GB/s, 0.82); stage 2 Instant Cluster (2 × 8 A100 SXM) ran twice and produced no multi-node figure: first NCCL fell back to sockets (0.32 GB/s), then with the cluster image every InfiniBand HCA hit *local catastrophic error* on the first transfer — a host PCIe fault per Runpod support (2026-11-07/08, USD 15.91 charged — billing stopped when Runpod pulled the hosts — and refunded as USD 16 in credit on 2026-11-14; [#52](https://github.com/litkhai/runpod-hols/issues/52), recorded as a failure); Stage 1 re-run on REST v2 2026-11-24 ([#123](https://github.com/litkhai/runpod-hols/issues/123)): 2× RTX 4090 on another host, `NODE`, 3.58 GB/s, scaling 0.06; `cluster.py` moved to REST v2 `/v2/clusters` 2026-11-24, create not run ([#126](https://github.com/litkhai/runpod-hols/issues/126)); 2-hour wait 2026-11-24: catalog showed stock `LOW` six times, every create `400 Insufficient resources`, nothing billed ([#130](https://github.com/litkhai/runpod-hols/issues/130)); REST v2 create succeeded 2026-11-26 for 2 × 8 H100 SXM: SSH, 16 GPUs, cluster variables and 8 IB HCAs per node checked, deleted after 85 s, billed USD 84.29/hr (over the USD 80 spend limit, not blocked); NCCL across nodes not run ([#19](https://github.com/litkhai/runpod-hols/issues/19)); **stage 2 on 2 × 8 H100 SXM 2026-11-26: NCCL over InfiniBand (8 × 400 Gb/s, GPUDirect RDMA), all-reduce busbw 446.7 GB/s at 1 GiB, DDP 16 GPUs 599,064 samples/s, scaling 0.68; 115 s, about USD 2.7** ([#19](https://github.com/litkhai/runpod-hols/issues/19)) |
| [`inference-characterization/`](./inference-characterization) | **Yes** — Pod sweeps on Secure Cloud GPU types, Serverless cold-start probes with worker logs, 2026-10-06/07; Community Cloud Pod never reachable over SSH; per-run seed re-run and three-host run found no Secure capacity on 2026-11-06 (C31, [#6](https://github.com/litkhai/runpod-hols/issues/6) closed); review follow-up tests all done ([#8](https://github.com/litkhai/runpod-hols/issues/8) closed; T4 cached model 2026-11-07, C32: no weight download, a container per cold start); FlashBoot-off claims C9/C17/C19 re-run with the state read back (C33, [#60](https://github.com/litkhai/runpod-hols/issues/60)): the create call had ignored `flashboot: false`, and October's off figures did not recur; REST v2 control plane checked 2026-11-24 ([#123](https://github.com/litkhai/runpod-hols/issues/123)): endpoint create with FlashBoot `OFF` and `FLASHBOOT` read back as set; sweeps not re-run |
| [`sdk/`](./sdk) | Source read at 1.11.0 and 1.12.0; client exercised live |
| [`gpu-topology/`](./gpu-topology) | **Yes** — catalogue and OpenAPI queried live; `topo -m` (`NV12`), MIG refusal and CUDA MPS run 2026-11-05 on a 2× A100 SXM Secure Cloud Pod; Bare Metal MIG stays vendor-doc only |
| [`storage/`](./storage) | **Yes** — every tier through one fio method on 2026-11-07 (container disk, Pod volume and standard network volume = MooseFS, high-performance = VAST NFS in US-CA-2, global = geesefs object store); concurrent writers; weights on a network volume did not shorten cold starts (C35) ([#69](https://github.com/litkhai/runpod-hols/issues/69)); S3 API measured (upload 20–30 MiB/s, download 66–210 MiB/s; files land as root 600) |
| [`docs/`](./docs) | <https://runpod.litkhai.dev> — four languages; console screenshots on setup, serverless, pod, sdk pages and cluster (#53, #56); [GPU & LLM Basics](https://runpod.litkhai.dev/readings/gpu-llm-basics/) with sizing calculators (#58) |

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

API keys (2026-11-24): `runpod-hols-lab-2026-11-24` is scoped — REST Write on Pods,
Serverless, Instant clusters, Volumes, Templates, Secrets; Read on Audit logs, Billing,
Catalog, Tags, Account; `api.runpod.ai` Read/Write; GraphQL None
([#103](https://github.com/litkhai/runpod-hols/issues/103)). The full-access
`runpod-hols-2026-11-07` key is still enabled until its owner revokes it.

> `Endpoint.health()` reports worker slots even when nothing is billing. It is
> not a spend signal — read `spendRate.current` from `GET /v2/account/limits`
> (or GraphQL `myself { currentSpendPerHr }`) for that.

## Open work

Tracked as issues — [all open](https://github.com/litkhai/runpod-hols/issues) ·
[needs a re-run](https://github.com/litkhai/runpod-hols/issues?q=is%3Aopen+label%3Are-verify) ·
[new labs](https://github.com/litkhai/runpod-hols/issues?q=is%3Aopen+label%3Aenhancement).

- No open lab issues; [#52](https://github.com/litkhai/runpod-hols/issues/52) (A100 cluster, host PCIe faults) stays recorded as a failure.
