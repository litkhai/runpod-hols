# STATUS.md

Updated 2026-09-02.

## Tracks

| Track | Run against a real account? |
|---|---|
| [`setup/`](./setup) | Yes |
| [`serverless/01-hello-worker`](./serverless/01-hello-worker) | **Yes** — deployed, called, measured; re-run on SDK 1.12.0 |
| [`serverless/02-llm-chat`](./serverless/02-llm-chat) | No — verified locally, never deployed |
| [`pod/01-launch-connect`](./pod/01-launch-connect) | No — `--dry-run` only, no Pod ever launched |
| [`terraform/01-endpoint`](./terraform/01-endpoint) | No — `plan` only |
| [`terraform/02-pod`](./terraform/02-pod) | No — `plan` only |
| [`cluster/`](./cluster) | No — README only, deferred on cost |
| [`sdk/`](./sdk) | Source read at 1.11.0 and 1.12.0; client exercised live |
| [`gpu-topology/`](./gpu-topology) | Catalogue and OpenAPI queried live; hardware claims unrun |
| [`docs/`](./docs) | <https://litkhai.github.io/runpod-hols> |

Not written: `serverless/03-vllm-endpoint`, `pod/02-storage`,
`pod/03-custom-template`, `pod/04-pod-to-serverless`, the cluster labs.

## Unverified, and what it would take

| Claim | Needs |
|---|---|
| Lab 02's cache path — docs say `/runpod-volume/huggingface-cache/…`, the SDK probes `/runpod/cache/…` | Deploying Lab 02 and reading the worker log |
| `nvidia-smi topo -m` output on a Runpod host | A multi-GPU pod |
| Bare Metal permitting MIG configuration | A Bare Metal machine |
| CUDA MPS inside a Runpod container | Any GPU pod |
| The Terraform provider applying cleanly | `terraform apply` |
| Pod launch, SSH, teardown | A Pod |

## Account

| Endpoint | ID | Part of a lab? |
|---|---|---|
| `01-hello-world` | `ku3jultxavac2v` | Lab 01 |
| `vLLM v2.22.5` | `56snfp0y0lh5qc` | No — earlier exploration with Runpod's prebuilt vLLM worker |

Both scale to zero; `currentSpendPerHr` was `0` at last check.

> `Endpoint.health()` reports worker slots even when nothing is billing. It is
> not a spend signal — query `myself { currentSpendPerHr }` for that.

## Next

1. Deploy Lab 02 — console only, fields in
   [its README](./serverless/02-llm-chat). Preflight done: base image tag
   resolves, all three pins exist on PyPI, transformers does not pull torch.
2. Settle the cache path from that deployment's worker log.
3. The unwritten labs.
