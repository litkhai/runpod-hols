# STATUS.md

What has actually been run, and what is next. English only — tooling, not lab
content. Conventions are in [`AGENTS.md`](./AGENTS.md).

Keep this thin. Per-lab detail belongs in that lab's README; this page exists so
nobody mistakes *written* for *deployed*.

Last updated 2026-09-02.

---

## Tracks

| Track | State | Run against a real account? |
|---|---|---|
| [`setup/`](./setup) | Done | Yes — API key, tool checks, auth smoke test |
| [`serverless/01-hello-worker`](./serverless/01-hello-worker) | Done | **Yes** — deployed, called, measured. Re-run on SDK 1.12.0 |
| [`serverless/02-llm-chat`](./serverless/02-llm-chat) | Written, verified locally | **No** — never deployed |
| [`pod/01-launch-connect`](./pod/01-launch-connect) | Written | **No** — `--dry-run` and read-only paths only; no Pod ever launched |
| [`terraform/01-endpoint`](./terraform/01-endpoint) | Written | **No** — `plan` only, never applied |
| [`terraform/02-pod`](./terraform/02-pod) | Written | **No** — `plan` only, never applied |
| [`cluster/`](./cluster) | README only | No — deferred, multi-node costs are the reason |
| [`sdk/`](./sdk) | Done | Source read at 1.11.0 and 1.12.0; client exercised against a live endpoint |
| [`gpu-topology/`](./gpu-topology) | Done | Catalogue and OpenAPI spec queried live; hardware claims unrun (see below) |
| [`docs/`](./docs) | Live | <https://litkhai.github.io/runpod-hols> |

## Not written yet

`serverless/03-vllm-endpoint` · `pod/02-storage` · `pod/03-custom-template` ·
`pod/04-pod-to-serverless` · the cluster labs.

## Deliberately unverified

Each of these is labelled as such on its own page. They need a paid resource and
the repository does not spend on GPU time without a reason.

| Claim | What it would take |
|---|---|
| Lab 02's cached-model path — docs say `/runpod-volume/huggingface-cache/…`, the SDK probes `/runpod/cache/…` | Deploy Lab 02 and read the worker log |
| `nvidia-smi topo -m` output on a Runpod host | A multi-GPU pod |
| Bare Metal permitting MIG configuration | A Bare Metal machine |
| CUDA MPS inside a Runpod container | Any GPU pod |
| Terraform provider applying cleanly | `terraform apply` |
| Pod launch, SSH, teardown end to end | A Pod |

## Account

Checked 2026-09-02. Two endpoints exist:

| Endpoint | ID | Part of a lab? |
|---|---|---|
| `01-hello-world` | `ku3jultxavac2v` | Yes — Lab 01 |
| `vLLM v2.22.5` | `56snfp0y0lh5qc` | No — earlier exploration using Runpod's prebuilt vLLM worker, `MODEL_NAME=Qwen/Qwen2.5-7B-Instruct` |

Both scale to zero. `currentSpendPerHr` was `0` at last check.

> `Endpoint.health()` reports worker slots — `idle`, `initializing`, `ready` —
> even when nothing is billing. It is not a spend signal. Query
> `myself { currentSpendPerHr }` for that.

## Next

1. **Deploy Lab 02.** Console only. Repo `litkhai/runpod-hols`, branch `main`,
   Dockerfile path `/serverless/02-llm-chat/Dockerfile`, **Build context**
   `/serverless/02-llm-chat`, Model `Qwen/Qwen2.5-1.5B-Instruct`, env `MODEL_ID`
   matching it, container disk 20GB, 16–24GB GPU, active workers 0, max 1.
   Preflight already done: base image tag resolves, all three pins exist on
   PyPI, transformers does not pull torch.
2. Settle the cached-model path question from that deployment's worker log.
3. Then the unwritten labs, in whatever order suits.
