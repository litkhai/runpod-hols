# Evidence excerpts

Lines this lab relies on, fetched by `lab/collect_evidence.py` on 2026-10-07. Each block keeps only the matching lines; follow the URL for context.

## Runpod docs — Choose a Pod (Secure vs Community)

<https://docs.runpod.io/pods/choose-a-pod.md> — read 2026-10-07

```
<Note>RTX PRO 6000 Multi-Instance GPU (MIG) slices are partitioned GPU instances with dedicated memory and compute. Available on Secure Cloud only. All MIG slices use Blackwell architecture. Verify your CUDA version and framework versions support Blackwell before deploying.</Note>
## Secure Cloud vs Community Cloud
| | Secure Cloud | Community Cloud |
| **Infrastructure** | T3/T4 data centers | Peer-to-peer providers |
Runpod is no longer accepting new hosts for Community Cloud. Existing Community Cloud resources remain available.
```

## Runpod docs — Pod pricing

<https://docs.runpod.io/pods/pricing.md> — read 2026-10-07

```
Pods are billed by the second for compute and storage, with no fees for data ingress or egress. Find the latest GPU pricing on the [Runpod console](https://www.console.runpod.io/pods) during Pod deployment.
| | On-demand | Savings plan |
| **Commitment** | None | 3 or 6 months upfront |
Commit to a 3-month or 6-month term upfront for significant discounts on compute costs. When you stop a Pod, the savings plan automatically applies to your next deployment of the same GPU type.
Savings plans only cover GPU compute costs—[storage costs](/pods/storage/types) are billed at standard rates. Storage charges continue to accrue on stopped Pods. If your balance reaches \$0, your Pods stop: those with a network volume are preserved, while those without one are terminated and their data cannot be recovered. Plans are non-refundable and have fixed expiration dates.
Storage is billed per-second for container and volume disks, and hourly for network volumes. You are not charged if the host <MachineTooltip /> is unavailable.
* **Savings plans**: Monitor active plans, commitment periods, and expiration dates in the [Savings plans](https://www.console.runpod.io/savings-plans) section.
```

## Runpod docs — Pod migration

<https://docs.runpod.io/pods/troubleshooting/pod-migration.md> — read 2026-10-07

```
> Automatically migrate your Pod to a new machine when your GPU is unavailable. Review setup, configuration, and operations guidance for Runpod Pods.
Pod migration is currently in beta. [Join our Discord](https://discord.com/invite/runpod) if you'd like to provide feedback.
<iframe className="w-full aspect-video rounded-xl" src="https://www.youtube.com/embed/q7I0uVTOhqg" title="3 Minute Runpod: Migrate your volume to a new Pod automatically" frameBorder="0" allow="fullscreen; accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
## Your options when GPUs are unavailable
When prompted to migrate your Pod, you have three options:
1. **Do nothing**: If you don't want to migrate your data, you can wait and try again later. The GPU will become available once another user stops their Pod on that machine.
2. **Start Pod with CPUs**: If you don't need GPU access immediately, you can start your Pod with CPUs only. This lets you access your data and manually migrate files if needed, but the Pod will have limited CPU resources and is not suitable for compute-intensive tasks.
3. **Automatically migrate Pod data**: This option spins up a new Pod with the same specifications as your current one and automatically migrates your data to a machine with available GPUs. The migration process finds a new machine with your requested GPU type, provisions the instance, and transfers your network volume data from the old Pod to the new one.
```

## Runpod API v2 — Stream serverless worker logs

<https://docs.runpod.io/api-reference-v2/serverless/stream-serverless-worker-logs.md> — read 2026-10-07

```
> Stream a Runpod Serverless worker's logs in real time as Server-Sent Events, with resumable reconnects via Last-Event-ID.
````yaml get /v2/serverless/{id}/workers/{workerId}/logs
/v2/serverless/{id}/workers/{workerId}/logs:
Streams a serverless worker's logs as Server-Sent Events. The `source`
`{ "source": "container", "line": "...", "ts": "..." }`.
Server-Sent Events stream. Each event includes an `id:` line
{"ts":"2026-06-01T12:05:04Z","source":"container","line":"Worker
description: Log source to stream. Omit to include both container and system logs.
Number of historical lines to backfill before streaming. Defaults to
100 when omitted; set `0` to stream live with no backfill. Maximum 5000.
drives the backfill instead.
- LogSourceContainer
```

