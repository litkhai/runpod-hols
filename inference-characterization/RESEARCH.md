# GPU Inference Platforms — Desk Research from Public Documentation

[English](#english) | [한국어](#한국어)

> Public documentation read on 2026-10-06. Nothing here was measured: every figure is vendor documentation (or upstream project documentation) and carries a reference whose type — doc, API reference, pricing page, marketing page, blog — is stated in the source list. "문서 없음 / not documented" means the pages read did not state it, not that the capability is absent.
>
> 2026-10-06 에 읽은 공개 문서 기준입니다. 실측한 것은 없습니다. 모든 수치는 벤더 문서(또는 업스트림 프로젝트 문서)이며 참조 번호가 붙어 있고, 참조의 종류(문서, API 레퍼런스, 가격 페이지, 마케팅 페이지, 블로그)는 출처 목록에 적었습니다. "문서 없음 / not documented" 는 읽은 페이지에 그 내용이 없었다는 뜻이지, 기능이 없다는 뜻이 아닙니다.

---

## English

### Platform comparison

| Platform | GPU menu breadth | Billing unit and commitment | Host attributes the customer can see | Cold-start data exposed | Metrics / OTel export | Per-request GPU context | Sources |
|---|---|---|---|---|---|---|---|
| Runpod | GPU reference lists consumer RTX 30/40/50 cards, workstation RTX A/Ada/PRO cards, data-center A30, A40, A100, L4, L40S, H100 (SXM, PCIe, NVL), H200, B200, B300, V100 and AMD MI300X [RP1]. Serverless GPU pools span 16 GB to 180 GB classes [RP3]. The reference is a catalogue; per-type availability is not stated [RP1]. | Pods billed "by the second" [RP2]; on-demand vs savings plans paid "3 or 6 months upfront" [RP2]; a default hourly account spend limit applies [RP2]. Serverless priced per second [RP3]; "Per second, from worker start to full stop, rounded up to the nearest second" (marketing page) [RP4]. | Pod object: `machineId` ("A unique string identifying the host machine a Pod is running on"), `machine.cpuType` (displayName, cores, threadsPerCore), `dataCenterId`, `location`, `secureCloud`, `gpuTypeId` [RP5]. Create filters: `allowedCudaVersions`, `cloudType` SECURE/COMMUNITY, `minVCPUPerGPU`, `minRAMPerGPU`, `minDiskBandwidthMBps` [RP6]. Env: `RUNPOD_DC_ID`, `RUNPOD_POD_HOSTNAME`, `CUDA_VERSION` [RP7]. Serverless worker list: `gpuTypeId`, `dataCenterId` [RP12]. GPU UUID, PCIe gen/width, NVLink topology, driver: 문서 없음 / not documented. | Aggregate only: cold start time shown as P70/P90/P98 and cold start count on the endpoint page [RP8]; `delayTime` "includes the cold start time if a new worker needs to be spun up" [RP9]. Per-phase breakdown: 문서 없음 / not documented. | Built-in Serverless metrics page with "pXX latencies, queue delay, throughput, and worker states" [RP13]; REST API v2 adds log streaming and "Serverless observability" [RP13]. OTLP, Prometheus, DCGM export: 문서 없음 / not documented. Marketing page claims "distributed tracing" and "integrate with popular APM tools" with no documented mechanism (ambiguous) [RP4]. | Serverless job result carries `workerId` [RP10]; the worker list maps a worker `id` to `gpuTypeId` and `dataCenterId` [RP12]; that `workerId` equals that `id`: 문서 없음 / not documented. Span-level GPU or host attributes: 문서 없음 / not documented. | RP1-RP16 |
| Modal | T4, L4, A10, L40S, A100 (40 GB, 80 GB), RTX-PRO-6000, H100, H200, B200, B300 [MO1]; a function may list fallback GPU types [MO1]; "All H100 and H200 GPUs on the Modal platform are of the SXM variant" [MO1]. | Per second for GPU and CPU [MO2]; Starter and Team plans are "pay-as-you-go and does not require pre-purchasing compute" [MO2]; GPU concurrency cap per plan: Starter 10, Team 50 [MO2]. | `MODAL_CLOUD_PROVIDER` (AWS, GCP, OCI), `MODAL_REGION`, `MODAL_TASK_ID` [MO3]; H100 requests may be upgraded to H200, A100 to 80 GB [MO1]. GPU UUID, PCIe, NVLink, CPU model, driver, host id: 문서 없음 / not documented. | OTel metrics `modal.input_events.coldstart_time_us` and `modal.input_events.input_queue_time_us` are exported, with no description given (ambiguous) [MO4]. Per-phase breakdown: 문서 없음 / not documented [MO5]. | OTel integration exports metrics including `modal.gpu.memory.usage` and `modal.gpu.compute.utilization`, and Function logs [MO4]; custom metrics and spans in beta: "Contact us to enable custom metrics for your workspace" [MO4]; attributes `container_id`, `app_name`, `function_name`, `workspace_name` and their IDs [MO4]. | `container_id` on metrics and spans [MO4]; GPU or host identity: 문서 없음 / not documented. | MO1-MO6 |
| Baseten | T4, L4, A10G, A100, H100, H100MIG, H200, B200, RTX-PRO-6000 [BT1]. | "down to the minute" for dedicated deployments [BT2]; Basic plan is pay-as-you-go [BT2]; "Talk to Sales about compute in other countries and regions" [BT2]. | Metric labels `replica` ("The ID of the replica") and `gpu` ("The ID of the GPU"; ambiguous: index or UUID) [BT4]. CPU model, driver, PCIe, NVLink, datacenter, host id: 문서 없음 / not documented. | `baseten_replicas_starting`: "either waiting for resources to be available or loading the model" [BT4]. Startup duration or per-phase: 문서 없음 / not documented. | "Prometheus format at `https://app.baseten.co/metrics`" [BT3]; Datadog and New Relic "receive the metrics through an OpenTelemetry Collector" [BT3]; GPU utilization and memory metrics [BT4]. | 문서 없음 / not documented | BT1-BT4 |
| fal | Serverless machine types GPU-A100, GPU-L40, GPU-H100, GPU-RTXPRO6000, GPU-H200, GPU-B200 [FA1]; pricing page also lists B300 and GB200 (marketing page) [FA2]; fal Compute: 1x and 8x H100 SXM [FA4]. | Serverless "measured per-second by machine type" [FA3]; PENDING and DOCKER_PULL not billed [FA3]; deploys "need access that the fal team approves for each account" [FA3]. Compute: "Per-hour at fixed rates" [FA4]. | Runner view shows CPU, memory, GPU and VRAM usage [FA9]; 8x H100 supports InfiniBand [FA4]. GPU UUID, PCIe, NVLink, CPU model, driver, datacenter, host id: 문서 없음 / not documented. | Runner states PENDING, DOCKER_PULL, SETUP, IDLE and later; "The time from PENDING to IDLE is your cold start latency" [FA5]; "The Runners tab also aggregates cold starts across all runners in the selected range, with p50, p95, p99, and average duration per state" (vendor blog) [FA6]. | Prometheus-compatible endpoint: runner counts, queue depth, concurrent requests, request throughput, latency buckets [FA7]; OTel traces from a user-instrumented SDK reading `OTEL_EXPORTER_OTLP_ENDPOINT` [FA8]. | No automatic resource attributes documented; the example sets only `service.name` [FA8]. 문서 없음 / not documented | FA1-FA9 |
| CoreWeave | GB300 NVL72, GB200 NVL72, HGX B300, B200, H200, H100, RTX PRO 6000, GH200, L40, L40S, A100 [CW1]; GB300 NVL72, HGX B300 and some RTX PRO 6000 configurations are "Contact Sales" [CW1]. | "On-Demand Price (Per Hour)" [CW1]; discounts "for committed usage" [CW1]. | Node labels `gpu.coreweave.cloud/driver-version` [CW2], `topology.kubernetes.io/region`, `node.coreweave.cloud/rack` "to co-locate nodes on the same NVLink fabric" [CW3]; CPU model per instance listed [CW1]; DCGM "pre-installed on all servers", IPMI metrics [CW4]. GPU UUID, PCIe gen/width: 문서 없음 / not documented. | 문서 없음 / not documented | DCGM chip-level metrics and curated dashboards [CW4]; forwarding via Prometheus Agent remote-write [CW5]. OTLP: 문서 없음 / not documented. | 문서 없음 / not documented | CW1-CW5 |
| Lambda | B200 SXM6, H100 SXM, H100 PCIe, A100 SXM, A100 PCIe, GH200, A6000, A10, Quadro RTX 6000, Tesla V100 (marketing page) [LA1]; instance list [LA2]. | "ODC prices instances by hourly usage and bills in one-minute increments" [LA3]; 1-Click Clusters "billed in weekly increments according to the terms of your reservation" [LA3]. Quota or contract for on-demand: 문서 없음 / not documented. | Instance specs (vCPU, RAM, VRAM, root volume) [LA2]; beyond that: 문서 없음 / not documented. | 문서 없음 / not documented | Guest agent sends "system metrics, such as GPU and VRAM utilization" to the Lambda console [LA4]; export to the customer's stack: 문서 없음 / not documented. | 문서 없음 / not documented | LA1-LA4 |
| AWS (EC2, SageMaker) | EC2: T4 (G4dn), T4g (G5g), A10G (G5), L4 (G6, fractional G6f), L40S (G6e), RTX PRO 4500 (G7), RTX PRO Server 6000 (G7e), A100 (P4d, P4de), H100 (P5), H200 (P5e, P5en), B200 (P6-B200, P6e-GB200), B300 (P6-B300) [AW1]. | EC2 On-Demand "billed per-second" (Linux and others), 60-second minimum, "no long-term commitments" [AW2]; quotas "Running On-Demand G and VT instances" and "Running On-Demand P instances" default 0 vCPUs, adjustable [AW3]. SageMaker: "You are charged for usage of the instance type you choose", granularity not stated (ambiguous) [AW4]; Savings Plans optional [AW4]. | CPU model fixed per instance type [AW1]; CloudWatch agent GPU metrics include `pcie_link_gen_current`, `pcie_link_width_current`, with dimensions `index`, `name`, `arch` (no UUID) [AW5]; `DescribeInstanceTopology` shows relative network placement of running instances [AW6]; SageMaker enhanced metrics add `InstanceId` and `AcceleratorId` dimensions [AW7]. Driver, host id: 문서 없음 / not documented. | SageMaker `ModelSetupTime` for serverless endpoints, varying with "model size, how long it takes to download the model, and the start-up time of the container" [AW7]; multi-model endpoints: `ModelDownloadingTime`, `ModelLoadingTime`, `ModelLoadingWaitTime` [AW7]. Serverless Inference excludes GPUs [AW8]. | CloudWatch: SageMaker metrics at 1-minute frequency, configurable down to 10 seconds [AW7]; CloudWatch agent `nvidia_smi` metrics [AW5]. | 문서 없음 / not documented (enhanced metrics are aggregates by `InstanceId` and `AcceleratorId`) [AW7] | AW1-AW8 |
| GCP (GCE, Cloud Run) | GCE: GB300, GB200, B200, H200, H100, A100 80 GB and 40 GB, RTX PRO 6000, L4, T4, P4, V100 [GC1]; A4X Max, A4X, A4 and A3 Ultra need a reservation, Spot, Flex-start or a MIG resize request [GC1]. Cloud Run: RTX PRO 6000 and L4 [GC4]. | GCE: "VMs are charged on a per-second basis with a 1 minute minimum" [GC2]; GPU quota per region plus global "GPUs (all regions)" must be requested; Free Trial accounts cannot change quota [GC3]. Cloud Run GPU: instance-based billing mandatory, minimum instances billed while idle [GC4]; automatic initial quota of 3 GPUs per region [GC4]. | CPU platform per machine series, e.g. A3 Mega/High/Edge "Intel Xeon Platinum 8481C", visible in-guest via `lscpu` [GC5]; `physicalHostTopology` (cluster, block, sub-block, host) only for A4X Max, A4X, A4, A3 Ultra, A3 Mega, A3 High 8-GPU, A3 Edge, H4D or compact placement, and "you must contact your account team or the sales team to request access" [GC6]; Ops Agent GPU metric labels `gpu_number`, `uuid`, `model` [GC7]; Cloud Run driver 580.x (CUDA 13.0) [GC4]. | Cloud Run "Container startup latency" metric, no phase breakdown [GC9]; Cloud Run GPU instances "start in approximately 5 seconds" (vendor claim) [GC4]; GKE `pod_first_ready` "including image pulls", image pull time only in kubelet events [GC10]. | Ops Agent: "Collection of OpenTelemetry Protocol (OTLP) metrics and traces" and DCGM metrics [GC8]; DCGM covers SM, PCIe and NVLink traffic [GC11]; Cloud Run GPU utilization and memory metrics [GC9]. | 문서 없음 / not documented | GC1-GC11 |
| Azure (VMs, ML, Container Apps) | VM families NC (RTX PRO 6000 BSE, H100 series, V100, T4, A100), ND (GB300, GB200, MI300X, H200, H100, A100), NV (A10, V710 and older), NG (Radeon V620) [AZ1]; Container Apps serverless GPUs: A100 and T4 [AZ4]. | VMs: "We charge for the number of full minutes your virtual machine is running" [AZ2]; VM-family vCPU quotas per region, raised by request [AZ3]. Container Apps: "per-second billing with scale down to zero" [AZ4]; A100 and T4 quota enabled by default for EA and pay-as-you-go customers [AZ4]. | IMDS: `vmSize`, `location`, `physicalZone`, `platformFaultDomain`; `host.id` "Name of the host of the VM. Note that a VM will either have a host or a hostGroup but not both." (ambiguous: whether set outside dedicated hosts) [AZ5]; Container Apps driver 570 with CUDA 12.x, moving to 580 with 13.x [AZ4]. GPU UUID, PCIe, NVLink, CPU model: 문서 없음 / not documented. | Azure ML `AmlOnlineEndpointEventLog`: Pulled, Created and Started events for `image-fetcher`, `model-mount`, `inference-server`, each with `TimeGenerated` and `InstanceId` [AZ6]; durations are not computed by the platform. Container Apps: guidance only (artifact streaming, storage mounts) [AZ4]. | Azure Monitor; Azure ML deployment CPU/GPU metrics drill down to instance level [AZ6]. Container Apps managed OTel agent sends logs, metrics and traces to any OTLP endpoint for app-instrumented data; "System data, such as system logs or Container Apps standard metrics, isn't available to be sent" [AZ7]. | Azure ML traffic log has `XRequestId` and durations but no instance field; console log has `InstanceId` [AZ6]. GPU identity per request: 문서 없음 / not documented. | AZ1-AZ7 |
| Self-hosted Kubernetes + NVIDIA DCGM exporter | Not applicable: operator-owned hardware. | Not applicable: no vendor billing. | Exporter labels `gpu`, `UUID` or `uuid`, `pci_bus_id`, `device`, `modelName`, plus hostname "when enabled" [K81]; clock event reasons (`power_cap`, `hw_thermal`, `sw_thermal` and others) from `DCGM_FI_DEV_CLOCKS_EVENT_REASONS` [K81]; PCIe and NVLink throughput [K81][K86]. PCIe link gen/width fields: 문서 없음 / not documented in the exporter metric reference [K81]. | `kubelet_pod_start_sli_duration_seconds` (ALPHA) [K85]; the upstream SLI is "excluding time to pull images and run init containers" [K84]; image pull and model load as metrics: 문서 없음 / not documented (GKE notes image pull time appears only in kubelet events [GC10]). | Prometheus endpoint, default ":9400" [K83]. | `-k` "Map metrics to Kubernetes pods" [K82]; labels `pod`, `namespace`, `container` (as documented by GKE for the same exporter) [K86]. Request-level: 문서 없음 / not documented. | K81-K86, GC10 |

### Sources by platform

#### Runpod

- [RP1] https://docs.runpod.io/references/gpu-types — vendor doc, read 2026-10-06
- [RP2] https://docs.runpod.io/pods/pricing — vendor doc, read 2026-10-06
- [RP3] https://docs.runpod.io/serverless/endpoints/endpoint-configurations — vendor doc, read 2026-10-06
- [RP4] https://www.runpod.io/product/serverless — vendor marketing page, read 2026-10-06
- [RP5] https://docs.runpod.io/api-reference/pods/GET/pods/podId — vendor API reference, read 2026-10-06
- [RP6] https://docs.runpod.io/api-reference/pods/POST/pods — vendor API reference, read 2026-10-06
- [RP7] https://docs.runpod.io/pods/references/environment-variables — vendor doc, read 2026-10-06
- [RP8] https://docs.runpod.io/serverless/endpoints/job-states — vendor doc, read 2026-10-06
- [RP9] https://docs.runpod.io/serverless/development/benchmarking — vendor doc, read 2026-10-06
- [RP10] https://docs.runpod.io/tutorials/serverless/run-your-first — vendor doc (tutorial), read 2026-10-06
- [RP11] https://docs.runpod.io/serverless/endpoints/operation-reference — vendor doc, read 2026-10-06
- [RP12] https://docs.runpod.io/api-reference-v2/serverless/list-serverless-endpoint-workers — vendor API reference, read 2026-10-06
- [RP13] https://docs.runpod.io/release-notes — vendor doc, read 2026-10-06
- [RP14] https://docs.runpod.io/serverless/development/dual-mode-worker — vendor doc, read 2026-10-06
- [RP15] https://www.runpod.io/blog/introducing-flashboot-serverless-cold-start — vendor blog (first published 2023-06-17, updated 2026-09-13 per the page), read 2026-10-06
- [RP16] https://docs.runpod.io/serverless/development/environment-variables — vendor doc, read 2026-10-06

#### Modal

- [MO1] https://modal.com/docs/guide/gpu — vendor doc, read 2026-10-06
- [MO2] https://modal.com/pricing — vendor pricing page, read 2026-10-06
- [MO3] https://modal.com/docs/guide/environment_variables — vendor doc, read 2026-10-06
- [MO4] https://modal.com/docs/guide/otel-integration — vendor doc, read 2026-10-06
- [MO5] https://modal.com/docs/guide/cold-start — vendor doc, read 2026-10-06
- [MO6] https://modal.com/docs/guide/sandbox — vendor doc, read 2026-10-06

#### Baseten

- [BT1] https://docs.baseten.co/performance/instances — vendor doc, read 2026-10-06
- [BT2] https://www.baseten.co/pricing/ — vendor pricing page, read 2026-10-06
- [BT3] https://docs.baseten.co/observability/export-metrics/overview — vendor doc, read 2026-10-06
- [BT4] https://docs.baseten.co/observability/export-metrics/supported-metrics — vendor doc, read 2026-10-06

#### fal

- [FA1] https://fal.ai/docs/serverless/deployment-operations/machine-types — vendor doc, read 2026-10-06
- [FA2] https://fal.ai/pricing — vendor marketing/pricing page, read 2026-10-06
- [FA3] https://fal.ai/docs/documentation/serverless/pricing — vendor doc, read 2026-10-06
- [FA4] https://fal.ai/docs/documentation/compute — vendor doc, read 2026-10-06
- [FA5] https://fal.ai/docs/serverless/deployment-operations/understand-runners — vendor doc, read 2026-10-06
- [FA6] https://blog.fal.ai/h3-max-built-with-fal-inference-and-training/ — vendor blog (published 2026-09-17), read 2026-10-06
- [FA7] https://fal.ai/docs/documentation/serverless/observability/monitor-performance — vendor doc, read 2026-10-06
- [FA8] https://fal.ai/docs/documentation/serverless/observability/opentelemetry-traces — vendor doc, read 2026-10-06
- [FA9] https://fal.ai/docs/documentation/serverless/observability/app-analytics — vendor doc, read 2026-10-06

#### CoreWeave

- [CW1] https://www.coreweave.com/pricing — vendor pricing page, read 2026-10-06
- [CW2] https://docs.coreweave.com/products/cks/nodes/gpu-driver-management/update-gpu-driver — vendor doc, read 2026-10-06
- [CW3] https://docs.coreweave.com/platform/regions/about-regions-and-azs — vendor doc, read 2026-10-06
- [CW4] https://docs.coreweave.com/platform/fleet-management/hardware-observability — vendor doc, read 2026-10-06
- [CW5] https://docs.coreweave.com/docs/observability/telemetry-forwarding — vendor doc, read 2026-10-06

#### Lambda

- [LA1] https://lambda.ai/instances — vendor marketing page, read 2026-10-06
- [LA2] https://docs.lambda.ai/public-cloud/on-demand/ — vendor doc, read 2026-10-06
- [LA3] https://docs.lambda.ai/public-cloud/billing/ — vendor doc, read 2026-10-06
- [LA4] https://docs.lambda.ai/public-cloud/guest-agent/ — vendor doc, read 2026-10-06

#### AWS

- [AW1] https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html — vendor doc, read 2026-10-06
- [AW2] https://aws.amazon.com/ec2/pricing/on-demand/ — vendor pricing page, read 2026-10-06
- [AW3] https://docs.aws.amazon.com/ec2/latest/instancetypes/ec2-instance-quotas.html — vendor doc, read 2026-10-06
- [AW4] https://aws.amazon.com/sagemaker/ai/pricing/ — vendor pricing page, read 2026-10-06
- [AW5] https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-NVIDIA-GPU.html — vendor doc, read 2026-10-06
- [AW6] https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-topology.html — vendor doc, read 2026-10-06
- [AW7] https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-cloudwatch.html — vendor doc, read 2026-10-06
- [AW8] https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html — vendor doc, read 2026-10-06

#### GCP

- [GC1] https://docs.cloud.google.com/compute/docs/gpus — vendor doc, read 2026-10-06
- [GC2] https://docs.cloud.google.com/compute/docs/faq — vendor doc, read 2026-10-06
- [GC3] https://docs.cloud.google.com/compute/resource-usage — vendor doc, read 2026-10-06
- [GC4] https://docs.cloud.google.com/run/docs/configuring/services/gpu — vendor doc, read 2026-10-06
- [GC5] https://docs.cloud.google.com/compute/docs/cpu-platforms — vendor doc, read 2026-10-06
- [GC6] https://docs.cloud.google.com/compute/docs/instances/view-instance-topology — vendor doc, read 2026-10-06
- [GC7] https://docs.cloud.google.com/monitoring/api/metrics_opsagent — vendor doc, read 2026-10-06
- [GC8] https://docs.cloud.google.com/monitoring/agent/ops-agent — vendor doc, read 2026-10-06
- [GC9] https://docs.cloud.google.com/run/docs/monitoring — vendor doc, read 2026-10-06
- [GC10] https://docs.cloud.google.com/kubernetes-engine/docs/how-to/monitor-startup-latency-metrics — vendor doc, read 2026-10-06
- [GC11] https://docs.cloud.google.com/compute/docs/gpus/monitor-gpus — vendor doc, read 2026-10-06

#### Azure

- [AZ1] https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/overview — vendor doc, read 2026-10-06
- [AZ2] https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/ — vendor pricing page (FAQ), read 2026-10-06
- [AZ3] https://learn.microsoft.com/en-us/azure/quotas/per-vm-quota-requests — vendor doc, read 2026-10-06
- [AZ4] https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview — vendor doc, read 2026-10-06
- [AZ5] https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service — vendor doc, read 2026-10-06
- [AZ6] https://learn.microsoft.com/en-us/azure/machine-learning/how-to-monitor-online-endpoints — vendor doc, read 2026-10-06
- [AZ7] https://learn.microsoft.com/en-us/azure/container-apps/opentelemetry-agents — vendor doc, read 2026-10-06

#### Self-hosted Kubernetes + DCGM exporter

- [K81] https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html — NVIDIA doc, read 2026-10-06
- [K82] https://docs.nvidia.com/datacenter/dcgm/latest/reference/command-line-reference/dcgm-exporter.html — NVIDIA doc, read 2026-10-06
- [K83] https://docs.nvidia.com/datacenter/cloud-native/gpu-telemetry/latest/dcgm-exporter.html — NVIDIA doc, read 2026-10-06
- [K84] https://github.com/kubernetes/community/blob/main/sig-scalability/slos/pod_startup_latency.md — upstream project doc, read 2026-10-06
- [K85] https://github.com/kubernetes/website/blob/main/content/en/docs/reference/instrumentation/metrics.md — upstream project doc, read 2026-10-06
- [K86] https://docs.cloud.google.com/kubernetes-engine/docs/how-to/dcgm-metrics — vendor doc (GKE, same exporter), read 2026-10-06

#### Vast.ai (out of scope)

- [VA1] https://docs.vast.ai/documentation/instances/pricing — vendor doc, read 2026-10-06
- [VA2] https://vast.ai/products/serverless — vendor marketing page, read 2026-10-06

### F5 test

**F5:** Runpod is the only reviewed platform that simultaneously offers (1) a wide on-demand GPU menu with per-second billing and no commitment, (2) heterogeneous hosts whose attributes are observable, (3) serverless and long-running pods from the same image, (4) fleet-wide performance data. For Runpod, condition 1 is **supported**: the GPU reference spans consumer RTX cards through B300 and AMD MI300X [RP1], and Pods bill "by the second" with savings plans as the only commitment option [RP2]; the reference does not state per-type availability, and a default hourly spend limit applies [RP2]. Condition 2 is **supported** for the documented fields: each Pod exposes `machineId`, CPU type, data center, location and the Secure/Community flag [RP5], and host-level filters exist at creation [RP6]; the docs do not quantify how much hosts differ, and GPU UUID, PCIe, NVLink and driver are not platform-exposed. Condition 3 is **supported**: one image runs as a Pod and as a Serverless worker [RP14]. Condition 4 **cannot be verified from public docs**: no public page describes fleet-wide performance data, so whether Runpod holds it, and in what form, is unknowable from outside. Counterexample search: Modal meets condition 1 (per-second, no pre-purchase, T4 through B300 on one account [MO1][MO2], with a Starter-plan cap of 10 concurrent GPUs [MO2]), condition 3 (Functions and GPU Sandboxes from the same Image, Sandboxes up to 24 hours [MO6]) and condition 2 at cloud and region granularity (containers land on AWS, GCP or OCI with `MODAL_CLOUD_PROVIDER` and `MODAL_REGION` exposed, and H100 requests may land on H200 [MO1][MO3]). Because the hypothesis does not define "wide" or "observable", Modal satisfies conditions 1–3 together under a literal reading, and **F5 is not supported as written**. A narrower variant — documented per-host identity (host id, CPU model) on per-second, no-commitment capacity, alongside 3 — is consistent with every page read: Modal documents no host id or CPU model; GCP bills per second [GC2] but GPU quota must be requested [GC3], top SKUs need reservations, Spot or Flex-start [GC1], and physical-host IDs are limited to specific series with sales-granted access [GC6]; AWS bills per second [AW2] but GPU on-demand quotas default to 0 [AW3] and SageMaker Serverless excludes GPUs [AW8]; CoreWeave exposes driver, region and rack labels [CW2][CW3] but bills per hour [CW1]; Lambda and Baseten bill by the minute [LA3][BT2]; Azure VMs bill by the full minute [AZ2] and its per-second serverless GPUs are A100 and T4 only [AZ4]; fal bills per second but serverless access needs per-account approval [FA3] and documents no host attributes.

Out of scope: Vast.ai bills instances "by the second" [VA1] and markets a serverless product [VA2]; its host-attribute exposure and image reuse were not reviewed, so it remains an unexamined candidate counterexample for the narrower variant.

### Runpod facts for the lab

- **Pod environment variables** [RP7]: `RUNPOD_POD_ID`, `RUNPOD_DC_ID`, `RUNPOD_POD_HOSTNAME` ("Server hostname"), `RUNPOD_GPU_COUNT`, `RUNPOD_CPU_COUNT`, `RUNPOD_PUBLIC_IP`, `RUNPOD_TCP_PORT_22`, `RUNPOD_VOLUME_ID`, `RUNPOD_API_KEY` ("Pod-scoped API key" — host capture must exclude it), `PUBLIC_KEY`, `CUDA_VERSION`, `PYTORCH_VERSION`. No variable carries GPU type, GPU UUID, driver or `machineId`; `machineId` and CPU type come from the REST Pod object [RP5].
- **Serverless worker variables:** the Serverless environment-variable page documents only user-defined variables [RP16]. Which `RUNPOD_*` variables a worker receives is 문서 없음 / not documented, and is a capture item for the lab.
- **`/status` fields:** the operation reference examples show `delayTime`, `executionTime`, `id`, `output`, `status` [RP11]; `workerId` appears in the tutorial example [RP10] but not in the operation reference examples [RP11] (ambiguous: whether always returned). `delayTime` has two definitions: "the duration a request spends waiting in the queue before it is picked up by a worker" [RP8] and "The time spent waiting for a worker to become available. This includes the cold start time if a new worker needs to be spun up." [RP9] (ambiguous). `executionTime`: "The time the GPU takes to process the request once the worker has received the job." [RP9]. Unit: not stated; the benchmarking sample script prints both with an `ms` suffix [RP9] (ambiguous). The REST v2 worker list returns `gpuTypeId` and `dataCenterId` per worker [RP12].
- **FlashBoot:** documented [RP3] as "Reduces cold starts by retaining worker state after spin-down, allowing faster 'revival' than fresh boots", "Most effective on endpoints with consistent traffic where workers frequently cycle between active and idle"; the docs give no number. The marketing page claims "<200ms cold-start with FlashBoot" [RP4]. The blog claims "as low as 500ms" and "95% of our cold-starts are less than 2.3 seconds", conditional on endpoint popularity [RP15]. All three are vendor claims, not measured here; the April 2026 release notes add Priority FlashBoot for cluster workers and FlashBoot for CPU Serverless [RP13].
- **Cold-start phase breakdown:** 문서 없음 / not documented. The endpoint page shows an aggregate cold start time that "includes the time needed to start the container, load the model into GPU VRAM, and get the worker ready to process a job", as P70/P90/P98, plus a cold start count [RP8]; API responses carry no per-phase fields [RP11]. Elsewhere, fal documents per-state cold-start durations [FA5][FA6], SageMaker multi-model endpoints report model download and load times [AW7], and Azure ML logs container lifecycle events with timestamps [AZ6].

## 한국어

### 플랫폼 비교

| 플랫폼 | GPU 메뉴 폭 | 과금 단위와 약정 | 고객이 볼 수 있는 호스트 속성 | 콜드스타트 데이터 노출 | 메트릭 / OTel 내보내기 | 요청 단위 GPU 컨텍스트 | 출처 |
|---|---|---|---|---|---|---|---|
| Runpod | GPU 레퍼런스에 소비자용 RTX 30/40/50, 워크스테이션 RTX A/Ada/PRO, 데이터센터용 A30, A40, A100, L4, L40S, H100(SXM, PCIe, NVL), H200, B200, B300, V100, AMD MI300X 가 있음 [RP1]. Serverless GPU 풀은 16 GB 급부터 180 GB 급까지 [RP3]. 레퍼런스는 카탈로그이며 종류별 재고 여부는 명시 없음 [RP1]. | Pod 는 "by the second" 과금 [RP2]. 온디맨드와 "3 or 6 months upfront" 선결제 savings plan 중 선택 [RP2]. 계정 기본 시간당 지출 한도 있음 [RP2]. Serverless 는 초 단위 가격 [RP3]. "Per second, from worker start to full stop, rounded up to the nearest second" (마케팅 페이지) [RP4]. | Pod 객체: `machineId` ("A unique string identifying the host machine a Pod is running on"), `machine.cpuType` (displayName, cores, threadsPerCore), `dataCenterId`, `location`, `secureCloud`, `gpuTypeId` [RP5]. 생성 필터: `allowedCudaVersions`, `cloudType` SECURE/COMMUNITY, `minVCPUPerGPU`, `minRAMPerGPU`, `minDiskBandwidthMBps` [RP6]. 환경변수: `RUNPOD_DC_ID`, `RUNPOD_POD_HOSTNAME`, `CUDA_VERSION` [RP7]. Serverless 워커 목록: `gpuTypeId`, `dataCenterId` [RP12]. GPU UUID, PCIe 세대와 폭, NVLink 토폴로지, 드라이버: 문서 없음 / not documented. | 집계값만: 엔드포인트 페이지의 cold start time(P70/P90/P98)과 cold start count [RP8]. `delayTime` 은 "includes the cold start time if a new worker needs to be spun up" [RP9]. 단계별 분해: 문서 없음 / not documented. | 내장 Serverless 메트릭 페이지("pXX latencies, queue delay, throughput, and worker states") [RP13]. REST API v2 에 로그 스트리밍과 "Serverless observability" 추가 [RP13]. OTLP, Prometheus, DCGM 내보내기: 문서 없음 / not documented. 마케팅 페이지가 "distributed tracing", "integrate with popular APM tools" 를 주장하나 방법은 문서화되지 않음(모호) [RP4]. | Serverless 작업 결과에 `workerId` 가 있음 [RP10]. 워커 목록은 워커 `id` 를 `gpuTypeId`, `dataCenterId` 에 대응시킴 [RP12]. `workerId` 와 그 `id` 가 같은 값인지: 문서 없음 / not documented. 스팬 단위 GPU 또는 호스트 속성: 문서 없음 / not documented. | RP1-RP16 |
| Modal | T4, L4, A10, L40S, A100(40 GB, 80 GB), RTX-PRO-6000, H100, H200, B200, B300 [MO1]. 함수에 대체 GPU 종류 목록 지정 가능 [MO1]. "All H100 and H200 GPUs on the Modal platform are of the SXM variant" [MO1]. | GPU 와 CPU 초 단위 과금 [MO2]. Starter, Team 플랜은 "pay-as-you-go and does not require pre-purchasing compute" [MO2]. 플랜별 GPU 동시 사용 상한: Starter 10, Team 50 [MO2]. | `MODAL_CLOUD_PROVIDER`(AWS, GCP, OCI), `MODAL_REGION`, `MODAL_TASK_ID` [MO3]. H100 요청이 H200 으로, A100 이 80 GB 로 올라갈 수 있음 [MO1]. GPU UUID, PCIe, NVLink, CPU 모델, 드라이버, 호스트 ID: 문서 없음 / not documented. | OTel 메트릭 `modal.input_events.coldstart_time_us`, `modal.input_events.input_queue_time_us` 를 내보내나 설명은 없음(모호) [MO4]. 단계별 분해: 문서 없음 / not documented [MO5]. | OTel 연동으로 `modal.gpu.memory.usage`, `modal.gpu.compute.utilization` 등 메트릭과 Function 로그를 내보냄 [MO4]. 커스텀 메트릭과 스팬은 베타: "Contact us to enable custom metrics for your workspace" [MO4]. 속성: `container_id`, `app_name`, `function_name`, `workspace_name` 과 각 ID [MO4]. | 메트릭과 스팬에 `container_id` [MO4]. GPU 또는 호스트 식별: 문서 없음 / not documented. | MO1-MO6 |
| Baseten | T4, L4, A10G, A100, H100, H100MIG, H200, B200, RTX-PRO-6000 [BT1]. | 전용 배포는 "down to the minute" [BT2]. Basic 플랜은 종량제 [BT2]. "Talk to Sales about compute in other countries and regions" [BT2]. | 메트릭 라벨 `replica`("The ID of the replica"), `gpu`("The ID of the GPU", 인덱스인지 UUID 인지 모호) [BT4]. CPU 모델, 드라이버, PCIe, NVLink, 데이터센터, 호스트 ID: 문서 없음 / not documented. | `baseten_replicas_starting`: "either waiting for resources to be available or loading the model" [BT4]. 기동 소요 시간이나 단계별 값: 문서 없음 / not documented. | "Prometheus format at `https://app.baseten.co/metrics`" [BT3]. Datadog, New Relic 은 "receive the metrics through an OpenTelemetry Collector" [BT3]. GPU 사용률과 메모리 메트릭 [BT4]. | 문서 없음 / not documented | BT1-BT4 |
| fal | Serverless 머신 타입 GPU-A100, GPU-L40, GPU-H100, GPU-RTXPRO6000, GPU-H200, GPU-B200 [FA1]. 가격 페이지에는 B300, GB200 도 있음(마케팅 페이지) [FA2]. fal Compute: H100 SXM 1개, 8개 [FA4]. | Serverless 는 "measured per-second by machine type" [FA3]. PENDING, DOCKER_PULL 은 과금 안 됨 [FA3]. 배포는 "need access that the fal team approves for each account" [FA3]. Compute 는 "Per-hour at fixed rates" [FA4]. | 러너 화면에 CPU, 메모리, GPU, VRAM 사용량 [FA9]. 8x H100 은 InfiniBand 지원 [FA4]. GPU UUID, PCIe, NVLink, CPU 모델, 드라이버, 데이터센터, 호스트 ID: 문서 없음 / not documented. | 러너 상태 PENDING, DOCKER_PULL, SETUP, IDLE 이후. "The time from PENDING to IDLE is your cold start latency" [FA5]. "The Runners tab also aggregates cold starts across all runners in the selected range, with p50, p95, p99, and average duration per state" (벤더 블로그) [FA6]. | Prometheus 호환 엔드포인트: 러너 수, 큐 깊이, 동시 요청, 처리량, 지연 버킷 [FA7]. OTel 트레이스는 사용자가 계측한 SDK 가 `OTEL_EXPORTER_OTLP_ENDPOINT` 를 읽어 전송 [FA8]. | 자동 리소스 속성은 문서화되지 않음. 예제는 `service.name` 만 설정 [FA8]. 문서 없음 / not documented | FA1-FA9 |
| CoreWeave | GB300 NVL72, GB200 NVL72, HGX B300, B200, H200, H100, RTX PRO 6000, GH200, L40, L40S, A100 [CW1]. GB300 NVL72, HGX B300, 일부 RTX PRO 6000 구성은 "Contact Sales" [CW1]. | "On-Demand Price (Per Hour)" [CW1]. 약정 사용 시 할인("for committed usage") [CW1]. | 노드 라벨 `gpu.coreweave.cloud/driver-version` [CW2], `topology.kubernetes.io/region`, 같은 NVLink 패브릭 배치용 `node.coreweave.cloud/rack` [CW3]. 인스턴스별 CPU 모델 표기 [CW1]. DCGM "pre-installed on all servers", IPMI 메트릭 [CW4]. GPU UUID, PCIe 세대와 폭: 문서 없음 / not documented. | 문서 없음 / not documented | DCGM 칩 수준 메트릭과 기본 대시보드 [CW4]. Prometheus Agent remote-write 로 전달 [CW5]. OTLP: 문서 없음 / not documented. | 문서 없음 / not documented | CW1-CW5 |
| Lambda | B200 SXM6, H100 SXM, H100 PCIe, A100 SXM, A100 PCIe, GH200, A6000, A10, Quadro RTX 6000, Tesla V100 (마케팅 페이지) [LA1]. 인스턴스 목록 [LA2]. | "ODC prices instances by hourly usage and bills in one-minute increments" [LA3]. 1-Click Clusters 는 "billed in weekly increments according to the terms of your reservation" [LA3]. 온디맨드의 쿼터나 계약: 문서 없음 / not documented. | 인스턴스 사양(vCPU, RAM, VRAM, 루트 볼륨) [LA2]. 그 이상: 문서 없음 / not documented. | 문서 없음 / not documented | 게스트 에이전트가 "system metrics, such as GPU and VRAM utilization" 을 Lambda 콘솔로 전송 [LA4]. 고객 스택으로 내보내기: 문서 없음 / not documented. | 문서 없음 / not documented | LA1-LA4 |
| AWS (EC2, SageMaker) | EC2: T4(G4dn), T4g(G5g), A10G(G5), L4(G6, 분할 G6f), L40S(G6e), RTX PRO 4500(G7), RTX PRO Server 6000(G7e), A100(P4d, P4de), H100(P5), H200(P5e, P5en), B200(P6-B200, P6e-GB200), B300(P6-B300) [AW1]. | EC2 온디맨드는 "billed per-second"(Linux 등), 최소 60초, "no long-term commitments" [AW2]. "Running On-Demand G and VT instances", "Running On-Demand P instances" 쿼터 기본값 0 vCPU, 조정 가능 [AW3]. SageMaker: "You are charged for usage of the instance type you choose", 과금 단위 명시 없음(모호) [AW4]. Savings Plans 는 선택 [AW4]. | 인스턴스 타입별 CPU 모델 고정 [AW1]. CloudWatch 에이전트 GPU 메트릭에 `pcie_link_gen_current`, `pcie_link_width_current`, 차원은 `index`, `name`, `arch`(UUID 없음) [AW5]. `DescribeInstanceTopology` 가 실행 중 인스턴스의 상대적 네트워크 위치를 보여줌 [AW6]. SageMaker enhanced metrics 에 `InstanceId`, `AcceleratorId` 차원 [AW7]. 드라이버, 호스트 ID: 문서 없음 / not documented. | SageMaker 서버리스 엔드포인트의 `ModelSetupTime`, "model size, how long it takes to download the model, and the start-up time of the container" 에 따라 달라짐 [AW7]. 멀티모델 엔드포인트: `ModelDownloadingTime`, `ModelLoadingTime`, `ModelLoadingWaitTime` [AW7]. Serverless Inference 는 GPU 미지원 [AW8]. | CloudWatch: SageMaker 메트릭 기본 1분 주기, 10초까지 설정 가능 [AW7]. CloudWatch 에이전트 `nvidia_smi` 메트릭 [AW5]. | 문서 없음 / not documented (enhanced metrics 는 `InstanceId`, `AcceleratorId` 별 집계값) [AW7] | AW1-AW8 |
| GCP (GCE, Cloud Run) | GCE: GB300, GB200, B200, H200, H100, A100 80 GB 와 40 GB, RTX PRO 6000, L4, T4, P4, V100 [GC1]. A4X Max, A4X, A4, A3 Ultra 는 예약, Spot, Flex-start, MIG 리사이즈 요청 필요 [GC1]. Cloud Run: RTX PRO 6000, L4 [GC4]. | GCE: "VMs are charged on a per-second basis with a 1 minute minimum" [GC2]. 리전별 GPU 쿼터와 전역 "GPUs (all regions)" 쿼터를 요청해야 함. 무료 체험 계정은 쿼터 변경 불가 [GC3]. Cloud Run GPU: 인스턴스 기반 과금 필수, 최소 인스턴스는 유휴 중에도 과금 [GC4]. 리전당 GPU 3개 초기 쿼터 자동 부여 [GC4]. | 머신 시리즈별 CPU 플랫폼, 예: A3 Mega/High/Edge 는 "Intel Xeon Platinum 8481C", 게스트에서 `lscpu` 로 확인 [GC5]. `physicalHostTopology`(cluster, block, sub-block, host)는 A4X Max, A4X, A4, A3 Ultra, A3 Mega, A3 High 8-GPU, A3 Edge, H4D 또는 compact placement 에서만, "you must contact your account team or the sales team to request access" [GC6]. Ops Agent GPU 메트릭 라벨 `gpu_number`, `uuid`, `model` [GC7]. Cloud Run 드라이버 580.x(CUDA 13.0) [GC4]. | Cloud Run "Container startup latency" 메트릭, 단계 분해 없음 [GC9]. Cloud Run GPU 인스턴스는 "start in approximately 5 seconds"(벤더 주장) [GC4]. GKE `pod_first_ready` 는 "including image pulls", 이미지 풀 시간은 kubelet 이벤트에만 [GC10]. | Ops Agent: "Collection of OpenTelemetry Protocol (OTLP) metrics and traces" 와 DCGM 메트릭 [GC8]. DCGM 은 SM, PCIe, NVLink 트래픽 포함 [GC11]. Cloud Run GPU 사용률과 메모리 메트릭 [GC9]. | 문서 없음 / not documented | GC1-GC11 |
| Azure (VMs, ML, Container Apps) | VM 패밀리 NC(RTX PRO 6000 BSE, H100 계열, V100, T4, A100), ND(GB300, GB200, MI300X, H200, H100, A100), NV(A10, V710 및 이전 세대), NG(Radeon V620) [AZ1]. Container Apps 서버리스 GPU: A100, T4 [AZ4]. | VM: "We charge for the number of full minutes your virtual machine is running" [AZ2]. 리전별 VM 패밀리 vCPU 쿼터, 요청으로 상향 [AZ3]. Container Apps: "per-second billing with scale down to zero" [AZ4]. EA 와 종량제 고객은 A100, T4 쿼터가 기본 활성화 [AZ4]. | IMDS: `vmSize`, `location`, `physicalZone`, `platformFaultDomain`. `host.id` "Name of the host of the VM. Note that a VM will either have a host or a hostGroup but not both."(전용 호스트 외에도 채워지는지 모호) [AZ5]. Container Apps 드라이버 570 과 CUDA 12.x, 580 과 13.x 로 전환 예정 [AZ4]. GPU UUID, PCIe, NVLink, CPU 모델: 문서 없음 / not documented. | Azure ML `AmlOnlineEndpointEventLog`: `image-fetcher`, `model-mount`, `inference-server` 의 Pulled, Created, Started 이벤트, 각각 `TimeGenerated`, `InstanceId` 포함 [AZ6]. 소요 시간은 플랫폼이 계산해 주지 않음. Container Apps: 개선 가이드만(artifact streaming, storage mount) [AZ4]. | Azure Monitor. Azure ML 배포의 CPU/GPU 메트릭을 인스턴스 수준까지 내려 봄 [AZ6]. Container Apps 관리형 OTel 에이전트가 앱이 계측한 로그, 메트릭, 트레이스를 임의의 OTLP 엔드포인트로 전송. "System data, such as system logs or Container Apps standard metrics, isn't available to be sent" [AZ7]. | Azure ML 트래픽 로그에 `XRequestId` 와 소요 시간이 있으나 인스턴스 필드는 없음. 콘솔 로그에 `InstanceId` [AZ6]. 요청 단위 GPU 식별: 문서 없음 / not documented. | AZ1-AZ7 |
| 셀프호스팅 Kubernetes + NVIDIA DCGM exporter | 해당 없음: 운영자 소유 하드웨어. | 해당 없음: 벤더 과금 없음. | exporter 라벨 `gpu`, `UUID` 또는 `uuid`, `pci_bus_id`, `device`, `modelName`, 그리고 "when enabled" 일 때 hostname [K81]. `DCGM_FI_DEV_CLOCKS_EVENT_REASONS` 기반 클럭 이벤트 사유(`power_cap`, `hw_thermal`, `sw_thermal` 등) [K81]. PCIe, NVLink 처리량 [K81][K86]. PCIe 링크 세대와 폭 필드: exporter 메트릭 레퍼런스에 문서 없음 / not documented [K81]. | `kubelet_pod_start_sli_duration_seconds`(ALPHA) [K85]. 업스트림 SLI 는 "excluding time to pull images and run init containers" [K84]. 이미지 풀과 모델 로드의 메트릭: 문서 없음 / not documented (GKE 는 이미지 풀 시간이 kubelet 이벤트에만 나온다고 설명 [GC10]). | Prometheus 엔드포인트, 기본 ":9400" [K83]. | `-k` "Map metrics to Kubernetes pods" [K82]. 라벨 `pod`, `namespace`, `container`(같은 exporter 에 대한 GKE 문서 기준) [K86]. 요청 단위: 문서 없음 / not documented. | K81-K86, GC10 |

### 플랫폼별 출처

#### Runpod

- [RP1] https://docs.runpod.io/references/gpu-types — 벤더 문서, 2026-10-06 읽음
- [RP2] https://docs.runpod.io/pods/pricing — 벤더 문서, 2026-10-06 읽음
- [RP3] https://docs.runpod.io/serverless/endpoints/endpoint-configurations — 벤더 문서, 2026-10-06 읽음
- [RP4] https://www.runpod.io/product/serverless — 벤더 마케팅 페이지, 2026-10-06 읽음
- [RP5] https://docs.runpod.io/api-reference/pods/GET/pods/podId — 벤더 API 레퍼런스, 2026-10-06 읽음
- [RP6] https://docs.runpod.io/api-reference/pods/POST/pods — 벤더 API 레퍼런스, 2026-10-06 읽음
- [RP7] https://docs.runpod.io/pods/references/environment-variables — 벤더 문서, 2026-10-06 읽음
- [RP8] https://docs.runpod.io/serverless/endpoints/job-states — 벤더 문서, 2026-10-06 읽음
- [RP9] https://docs.runpod.io/serverless/development/benchmarking — 벤더 문서, 2026-10-06 읽음
- [RP10] https://docs.runpod.io/tutorials/serverless/run-your-first — 벤더 문서(튜토리얼), 2026-10-06 읽음
- [RP11] https://docs.runpod.io/serverless/endpoints/operation-reference — 벤더 문서, 2026-10-06 읽음
- [RP12] https://docs.runpod.io/api-reference-v2/serverless/list-serverless-endpoint-workers — 벤더 API 레퍼런스, 2026-10-06 읽음
- [RP13] https://docs.runpod.io/release-notes — 벤더 문서, 2026-10-06 읽음
- [RP14] https://docs.runpod.io/serverless/development/dual-mode-worker — 벤더 문서, 2026-10-06 읽음
- [RP15] https://www.runpod.io/blog/introducing-flashboot-serverless-cold-start — 벤더 블로그(페이지 표기상 2023-06-17 게시, 2026-09-13 갱신), 2026-10-06 읽음
- [RP16] https://docs.runpod.io/serverless/development/environment-variables — 벤더 문서, 2026-10-06 읽음

#### Modal

- [MO1] https://modal.com/docs/guide/gpu — 벤더 문서, 2026-10-06 읽음
- [MO2] https://modal.com/pricing — 벤더 가격 페이지, 2026-10-06 읽음
- [MO3] https://modal.com/docs/guide/environment_variables — 벤더 문서, 2026-10-06 읽음
- [MO4] https://modal.com/docs/guide/otel-integration — 벤더 문서, 2026-10-06 읽음
- [MO5] https://modal.com/docs/guide/cold-start — 벤더 문서, 2026-10-06 읽음
- [MO6] https://modal.com/docs/guide/sandbox — 벤더 문서, 2026-10-06 읽음

#### Baseten

- [BT1] https://docs.baseten.co/performance/instances — 벤더 문서, 2026-10-06 읽음
- [BT2] https://www.baseten.co/pricing/ — 벤더 가격 페이지, 2026-10-06 읽음
- [BT3] https://docs.baseten.co/observability/export-metrics/overview — 벤더 문서, 2026-10-06 읽음
- [BT4] https://docs.baseten.co/observability/export-metrics/supported-metrics — 벤더 문서, 2026-10-06 읽음

#### fal

- [FA1] https://fal.ai/docs/serverless/deployment-operations/machine-types — 벤더 문서, 2026-10-06 읽음
- [FA2] https://fal.ai/pricing — 벤더 마케팅/가격 페이지, 2026-10-06 읽음
- [FA3] https://fal.ai/docs/documentation/serverless/pricing — 벤더 문서, 2026-10-06 읽음
- [FA4] https://fal.ai/docs/documentation/compute — 벤더 문서, 2026-10-06 읽음
- [FA5] https://fal.ai/docs/serverless/deployment-operations/understand-runners — 벤더 문서, 2026-10-06 읽음
- [FA6] https://blog.fal.ai/h3-max-built-with-fal-inference-and-training/ — 벤더 블로그(2026-09-17 게시), 2026-10-06 읽음
- [FA7] https://fal.ai/docs/documentation/serverless/observability/monitor-performance — 벤더 문서, 2026-10-06 읽음
- [FA8] https://fal.ai/docs/documentation/serverless/observability/opentelemetry-traces — 벤더 문서, 2026-10-06 읽음
- [FA9] https://fal.ai/docs/documentation/serverless/observability/app-analytics — 벤더 문서, 2026-10-06 읽음

#### CoreWeave

- [CW1] https://www.coreweave.com/pricing — 벤더 가격 페이지, 2026-10-06 읽음
- [CW2] https://docs.coreweave.com/products/cks/nodes/gpu-driver-management/update-gpu-driver — 벤더 문서, 2026-10-06 읽음
- [CW3] https://docs.coreweave.com/platform/regions/about-regions-and-azs — 벤더 문서, 2026-10-06 읽음
- [CW4] https://docs.coreweave.com/platform/fleet-management/hardware-observability — 벤더 문서, 2026-10-06 읽음
- [CW5] https://docs.coreweave.com/docs/observability/telemetry-forwarding — 벤더 문서, 2026-10-06 읽음

#### Lambda

- [LA1] https://lambda.ai/instances — 벤더 마케팅 페이지, 2026-10-06 읽음
- [LA2] https://docs.lambda.ai/public-cloud/on-demand/ — 벤더 문서, 2026-10-06 읽음
- [LA3] https://docs.lambda.ai/public-cloud/billing/ — 벤더 문서, 2026-10-06 읽음
- [LA4] https://docs.lambda.ai/public-cloud/guest-agent/ — 벤더 문서, 2026-10-06 읽음

#### AWS

- [AW1] https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html — 벤더 문서, 2026-10-06 읽음
- [AW2] https://aws.amazon.com/ec2/pricing/on-demand/ — 벤더 가격 페이지, 2026-10-06 읽음
- [AW3] https://docs.aws.amazon.com/ec2/latest/instancetypes/ec2-instance-quotas.html — 벤더 문서, 2026-10-06 읽음
- [AW4] https://aws.amazon.com/sagemaker/ai/pricing/ — 벤더 가격 페이지, 2026-10-06 읽음
- [AW5] https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-NVIDIA-GPU.html — 벤더 문서, 2026-10-06 읽음
- [AW6] https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-topology.html — 벤더 문서, 2026-10-06 읽음
- [AW7] https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-cloudwatch.html — 벤더 문서, 2026-10-06 읽음
- [AW8] https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html — 벤더 문서, 2026-10-06 읽음

#### GCP

- [GC1] https://docs.cloud.google.com/compute/docs/gpus — 벤더 문서, 2026-10-06 읽음
- [GC2] https://docs.cloud.google.com/compute/docs/faq — 벤더 문서, 2026-10-06 읽음
- [GC3] https://docs.cloud.google.com/compute/resource-usage — 벤더 문서, 2026-10-06 읽음
- [GC4] https://docs.cloud.google.com/run/docs/configuring/services/gpu — 벤더 문서, 2026-10-06 읽음
- [GC5] https://docs.cloud.google.com/compute/docs/cpu-platforms — 벤더 문서, 2026-10-06 읽음
- [GC6] https://docs.cloud.google.com/compute/docs/instances/view-instance-topology — 벤더 문서, 2026-10-06 읽음
- [GC7] https://docs.cloud.google.com/monitoring/api/metrics_opsagent — 벤더 문서, 2026-10-06 읽음
- [GC8] https://docs.cloud.google.com/monitoring/agent/ops-agent — 벤더 문서, 2026-10-06 읽음
- [GC9] https://docs.cloud.google.com/run/docs/monitoring — 벤더 문서, 2026-10-06 읽음
- [GC10] https://docs.cloud.google.com/kubernetes-engine/docs/how-to/monitor-startup-latency-metrics — 벤더 문서, 2026-10-06 읽음
- [GC11] https://docs.cloud.google.com/compute/docs/gpus/monitor-gpus — 벤더 문서, 2026-10-06 읽음

#### Azure

- [AZ1] https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/overview — 벤더 문서, 2026-10-06 읽음
- [AZ2] https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/ — 벤더 가격 페이지(FAQ), 2026-10-06 읽음
- [AZ3] https://learn.microsoft.com/en-us/azure/quotas/per-vm-quota-requests — 벤더 문서, 2026-10-06 읽음
- [AZ4] https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview — 벤더 문서, 2026-10-06 읽음
- [AZ5] https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service — 벤더 문서, 2026-10-06 읽음
- [AZ6] https://learn.microsoft.com/en-us/azure/machine-learning/how-to-monitor-online-endpoints — 벤더 문서, 2026-10-06 읽음
- [AZ7] https://learn.microsoft.com/en-us/azure/container-apps/opentelemetry-agents — 벤더 문서, 2026-10-06 읽음

#### 셀프호스팅 Kubernetes + DCGM exporter

- [K81] https://docs.nvidia.com/datacenter/dcgm/latest/reference/dcgm-exporter-metrics.html — NVIDIA 문서, 2026-10-06 읽음
- [K82] https://docs.nvidia.com/datacenter/dcgm/latest/reference/command-line-reference/dcgm-exporter.html — NVIDIA 문서, 2026-10-06 읽음
- [K83] https://docs.nvidia.com/datacenter/cloud-native/gpu-telemetry/latest/dcgm-exporter.html — NVIDIA 문서, 2026-10-06 읽음
- [K84] https://github.com/kubernetes/community/blob/main/sig-scalability/slos/pod_startup_latency.md — 업스트림 프로젝트 문서, 2026-10-06 읽음
- [K85] https://github.com/kubernetes/website/blob/main/content/en/docs/reference/instrumentation/metrics.md — 업스트림 프로젝트 문서, 2026-10-06 읽음
- [K86] https://docs.cloud.google.com/kubernetes-engine/docs/how-to/dcgm-metrics — 벤더 문서(GKE, 같은 exporter), 2026-10-06 읽음

#### Vast.ai (범위 밖)

- [VA1] https://docs.vast.ai/documentation/instances/pricing — 벤더 문서, 2026-10-06 읽음
- [VA2] https://vast.ai/products/serverless — 벤더 마케팅 페이지, 2026-10-06 읽음

### F5 검증

**F5:** 검토한 플랫폼 중 Runpod 만이 (1) 초 단위 과금과 무약정의 넓은 온디맨드 GPU 메뉴, (2) 속성을 관찰할 수 있는 이질적 호스트, (3) 같은 이미지로 서버리스와 장기 실행 Pod, (4) 플릿 전체 성능 데이터를 동시에 제공한다. Runpod 에 대해 조건 1 은 **지지됨**: GPU 레퍼런스가 소비자용 RTX 부터 B300, AMD MI300X 까지 포괄하고 [RP1], Pod 는 "by the second" 과금이며 약정은 savings plan 을 고를 때뿐이다 [RP2]. 다만 레퍼런스는 종류별 재고를 말하지 않고, 계정 기본 시간당 지출 한도가 있다 [RP2]. 조건 2 는 문서화된 필드 범위에서 **지지됨**: Pod 마다 `machineId`, CPU 종류, 데이터센터, 위치, Secure/Community 구분이 노출되고 [RP5] 생성 시 호스트 수준 필터가 있다 [RP6]. 호스트 간 차이의 크기는 문서가 정량화하지 않으며, GPU UUID, PCIe, NVLink, 드라이버는 플랫폼이 노출하지 않는다. 조건 3 은 **지지됨**: 하나의 이미지가 Pod 와 Serverless 워커로 모두 실행된다 [RP14]. 조건 4 는 **공개 문서로 검증할 수 없음**: 플릿 전체 성능 데이터를 설명하는 공개 페이지가 없으므로, Runpod 이 그것을 갖고 있는지, 어떤 형태인지는 외부에서 알 수 없다. 반례 탐색: Modal 은 조건 1(초 단위, 사전 구매 없음, 한 계정에서 T4 부터 B300 까지 [MO1][MO2], 단 Starter 플랜은 GPU 동시 10개 상한 [MO2]), 조건 3(Function 과 GPU Sandbox 가 같은 Image 사용, Sandbox 최대 24시간 [MO6]), 그리고 클라우드와 리전 수준에서 조건 2(컨테이너가 AWS, GCP, OCI 중 어디든 배치되고 `MODAL_CLOUD_PROVIDER`, `MODAL_REGION` 이 노출되며, H100 요청이 H200 에 배치될 수 있음 [MO1][MO3])를 충족한다. 가설이 "넓은"과 "관찰 가능한"을 정의하지 않으므로, 문언 그대로 읽으면 Modal 이 조건 1–3 을 함께 충족하며 **F5 은 쓰인 그대로는 지지되지 않는다**. 더 좁은 변형 — 초 단위·무약정 용량에서 호스트 단위 식별(호스트 ID, CPU 모델)이 문서화되어 있고 조건 3 도 갖춤 — 은 읽은 모든 페이지와 모순되지 않는다: Modal 은 호스트 ID 와 CPU 모델을 문서화하지 않는다. GCP 는 초 단위 과금이지만 [GC2] GPU 쿼터를 요청해야 하고 [GC3], 최상위 SKU 는 예약, Spot, Flex-start 가 필요하며 [GC1], 물리 호스트 ID 는 특정 시리즈에서 영업 승인을 거쳐서만 볼 수 있다 [GC6]. AWS 는 초 단위 과금이지만 [AW2] GPU 온디맨드 쿼터 기본값이 0 이고 [AW3] SageMaker Serverless 는 GPU 를 지원하지 않는다 [AW8]. CoreWeave 는 드라이버, 리전, 랙 라벨을 노출하지만 [CW2][CW3] 시간 단위 과금이다 [CW1]. Lambda 와 Baseten 은 분 단위 과금이다 [LA3][BT2]. Azure VM 은 온전한 분 단위로 과금하고 [AZ2] 초 단위 서버리스 GPU 는 A100, T4 뿐이다 [AZ4]. fal 은 초 단위 과금이지만 서버리스 사용에 계정별 승인이 필요하고 [FA3] 호스트 속성을 문서화하지 않는다.

범위 밖: Vast.ai 는 인스턴스를 "by the second" 과금하고 [VA1] 서버리스 제품을 내세운다 [VA2]. 호스트 속성 노출과 이미지 재사용은 검토하지 않았으므로, 좁은 변형에 대한 미검토 반례 후보로 남는다.

### 실습에 필요한 Runpod 사실

- **Pod 환경변수** [RP7]: `RUNPOD_POD_ID`, `RUNPOD_DC_ID`, `RUNPOD_POD_HOSTNAME`("Server hostname"), `RUNPOD_GPU_COUNT`, `RUNPOD_CPU_COUNT`, `RUNPOD_PUBLIC_IP`, `RUNPOD_TCP_PORT_22`, `RUNPOD_VOLUME_ID`, `RUNPOD_API_KEY`("Pod-scoped API key" — 호스트 캡처에서 반드시 제외), `PUBLIC_KEY`, `CUDA_VERSION`, `PYTORCH_VERSION`. GPU 종류, GPU UUID, 드라이버, `machineId` 를 담은 변수는 없다. `machineId` 와 CPU 종류는 REST Pod 객체에서 얻는다 [RP5].
- **Serverless 워커 변수:** Serverless 환경변수 페이지는 사용자 정의 변수만 다룬다 [RP16]. 워커가 어떤 `RUNPOD_*` 변수를 받는지는 문서 없음 / not documented 이며, 실습에서 캡처할 항목이다.
- **`/status` 필드:** operation reference 예시에는 `delayTime`, `executionTime`, `id`, `output`, `status` 가 있다 [RP11]. `workerId` 는 튜토리얼 예시에는 있으나 [RP10] operation reference 예시에는 없다 [RP11](항상 반환되는지 모호). `delayTime` 정의가 둘이다: "the duration a request spends waiting in the queue before it is picked up by a worker" [RP8], "The time spent waiting for a worker to become available. This includes the cold start time if a new worker needs to be spun up." [RP9](모호). `executionTime`: "The time the GPU takes to process the request once the worker has received the job." [RP9]. 단위: 명시 없음. 벤치마킹 예제 스크립트가 둘 다 `ms` 를 붙여 출력한다 [RP9](모호). REST v2 워커 목록은 워커별 `gpuTypeId`, `dataCenterId` 를 반환한다 [RP12].
- **FlashBoot:** 문서에 있음 [RP3]: "Reduces cold starts by retaining worker state after spin-down, allowing faster 'revival' than fresh boots", "Most effective on endpoints with consistent traffic where workers frequently cycle between active and idle". 문서에는 수치가 없다. 마케팅 페이지는 "<200ms cold-start with FlashBoot" 를 주장한다 [RP4]. 블로그는 "as low as 500ms", "95% of our cold-starts are less than 2.3 seconds" 를 주장하며 엔드포인트 인기도에 좌우된다고 한다 [RP15]. 셋 다 벤더 주장이며 여기서 실측하지 않았다. 2026년 4월 릴리스 노트는 클러스터 워커용 Priority FlashBoot 와 CPU Serverless 용 FlashBoot 를 추가했다 [RP13].
- **콜드스타트 단계별 분해:** 문서 없음 / not documented. 엔드포인트 페이지는 "includes the time needed to start the container, load the model into GPU VRAM, and get the worker ready to process a job" 인 집계 cold start time 을 P70/P90/P98 로, 그리고 cold start count 를 보여준다 [RP8]. API 응답에는 단계별 필드가 없다 [RP11]. 다른 곳에서는 fal 이 상태별 콜드스타트 소요 시간을 [FA5][FA6], SageMaker 멀티모델 엔드포인트가 모델 다운로드와 로드 시간을 [AW7], Azure ML 이 타임스탬프가 붙은 컨테이너 수명주기 이벤트를 [AZ6] 문서화한다.