## Runpod API v2 — List serverless endpoint workers

<https://docs.runpod.io/api-reference-v2/serverless/list-serverless-endpoint-workers.md> — read 2026-10-07

```
````yaml get /v2/serverless/{id}/workers
/v2/serverless/{id}/workers:
running: 1
idle: 1
throttled: 0
status: RUNNING
gpuTypeId: NVIDIA GeForce RTX 4090
dataCenterId: US-KS-2
startedAt: '2026-06-01T12:05:00Z'
`version` differs is running stale config (see `worker.isStale`).
True when the worker is running an older endpoint configuration than
Endpoint configuration version this worker is running. Compare with
description: Container image the worker is running.
Seconds the worker has been running. Null until the worker is placed
and running.
gpuTypeId:
dataCenterId:
startedAt:
roll-up of the `workers` array, so `running + idle + initializing +
throttled + unhealthy == total == len(workers)`.
- running
- idle
- throttled
running:
idle:
```

## Runpod docs — Endpoint settings (FlashBoot, GPU priority)

<https://docs.runpod.io/serverless/endpoints/endpoint-configurations.md> — read 2026-10-07

```
| **Active workers** | 0 | Always-on workers (eliminates cold starts) |
| **Idle timeout** | 5s | Time before idle worker shuts down |
| **FlashBoot** | Enabled | Faster cold starts via state retention |
Specify up to three GPU types in priority order when configuring an endpoint. Runpod uses this ranking to distribute workers across available GPUs, improving availability during high demand.
### Active workers
Minimum number of workers that remain warm and ready at all times. Setting this to 1+ eliminates cold starts. Active workers incur charges continuously, including when idle.
### Idle timeout
### FlashBoot
Reduces cold starts by retaining worker state after spin-down, allowing faster "revival" than fresh boots. Most effective on endpoints with consistent traffic where workers frequently cycle between active and idle.
Both new GPU and CPU endpoints will have FlashBoot enabled by default, and you can edit existing endpoints to enable or disable FlashBoot.
```

## Runpod docs — Cached models

<https://docs.runpod.io/serverless/endpoints/model-caching.md> — read 2026-10-07

```
# Cached models
> Accelerate worker cold starts and reduce costs by using cached models. Review configuration and operations guidance for Runpod Serverless.
return <Tooltip headline="Cold start" tip="The time between when an endpoint with no running workers receives a request, and when a worker is fully warmed up and ready to handle the request." cta="Learn more about cold starts" href="/serverless/overview#cold-starts">cold start</Tooltip>;
To learn how to use cached models with the Hugging Face Transformers library, see [Use Hugging Face models](/serverless/development/huggingface-models#use-cached-models). For a complete end-to-end deployment walkthrough, see the [cached model tutorial](/tutorials/serverless/model-caching-text).
Enabling cached models on your endpoints can reduce <ColdStartTooltip /> times and dramatically reduce the cost for loading large models.
## Why use cached models?
* **Faster cold starts:** Using cached models can reduce <ColdStartTooltip /> times to just a few seconds, even for large models.
* **Accelerated deployment:** You can deploy cached models instantly without waiting for external downloads or transfers.
* **Shared across workers:** Multiple <WorkersTooltip /> running on the same host <MachineTooltip /> can reference the same cached model, eliminating redundant downloads and saving disk space.
## Cached model compatibility
Cached models work with any model hosted on Hugging Face, including:
* **Public models:** Any publicly available model on Hugging Face.
* **Gated models:** Models that require you to accept terms (provide a Hugging Face access token).
* **Private models:** Private models your Hugging Face token has access to.
Cached models aren't suitable if your model is private and not hosted on Hugging Face. In that case, [bake it into your Docker image](/serverless/workers/deploy#including-models-and-external-files) instead.
When you select a cached model for your endpoint, Runpod automatically tries to start your workers on hosts that already contain the selected model.
If no cached host <MachinesTooltip /> are available, the system delays starting your workers until the model is downloaded onto the machine where your workers will run, ensuring you still won't be charged for the download time.
CheckWorkers -->|"&nbsp;&nbsp;No&nbsp;&nbsp;"| CheckCache{Cached model<br/>host available?}
CheckCache -->|"&nbsp;&nbsp;Yes&nbsp;&nbsp;"| FastStart[Start worker on<br/>cached host]
## Enable cached models
Follow these steps to select and add a cached model to your endpoint:
Navigate to the [Serverless section](https://www.console.runpod.io/serverless) of the console and click **New Endpoint**. Choose your deployment type (Hugging Face, Docker, GitHub, or Hub).
If you select **Hugging Face**, the model field is the primary input—model caching is pre-configured automatically.
<Frame alt="Cached model setting">
If you're using a gated model, you'll need to enter a [Hugging Face access token](https://huggingface.co/docs/hub/en/security-tokens).
```

## Runpod docs — Serverless logs

<https://docs.runpod.io/serverless/development/logs.md> — read 2026-10-07

```
Endpoint logs are retained for 90 days, after which they are automatically removed from the system. If you need to retain logs indefinitely, you can [write them to a network volume](#persistent-log-storage) or an external service.
## Worker logs
Worker logs are temporary logs that exist only on the specific server where the worker is running. These logs are not throttled, but are not persistent, and are removed when a worker terminates.
To view worker logs:
4. **Review retention period**: Logs older than 90 days are automatically removed.
```

No match for: `container`

## Runpod Overdrive

<https://www.runpod.io/overdrive> — read 2026-10-07

```
Runpod Overdrive: Same GPU, Up to 3.5x Faster
Run the same GPU up to 3.5x faster
Any self-hosted model runs on vLLM
Builds upon Runpod Serverless
Tell us your workload model, context length, traffic pattern. We benchmark your endpoint’s current performance.
Your deploy runs on Runpod Serverless. Sub-200ms cold starts. Zero idle cost.
If we don't beat your baseline, you pay nothing.
```

## worker-vllm v2.28.0 release

<https://api.github.com/repos/runpod-workers/worker-vllm/releases/tags/v2.28.0> — read 2026-10-07

```
* Bump vLLM to v0.30.0 by @velaraptor-runpod in https://github.com/runpod-workers/worker-vllm/pull/345
```

## vLLM v0.31.0 — vllm/benchmarks/serve.py

<https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/vllm/benchmarks/serve.py> — read 2026-10-07

```
1298:             "request_goodput": metrics.request_goodput if goodput_config_dict else None,
1299:             "output_throughput": metrics.output_throughput,
1402:             result[f"p{p_word}_{metric_attribute_name}_ms"] = value
1778:         "--metadata",
1838:         "--goodput",
2153:     # when using random datasets, default to ignoring EOS
```

## vLLM v0.31.0 — vllm/v1/metrics/loggers.py

<https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/vllm/v1/metrics/loggers.py> — read 2026-10-07

```
677:             name="vllm:num_preemptions",
```

## PyPI — vllm 0.31.0 requires_dist

<https://pypi.org/pypi/vllm/0.31.0/json> — read 2026-10-07

```
torch==2.13.0
torchaudio==2.11.0
torchvision==0.28.0
torchcodec>=0.14
nvidia-cudnn-frontend>=1.19.1
nvidia-cutlass-dsl[cu13]==4.7.1
nvidia-deepstream-videodecode-cu13>=9.0.2; extra == "deepstream"
```

## Runpod REST API v1 — OpenAPI spec

<https://rest.runpod.io/v1/openapi.json> — read 2026-10-07

```
paths: 23
PodCreateInput.allowedCudaVersions enum: ['13.0', '12.9', '12.8', '12.7', '12.6', '12.5', '12.4', '12.3', '12.2', '12.1', '12.0', '11.8']
PodCreateInput fields used: cloudType, gpuTypeIds, allowedCudaVersions, supportPublicIp, ports, env
EndpointCreateInput fields used: flashboot, idleTimeout, workersMin, workersMax, minCudaVersion, gpuTypeIds
Pod.portMappings: A mapping of internal ports to public ports on a Pod. For example, { "22": 10341 } means that port 22 on the Pod is mapped to port 10341 and is publicly accessi
```

## NVIDIA H100 NVL product brief

<https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/h100/PB-11773-001_v01.pdf> — read 2026-10-07

```
Total board power                PCIe 16-pin cable strapped for 450 W or 600 W power mode:
                                  > 400 W maximum (default)
                                  > 310 W power compliance limit1
                                  > 200 W minimum
                                  PCIe 16-pin cable strapped for 300 W power mode:
                                  > 310 W maximum (default)
                                  > 310 W power compliance limit
                                  > 200 W minimum
```

