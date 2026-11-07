---
layout: default
title: GPU & LLM Basics
permalink: /readings/gpu-llm-basics/
description: GPU hardware, precision, sizing formulas with calculators, serving and cost — each next to what the runpod-hols labs measured on Runpod.
scripts:
  - /assets/calc.js
---

# GPU & LLM Basics

<div class="lang" data-lang="en" markdown="1">

## English

A GPU is easiest to reason about as a memory hierarchy plus two kinds of execution unit. Every sizing and optimisation argument below falls out of that one framework. Four formulas then cover almost every "what does this model need?" question, and three calculators let you work the numbers rather than memorise them.

Concepts and spec figures are general and come from vendor material. The **Measured here** boxes are what these labs actually ran on Runpod — they are where the general rule meets one real machine. Throughout: separate training from inference, because memory, bottleneck and GPU choice are opposites for the two.

## GPU hardware
{: #hardware }

### Two kinds of execution unit

| | CUDA core | Tensor core |
|---|---|---|
| Unit of work | Scalar FMA, a×b+c | Matrix-block multiply-accumulate, D = A×B + C |
| MACs per instruction | 1 | Hundreds to thousands |
| Count on H100 SXM | 16,896 | 528 |
| H100 throughput | 67 TFLOPS (FP32) | 989 (FP16) / 1,979 (FP8) |
| What it can do | Anything — branches, transcendentals | Matrix multiply only |
| How you reach it | Ordinary CUDA C++ arithmetic | Through cuBLAS / CUTLASS / Triton |

32× fewer units, 15–30× more throughput. Doing the same MACs on CUDA cores pays instruction fetch, decode and register traffic every time; a tensor core amortises that overhead across thousands of operations in one instruction.

<div class="warn" markdown="1">
**"Tensor cores are just better" is the wrong summary.** They do not compete. Softmax, RMSNorm, RoPE, activations, residual adds, KV-cache indexing and sampling cannot run on a tensor core — all of it lands on CUDA cores. And the faster tensor cores get, the more that remainder becomes the bottleneck. A large share of real optimisation work is not the GEMMs but the gaps between them.
</div>

### Memory hierarchy

```
Registers            tens of KB/SM     tens of TB/s
L1 / shared memory   ~256 KB/SM        ~20 TB/s
L2 cache             50 MB (H100)      ~5 TB/s
HBM (VRAM)           80–288 GB         2–8 TB/s     ← the LLM bottleneck
Host RAM             TBs               ~64 GB/s (PCIe 5.0 x16)
```

### Roofline — which side are you on

Arithmetic intensity = FLOPs ÷ bytes moved. The crossover on H100 SXM is 989 TFLOPS ÷ 3.35 TB/s ≈ **295 FLOP/byte**. Below it you are memory bound; above it, compute bound.

- LLM decode at batch 1: intensity around 2 — under 1% of H100's compute. This is why batching multiplies throughput.
- LLM prefill on a long prompt: several hundred — compute bound, where tensor cores earn their keep.
- RMSNorm, residual adds: 1–2 — purely memory bound, and the reason kernel fusion exists.

### Current line-up (specs as of 2026.09)

| GPU | Memory | Bandwidth | NVLink | TDP | Typical use |
|---|---|---|---|---|---|
| L4 | 24 GB | 0.30 TB/s | — | 72 W | Light inference, video |
| RTX 4090 | 24 GB | 1.01 TB/s | — | 450 W | Development, QLoRA |
| L40S | 48 GB | 0.86 TB/s | — | 350 W | Mid-size inference |
| A100 80GB SXM | 80 GB | 2.04 TB/s | 600 GB/s | 400 W | Cost-effective training |
| H100 PCIe | 80 GB | 2.00 TB/s | 600 GB/s | 350 W | General purpose |
| H100 SXM | 80 GB | 3.35 TB/s | 900 GB/s | 700 W | Training standard |
| RTX PRO 6000 | 96 GB | ~1.8 TB/s | — | 600 W | Workstation inference |
| H200 SXM | 141 GB | 4.80 TB/s | 900 GB/s | 700 W | Long-context inference |
| B200 | 180 GB | ~8 TB/s | 1.8 TB/s | ~1000 W | Current-generation training |
| B300 | 288 GB | ~8 TB/s | 1.8 TB/s | ~1400 W | Large models |
| GB200/GB300 NVL72 | 72-GPU domain | — | Whole rack | ~130 kW/rack | Frontier, liquid cooled |

Three things worth remembering:

1. **SXM vs PCIe.** 3.35 TB/s against 2.00 TB/s, and 900 GB/s of NVLink against a two-card bridge. For multi-GPU training, anything but SXM makes communication the bottleneck.
2. **L40S and the RTX parts have no NVLink.** If the model needs model parallelism they are out; they are for models that fit on one card.
3. **From Blackwell on, power and cooling are the real constraint.** On a cloud like Runpod that shows up as price and availability rather than as your problem — but it is why the newest parts are the scarcest.

### Nameplate capacity versus usable capacity

An "H100 80GB" does not give you 80 GB for tensors. The gap opens in three places.

**① Physical capacity versus product specification**

| GPU | Physical configuration | Physical total | Spec | Why |
|---|---|---|---|---|
| H100 SXM | HBM3 16GB × 6 sites, 5 enabled | 96 GB | 80 GB | One stack disabled for yield |
| H200 SXM | HBM3e 24GB × 6 | 144 GB | 141 GB | Row redundancy and internal reserve (undocumented) |
| B200 | HBM3e, 8 chips in 2 stacks | 192 GB | 180–192 GB | Varies by SKU and provider — Runpod lists 180 GB |

**② What `nvidia-smi` reports** — in MiB. NVIDIA's "80GB" is effectively 80 GiB (85.9 GB decimal); `torch.cuda.get_device_properties(0).total_memory` is bytes, so divide by 1024³ to reconcile.

```
A100 80GB   81,920 MiB  =  80.0 GiB
H100 80GB   81,559 MiB  =  79.6 GiB
A100 40GB   40,536 MiB  =  39.6 GiB
```

**③ What is consumed before a tensor is allocated**

| Consumer | Size | Notes |
|---|---|---|
| CUDA context | 300–600 MB | Per process; multiplies with multiple processes |
| cuDNN / cuBLAS workspace | Hundreds of MB to several GB | Varies with kernel selection |
| NCCL buffers | Hundreds of MB | Multi-GPU only |
| Allocator fragmentation | 5–10% | Worse with variable sequence lengths |

ECC costs nothing visible on HBM parts (A100, H100, H200, B200 — on-die ECC). GDDR parts such as L40S and RTX A6000 lose 1 in 16 (6.25%) when it is on: 48 GB becomes roughly 45 GB.

**Sizing ceiling = nameplate × 0.90 to 0.93.** For an H100 80GB, design against 72–74 GB. This is why a 70B in FP8 — 70 GB of weights — "fits in 80 GB" on paper and fails to start in practice.

<div class="note" markdown="1">
**Measured here.** `nvidia-smi` on Runpod Secure Cloud Pods, 2026-11-07 ([cluster lab 01]({{ '/cluster/' | relative_url }})): A100-SXM4-80GB **81,920 MiB**, RTX 4090 **24,564 MiB**.
</div>

### Interconnect

| Path | Bandwidth | Notes |
|---|---|---|
| PCIe 4.0 x16 | 32 GB/s | Older servers |
| PCIe 5.0 x16 | 64 GB/s | Current |
| NVLink 4 (Hopper) | 900 GB/s | GPU to GPU, direct |
| NVLink 5 (Blackwell) | 1.8 TB/s | |
| NVSwitch | Full mesh in node | DGX / HGX |
| InfiniBand NDR | 400 Gb/s = 50 GB/s | Between nodes |
| RoCE v2 | Ethernet-based | Cheaper, harder to tune |

NCCL handles the collectives — AllReduce, AllGather, ReduceScatter, Broadcast. Data-parallel training does a gradient AllReduce every step, and the volume scales with parameter count: 14 GB per step for a 7B model in FP16. That is why PCIe at 64 GB/s cannot carry it.

FP32 TFLOPS tells you almost nothing about an LLM workload. Three numbers matter: dense tensor-core throughput at the precision you will actually run, HBM capacity, and HBM bandwidth. For training it is tensor-core throughput and NVLink. For inference it is capacity and bandwidth first — decode is bandwidth bound, so an L40S with respectable FP8 numbers still loses to an A100 on single-model inference: GDDR6 at 864 GB/s.

<div class="note" markdown="1">
**Measured here.** Two GPUs, one Pod, the same 101M-parameter DDP job ([cluster lab 01]({{ '/cluster/' | relative_url }}), 2026-11-07): RTX 4090 pair over PCIe across NUMA nodes (`SYS`), NCCL through host memory — all-reduce **15.6 GB/s**, two cards trained **2.4× slower** than one. A100 SXM pair over `NV12` — **201 GB/s**, 91% scaling. Topology details in [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}).
</div>

## Precision
{: #precision }

Changing nothing but precision moves throughput by 15× on the same silicon — and the real reason to go lower is more often memory than speed.

| Format | Bits | Per param | Where it is used |
|---|---|---|---|
| FP32 | 32 | 4 B | Optimiser master weights; rarely the compute path |
| TF32 | 19 (stored as 32) | 4 B | Ampere+ accelerates FP32 matmul with it — when allowed |
| FP16 | 16 | 2 B | Narrow exponent range — needs loss scaling |
| BF16 | 16 | 2 B | FP32 exponent range. The current training default |
| FP8 (E4M3 / E5M2) | 8 | 1 B | Hopper onward; becoming the inference standard |
| INT8 | 8 | 1 B | Post-training quantisation (SmoothQuant, AWQ) |
| NF4 / INT4 | 4 | 0.5 B | QLoRA. Quality degradation becomes visible here |
| FP4 / FP6 | 4 / 6 | 0.5 / 0.75 B | New in Blackwell |

**Same H100 SXM, different precision**

| Precision | Dense TFLOPS | vs FP32 |
|---|---|---|
| FP64 | 34 | 0.5× |
| FP32 (CUDA cores) | 67 | 1× |
| TF32 (tensor cores) | 495 | 7.4× |
| FP16 / BF16 | 989 | 14.8× |
| FP8 | 1,979 | 29.5× |

### Dense and sparse — one word, two meanings

**In throughput figures**, "dense" means without 2:4 structured sparsity. From Ampere on, tensor cores can skip zeros when weights are grouped in fours with at most two non-zero — twice the matmul in the same time, which is why spec sheets double (H100 FP8: 1,979 dense, 3,958 sparse). Collecting it needs the model pruned to the pattern, retrained, and run through cuSPARSELt or TensorRT; production LLMs rarely do it, and decode is bandwidth bound anyway. Compare specs on dense figures. "H100 does four petaflops" is almost always FP8 sparse.

**Next to a model name**, "dense" means not a mixture of experts: every token passes through every parameter (Llama 3 70B), whereas an MoE routes each token to its top-k experts (Mixtral 8×7B, DeepSeek-V3).

### Tensor core generations

| Gen | Architecture | What it added |
|---|---|---|
| 1st | Volta (V100) | FP16 |
| 2nd | Turing (T4) | INT8, INT4 |
| 3rd | Ampere (A100) | TF32, BF16, structured sparsity |
| 4th | Hopper (H100/H200) | FP8, Transformer Engine, async WGMMA |
| 4th | Ada (L40S, RTX 40) | FP8 — but the FP32-accumulate path is rate-limited |
| 5th | Blackwell (B200/B300, RTX PRO 6000) | FP4/FP6, 2nd-generation Transformer Engine |

Transformer Engine picks FP8 or BF16 per layer and per tensor at runtime and manages the scaling factors; FP8 training is practical because of it.

<div class="warn" markdown="1">
**How tensor cores get left idle.** They are not switched on; they engage when conditions are met and silently fall back otherwise. Training in pure FP32 gives 67 TFLOPS instead of 989 on an H100. With `allow_tf32 = False` — PyTorch's default for matmul — even FP32 matmul skips them. Hidden dimensions that are not multiples of 8 or 16 pick a slower kernel (hence vocabularies padded from 32,000 to 32,768). Hand-written kernels that never go through cuBLAS or CUTLASS never reach them.
</div>

<div class="note" markdown="1">
**Measured here.** The cluster lab's model runs plain FP32 with TF32 off. On one GPU, an RTX 4090 trained at **39,453** samples/s and an A100 SXM at **23,132** — the A100 lost because its tensor cores sat idle and the 4090 has more FP32 CUDA-core throughput. The A100's case is BF16/TF32 and the link, not FP32.
</div>

Lowering precision is more often about memory than speed: decode is bandwidth bound, so halving the bytes per weight nearly doubles token rate and frees room for KV cache. Below 8 bits quality loss starts to show, so check 4-bit on your own evaluation data before shipping it.

## Sizing formulas
{: #sizing }

With four formulas you can meet "what does a 7B need?" by asking the right conditions back and then producing numbers.

```
① Training memory = 16N bytes (FP16 + AdamW) · 10N with 8-bit Adam · LoRA is 2N + α
② Training FLOPs  = 6 × params × tokens     (forward 2N + backward 4N)
   Inference FLOPs = 2 × params × tokens
③ KV cache per token = 2 × layers × KV heads × head_dim × bytes per element
④ Decode ceiling = HBM bandwidth ÷ model bytes      (single stream, tok/s)
```

The same 7B spans 8 GB to over 110 GB depending on method, so the first questions are always: full fine-tune or PEFT, how far can precision drop, and what context length will it finally serve.

### ① Where training memory goes

| Component | Bytes | At 7B | Why it exists |
|---|---|---|---|
| FP16 weights | 2N | 14 GB | Forward and backward compute |
| FP16 gradients | 2N | 14 GB | Backward pass output |
| FP32 master weights | 4N | 28 GB | Update without precision loss |
| Adam first moment m | 4N | 28 GB | Optimiser state |
| Adam second moment v | 4N | 28 GB | Optimiser state |
| **Subtotal** | **16N** | **112 GB** | Plus activations |

A full fine-tune of 7B will not fit on one 80 GB card: two cards with ZeRO-3 or FSDP is the floor, four is realistic with activation headroom.

AdamW keeps two pieces of history for every parameter — **m**, a running mean of recent gradients, and **v**, their variance — both in FP32. That is 8 bytes per parameter, which is why 84 of the 112 GB is optimiser-related. **8-bit Adam** (bitsandbytes) stores m and v in 8 bits: those 56 GB become 14 GB and the total drops to about 70 GB, with small enough quality loss that it is routinely on.

| Technique | Effect | Cost |
|---|---|---|
| 8-bit Adam | Optimiser 8N → 2N; total 16N → 10N | Negligible |
| Gradient checkpointing | Large drop in activation memory | ~30% more compute |
| ZeRO-1 / -2 / -3, FSDP | Shards optimiser, then gradients, then parameters | Communication grows per stage |
| LoRA | Trainable surface drops to 0.1–1% | Limited expressiveness |
| QLoRA NF4 | 4-bit frozen base | Slower training |
| CPU / NVMe offload | Solves memory | Collapses throughput — last resort |

### ③ KV cache — the inference memory problem

| Model | Attention shape | Per token | 32k context, 1 request |
|---|---|---|---|
| Llama-2-7B | MHA · 32 layers · 32 KV heads · head_dim 128 | 512 KB | 16 GB |
| Llama-3-8B | GQA · 32 layers · 8 KV heads · head_dim 128 | 128 KB | 4 GB |
| Llama-3-70B | GQA · 80 layers · 8 KV heads · head_dim 128 | 320 KB | 10 GB |

GQA buys a 4× reduction, which is why every recent model uses GQA or MQA; an FP8 KV cache halves it again.

<div class="note" markdown="1">
**Measured here.** The inference sweep ([FINDINGS](https://github.com/litkhai/runpod-hols/blob/main/inference-characterization/FINDINGS.md)) ran one vLLM image on nine GPU types. vLLM's preemption counter — requests evicted because the KV cache filled up — rose **only on the three GPUs with the smallest KV cache**: RTX 4090, L4 and L40 (C6). On A100, H100 and H200, whose KV cache holds over a million tokens, 97–100% of prompt tokens were served from the prefix cache (C21).
</div>

### The five workloads

| Workload | At 7B | What changes | When to use it |
|---|---|---|---|
| Inference | 14 GB + KV | Nothing — used as-is | Running the service |
| Full FT (AdamW) | 112 GB | All parameters | When the domain vocabulary itself differs |
| Full FT (8-bit Adam) | ~70 GB | All parameters, lighter optimiser | Same, when GPUs are short |
| LoRA | ~19 GB | 0.1–1% of parameters | Where most requirements end |
| QLoRA | ~9 GB | 0.1–1%, base also compressed | Experimenting on a single card |

**LoRA** freezes the original weights and trains two small matrices alongside them:

```
standard   y = W · x            train all of W (4096×4096 = 16.8M params)
LoRA       y = W · x + B·A·x    W frozen; train only A (4096×16) and B (16×4096)
                                → 131K params, 0.8% of the original
```

The 16 in the middle is the **rank**; 16 to 64 is the usual range. Memory collapses because the frozen base needs no gradients and no optimiser state, and the result is one adapter file of tens of MB. **QLoRA** also compresses the frozen base to 4-bit NF4, dequantised to FP16 only during each computation: the base drops from 14 GB to 3.5 GB, putting a 7B fine-tune on one 24 GB card, at the cost of speed.

<div class="calc" data-calc="vram" markdown="0">
  <div class="calc-hd"><b>VRAM sizing</b><span>CALCULATOR 01</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>Params (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>Workload</label><select data-f="mode"><option value="inf">Inference</option><option value="lora">LoRA</option><option value="qlora">QLoRA (4-bit)</option><option value="full">Full FT (AdamW)</option><option value="full8">Full FT (8-bit Adam)</option></select></div>
      <div><label>Weight precision</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1">FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>Layers</label><input data-f="L" type="number" value="32" min="1"></div>
      <div><label>KV heads</label><input data-f="kh" type="number" value="8" min="1"></div>
      <div><label>head_dim</label><input data-f="hd" type="number" value="128" min="8"></div>
      <div><label>Context length</label><input data-f="ctx" type="number" value="8192" min="128" step="512"></div>
      <div><label>Concurrent requests</label><input data-f="bs" type="number" value="8" min="1"></div>
      <div><label>KV precision</label><select data-f="kp"><option value="2">FP16</option><option value="1">FP8</option></select></div>
    </div>
    <div class="calc-out">
      <div><span>Weights (GB)</span><b data-o="w">–</b></div>
      <div><span>Grads + optimiser (GB)</span><b data-o="o">–</b></div>
      <div><span>KV cache (GB)</span><b data-o="k">–</b></div>
      <div><span>Activations + overhead (GB)</span><b data-o="a">–</b></div>
      <div class="hi"><span>Total (GB)</span><b data-o="t">–</b></div>
    </div>
    <div class="calc-bar" data-o="bar"><i></i><i></i><i></i><i></i></div>
    <div class="calc-key"><span><s class="k1"></s>Weights</span><span><s class="k2"></s>Grads + optimiser</span><span><s class="k3"></s>KV cache</span><span><s class="k4"></s>Activations</span></div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ④ The decode ceiling

Single-stream token rate is set by how many times per second you can read the weights, because every token pulls the whole model out of HBM once.

| Configuration | Model bytes | Ceiling | Realistic (~70%) |
|---|---|---|---|
| 7B FP16 on H100 SXM (3.35 TB/s) | 14 GB | 239 tok/s | ~167 |
| 7B FP8 on H100 SXM | 7 GB | 479 tok/s | ~335 |
| 70B FP16 on 2×H100 (6.7 TB/s) | 140 GB | 48 tok/s | ~34 |

<div class="calc" data-calc="decode" markdown="0">
  <div class="calc-hd"><b>Decode throughput and inference cost</b><span>CALCULATOR 02</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>GPU (Runpod Secure, 2026-11-07)</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU count</label><input data-f="n" type="number" value="1" min="1" max="8"></div>
      <div><label>Params (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>Weight precision</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1" selected>FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>Concurrent requests</label><input data-f="b" type="number" value="32" min="1"></div>
      <div><label>Average context</label><input data-f="ctx" type="number" value="4096" min="128" step="512"></div>
      <div><label>KV per token (KB)</label><input data-f="kv" type="number" value="128" min="1"></div>
    </div>
    <div class="calc-out">
      <div><span>Single stream (tok/s)</span><b data-o="s">–</b></div>
      <div><span>Bandwidth limit (tok/s)</span><b data-o="bw">–</b></div>
      <div><span>Compute limit (tok/s)</span><b data-o="cl">–</b></div>
      <div class="hi"><span>Total throughput (tok/s)</span><b data-o="t">–</b></div>
      <div class="hi"><span>Per 1M output tokens (USD)</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ② Training time and cost

**MFU** (Model FLOPs Utilization) is achieved FLOPS over peak. Well-tuned large-scale training lands at 40–50%; under 30% means something is wrong.

<div class="calc" data-calc="train" markdown="0">
  <div class="calc-hd"><b>Training time and cost</b><span>CALCULATOR 03</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>Params (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>Tokens (B)</label><input data-f="tok" type="number" value="1" min="0.001" step="0.1"></div>
      <div><label>Method</label><select data-f="m"><option value="6">Full FT (6N)</option><option value="5">LoRA (~5N)</option></select></div>
      <div><label>GPU (Runpod Secure, 2026-11-07)</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU count</label><input data-f="n" type="number" value="8" min="1"></div>
      <div><label>MFU (%)</label><input data-f="mfu" type="number" value="40" min="5" max="70"></div>
    </div>
    <div class="calc-out">
      <div><span>Total compute (EFLOPs)</span><b data-o="f">–</b></div>
      <div><span>GPU-hours</span><b data-o="gh">–</b></div>
      <div><span>Wall clock (hours)</span><b data-o="w">–</b></div>
      <div class="hi"><span>Estimated cost (USD)</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

<div class="note" markdown="1">
**About these calculators.** First-order approximations: real numbers move with framework, batch composition, sequence-length distribution and scheduler. The point is which variable dominates, not an exact figure. FLOPS are dense and Blackwell figures approximate; prices are Runpod Secure Cloud on-demand per GPU-hour, read from the catalogue on 2026-11-07.
</div>

## The transformer, briefly
{: #transformer }

One decoder layer, end to end — what runs on tensor cores and what lands on CUDA cores:

```
x                                        input [batch, seq, 4096]
h  = RMSNorm(x)                          CUDA
q  = h @ W_q ;  k = h @ W_k ;  v = h @ W_v   TENSOR  QKV projection
q, k = RoPE(q, k)                        CUDA
k, v = KVCache.append(k, v)              CUDA    memory movement
s  = q @ kᵀ / √head_dim                  TENSOR  attention scores
s  = causal_mask(s) ; p = softmax(s)     CUDA
o  = p @ v                               TENSOR  weighted sum
o  = o @ W_o                             TENSOR
x  = x + o                               CUDA    residual
h  = RMSNorm(x)                          CUDA
g  = h @ W_gate ;  u = h @ W_up          TENSOR  FFN
f  = SiLU(g) * u                         CUDA    activation
x  = x + (f @ W_down)                    TENSOR + CUDA
── after 32 repeats ──
logits = RMSNorm(x) @ W_lm_head          TENSOR  32,000 vocabulary scores
token  = sample(logits)                  CUDA
```

Essentially all FLOPs are GEMMs on tensor cores. Everything else is memory bound:

| Operation | Bytes moved per token (7B) | Intensity | Character |
|---|---|---|---|
| RMSNorm | ~1.6 MB | < 1 | Reduction, memory bound |
| RoPE | ~0.7 MB | ~2 | Memory bound |
| Activation (SwiGLU) | ~2.1 MB | ~1 | Largest elementwise tensor |
| Residual | ~1.6 MB | 0.17 | Extreme memory bound — 1,700× below H100's crossover |
| Softmax | Scales with context | < 1 | Special-function unit plus reduction |
| KV indexing | Scales with batch × context | ≈ 0 | Pure data movement |
| Sampling | batch × vocabulary | Sort | Branch heavy |

Their share of wall clock depends on the regime. In batch-1 decode, reading the weights dominates and the real cost is kernel-launch overhead — a dozen kernels per layer × 32 layers × every token — which is what CUDA Graph removes. In prefill and training, activations scale with batch × sequence and this work reaches 30–40% of wall clock, where kernel fusion is the biggest lever. FlashAttention is the same idea for attention: the [n×n] score matrix never reaches HBM, so attention memory goes from O(n²) to O(n).

Tokens are BPE subwords. Scripts the vocabulary under-covers — Korean, Chinese and Japanese among them in many models — can cost two to three times the tokens for the same content, which hits both price and context limit.

## Training
{: #training }

There is one objective: predict the next token. Loss = −log P(target token); perplexity = exp(loss), roughly "how many options the model is torn between". The text is its own label — shift it by one and you have input and target — which is what made internet-scale data usable.

One step: **forward** (batch through, logits and loss; tensor cores), **backward** (gradient of the loss for every parameter, about twice the forward compute), **optimiser update** (AdamW, hence two extra states per parameter). The 16N memory and 6N compute of the sizing formulas come straight from this; inference has only the forward pass, hence 2N and 2N.

| Stage | What it does | Data | Cost scale |
|---|---|---|---|
| ① Pre-training | Next-token prediction only. Language, knowledge and reasoning form here | Trillions of tokens | Thousands of GPUs, months |
| ② Supervised fine-tuning (SFT) | Teaches the question-answer format, not new capability | Tens to hundreds of thousands of dialogues | A few to a few dozen GPUs, days |
| ③ Alignment (RLHF / DPO) | Steers toward preferred responses | Preference pairs | Comparable to ② or more |

Knowledge enters in ①; ② and ③ shape how it is surfaced. That is why "fine-tune to inject our internal knowledge" usually fails and retrieval (RAG) is the right tool; fine-tuning is for format, register and domain vocabulary.

| Strategy | What it splits | Communication | When |
|---|---|---|---|
| DP — data parallel | The batch | Gradient AllReduce per step | Model fits on one GPU |
| ZeRO / FSDP | Stage 1 optimiser → 2 + gradients → 3 + parameters | Grows with each stage | Model does not fit — first choice |
| TP — tensor parallel | Matrices inside a layer | AllReduce every layer — very heavy | Inside the NVLink domain only |
| PP — pipeline parallel | Blocks of layers | Only at stage boundaries — light | Scaling across nodes |
| SP — sequence parallel | Sequence length | Moderate | Long-context training |
| EP — expert parallel | MoE experts | All-to-All | MoE models |

The working combination: TP within the node, PP or FSDP across nodes. Push TP past the node boundary and throughput collapses even on InfiniBand — the numbers are in [GPU Topology]({{ '/readings/gpu-topology/#in-numbers' | relative_url }}).

**MoE** routes each token to its top-k experts. Memory scales with total parameters, compute with active ones: a 200B-total / 20B-active model computes like a 20B but still needs 200B worth of VRAM. "It is MoE, so it is cheap" is only half true.

<div class="note" markdown="1">
**Measured here.** Data parallelism on one Pod with two GPUs ([cluster lab 01]({{ '/cluster/' | relative_url }})): about 400 MB of FP32 gradients per step. Over NVLink that all-reduce took ~2 ms and the pair scaled at 0.91; over PCIe with host staging it took ~26 ms against 6.5 ms of compute, and the pair scaled at 0.21.
</div>

## Inference and serving
{: #inference }

Training cost is one-off. Inference cost runs as long as the product lives, and it sets unit economics.

| | Prefill | Decode |
|---|---|---|
| Processing | Whole prompt in parallel | One token at a time |
| Bottleneck | Compute bound | Memory-bandwidth bound |
| Metric | TTFT — time to first token | TPOT / ITL — inter-token latency |
| Levers | Chunked prefill, prefix caching | Quantisation, batching, speculative decoding |
| 7B feel | 1,000-token prompt ≈ 35 ms | Per token: 0.035 ms compute, 4.2 ms memory |

0.035 ms of arithmetic against 4.2 ms of reading — a factor of 120. That is why batching is not optional: many requests must share one weight read for the GPU to earn its cost. Some long-context services now put prefill and decode on separate GPU pools (disaggregated serving), because their characters interfere.

| Technique | Mechanism | Effect |
|---|---|---|
| Continuous batching | Admit a new request the moment a slot frees | 2–5× throughput |
| PagedAttention | Manage the KV cache in blocks, like OS paging | Recovers 60–80% of memory lost to fragmentation |
| Prefix caching | Reuse the KV of a shared prompt prefix | Large TTFT cut for RAG and agents |
| Speculative decoding | A small draft model proposes; the large one verifies in one pass | 2–3×, output identical |
| FlashAttention | Tiled fused kernel; the score matrix never touches HBM | Memory O(n²)→O(n), 2–4× |
| Quantisation | FP8/INT8 weights (AWQ, GPTQ), FP8 KV cache | Half the memory, more speed |
| Chunked prefill | Split long prompts and interleave with decode | Long requests stop blocking short ones |

A **kernel** is one function launched on the GPU; each launch costs microseconds and, more importantly, a round trip through HBM. Fusing RMSNorm and a residual into one kernel saves a full write and read — worth 2–3× on bandwidth-bound work. `torch.compile` automates it; OpenAI's Triton is the language those kernels are written in (not to be confused with NVIDIA's Triton Inference Server, a serving front end).

**Three metrics:** TTFT (perceived responsiveness), TPOT/ITL (reading speed; 20–30 tok/s is enough for a person), throughput (unit cost). TTFT and throughput trade against each other — a bigger batch raises both throughput and individual latency — so set separate targets per workload.

| Stack | Character | When |
|---|---|---|
| vLLM | Origin of PagedAttention, OpenAI-compatible API, continuous batching by default | The default choice |
| SGLang | RadixAttention prefix caching, structured output | Agent and RAG workloads |
| TensorRT-LLM | NVIDIA's own; highest performance, per-model engine build | Fixed model, maximum performance |
| Triton Inference Server | Multi-model, multi-framework front end | Many models behind one endpoint |
| Ollama / llama.cpp | GGUF, CPU and edge | Local, demos |

A reasoning model multiplies output tokens, and decode throughput is the product cost — so model cost on expected tokens per request, not on price per token.

<div class="note" markdown="1">
**Measured here.** vLLM is what these labs serve with ([Serverless lab 03]({{ '/serverless/' | relative_url }}), the inference sweep). On cold Serverless workers, vLLM's CUDA-graph capture alone took 9 s on one host and 62–73 s on others for the same image and model (C19) — the launch-overhead fix is itself paid at every cold start.
</div>

## Operations, as they apply on Runpod
{: #operations }

**The version matrix.** Host driver → CUDA toolkit → container. The CUDA inside the container must be at or below what the host driver supports; on Runpod you pick the image, the host picks the driver.

<div class="note" markdown="1">
**Measured here.** A 16 GB/24 GB Serverless pool handed out an RTX PRO 6000 Blackwell MIG slice (sm_120); a CUDA 12.6 PyTorch image stops at sm_90 and the worker died with `no kernel image is available` ([Serverless lab 02]({{ '/serverless/' | relative_url }})). The console now splits GPUs into *Previous* and *Latest generation*, the latter requiring a CUDA 12.8+ image.
</div>

**What to watch.** Not `utilization.gpu` but SM occupancy and memory-bandwidth utilisation. `nvidia-smi` GPU-Util is the fraction of time a kernel was resident, so a kernel using 1% of the device still reads 100%.

<div class="note" markdown="1">
**Measured here.** During the 2× RTX 4090 run the console's Telemetry showed both GPUs at **100%** while the pair trained at a fifth of its ideal speed — the kernels were NCCL waiting on PCIe ([screenshot]({{ '/cluster/' | relative_url }})).
</div>

| Symptom | Cause and fix |
|---|---|
| CUDA OOM with memory apparently free | Fragmentation → `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` |
| Sudden performance drop | Thermal or power throttling → `nvidia-smi -q -d PERFORMANCE` |
| Xid errors | Kernel log: 13/31 application fault, 48/63/64 ECC, 79 GPU fell off the bus |
| NCCL timeout | Topology or interface → `NCCL_DEBUG=INFO`, `nvidia-smi topo -m`; on Instant Clusters set `NCCL_SOCKET_IFNAME=ens1` |
| Multi-minute cold start | Pulling model weights → keep weights out of the image (below) |
| Training MFU under 30% | Data loader, communication, or batch too small → profile per phase |

**Cold start.** Weights baked into a tens-of-GB image take minutes to pull; keep them out of the image and load from a cache or volume. `safetensors` with mmap pages in only the tensors needed. On Serverless the platform offers three of these levers: the endpoint's **Model** field caches Hugging Face weights on the host, a network volume holds them across workers, and FlashBoot keeps a stopped worker's state for a fast restart.

<div class="note" markdown="1">
**Measured here.** Every logged cold start of the inference sweep's vLLM endpoint created a new container and downloaded 14.19 GiB of weights again, FlashBoot on or off (C17). With FlashBoot on and a 5 s idle timeout, requests 15 s and 30 s apart reused the same container (`delayTime` 1.9 and 1.3 s); from a 60 s gap on, each got a new one at 97–104 s (C22). With FlashBoot set to Standard on 2026-11-07, gaps of 30–120 s reused the container (1.1–1.2 s) — the window had grown (C34). Weights on a network volume were slower still — see [Storage]({{ '/readings/storage/#model-weights' | relative_url }}) (C35). See [Serverless]({{ '/serverless/' | relative_url }}) for the Model field and the cold-start phases.
</div>

## Cost
{: #cost }

```
inference cost per 1M output tokens = (hourly price ÷ 3600) ÷ throughput (tok/s) × 1,000,000
```

7B in FP8 on one H100 SXM at 3,000 tok/s with continuous batching: 1,000,000 ÷ 3,000 = 333 s = 0.093 h, × USD 3.99 = **about USD 0.37 per 1M output tokens**. Set that against API pricing and the self-hosting break-even falls out.

**Effective cost = hourly price ÷ actual utilisation.** A USD 3.99 GPU used 20% of the time effectively costs about USD 20 an hour. That is the case for Serverless and autoscaling, and why cold start is a headline metric.

Runpod Pod prices per GPU-hour, read from the catalogue on 2026-11-07:

| GPU | VRAM | Secure Cloud | Community Cloud |
|---|---|---|---|
| L4 | 24 GB | 0.59 | 0.44 |
| RTX 4090 | 24 GB | 0.89 | 0.34 |
| L40S | 48 GB | 1.09 | 0.79 |
| A100 SXM | 80 GB | 1.79 | 1.39 |
| H100 PCIe | 80 GB | 2.89 | 1.99 |
| RTX PRO 6000 | 96 GB | 2.49 | 1.69 |
| H100 SXM | 80 GB | 3.99 | 2.69 |
| H200 SXM | 141 GB | 5.29 | 3.59 |
| B200 | 180 GB | 7.99 | 5.98 |
| B300 | 288 GB | 8.99 | 6.94 |

| Shape | Price | Risk |
|---|---|---|
| On demand | Baseline | None |
| Spot / community | Cheaper — 22–62% on the table above | Preemption or weaker guarantees; checkpointing mandatory |
| Reserved / committed | 30–50% cheaper | 1–3 year lock-in, generation risk |
| Self-built | Lowest in the long run | Space, power, cooling, depreciation, headcount |

An 8×H100 server runs roughly USD 250–300k; over three years that is USD 1.2–1.5 per GPU-hour before power, space and people. Self-hosting wins only if you can hold 60%+ utilisation for three years — most teams cannot. And with NVIDIA on a yearly architecture cadence, build against CUDA, CUTLASS and Triton rather than hard-coding precision and memory assumptions.

<div class="note" markdown="1">
**Measured here.** Community Cloud is cheaper, but a Community RTX 4090 Pod created with a public IP never got one, or an SSH port, within 15 minutes (C7); the [cluster]({{ '/cluster/' | relative_url }}) and [Pod]({{ '/pod/' | relative_url }}) labs run on Secure Cloud.
</div>

## Glossary
{: #glossary }

| Term | Area | Meaning |
|---|---|---|
| AllReduce | Distributed | NCCL collective that sums across all GPUs and distributes the result; every step of data-parallel training |
| AWQ / GPTQ | Inference | Post-training weight quantisation preserving salient channels using activation statistics |
| BF16 | Precision | 16 bits with FP32 exponent range; the training default |
| BPE | Tokenizer | Byte-Pair Encoding; merges frequent pairs into a subword vocabulary |
| busbw / algbw | Diagnostics | nccl-tests output; judge link utilisation by busbw |
| Continuous batching | Inference | Admit a new request the moment a slot frees; 2–5× throughput |
| CUDA core | Hardware | Scalar FMA unit; general purpose, slow at matrix multiply |
| CUDA Graph | Optimisation | Captures a kernel launch sequence for replay; removes launch overhead in batch-1 decode |
| DCGM | Ops | Data Center GPU Manager; exports GPU telemetry |
| FlashAttention | Kernels | Attention as a tiled fused kernel; the [n×n] matrix never reaches HBM |
| FSDP | Distributed | Fully Sharded Data Parallel; PyTorch-native, like ZeRO-3 |
| GEMM | Compute | General Matrix Multiply; the only form a tensor core executes |
| GQA / MQA | Architecture | Grouped- / Multi-Query Attention; fewer KV heads, 4–8× smaller cache |
| Gradient checkpointing | Training | Recompute activations in backward instead of storing them; memory down, compute +30% |
| HBM | Hardware | High Bandwidth Memory — the GPU's VRAM; 2–8 TB/s |
| KV cache | Inference | Stored K and V of earlier tokens; the dominant term in inference memory |
| LoRA / QLoRA | Training | Low-rank adapters on a frozen base; QLoRA adds a 4-bit NF4 base |
| MBU / MFU | Metrics | Achieved over theoretical bandwidth / FLOPS; 40–50% MFU is normal at scale |
| MIG / MPS | Ops | Hardware partitioning / process sharing — see [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) |
| MoE | Architecture | Mixture of Experts; memory scales with total parameters, compute with active |
| NCCL | Distributed | NVIDIA Collective Communications Library |
| NVLink domain | Hardware | GPUs in NVSwitch full mesh; the ceiling on TP degree |
| PagedAttention | Inference | Block-based KV cache management; the core of vLLM |
| Prefill / Decode | Inference | Parallel prompt processing vs one-token-at-a-time generation; opposite bottlenecks |
| Roofline | Performance | Classifies work as compute or memory bound by arithmetic intensity |
| Speculative decoding | Inference | Draft proposes, target verifies in one pass; 2–3×, output identical |
| Tensor core | Hardware | Matrix-multiply unit; low-precision inputs, FP32 accumulate |
| TF32 | Precision | 19-bit format letting Ampere+ tensor cores run FP32 matmul — off by default in PyTorch matmul |
| TTFT / TPOT / ITL | Metrics | Time to first token / per output token / between tokens |
| vLLM | Serving | PagedAttention plus continuous batching; the de facto default engine |
| ZeRO | Distributed | DeepSpeed sharding: stage 1 optimiser, 2 gradients, 3 parameters |
| 2:4 sparsity | Precision | Two of every four weights zero; marketing FLOPS usually assume it |

</div>

<div class="lang" data-lang="ko" markdown="1">

## 한국어

GPU 는 메모리 계층과 두 종류의 연산 유닛으로 이해하면 가장 다루기 쉽습니다. 이후의 모든 산정과 최적화 논의가 이 한 체계 안에서 설명됩니다. 여기에 공식 네 개면 "이 모델에 무엇이 필요한가" 라는 질문 대부분에 답할 수 있고, 계산기 세 개로 숫자를 외우는 대신 직접 계산해 볼 수 있습니다.

개념과 사양 수치는 일반적인 내용이며 벤더 자료를 기준으로 합니다. **여기서 측정한 것** 상자는 이 실습들이 Runpod 에서 실제로 실행한 결과로, 일반 규칙이 실제 머신 한 대와 만나는 지점입니다. 전체에 걸쳐 학습과 추론을 분리해서 보세요. 메모리도, 병목도, GPU 선택 기준도 둘이 정반대입니다.

## GPU 하드웨어
{: #hardware-ko }

### 연산 유닛 두 종류

| | CUDA 코어 | 텐서 코어 |
|---|---|---|
| 단위 연산 | 스칼라 FMA, a×b+c | 행렬 블록 곱셈-누적, D = A×B + C |
| 1명령당 MAC | 1 | 수백 ~ 수천 |
| H100 SXM 탑재 개수 | 16,896 | 528 |
| H100 성능 | 67 TFLOPS (FP32) | 989 (FP16) / 1,979 (FP8) |
| 가능한 연산 | 무엇이든 — 분기, 초월함수 포함 | 행렬곱만 |
| 접근 방법 | 일반 CUDA C++ 산술 | cuBLAS / CUTLASS / Triton 경유 |

개수는 32배 적은데 성능은 15–30배 높습니다. 같은 MAC 을 CUDA 코어로 하면 매번 명령 인출·디코드·레지스터 접근 오버헤드가 붙지만, 텐서 코어는 명령 하나로 그 오버헤드를 수천 연산에 걸쳐 상각합니다.

<div class="warn" markdown="1">
**"텐서 코어가 더 좋다" 는 틀린 요약입니다.** 둘은 경쟁하지 않습니다. Softmax, RMSNorm, RoPE, 활성화, 잔차 덧셈, KV 캐시 인덱싱, 샘플링은 텐서 코어에서 돌 수 없고 전부 CUDA 코어 몫입니다. 그리고 텐서 코어가 빨라질수록 이 나머지가 병목이 됩니다. 실무 최적화의 상당 부분은 GEMM 자체가 아니라 GEMM 사이의 틈을 없애는 일입니다.
</div>

### 메모리 계층

```
레지스터             수십 KB/SM        수십 TB/s
L1 / shared memory   ~256 KB/SM        ~20 TB/s
L2 캐시              50 MB (H100)      ~5 TB/s
HBM (VRAM)           80–288 GB         2–8 TB/s     ← 여기가 LLM 의 병목
호스트 RAM           수 TB             ~64 GB/s (PCIe 5.0 x16)
```

### Roofline — 어느 쪽에 걸렸는지 판별

연산 강도(arithmetic intensity) = FLOP 수 ÷ 이동 바이트 수. H100 SXM 의 손익분기는 989 TFLOPS ÷ 3.35 TB/s ≈ **295 FLOP/byte** 입니다. 이보다 낮으면 메모리 바운드, 높으면 계산 바운드입니다.

- LLM 디코딩(배치 1): 연산 강도 약 2 — H100 연산 능력의 1% 미만입니다. 배칭이 처리량을 몇 배로 올리는 이유입니다.
- 긴 프롬프트의 LLM 프리필: 수백 — 계산 바운드이며, 여기서 텐서 코어가 제값을 합니다.
- RMSNorm, 잔차 덧셈: 1–2 — 완전한 메모리 바운드이며, 커널 융합이 존재하는 이유입니다.

### 현행 라인업 (2026.09 기준 사양)

| GPU | 메모리 | 대역폭 | NVLink | TDP | 주 용도 |
|---|---|---|---|---|---|
| L4 | 24 GB | 0.30 TB/s | — | 72 W | 경량 추론, 비디오 |
| RTX 4090 | 24 GB | 1.01 TB/s | — | 450 W | 개발, QLoRA |
| L40S | 48 GB | 0.86 TB/s | — | 350 W | 중형 추론 |
| A100 80GB SXM | 80 GB | 2.04 TB/s | 600 GB/s | 400 W | 가성비 학습 |
| H100 PCIe | 80 GB | 2.00 TB/s | 600 GB/s | 350 W | 범용 |
| H100 SXM | 80 GB | 3.35 TB/s | 900 GB/s | 700 W | 학습 표준 |
| RTX PRO 6000 | 96 GB | ~1.8 TB/s | — | 600 W | 워크스테이션 추론 |
| H200 SXM | 141 GB | 4.80 TB/s | 900 GB/s | 700 W | 롱컨텍스트 추론 |
| B200 | 180 GB | ~8 TB/s | 1.8 TB/s | ~1000 W | 현세대 학습 |
| B300 | 288 GB | ~8 TB/s | 1.8 TB/s | ~1400 W | 대형 모델 |
| GB200/GB300 NVL72 | 72 GPU 단일 도메인 | — | 랙 전체 | ~130 kW/랙 | 프론티어, 수랭 |

기억할 세 가지:

1. **SXM vs PCIe.** 3.35 TB/s 대 2.00 TB/s, 그리고 900 GB/s NVLink 대 카드 두 장짜리 브리지입니다. 다중 GPU 학습이면 SXM 이 아닌 한 통신이 병목이 됩니다.
2. **L40S 와 RTX 계열은 NVLink 가 없습니다.** 모델 병렬이 필요한 크기라면 후보에서 탈락이고, 한 장에 들어가는 모델용입니다.
3. **Blackwell 이후는 전력과 냉각이 실제 제약입니다.** Runpod 같은 클라우드에서는 이것이 내 문제가 아니라 가격과 수급으로 드러납니다 — 다만 최신 GPU 가 가장 구하기 어려운 이유가 이것입니다.

### 명판 용량과 실사용 용량

"H100 80GB" 에서 텐서에 실제로 쓸 수 있는 것은 80 GB 가 아닙니다. 차이가 세 단계에서 발생합니다.

**① 물리 용량 vs 제품 사양**

| GPU | 물리 구성 | 물리 합계 | 제품 사양 | 차이의 이유 |
|---|---|---|---|---|
| H100 SXM | HBM3 16GB × 6사이트, 5개 활성 | 96 GB | 80 GB | 수율 확보를 위해 1스택 비활성 |
| H200 SXM | HBM3e 24GB × 6 | 144 GB | 141 GB | 행 리던던시·내부 예약 (미공개) |
| B200 | HBM3e 8칩 (2스택) | 192 GB | 180–192 GB | SKU·제공사마다 다름 — Runpod 은 180 GB 로 표기 |

**② `nvidia-smi` 가 보고하는 값** — MiB 단위입니다. NVIDIA 의 "80GB" 는 사실상 80 GiB(십진 85.9 GB)이고, `torch.cuda.get_device_properties(0).total_memory` 는 바이트 단위이므로 1024³ 으로 나눠야 같은 숫자가 나옵니다.

```
A100 80GB   81,920 MiB  =  80.0 GiB
H100 80GB   81,559 MiB  =  79.6 GiB
A100 40GB   40,536 MiB  =  39.6 GiB
```

**③ 텐서를 할당하기 전에 빠지는 것**

| 차감 항목 | 크기 | 비고 |
|---|---|---|
| CUDA 컨텍스트 | 300–600 MB | 프로세스당. 멀티프로세스면 배수 |
| cuDNN / cuBLAS 워크스페이스 | 수백 MB ~ 수 GB | 커널 선택에 따라 변동 |
| NCCL 버퍼 | 수백 MB | 다중 GPU 일 때만 |
| 할당자 단편화 | 5–10% | 가변 길이 시퀀스에서 더 심함 |

HBM 계열(A100, H100, H200, B200 — 온다이 ECC)은 ECC 를 켜도 보이는 손실이 없습니다. L40S, RTX A6000 같은 GDDR 계열은 켜면 1/16(6.25%)이 사라져 48 GB 가 약 45 GB 가 됩니다.

**사이징 상한 = 명판 × 0.90 ~ 0.93.** H100 80GB 면 72–74 GB 를 상한으로 잡고 설계합니다. 70B FP8(가중치 70 GB)이 계산상 "80 GB 에 들어가는데" 실제로는 뜨지 않는 이유가 이것입니다.

<div class="note" markdown="1">
**여기서 측정한 것.** Runpod Secure Cloud Pod 의 `nvidia-smi`, 2026-11-07 ([클러스터 실습 01]({{ '/cluster/' | relative_url }})): A100-SXM4-80GB **81,920 MiB**, RTX 4090 **24,564 MiB**.
</div>

### 인터커넥트

| 경로 | 대역폭 | 비고 |
|---|---|---|
| PCIe 4.0 x16 | 32 GB/s | 구형 서버 |
| PCIe 5.0 x16 | 64 GB/s | 현행 |
| NVLink 4 (Hopper) | 900 GB/s | GPU ↔ GPU 직결 |
| NVLink 5 (Blackwell) | 1.8 TB/s | |
| NVSwitch | 노드 내 풀메시 | DGX / HGX |
| InfiniBand NDR | 400 Gb/s = 50 GB/s | 노드 간 |
| RoCE v2 | 이더넷 기반 | 저렴하나 튜닝 난도 높음 |

NCCL 이 집합 통신(AllReduce, AllGather, ReduceScatter, Broadcast)을 담당합니다. 데이터 병렬 학습은 매 스텝 그래디언트 AllReduce 를 하고, 통신량은 파라미터 수에 비례합니다 — 7B FP16 이면 스텝당 14 GB. 64 GB/s 의 PCIe 로는 감당할 수 없는 이유입니다.

FP32 TFLOPS 는 LLM 워크로드에 대해 거의 아무것도 알려주지 않습니다. 중요한 숫자는 세 가지입니다 — 실제로 돌릴 정밀도에서의 텐서 코어 dense 처리량, HBM 용량, HBM 대역폭. 학습이면 텐서 코어 성능과 NVLink 이고, 추론이면 용량과 대역폭이 먼저입니다. 디코딩은 대역폭 바운드라, FP8 성능이 괜찮은 L40S 도 GDDR6 864 GB/s 때문에 단일 모델 추론에서는 A100 보다 떨어집니다.

<div class="note" markdown="1">
**여기서 측정한 것.** GPU 두 장, Pod 하나, 같은 1억 1백만 파라미터 DDP 잡 ([클러스터 실습 01]({{ '/cluster/' | relative_url }}), 2026-11-07): RTX 4090 쌍은 NUMA 노드를 넘는 PCIe(`SYS`)로 연결되어 NCCL 이 호스트 메모리를 거쳤고 — all-reduce **15.6 GB/s**, 두 장이 한 장보다 **2.4배 느리게** 학습했습니다. A100 SXM 쌍은 `NV12` 로 — **201 GB/s**, 확장 효율 91% 였습니다. 토폴로지 상세는 [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) 에 있습니다.
</div>

## 정밀도
{: #precision-ko }

같은 칩에서 정밀도만 바꿔도 처리량이 15배 달라집니다 — 그리고 정밀도를 낮추는 진짜 이유는 속도보다 메모리인 경우가 더 많습니다.

| 형식 | 비트 | 파라미터당 | 용도 |
|---|---|---|---|
| FP32 | 32 | 4 B | 옵티마이저 마스터 가중치. 계산 경로에는 거의 안 씀 |
| TF32 | 19 (저장 32) | 4 B | 허용하면 Ampere+ 가 FP32 행렬곱을 이것으로 가속 |
| FP16 | 16 | 2 B | 지수 범위가 좁음 — loss scaling 필요 |
| BF16 | 16 | 2 B | FP32 와 같은 지수 범위. 현재 학습 기본값 |
| FP8 (E4M3 / E5M2) | 8 | 1 B | Hopper 부터. 추론 표준으로 정착 중 |
| INT8 | 8 | 1 B | 학습 후 양자화 (SmoothQuant, AWQ) |
| NF4 / INT4 | 4 | 0.5 B | QLoRA. 품질 저하가 보이기 시작하는 지점 |
| FP4 / FP6 | 4 / 6 | 0.5 / 0.75 B | Blackwell 신규 |

**같은 H100 SXM, 정밀도만 다르게**

| 정밀도 | dense TFLOPS | FP32 대비 |
|---|---|---|
| FP64 | 34 | 0.5× |
| FP32 (CUDA 코어) | 67 | 1× |
| TF32 (텐서 코어) | 495 | 7.4× |
| FP16 / BF16 | 989 | 14.8× |
| FP8 | 1,979 | 29.5× |

### Dense 와 sparse — 같은 단어, 두 가지 뜻

**처리량 수치에서** dense 는 2:4 구조적 희소성을 쓰지 않은 값입니다. Ampere 부터 텐서 코어는 가중치를 4개씩 묶어 그중 최대 2개만 0이 아니면 0인 자리를 건너뛸 수 있습니다 — 같은 시간에 두 배의 행렬곱을 처리하므로 스펙 수치가 정확히 두 배가 됩니다(H100 FP8: dense 1,979, sparse 3,958). 이를 실제로 받으려면 모델을 그 패턴으로 가지치기하고, 재학습하고, cuSPARSELt 나 TensorRT 로 돌려야 합니다. 프로덕션 LLM 에서는 드물고, 어차피 디코딩은 대역폭 바운드입니다. 스펙은 dense 로 통일해서 비교하세요. "H100 은 4 페타플롭스" 라는 문구는 거의 항상 FP8 sparse 기준입니다.

**모델 이름 옆에서** dense 는 MoE 가 아니라는 뜻입니다. 모든 토큰이 모든 파라미터를 통과하고(Llama 3 70B), MoE 는 토큰마다 상위 k개 전문가로 라우팅합니다(Mixtral 8×7B, DeepSeek-V3).

### 텐서 코어 세대

| 세대 | 아키텍처 | 추가된 것 |
|---|---|---|
| 1세대 | Volta (V100) | FP16 |
| 2세대 | Turing (T4) | INT8, INT4 |
| 3세대 | Ampere (A100) | TF32, BF16, 구조적 희소성 |
| 4세대 | Hopper (H100/H200) | FP8, Transformer Engine, 비동기 WGMMA |
| 4세대 | Ada (L40S, RTX 40) | FP8 — 단 FP32 누적 경로 처리량 제한 |
| 5세대 | Blackwell (B200/B300, RTX PRO 6000) | FP4/FP6, 2세대 Transformer Engine |

Transformer Engine 은 레이어별·텐서별로 FP8 과 BF16 중 무엇을 쓸지 런타임에 정하고 스케일링 팩터를 관리합니다. FP8 학습이 실용화된 것이 이것 덕분입니다.

<div class="warn" markdown="1">
**텐서 코어를 놀리게 되는 경우.** 텐서 코어는 "켜는" 것이 아니라 조건을 충족하면 쓰이고, 아니면 조용히 폴백합니다. 순수 FP32 로 학습하면 H100 에서 989 가 아니라 67 TFLOPS 입니다. `allow_tf32 = False` — PyTorch 의 행렬곱 기본값 — 면 FP32 행렬곱조차 텐서 코어를 거치지 않습니다. hidden 차원이 8 이나 16 의 배수가 아니면 느린 커널이 선택됩니다(어휘 크기를 32,000 이 아니라 32,768 로 패딩하는 관행이 여기서 나옵니다). cuBLAS 나 CUTLASS 를 거치지 않는 직접 작성 커널은 아예 닿지 못합니다.
</div>

<div class="note" markdown="1">
**여기서 측정한 것.** 클러스터 실습의 모델은 TF32 를 끈 순수 FP32 로 돕니다. GPU 한 장에서 RTX 4090 은 초당 **39,453** 샘플, A100 SXM 은 **23,132** 샘플로 학습했습니다 — 텐서 코어가 놀았기 때문에 A100 이 졌고, FP32 CUDA 코어 처리량은 4090 이 더 높습니다. A100 의 강점은 FP32 가 아니라 BF16/TF32 와 링크입니다.
</div>

정밀도를 낮추는 건 속도보다 메모리 때문인 경우가 더 많습니다. 디코딩이 대역폭 바운드라 가중치 바이트 수를 반으로 줄이면 토큰 생성 속도가 거의 두 배가 되고 KV 캐시 여유도 생깁니다. 8비트 아래로 내려가면 품질 저하가 보이기 시작하므로, 4비트는 배포 전에 반드시 자체 평가 데이터로 확인하세요.

## 사이징 공식
{: #sizing-ko }

공식 네 개면 "7B 면 뭐가 필요하냐" 는 질문에 조건부터 되묻고 숫자로 답할 수 있습니다.

```
① 학습 메모리   = 16N 바이트 (FP16 + AdamW) · 8-bit Adam 이면 10N · LoRA 는 2N + α
② 학습 FLOPs    = 6 × 파라미터 × 토큰     (순전파 2N + 역전파 4N)
   추론 FLOPs   = 2 × 파라미터 × 토큰
③ 토큰당 KV 캐시 = 2 × 레이어 수 × KV 헤드 수 × head_dim × 원소당 바이트
④ 디코딩 상한   = HBM 대역폭 ÷ 모델 바이트 수      (단일 스트림, tok/s)
```

같은 7B 가 방식에 따라 8 GB 에서 110 GB 이상까지 갈리므로, 먼저 묻는 것은 언제나 같습니다. full fine-tune 인가 PEFT 인가, 정밀도를 어디까지 내릴 수 있는가, 최종 서빙 컨텍스트 길이는 얼마인가.

### ① 학습 메모리의 내역

| 항목 | 바이트 | 7B 기준 | 왜 필요한가 |
|---|---|---|---|
| FP16 가중치 | 2N | 14 GB | 순전파·역전파 계산 |
| FP16 그래디언트 | 2N | 14 GB | 역전파 결과 |
| FP32 마스터 가중치 | 4N | 28 GB | 정밀도 손실 없는 갱신 |
| Adam 1차 모멘트 m | 4N | 28 GB | 옵티마이저 상태 |
| Adam 2차 모멘트 v | 4N | 28 GB | 옵티마이저 상태 |
| **소계** | **16N** | **112 GB** | + 활성값 |

7B full fine-tune 은 80 GB 한 장에 들어가지 않습니다. ZeRO-3 나 FSDP 로 두 장이 최소이고, 활성값 여유를 보면 네 장이 현실적입니다.

AdamW 는 파라미터 하나하나마다 이력 두 개를 기억합니다 — 최근 그래디언트의 이동평균 **m** 과 그 분산 **v** 이며, 둘 다 FP32 입니다. 파라미터당 8바이트이고, 112 GB 중 84 GB 가 옵티마이저 관련인 이유가 이것입니다. **8-bit Adam**(bitsandbytes)은 m 과 v 를 8비트로 저장합니다. 그 56 GB 가 14 GB 로 줄어 총량이 약 70 GB 가 되고, 품질 저하가 거의 없어 실무에서 자주 켭니다.

| 기법 | 효과 | 대가 |
|---|---|---|
| 8-bit Adam | 옵티마이저 8N → 2N, 총 16N → 10N | 미미 |
| Gradient checkpointing | 활성값 메모리 대폭 감소 | 계산 약 +30% |
| ZeRO-1 / -2 / -3, FSDP | 옵티마이저 → 그래디언트 → 파라미터 순으로 분할 | 단계마다 통신 증가 |
| LoRA | 학습 대상을 0.1–1% 로 축소 | 표현력 제한 |
| QLoRA NF4 | 동결된 베이스를 4비트로 | 학습 속도 저하 |
| CPU / NVMe 오프로드 | 메모리 해결 | 처리량 급락 — 최후 수단 |

### ③ KV 캐시 — 추론 메모리의 주범

| 모델 | 어텐션 구성 | 토큰당 | 32k 컨텍스트, 요청 1건 |
|---|---|---|---|
| Llama-2-7B | MHA · 32층 · KV 헤드 32 · head_dim 128 | 512 KB | 16 GB |
| Llama-3-8B | GQA · 32층 · KV 헤드 8 · head_dim 128 | 128 KB | 4 GB |
| Llama-3-70B | GQA · 80층 · KV 헤드 8 · head_dim 128 | 320 KB | 10 GB |

GQA 가 4배를 절감합니다. 최신 모델이 전부 GQA 또는 MQA 를 쓰는 이유이고, KV 캐시를 FP8 로 하면 한 번 더 절반입니다.

<div class="note" markdown="1">
**여기서 측정한 것.** 추론 스윕([FINDINGS](https://github.com/litkhai/runpod-hols/blob/main/inference-characterization/FINDINGS.md))은 vLLM 이미지 하나를 GPU 9종에서 돌렸습니다. vLLM 의 preemption 카운터 — KV 캐시가 가득 차 밀려난 요청 수 — 는 **KV 캐시가 가장 작은 GPU 세 종에서만** 올랐습니다: RTX 4090, L4, L40 (C6). KV 캐시가 100만 토큰 이상 들어가는 A100, H100, H200 에서는 프롬프트 토큰의 97–100% 가 프리픽스 캐시에서 처리됐습니다 (C21).
</div>

### 다섯 가지 작업

| 작업 | 7B 기준 | 무엇이 바뀌나 | 언제 쓰나 |
|---|---|---|---|
| 추론 | 14 GB + KV | 아무것도 — 그대로 사용 | 서비스 운영 |
| Full FT (AdamW) | 112 GB | 전체 파라미터 | 도메인 어휘 자체가 다를 때 |
| Full FT (8-bit Adam) | ~70 GB | 전체 파라미터, 옵티마이저만 경량화 | 위와 같되 GPU 가 부족할 때 |
| LoRA | ~19 GB | 파라미터의 0.1–1% | 대부분의 요구는 여기서 끝남 |
| QLoRA | ~9 GB | 0.1–1%, 베이스도 압축 | GPU 한 장으로 실험할 때 |

**LoRA** 는 원본 가중치를 동결하고, 옆에 작은 행렬 두 개를 붙여 그것만 학습합니다.

```
기존   y = W · x            W 를 통째로 학습 (4096×4096 = 1,680만 개)
LoRA   y = W · x + B·A·x    W 는 고정, A(4096×16)와 B(16×4096)만 학습
                            → 13만 개, 원본의 0.8%
```

가운데 16 이 **rank** 이고, 보통 16–64 를 씁니다. 동결된 베이스에는 그래디언트도 옵티마이저 상태도 필요 없어 메모리가 급감하고, 결과물은 수십 MB 짜리 어댑터 파일 하나입니다. **QLoRA** 는 동결된 베이스까지 NF4 4비트로 압축하고 계산할 때만 FP16 으로 풉니다. 베이스가 14 GB 에서 3.5 GB 로 줄어 7B 를 24 GB 카드 한 장으로 파인튜닝할 수 있고, 대가는 속도입니다.

<div class="calc" data-calc="vram" markdown="0">
  <div class="calc-hd"><b>VRAM 산정기</b><span>CALCULATOR 01</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>파라미터 (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>작업</label><select data-f="mode"><option value="inf">추론</option><option value="lora">LoRA</option><option value="qlora">QLoRA (4비트)</option><option value="full">Full FT (AdamW)</option><option value="full8">Full FT (8-bit Adam)</option></select></div>
      <div><label>가중치 정밀도</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1">FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>레이어 수</label><input data-f="L" type="number" value="32" min="1"></div>
      <div><label>KV 헤드 수</label><input data-f="kh" type="number" value="8" min="1"></div>
      <div><label>head_dim</label><input data-f="hd" type="number" value="128" min="8"></div>
      <div><label>컨텍스트 길이</label><input data-f="ctx" type="number" value="8192" min="128" step="512"></div>
      <div><label>동시 요청</label><input data-f="bs" type="number" value="8" min="1"></div>
      <div><label>KV 정밀도</label><select data-f="kp"><option value="2">FP16</option><option value="1">FP8</option></select></div>
    </div>
    <div class="calc-out">
      <div><span>가중치 (GB)</span><b data-o="w">–</b></div>
      <div><span>그래디언트 + 옵티마이저 (GB)</span><b data-o="o">–</b></div>
      <div><span>KV 캐시 (GB)</span><b data-o="k">–</b></div>
      <div><span>활성값 + 오버헤드 (GB)</span><b data-o="a">–</b></div>
      <div class="hi"><span>합계 (GB)</span><b data-o="t">–</b></div>
    </div>
    <div class="calc-bar" data-o="bar"><i></i><i></i><i></i><i></i></div>
    <div class="calc-key"><span><s class="k1"></s>가중치</span><span><s class="k2"></s>그래디언트 + 옵티마이저</span><span><s class="k3"></s>KV 캐시</span><span><s class="k4"></s>활성값</span></div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ④ 디코딩 속도 상한

단일 스트림의 토큰 속도는 초당 가중치를 몇 번 읽을 수 있느냐로 정해집니다. 매 토큰마다 모델 전체를 HBM 에서 한 번씩 읽어야 하기 때문입니다.

| 구성 | 모델 바이트 | 이론 상한 | 실효 (약 70%) |
|---|---|---|---|
| 7B FP16 on H100 SXM (3.35 TB/s) | 14 GB | 239 tok/s | ~167 |
| 7B FP8 on H100 SXM | 7 GB | 479 tok/s | ~335 |
| 70B FP16 on 2×H100 (6.7 TB/s) | 140 GB | 48 tok/s | ~34 |

<div class="calc" data-calc="decode" markdown="0">
  <div class="calc-hd"><b>디코딩 처리량 · 추론 비용</b><span>CALCULATOR 02</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>GPU (Runpod Secure, 2026-11-07)</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU 장수</label><input data-f="n" type="number" value="1" min="1" max="8"></div>
      <div><label>파라미터 (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>가중치 정밀도</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1" selected>FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>동시 요청</label><input data-f="b" type="number" value="32" min="1"></div>
      <div><label>평균 컨텍스트</label><input data-f="ctx" type="number" value="4096" min="128" step="512"></div>
      <div><label>토큰당 KV (KB)</label><input data-f="kv" type="number" value="128" min="1"></div>
    </div>
    <div class="calc-out">
      <div><span>단일 스트림 (tok/s)</span><b data-o="s">–</b></div>
      <div><span>대역폭 한계 (tok/s)</span><b data-o="bw">–</b></div>
      <div><span>연산 한계 (tok/s)</span><b data-o="cl">–</b></div>
      <div class="hi"><span>총 처리량 (tok/s)</span><b data-o="t">–</b></div>
      <div class="hi"><span>출력 1M 토큰당 (USD)</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ② 학습 시간과 비용

**MFU**(Model FLOPs Utilization)는 실제 달성 FLOPS ÷ 이론 피크입니다. 잘 튜닝된 대규모 학습이 40–50% 이고, 30% 미만이면 어딘가 문제가 있습니다.

<div class="calc" data-calc="train" markdown="0">
  <div class="calc-hd"><b>학습 시간 · 비용</b><span>CALCULATOR 03</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>파라미터 (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>학습 토큰 (B)</label><input data-f="tok" type="number" value="1" min="0.001" step="0.1"></div>
      <div><label>방식</label><select data-f="m"><option value="6">Full FT (6N)</option><option value="5">LoRA (~5N)</option></select></div>
      <div><label>GPU (Runpod Secure, 2026-11-07)</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU 장수</label><input data-f="n" type="number" value="8" min="1"></div>
      <div><label>MFU (%)</label><input data-f="mfu" type="number" value="40" min="5" max="70"></div>
    </div>
    <div class="calc-out">
      <div><span>총 연산량 (EFLOPs)</span><b data-o="f">–</b></div>
      <div><span>GPU-시간</span><b data-o="gh">–</b></div>
      <div><span>벽시계 시간 (시간)</span><b data-o="w">–</b></div>
      <div class="hi"><span>추정 비용 (USD)</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

<div class="note" markdown="1">
**계산기에 대해.** 전부 1차 근사입니다. 실제 값은 프레임워크, 배치 구성, 시퀀스 길이 분포, 스케줄러에 따라 달라집니다. 목적은 정확한 값이 아니라 어떤 변수가 지배하는지를 보는 것입니다. FLOPS 는 dense 기준이고 Blackwell 계열은 근사치입니다. 가격은 Runpod Secure Cloud 온디맨드 GPU 시간당 단가로, 2026-11-07 카탈로그에서 읽었습니다.
</div>

## 트랜스포머, 짧게
{: #transformer-ko }

디코더 레이어 하나의 처음부터 끝까지 — 무엇이 텐서 코어에서 돌고 무엇이 CUDA 코어 몫인지:

```
x                                        입력 [배치, 시퀀스, 4096]
h  = RMSNorm(x)                          CUDA
q  = h @ W_q ;  k = h @ W_k ;  v = h @ W_v   TENSOR  QKV 프로젝션
q, k = RoPE(q, k)                        CUDA
k, v = KVCache.append(k, v)              CUDA    메모리 이동
s  = q @ kᵀ / √head_dim                  TENSOR  어텐션 스코어
s  = causal_mask(s) ; p = softmax(s)     CUDA
o  = p @ v                               TENSOR  가중합
o  = o @ W_o                             TENSOR
x  = x + o                               CUDA    잔차
h  = RMSNorm(x)                          CUDA
g  = h @ W_gate ;  u = h @ W_up          TENSOR  FFN
f  = SiLU(g) * u                         CUDA    활성화
x  = x + (f @ W_down)                    TENSOR + CUDA
── 32회 반복 후 ──
logits = RMSNorm(x) @ W_lm_head          TENSOR  어휘 32,000개 점수
token  = sample(logits)                  CUDA
```

FLOPs 는 사실상 전부 텐서 코어의 GEMM 입니다. 나머지는 모두 메모리 바운드입니다.

| 연산 | 토큰당 이동량 (7B) | 연산 강도 | 성격 |
|---|---|---|---|
| RMSNorm | ~1.6 MB | < 1 | 리덕션, 메모리 바운드 |
| RoPE | ~0.7 MB | ~2 | 메모리 바운드 |
| 활성화 (SwiGLU) | ~2.1 MB | ~1 | 가장 큰 elementwise 텐서 |
| 잔차 | ~1.6 MB | 0.17 | 극단적 메모리 바운드 — H100 손익분기보다 1,700배 아래 |
| Softmax | 컨텍스트에 비례 | < 1 | SFU + 리덕션 |
| KV 인덱싱 | 배치 × 컨텍스트에 비례 | ≈ 0 | 순수 데이터 이동 |
| 샘플링 | 배치 × 어휘 크기 | 정렬 | 분기 많음 |

이들이 전체 시간에서 차지하는 비중은 국면에 따라 다릅니다. 배치 1 디코드에서는 가중치 읽기가 압도적이고, 진짜 비용은 커널 런치 오버헤드입니다 — 레이어당 십여 개 커널 × 32층 × 매 토큰. CUDA Graph 가 없애는 것이 이것입니다. 프리필과 학습에서는 활성값이 배치 × 시퀀스로 커져 이 작업이 전체 시간의 30–40% 까지 가고, 거기서는 커널 융합이 가장 큰 레버입니다. FlashAttention 은 같은 발상을 어텐션에 적용한 것입니다. [n×n] 스코어 행렬을 HBM 에 쓰지 않으므로 어텐션 메모리가 O(n²) 에서 O(n) 이 됩니다.

토큰은 BPE 서브워드입니다. 어휘가 충분히 커버하지 못하는 문자 — 많은 모델에서 한국어·중국어·일본어가 여기에 속합니다 — 는 같은 내용에도 토큰이 2–3배 들 수 있고, 가격과 컨텍스트 한도에 모두 영향을 줍니다.

## 학습
{: #training-ko }

목표는 하나뿐입니다 — 다음 토큰 예측. Loss = −log P(정답 토큰), perplexity = exp(loss) 로, 대략 "몇 개 후보 중에서 헷갈리는가" 입니다. 텍스트 자체가 정답입니다. 한 칸 밀면 입력과 정답이 되고, 이것이 인터넷 규모 데이터를 쓸 수 있게 된 이유입니다.

한 스텝: **순전파**(배치를 통과시켜 로짓과 loss 계산, 텐서 코어), **역전파**(모든 파라미터에 대한 loss 의 그래디언트, 순전파의 약 2배 연산), **옵티마이저 갱신**(AdamW, 그래서 파라미터당 상태 2개 추가). 사이징 공식의 16N 메모리와 6N 연산이 정확히 여기서 나옵니다. 추론에는 순전파만 있으니 2N 과 2N 입니다.

| 단계 | 하는 일 | 데이터 | 비용 규모 |
|---|---|---|---|
| ① 사전학습 (Pre-training) | 다음 토큰 예측만 반복. 언어·지식·추론 능력이 여기서 형성 | 수조 토큰 | GPU 수천 장, 수개월 |
| ② 지도 미세조정 (SFT) | 질문-답변 형식을 가르침. 새 능력이 아니라 형식 | 수만–수십만 대화 | GPU 수–수십 장, 수일 |
| ③ 정렬 (RLHF / DPO) | 선호하는 답변 쪽으로 조정 | 선호도 비교 쌍 | ②와 비슷하거나 더 큼 |

지식은 ①에서 들어가고, ②와 ③은 그것을 끌어내는 방식을 다듬습니다. 그래서 "파인튜닝으로 사내 지식을 주입하겠다" 는 접근은 대체로 실패하고 검색 증강(RAG)이 맞는 도구입니다. 파인튜닝은 형식·문체·도메인 어휘를 위한 것입니다.

| 전략 | 무엇을 나누나 | 통신 | 언제 |
|---|---|---|---|
| DP — 데이터 병렬 | 배치 | 스텝당 그래디언트 AllReduce | 모델이 GPU 한 장에 들어갈 때 |
| ZeRO / FSDP | 1단계 옵티마이저 → 2단계 + 그래디언트 → 3단계 + 파라미터 | 단계마다 증가 | 모델이 안 들어갈 때 — 1순위 |
| TP — 텐서 병렬 | 레이어 내부 행렬 | 레이어마다 AllReduce — 매우 큼 | NVLink 도메인 안에서만 |
| PP — 파이프라인 병렬 | 레이어 블록 | 스테이지 경계에서만 — 적음 | 노드 간 확장 |
| SP — 시퀀스 병렬 | 시퀀스 길이 | 중간 | 롱컨텍스트 학습 |
| EP — 전문가 병렬 | MoE 전문가 | All-to-All | MoE 모델 |

실무 조합은 노드 안에서 TP, 노드 간에는 PP 또는 FSDP 입니다. TP 를 노드 경계 밖으로 내보내면 InfiniBand 로도 처리량이 무너집니다 — 숫자는 [GPU Topology]({{ '/readings/gpu-topology/#in-numbers-ko' | relative_url }}) 에 있습니다.

**MoE** 는 토큰마다 상위 k개 전문가로 라우팅합니다. 메모리는 전체 파라미터에, 계산은 활성 파라미터에 비례합니다. 총 200B / 활성 20B 모델은 연산은 20B 급이지만 VRAM 은 200B 급이 필요합니다. "MoE 라서 싸다" 는 절반만 맞습니다.

<div class="note" markdown="1">
**여기서 측정한 것.** Pod 하나, GPU 두 장의 데이터 병렬 ([클러스터 실습 01]({{ '/cluster/' | relative_url }})): 스텝당 FP32 그래디언트 약 400 MB. NVLink 로는 그 all-reduce 가 ~2 ms 걸려 두 장의 확장 효율이 0.91 이었고, 호스트를 경유하는 PCIe 로는 계산 6.5 ms 에 대해 ~26 ms 가 걸려 0.21 이었습니다.
</div>

## 추론과 서빙
{: #inference-ko }

학습 비용은 일회성입니다. 추론 비용은 제품이 사는 동안 계속 나가고, 단위 원가를 결정합니다.

| | Prefill | Decode |
|---|---|---|
| 처리 방식 | 프롬프트 전체 병렬 | 1토큰씩 순차 |
| 병목 | 계산 바운드 | 메모리 대역폭 바운드 |
| 지표 | TTFT — 첫 토큰까지 시간 | TPOT / ITL — 토큰 간 지연 |
| 개선 수단 | chunked prefill, 프리픽스 캐싱 | 양자화, 배칭, speculative decoding |
| 7B 감각 | 1,000토큰 프롬프트 ≈ 35 ms | 토큰당 연산 0.035 ms, 메모리 4.2 ms |

연산 0.035 ms 대 읽기 4.2 ms — 120배 차이입니다. 그래서 배칭은 선택이 아닙니다. 여러 요청이 같은 가중치 읽기를 공유해야 GPU 가 제값을 합니다. 일부 롱컨텍스트 서비스는 이제 프리필과 디코드를 서로 다른 GPU 풀에 둡니다(disaggregated serving). 성격이 반대라 서로 방해하기 때문입니다.

| 기법 | 원리 | 효과 |
|---|---|---|
| Continuous batching | 슬롯이 비는 즉시 새 요청 투입 | 처리량 2–5배 |
| PagedAttention | KV 캐시를 OS 페이징처럼 블록 단위로 관리 | 단편화로 버려지던 메모리 60–80% 회수 |
| Prefix caching | 공통 프롬프트 접두부의 KV 를 재사용 | RAG·에이전트에서 TTFT 대폭 감소 |
| Speculative decoding | 작은 드래프트 모델이 제안하고 큰 모델이 한 번에 검증 | 2–3배, 출력 동일 |
| FlashAttention | 타일 단위 융합 커널. 스코어 행렬이 HBM 에 닿지 않음 | 메모리 O(n²)→O(n), 2–4배 |
| 양자화 | 가중치 FP8/INT8 (AWQ, GPTQ), KV 캐시 FP8 | 메모리 절반, 속도 향상 |
| Chunked prefill | 긴 프롬프트를 쪼개 디코드와 섞어 스케줄 | 긴 요청이 짧은 요청을 막지 않음 |

**커널**은 GPU 에서 실행되는 함수 하나입니다. 실행마다 수 µs 가 들고, 더 중요하게는 HBM 왕복이 붙습니다. RMSNorm 과 잔차를 한 커널로 융합하면 쓰기와 읽기를 한 번씩 덜어, 대역폭 바운드 작업에서 2–3배가 나옵니다. `torch.compile` 이 이를 자동화하고, OpenAI 의 Triton 은 그 커널을 작성하는 언어입니다(NVIDIA 의 Triton Inference Server — 서빙 프론트엔드 — 와 혼동하지 마세요).

**지표 세 가지:** TTFT(체감 반응성), TPOT/ITL(읽는 속도. 사람에게는 20–30 tok/s 면 충분), 처리량(단위 원가). TTFT 와 처리량은 상충합니다 — 배치를 키우면 처리량도 개별 지연도 오릅니다 — 그러니 워크로드별로 목표를 따로 잡으세요.

| 스택 | 특징 | 언제 |
|---|---|---|
| vLLM | PagedAttention 원조, OpenAI 호환 API, continuous batching 기본 | 기본 선택 |
| SGLang | RadixAttention 프리픽스 캐싱, 구조적 출력 | 에이전트·RAG 워크로드 |
| TensorRT-LLM | NVIDIA 공식. 최고 성능, 모델별 엔진 빌드 | 모델 고정 + 최대 성능 |
| Triton Inference Server | 멀티모델·멀티프레임워크 프론트엔드 | 여러 모델을 한 엔드포인트로 |
| Ollama / llama.cpp | GGUF, CPU·엣지 | 로컬, 데모 |

추론 모델(reasoning model)은 출력 토큰 수를 몇 배로 늘리고, 디코딩 처리량이 곧 제품 원가입니다. 그러니 비용은 토큰당 단가가 아니라 요청당 예상 토큰 수로 산정하세요.

<div class="note" markdown="1">
**여기서 측정한 것.** 이 실습들은 vLLM 으로 서빙합니다 ([Serverless 실습 03]({{ '/serverless/' | relative_url }}), 추론 스윕). 콜드 Serverless 워커에서 같은 이미지·같은 모델인데도 vLLM 의 CUDA graph 캡처만으로 한 호스트에서는 9 s, 다른 호스트들에서는 62–73 s 가 걸렸습니다 (C19) — 런치 오버헤드를 없애는 수단 자체가 콜드스타트마다 비용으로 붙습니다.
</div>

## Runpod 에 적용한 운영
{: #operations-ko }

**버전 매트릭스.** 호스트 드라이버 → CUDA toolkit → 컨테이너. 컨테이너 안의 CUDA 는 호스트 드라이버가 지원하는 버전 이하여야 합니다. Runpod 에서는 이미지는 내가 고르고, 드라이버는 호스트가 정합니다.

<div class="note" markdown="1">
**여기서 측정한 것.** 16 GB/24 GB Serverless 풀이 RTX PRO 6000 Blackwell MIG 슬라이스(sm_120)를 배정했는데, CUDA 12.6 PyTorch 이미지는 sm_90 까지만 지원해 워커가 `no kernel image is available` 로 죽었습니다 ([Serverless 실습 02]({{ '/serverless/' | relative_url }})). 콘솔은 이제 GPU 를 *Previous* 와 *Latest generation* 으로 나누며, 후자는 CUDA 12.8+ 이미지가 필요합니다.
</div>

**무엇을 봐야 하나.** `utilization.gpu` 가 아니라 SM 점유율과 메모리 대역폭 사용률입니다. `nvidia-smi` 의 GPU-Util 은 커널이 올라와 있던 시간 비율일 뿐이라, 장치의 1% 만 쓰는 커널도 100% 로 표시됩니다.

<div class="note" markdown="1">
**여기서 측정한 것.** RTX 4090 두 장 실행 중 콘솔 Telemetry 는 두 GPU 모두 **100%** 를 보였지만, 학습 속도는 이상치의 5분의 1 이었습니다 — 커널은 PCIe 를 기다리는 NCCL 이었습니다 ([스크린샷]({{ '/cluster/' | relative_url }})).
</div>

| 증상 | 원인과 처방 |
|---|---|
| 메모리가 남는데도 CUDA OOM | 단편화 → `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` |
| 성능이 갑자기 하락 | 온도·전력 스로틀링 → `nvidia-smi -q -d PERFORMANCE` |
| Xid 에러 | 커널 로그: 13/31 앱 오류, 48/63/64 ECC, 79 GPU 가 버스에서 탈락 |
| NCCL timeout | 토폴로지 또는 인터페이스 → `NCCL_DEBUG=INFO`, `nvidia-smi topo -m`. Instant Cluster 에서는 `NCCL_SOCKET_IFNAME=ens1` 설정 |
| 수 분짜리 콜드스타트 | 모델 가중치 pull → 가중치를 이미지에서 분리 (아래) |
| 학습 MFU 30% 미만 | 데이터 로더, 통신, 또는 배치 과소 → 구간별로 프로파일 |

**콜드스타트.** 가중치를 넣어 수십 GB 가 된 이미지는 pull 에 수 분이 걸립니다. 가중치는 이미지에서 빼고 캐시나 볼륨에서 로드하세요. `safetensors` 를 mmap 으로 쓰면 필요한 텐서만 페이지 인 됩니다. Serverless 에서는 플랫폼이 이 중 세 가지 레버를 제공합니다. 엔드포인트의 **Model** 필드는 Hugging Face 가중치를 호스트에 캐시하고, 네트워크 볼륨은 워커 간에 가중치를 유지하며, FlashBoot 는 멈춘 워커의 상태를 보존해 빠르게 재시작합니다.

<div class="note" markdown="1">
**여기서 측정한 것.** 추론 스윕의 vLLM 엔드포인트에서 기록된 콜드스타트는 FlashBoot 를 켜든 끄든 매번 새 컨테이너를 만들고 14.19 GiB 의 가중치를 다시 내려받았습니다 (C17). FlashBoot 를 켜고 idle timeout 5 s 로 두면 15 s, 30 s 간격의 요청은 같은 컨테이너를 재사용했고(`delayTime` 1.9 s, 1.3 s), 60 s 간격부터는 매번 새 컨테이너가 떠서 97–104 s 가 걸렸습니다 (C22). 2026-11-07 FlashBoot 를 Standard 로 두었을 때는 30–120 초 간격도 컨테이너를 재사용했습니다(1.1–1.2 초). 재사용 구간이 늘었습니다(C34). 가중치를 네트워크 볼륨에 두면 더 느렸습니다 — [Storage]({{ '/readings/storage/#model-weights-ko' | relative_url }}) 참고 (C35). Model 필드와 콜드스타트 단계는 [Serverless]({{ '/serverless/' | relative_url }}) 를 보세요.
</div>

## 비용
{: #cost-ko }

```
출력 1M 토큰당 추론 원가 = (시간당 단가 ÷ 3600) ÷ 처리량 (tok/s) × 1,000,000
```

7B FP8 을 H100 SXM 한 장에서 continuous batching 으로 3,000 tok/s 낸다고 하면: 1,000,000 ÷ 3,000 = 333 s = 0.093 h, × USD 3.99 = **출력 1M 토큰당 약 USD 0.37**. 이 숫자를 API 단가와 비교하면 자체 서빙 손익분기가 바로 나옵니다.

**실효 원가 = 시간당 단가 ÷ 실제 가동률.** USD 3.99 짜리 GPU 를 20% 만 쓰면 실효 시간당 약 USD 20 입니다. Serverless 와 오토스케일이 존재하는 이유이고, 콜드스타트가 핵심 지표인 이유입니다.

Runpod Pod 의 GPU 시간당 가격, 2026-11-07 카탈로그 기준:

| GPU | VRAM | Secure Cloud | Community Cloud |
|---|---|---|---|
| L4 | 24 GB | 0.59 | 0.44 |
| RTX 4090 | 24 GB | 0.89 | 0.34 |
| L40S | 48 GB | 1.09 | 0.79 |
| A100 SXM | 80 GB | 1.79 | 1.39 |
| H100 PCIe | 80 GB | 2.89 | 1.99 |
| RTX PRO 6000 | 96 GB | 2.49 | 1.69 |
| H100 SXM | 80 GB | 3.99 | 2.69 |
| H200 SXM | 141 GB | 5.29 | 3.59 |
| B200 | 180 GB | 7.99 | 5.98 |
| B300 | 288 GB | 8.99 | 6.94 |

| 형태 | 단가 | 리스크 |
|---|---|---|
| 온디맨드 | 기준 | 없음 |
| 스팟 / 커뮤니티 | 더 저렴 — 위 표에서 22–62% | 선점 또는 약한 보장. 체크포인팅 필수 |
| 예약 / 약정 | 30–50% 저렴 | 1–3년 락인, 세대 교체 리스크 |
| 자체 구축 | 장기 최저 | 상면·전력·냉각·감가·인력 |

H100 8장 서버가 약 USD 250–300k 입니다. 3년이면 전력·상면·인력을 빼고도 GPU 시간당 USD 1.2–1.5 입니다. 자체 구축은 가동률 60% 이상을 3년간 유지할 수 있을 때만 유리하고, 대부분의 팀은 그러지 못합니다. 그리고 NVIDIA 가 연 단위 아키텍처 주기로 가는 만큼, 정밀도와 메모리 가정을 하드코딩하지 말고 CUDA, CUTLASS, Triton 에 맞춰 만드세요.

<div class="note" markdown="1">
**여기서 측정한 것.** Community Cloud 가 더 싸지만, 공인 IP 를 요청해 만든 Community RTX 4090 Pod 는 15분 안에 공인 IP 도, SSH 포트도 받지 못했습니다 (C7). [클러스터]({{ '/cluster/' | relative_url }}) 와 [Pod]({{ '/pod/' | relative_url }}) 실습은 Secure Cloud 에서 돌립니다.
</div>

## 용어집
{: #glossary-ko }

| 용어 | 분류 | 뜻 |
|---|---|---|
| AllReduce | 분산 | 모든 GPU 의 값을 합산해 전체에 배포하는 NCCL 집합 통신. 데이터 병렬 학습의 매 스텝 |
| AWQ / GPTQ | 추론 | 활성값 통계로 중요 채널을 보존하는 학습 후 가중치 양자화 |
| BF16 | 정밀도 | FP32 와 같은 지수 범위의 16비트. 학습 기본값 |
| BPE | 토크나이저 | Byte-Pair Encoding. 자주 붙는 쌍을 병합해 서브워드 어휘 생성 |
| busbw / algbw | 진단 | nccl-tests 출력. 링크 이용률은 busbw 로 판단 |
| Continuous batching | 추론 | 슬롯이 비는 즉시 새 요청 투입. 처리량 2–5배 |
| CUDA 코어 | 하드웨어 | 스칼라 FMA 연산기. 범용이지만 행렬곱은 느림 |
| CUDA Graph | 최적화 | 커널 런치 시퀀스를 캡처해 재생. 배치 1 디코드의 런치 오버헤드 제거 |
| DCGM | 운영 | Data Center GPU Manager. GPU 텔레메트리 수집 |
| FlashAttention | 커널 | 어텐션을 타일 단위 융합 커널로. [n×n] 행렬이 HBM 에 닿지 않음 |
| FSDP | 분산 | Fully Sharded Data Parallel. PyTorch 네이티브, ZeRO-3 와 유사 |
| GEMM | 연산 | General Matrix Multiply. 텐서 코어가 실행하는 유일한 형태 |
| GQA / MQA | 아키텍처 | Grouped- / Multi-Query Attention. KV 헤드를 줄여 캐시 4–8배 절감 |
| Gradient checkpointing | 학습 | 활성값을 저장하지 않고 역전파 때 재계산. 메모리↓, 계산 +30% |
| HBM | 하드웨어 | High Bandwidth Memory — GPU 의 VRAM. 2–8 TB/s |
| KV 캐시 | 추론 | 이전 토큰의 K, V 를 저장. 추론 메모리의 지배 항 |
| LoRA / QLoRA | 학습 | 동결된 베이스 위의 저랭크 어댑터. QLoRA 는 베이스를 4비트 NF4 로 |
| MBU / MFU | 지표 | 달성 대역폭 / FLOPS ÷ 이론값. 대규모에서 MFU 40–50% 가 정상 |
| MIG / MPS | 운영 | 하드웨어 분할 / 프로세스 공유 — [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) 참고 |
| MoE | 아키텍처 | Mixture of Experts. 메모리는 전체 파라미터, 계산은 활성 파라미터에 비례 |
| NCCL | 분산 | NVIDIA Collective Communications Library |
| NVLink 도메인 | 하드웨어 | NVSwitch 풀메시로 묶인 GPU 집합. TP degree 의 상한 |
| PagedAttention | 추론 | 블록 기반 KV 캐시 관리. vLLM 의 핵심 |
| Prefill / Decode | 추론 | 프롬프트 병렬 처리 vs 한 토큰씩 생성. 병목이 정반대 |
| Roofline | 성능 | 연산 강도로 계산 바운드/메모리 바운드를 판별 |
| Speculative decoding | 추론 | 드래프트가 제안, 본 모델이 한 번에 검증. 2–3배, 출력 동일 |
| 텐서 코어 | 하드웨어 | 행렬곱 전용 유닛. 저정밀 입력, FP32 누적 |
| TF32 | 정밀도 | Ampere+ 텐서 코어가 FP32 행렬곱을 돌리는 19비트 형식 — PyTorch 행렬곱에서 기본 꺼짐 |
| TTFT / TPOT / ITL | 지표 | 첫 토큰까지 / 출력 토큰당 / 토큰 간 시간 |
| vLLM | 서빙 | PagedAttention + continuous batching. 사실상 기본 엔진 |
| ZeRO | 분산 | DeepSpeed 샤딩. 1단계 옵티마이저, 2단계 그래디언트, 3단계 파라미터 |
| 2:4 희소성 | 정밀도 | 4개 중 2개 가중치가 0. 마케팅 FLOPS 는 대개 이 기준 |

</div>

<div class="lang" data-lang="zh" markdown="1">

## 简体中文

理解 GPU 最简单的方式，是把它看作一个存储层次结构加上两类执行单元。下文所有关于规模估算和优化的论证都源自这一个框架。之后四个公式几乎可以回答所有“这个模型需要什么？”的问题，三个计算器则让你动手算数，而不必死记硬背。

概念和规格数据是通用的，来自厂商资料。**此处实测**框则是这些实验在 Runpod 上实际运行的结果——通用规律在这里落到一台真实机器上。贯穿全文的一点：把训练和推理分开看，因为两者在显存、瓶颈和 GPU 选择上恰好相反。

## GPU 硬件
{: #hardware-zh }

### 两类执行单元

| | CUDA core | Tensor core |
|---|---|---|
| 工作单位 | 标量 FMA，a×b+c | 矩阵块乘加，D = A×B + C |
| 每条指令的 MAC 数 | 1 | 数百到数千 |
| H100 SXM 上的数量 | 16,896 | 528 |
| H100 吞吐 | 67 TFLOPS (FP32) | 989 (FP16) / 1,979 (FP8) |
| 能做什么 | 任何运算——分支、超越函数 | 只能做矩阵乘法 |
| 如何调用 | 普通的 CUDA C++ 算术 | 通过 cuBLAS / CUTLASS / Triton |

单元数量少 32 倍，吞吐却高 15–30 倍。在 CUDA core 上做同样的 MAC，每次都要付出取指、译码和寄存器访问的开销；tensor core 则用一条指令把这些开销分摊到数千次运算上。

<div class="warn" markdown="1">
**“Tensor core 就是更好”是错误的总结。** 两者并不竞争。Softmax、RMSNorm、RoPE、激活函数、残差相加、KV cache 索引和采样都无法在 tensor core 上运行——它们全部落在 CUDA core 上。而且 tensor core 越快，剩下的这部分就越会成为瓶颈。实际优化工作中很大一部分不在 GEMM 本身，而在 GEMM 之间的空隙。
</div>

### 存储层次结构

```
Registers            tens of KB/SM     tens of TB/s
L1 / shared memory   ~256 KB/SM        ~20 TB/s
L2 cache             50 MB (H100)      ~5 TB/s
HBM (VRAM)           80–288 GB         2–8 TB/s     ← LLM 的瓶颈
Host RAM             TBs               ~64 GB/s (PCIe 5.0 x16)
```

### Roofline——你在哪一侧

算术强度 = FLOPs ÷ 搬运的字节数。H100 SXM 上的分界点是 989 TFLOPS ÷ 3.35 TB/s ≈ **295 FLOP/byte**。低于它是访存受限，高于它是计算受限。

- batch 1 的 LLM decode：强度约为 2——不到 H100 算力的 1%。这就是批处理能成倍提升吞吐的原因。
- 长提示词的 LLM prefill：数百——计算受限，正是 tensor core 发挥价值的地方。
- RMSNorm、残差相加：1–2——纯粹访存受限，这也是 kernel 融合存在的原因。

### 当前产品线（规格截至 2026.09）

| GPU | 显存 | 带宽 | NVLink | TDP | 典型用途 |
|---|---|---|---|---|---|
| L4 | 24 GB | 0.30 TB/s | — | 72 W | 轻量推理、视频 |
| RTX 4090 | 24 GB | 1.01 TB/s | — | 450 W | 开发、QLoRA |
| L40S | 48 GB | 0.86 TB/s | — | 350 W | 中等规模推理 |
| A100 80GB SXM | 80 GB | 2.04 TB/s | 600 GB/s | 400 W | 高性价比训练 |
| H100 PCIe | 80 GB | 2.00 TB/s | 600 GB/s | 350 W | 通用 |
| H100 SXM | 80 GB | 3.35 TB/s | 900 GB/s | 700 W | 训练标准 |
| RTX PRO 6000 | 96 GB | ~1.8 TB/s | — | 600 W | 工作站推理 |
| H200 SXM | 141 GB | 4.80 TB/s | 900 GB/s | 700 W | 长上下文推理 |
| B200 | 180 GB | ~8 TB/s | 1.8 TB/s | ~1000 W | 当代训练 |
| B300 | 288 GB | ~8 TB/s | 1.8 TB/s | ~1400 W | 大模型 |
| GB200/GB300 NVL72 | 72-GPU 域 | — | 整个机架 | ~130 kW/机架 | 前沿模型，液冷 |

值得记住的三点：

1. **SXM 与 PCIe。** 3.35 TB/s 对 2.00 TB/s，900 GB/s 的 NVLink 对两卡桥接。做多 GPU 训练时，只要不是 SXM，通信就会成为瓶颈。
2. **L40S 和 RTX 系列没有 NVLink。** 如果模型需要模型并行，它们就出局了；它们适合单卡放得下的模型。
3. **从 Blackwell 开始，功耗和散热才是真正的约束。** 在 Runpod 这样的云上，这体现为价格和可用性，而不是你要解决的问题——但这正是最新型号最稀缺的原因。

### 标称容量与可用容量

一块“H100 80GB”并不会给你 80 GB 放张量。差距出现在三个地方。

**① 物理容量与产品规格**

| GPU | 物理配置 | 物理总量 | 规格 | 原因 |
|---|---|---|---|---|
| H100 SXM | HBM3 16GB × 6 个位置，启用 5 个 | 96 GB | 80 GB | 为良率禁用一个堆栈 |
| H200 SXM | HBM3e 24GB × 6 | 144 GB | 141 GB | 行冗余和内部预留（未公开） |
| B200 | HBM3e，2 个堆栈中 8 颗芯片 | 192 GB | 180–192 GB | 因 SKU 和供应商而异——Runpod 标为 180 GB |

**② `nvidia-smi` 报告的数值**——单位是 MiB。NVIDIA 的“80GB”实际上是 80 GiB（十进制 85.9 GB）；`torch.cuda.get_device_properties(0).total_memory` 的单位是字节，除以 1024³ 即可对上。

```
A100 80GB   81,920 MiB  =  80.0 GiB
H100 80GB   81,559 MiB  =  79.6 GiB
A100 40GB   40,536 MiB  =  39.6 GiB
```

**③ 分配张量之前就被占用的部分**

| 占用方 | 大小 | 备注 |
|---|---|---|
| CUDA context | 300–600 MB | 每个进程一份；多进程时成倍增加 |
| cuDNN / cuBLAS 工作区 | 数百 MB 到数 GB | 随 kernel 选择而变 |
| NCCL 缓冲区 | 数百 MB | 仅多 GPU |
| 分配器碎片 | 5–10% | 序列长度不定时更严重 |

在 HBM 型号上（A100、H100、H200、B200——片上 ECC），ECC 没有可见的开销。L40S、RTX A6000 等 GDDR 型号开启 ECC 时损失 1/16（6.25%）：48 GB 变成约 45 GB。

**规模估算上限 = 标称值 × 0.90 到 0.93。** 对 H100 80GB，按 72–74 GB 来设计。这就是为什么一个 FP8 的 70B——70 GB 权重——纸面上“放得进 80 GB”，实际却启动失败。

<div class="note" markdown="1">
**此处实测。** Runpod Secure Cloud Pod 上的 `nvidia-smi`，2026-11-07（[集群实验 01]({{ '/cluster/' | relative_url }})）：A100-SXM4-80GB **81,920 MiB**，RTX 4090 **24,564 MiB**。
</div>

### 互连

| 路径 | 带宽 | 备注 |
|---|---|---|
| PCIe 4.0 x16 | 32 GB/s | 较旧的服务器 |
| PCIe 5.0 x16 | 64 GB/s | 当前 |
| NVLink 4 (Hopper) | 900 GB/s | GPU 到 GPU 直连 |
| NVLink 5 (Blackwell) | 1.8 TB/s | |
| NVSwitch | 节点内全互连 | DGX / HGX |
| InfiniBand NDR | 400 Gb/s = 50 GB/s | 节点之间 |
| RoCE v2 | 基于以太网 | 更便宜，更难调优 |

集合通信——AllReduce、AllGather、ReduceScatter、Broadcast——由 NCCL 负责。数据并行训练每一步都要做一次梯度 AllReduce，通信量随参数量增长：FP16 的 7B 模型每步 14 GB。这就是 64 GB/s 的 PCIe 扛不住的原因。

FP32 TFLOPS 对 LLM 工作负载几乎说明不了什么。重要的是三个数字：你实际运行精度下的 dense tensor core 吞吐、HBM 容量和 HBM 带宽。训练看 tensor core 吞吐和 NVLink。推理首先看容量和带宽——decode 受带宽限制，所以 FP8 数据不错的 L40S 在单模型推理上仍然输给 A100：它是 864 GB/s 的 GDDR6。

<div class="note" markdown="1">
**此处实测。** 一台 Pod 上的两块 GPU，同一个 1.01 亿参数的 DDP 作业（[集群实验 01]({{ '/cluster/' | relative_url }})，2026-11-07）：RTX 4090 双卡经 PCIe 跨 NUMA 节点（`SYS`），NCCL 经主机内存中转——all-reduce **15.6 GB/s**，两块卡的训练速度比一块**慢 2.4 倍**。A100 SXM 双卡经 `NV12`——**201 GB/s**，扩展效率 91%。拓扑细节见 [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }})。
</div>

## 精度
{: #precision-zh }

在同一块芯片上，只改变精度就能让吞吐相差 15 倍——而降低精度的真正理由更多是显存，而不是速度。

| 格式 | 位数 | 每参数 | 用在哪里 |
|---|---|---|---|
| FP32 | 32 | 4 B | 优化器主权重；很少用于计算路径 |
| TF32 | 19（以 32 位存储） | 4 B | Ampere+ 用它加速 FP32 矩阵乘——在允许时 |
| FP16 | 16 | 2 B | 指数范围窄——需要 loss scaling |
| BF16 | 16 | 2 B | 与 FP32 相同的指数范围。当前的训练默认值 |
| FP8 (E4M3 / E5M2) | 8 | 1 B | Hopper 起；正在成为推理标准 |
| INT8 | 8 | 1 B | 训练后量化（SmoothQuant、AWQ） |
| NF4 / INT4 | 4 | 0.5 B | QLoRA。质量下降在这里开始显现 |
| FP4 / FP6 | 4 / 6 | 0.5 / 0.75 B | Blackwell 新增 |

**同一块 H100 SXM，不同精度**

| 精度 | Dense TFLOPS | 相对 FP32 |
|---|---|---|
| FP64 | 34 | 0.5× |
| FP32 (CUDA cores) | 67 | 1× |
| TF32 (tensor cores) | 495 | 7.4× |
| FP16 / BF16 | 989 | 14.8× |
| FP8 | 1,979 | 29.5× |

### Dense 与 sparse——一个词，两种含义

**在吞吐数据中**，“dense”指不使用 2:4 结构化稀疏。从 Ampere 开始，当权重按四个一组、每组至多两个非零时，tensor core 可以跳过零值——同样时间内做两倍的矩阵乘，这就是规格表数字翻倍的原因（H100 FP8：dense 1,979，sparse 3,958）。要拿到这部分收益，需要把模型剪枝成这种模式、重新训练，并通过 cuSPARSELt 或 TensorRT 运行；生产环境的 LLM 很少这么做，而且 decode 本来就受带宽限制。比较规格时请用 dense 数据。“H100 有 4 petaflops”几乎总是 FP8 sparse。

**跟在模型名称旁边时**，“dense”指不是混合专家模型：每个 token 都经过所有参数（Llama 3 70B），而 MoE 把每个 token 路由到它的 top-k 专家（Mixtral 8×7B、DeepSeek-V3）。

### Tensor core 的各代

| 代 | 架构 | 新增内容 |
|---|---|---|
| 第 1 代 | Volta (V100) | FP16 |
| 第 2 代 | Turing (T4) | INT8, INT4 |
| 第 3 代 | Ampere (A100) | TF32、BF16、结构化稀疏 |
| 第 4 代 | Hopper (H100/H200) | FP8、Transformer Engine、异步 WGMMA |
| 第 4 代 | Ada (L40S, RTX 40) | FP8——但 FP32 累加路径被限速 |
| 第 5 代 | Blackwell (B200/B300, RTX PRO 6000) | FP4/FP6、第二代 Transformer Engine |

Transformer Engine 在运行时逐层、逐张量地选择 FP8 或 BF16，并管理缩放因子；正是有了它，FP8 训练才变得实用。

<div class="warn" markdown="1">
**Tensor core 是如何被闲置的。** 它们不是被“打开”的；条件满足时才会启用，否则会静默回退。纯 FP32 训练在 H100 上只有 67 TFLOPS 而不是 989。设置 `allow_tf32 = False`——这是 PyTorch 矩阵乘的默认值——连 FP32 矩阵乘也会绕过它们。隐藏维度不是 8 或 16 的倍数时会选到更慢的 kernel（所以词表会从 32,000 补齐到 32,768）。从不经过 cuBLAS 或 CUTLASS 的手写 kernel 也永远用不到它们。
</div>

<div class="note" markdown="1">
**此处实测。** 集群实验的模型以纯 FP32 运行，TF32 关闭。单 GPU 时，RTX 4090 的训练速度为每秒 **39,453** 样本，A100 SXM 为 **23,132**——A100 输了，因为它的 tensor core 闲置着，而 4090 的 FP32 CUDA core 吞吐更高。A100 的优势在于 BF16/TF32 和互连，而不是 FP32。
</div>

降低精度更多是为了显存而不是速度：decode 受带宽限制，所以每个权重的字节数减半，token 速率几乎翻倍，还能为 KV cache 腾出空间。低于 8 位时质量损失开始显现，所以上线 4 位之前，请先用你自己的评测数据验证。

## 规模估算公式
{: #sizing-zh }

有了四个公式，面对“7B 需要什么？”时，你可以先反问正确的条件，再给出数字。

```
① 训练显存 = 16N bytes (FP16 + AdamW) · 8-bit Adam 为 10N · LoRA 为 2N + α
② 训练 FLOPs  = 6 × params × tokens     (前向 2N + 反向 4N)
   推理 FLOPs = 2 × params × tokens
③ 每 token 的 KV cache = 2 × layers × KV heads × head_dim × 每元素字节数
④ Decode 上限 = HBM 带宽 ÷ 模型字节数      (单流，tok/s)
```

同一个 7B，视方法不同需要 8 GB 到 110 GB 以上，所以最先要问的总是：全量微调还是 PEFT，精度能降到多低，最终要支持多长的上下文。

### ① 训练显存都去了哪里

| 组成 | 字节 | 7B 时 | 为什么存在 |
|---|---|---|---|
| FP16 权重 | 2N | 14 GB | 前向和反向计算 |
| FP16 梯度 | 2N | 14 GB | 反向传播的输出 |
| FP32 主权重 | 4N | 28 GB | 无精度损失地更新 |
| Adam 一阶矩 m | 4N | 28 GB | 优化器状态 |
| Adam 二阶矩 v | 4N | 28 GB | 优化器状态 |
| **小计** | **16N** | **112 GB** | 另加激活值 |

7B 的全量微调放不进一张 80 GB 的卡：使用 ZeRO-3 或 FSDP 时两张卡是底线，考虑激活值余量，四张才现实。

AdamW 为每个参数保留两份历史——**m**，近期梯度的滑动平均；**v**，它们的方差——都是 FP32。每个参数 8 字节，这就是 112 GB 中有 84 GB 与优化器相关的原因。**8-bit Adam**（bitsandbytes）用 8 位存储 m 和 v：那 56 GB 变成 14 GB，总量降到约 70 GB，质量损失小到通常默认开启。

| 技术 | 效果 | 代价 |
|---|---|---|
| 8-bit Adam | 优化器 8N → 2N；总量 16N → 10N | 可忽略 |
| Gradient checkpointing | 激活显存大幅下降 | 计算量增加约 30% |
| ZeRO-1 / -2 / -3, FSDP | 依次切分优化器、梯度、参数 | 每一阶段通信都增加 |
| LoRA | 可训练部分降到 0.1–1% | 表达能力受限 |
| QLoRA NF4 | 4 位冻结基座 | 训练变慢 |
| CPU / NVMe offload | 解决显存问题 | 吞吐崩溃——最后手段 |

### ③ KV cache——推理的显存问题

| 模型 | 注意力结构 | 每 token | 32k 上下文，1 个请求 |
|---|---|---|---|
| Llama-2-7B | MHA · 32 层 · 32 个 KV head · head_dim 128 | 512 KB | 16 GB |
| Llama-3-8B | GQA · 32 层 · 8 个 KV head · head_dim 128 | 128 KB | 4 GB |
| Llama-3-70B | GQA · 80 层 · 8 个 KV head · head_dim 128 | 320 KB | 10 GB |

GQA 带来 4 倍的缩减，这就是近期模型都采用 GQA 或 MQA 的原因；FP8 KV cache 还能再减半。

<div class="note" markdown="1">
**此处实测。** 推理扫描实验（[FINDINGS](https://github.com/litkhai/runpod-hols/blob/main/inference-characterization/FINDINGS.md)）在九种 GPU 上运行了同一个 vLLM 镜像。vLLM 的抢占计数器——因 KV cache 占满而被驱逐的请求——**只在 KV cache 最小的三种 GPU 上上升**：RTX 4090、L4 和 L40（C6）。在 KV cache 能容纳超过一百万 token 的 A100、H100 和 H200 上，97–100% 的提示词 token 由 prefix cache 提供（C21）。
</div>

### 五种工作负载

| 工作负载 | 7B 时 | 改变什么 | 何时使用 |
|---|---|---|---|
| 推理 | 14 GB + KV | 不变——原样使用 | 运行服务 |
| 全量微调 (AdamW) | 112 GB | 全部参数 | 领域词汇本身不同时 |
| 全量微调 (8-bit Adam) | ~70 GB | 全部参数，优化器更轻 | 同上，GPU 不足时 |
| LoRA | ~19 GB | 0.1–1% 的参数 | 大多数需求止步于此 |
| QLoRA | ~9 GB | 0.1–1%，基座也被压缩 | 单卡实验 |

**LoRA** 冻结原始权重，并在旁边训练两个小矩阵：

```
standard   y = W · x            训练整个 W (4096×4096 = 16.8M params)
LoRA       y = W · x + B·A·x    W 冻结；只训练 A (4096×16) 和 B (16×4096)
                                → 131K params，原来的 0.8%
```

中间的 16 是 **rank**；通常取 16 到 64。显存大幅下降，是因为冻结的基座不需要梯度和优化器状态，产物是一个几十 MB 的 adapter 文件。**QLoRA** 还把冻结的基座压缩为 4 位 NF4，只在每次计算时反量化为 FP16：基座从 14 GB 降到 3.5 GB，让 7B 微调可以在一张 24 GB 的卡上完成，代价是速度。

<div class="calc" data-calc="vram" markdown="0">
  <div class="calc-hd"><b>显存估算</b><span>CALCULATOR 01</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>参数量 (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>工作负载</label><select data-f="mode"><option value="inf">推理</option><option value="lora">LoRA</option><option value="qlora">QLoRA (4-bit)</option><option value="full">全量微调 (AdamW)</option><option value="full8">全量微调 (8-bit Adam)</option></select></div>
      <div><label>权重精度</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1">FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>层数</label><input data-f="L" type="number" value="32" min="1"></div>
      <div><label>KV head 数</label><input data-f="kh" type="number" value="8" min="1"></div>
      <div><label>head_dim</label><input data-f="hd" type="number" value="128" min="8"></div>
      <div><label>上下文长度</label><input data-f="ctx" type="number" value="8192" min="128" step="512"></div>
      <div><label>并发请求数</label><input data-f="bs" type="number" value="8" min="1"></div>
      <div><label>KV 精度</label><select data-f="kp"><option value="2">FP16</option><option value="1">FP8</option></select></div>
    </div>
    <div class="calc-out">
      <div><span>权重 (GB)</span><b data-o="w">–</b></div>
      <div><span>梯度 + 优化器 (GB)</span><b data-o="o">–</b></div>
      <div><span>KV cache (GB)</span><b data-o="k">–</b></div>
      <div><span>激活值 + 开销 (GB)</span><b data-o="a">–</b></div>
      <div class="hi"><span>合计 (GB)</span><b data-o="t">–</b></div>
    </div>
    <div class="calc-bar" data-o="bar"><i></i><i></i><i></i><i></i></div>
    <div class="calc-key"><span><s class="k1"></s>权重</span><span><s class="k2"></s>梯度 + 优化器</span><span><s class="k3"></s>KV cache</span><span><s class="k4"></s>激活值</span></div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ④ Decode 上限

单流 token 速率取决于每秒能把权重读多少遍，因为每生成一个 token 都要从 HBM 把整个模型读一遍。

| 配置 | 模型字节数 | 上限 | 现实值（~70%） |
|---|---|---|---|
| 7B FP16，H100 SXM (3.35 TB/s) | 14 GB | 239 tok/s | ~167 |
| 7B FP8，H100 SXM | 7 GB | 479 tok/s | ~335 |
| 70B FP16，2×H100 (6.7 TB/s) | 140 GB | 48 tok/s | ~34 |

<div class="calc" data-calc="decode" markdown="0">
  <div class="calc-hd"><b>Decode 吞吐与推理成本</b><span>CALCULATOR 02</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>GPU（Runpod Secure，2026-11-07）</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU 数量</label><input data-f="n" type="number" value="1" min="1" max="8"></div>
      <div><label>参数量 (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>权重精度</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1" selected>FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>并发请求数</label><input data-f="b" type="number" value="32" min="1"></div>
      <div><label>平均上下文</label><input data-f="ctx" type="number" value="4096" min="128" step="512"></div>
      <div><label>每 token 的 KV (KB)</label><input data-f="kv" type="number" value="128" min="1"></div>
    </div>
    <div class="calc-out">
      <div><span>单流 (tok/s)</span><b data-o="s">–</b></div>
      <div><span>带宽上限 (tok/s)</span><b data-o="bw">–</b></div>
      <div><span>算力上限 (tok/s)</span><b data-o="cl">–</b></div>
      <div class="hi"><span>总吞吐 (tok/s)</span><b data-o="t">–</b></div>
      <div class="hi"><span>每 1M 输出 token (USD)</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ② 训练时间与成本

**MFU**（Model FLOPs Utilization）是实际达到的 FLOPS 与峰值之比。调优良好的大规模训练在 40–50%；低于 30% 说明有问题。

<div class="calc" data-calc="train" markdown="0">
  <div class="calc-hd"><b>训练时间与成本</b><span>CALCULATOR 03</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>参数量 (B)</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>Token 数 (B)</label><input data-f="tok" type="number" value="1" min="0.001" step="0.1"></div>
      <div><label>方法</label><select data-f="m"><option value="6">全量微调 (6N)</option><option value="5">LoRA (~5N)</option></select></div>
      <div><label>GPU（Runpod Secure，2026-11-07）</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU 数量</label><input data-f="n" type="number" value="8" min="1"></div>
      <div><label>MFU (%)</label><input data-f="mfu" type="number" value="40" min="5" max="70"></div>
    </div>
    <div class="calc-out">
      <div><span>总计算量 (EFLOPs)</span><b data-o="f">–</b></div>
      <div><span>GPU 小时</span><b data-o="gh">–</b></div>
      <div><span>墙钟时间（小时）</span><b data-o="w">–</b></div>
      <div class="hi"><span>估算成本 (USD)</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

<div class="note" markdown="1">
**关于这些计算器。** 这些是一阶近似：实际数字会随框架、批次组成、序列长度分布和调度器而变化。重点是看哪个变量起主导作用，而不是一个精确数字。FLOPS 为 dense 数据，Blackwell 数据为近似值；价格为 Runpod Secure Cloud 按需的每 GPU 小时价格，于 2026-11-07 从目录读取。
</div>

## Transformer 简介
{: #transformer-zh }

一个 decoder 层从头到尾——哪些在 tensor core 上运行，哪些落在 CUDA core 上：

```
x                                        输入 [batch, seq, 4096]
h  = RMSNorm(x)                          CUDA
q  = h @ W_q ;  k = h @ W_k ;  v = h @ W_v   TENSOR  QKV 投影
q, k = RoPE(q, k)                        CUDA
k, v = KVCache.append(k, v)              CUDA    内存搬运
s  = q @ kᵀ / √head_dim                  TENSOR  注意力分数
s  = causal_mask(s) ; p = softmax(s)     CUDA
o  = p @ v                               TENSOR  加权求和
o  = o @ W_o                             TENSOR
x  = x + o                               CUDA    残差
h  = RMSNorm(x)                          CUDA
g  = h @ W_gate ;  u = h @ W_up          TENSOR  FFN
f  = SiLU(g) * u                         CUDA    激活
x  = x + (f @ W_down)                    TENSOR + CUDA
── 重复 32 次之后 ──
logits = RMSNorm(x) @ W_lm_head          TENSOR  32,000 个词表分数
token  = sample(logits)                  CUDA
```

几乎所有 FLOPs 都是 tensor core 上的 GEMM。其余部分都是访存受限：

| 操作 | 每 token 搬运字节数 (7B) | 强度 | 特性 |
|---|---|---|---|
| RMSNorm | ~1.6 MB | < 1 | 归约，访存受限 |
| RoPE | ~0.7 MB | ~2 | 访存受限 |
| 激活 (SwiGLU) | ~2.1 MB | ~1 | 最大的逐元素张量 |
| 残差 | ~1.6 MB | 0.17 | 极度访存受限——比 H100 分界点低 1,700 倍 |
| Softmax | 随上下文增长 | < 1 | 特殊函数单元加归约 |
| KV 索引 | 随 batch × 上下文增长 | ≈ 0 | 纯数据搬运 |
| 采样 | batch × 词表 | 排序 | 分支密集 |

它们在墙钟时间中的占比取决于场景。在 batch 1 的 decode 中，读取权重占主导，真正的开销是 kernel 启动——每层十几个 kernel × 32 层 × 每个 token——而 CUDA Graph 消除的正是这部分。在 prefill 和训练中，激活值随 batch × 序列长度增长，这部分工作会占到墙钟时间的 30–40%，此时 kernel 融合是最大的杠杆。FlashAttention 是同一思路在注意力上的应用：[n×n] 分数矩阵从不写入 HBM，注意力显存因此从 O(n²) 降到 O(n)。

Token 是 BPE 子词。词表覆盖不足的文字——在许多模型中包括韩文、中文和日文——表达同样内容可能需要两到三倍的 token，这同时影响价格和上下文上限。

## 训练
{: #training-zh }

目标只有一个：预测下一个 token。Loss = −log P(目标 token)；perplexity = exp(loss)，大致相当于“模型在多少个选项之间犹豫”。文本本身就是标签——错开一位就得到输入和目标——这让互联网规模的数据变得可用。

一步包括：**前向**（批次流过模型，得到 logits 和 loss；tensor core），**反向**（对每个参数求 loss 的梯度，计算量约为前向的两倍），**优化器更新**（AdamW，因此每个参数多两份状态）。规模估算公式中的 16N 显存和 6N 计算量正是由此而来；推理只有前向，因此是 2N 和 2N。

| 阶段 | 做什么 | 数据 | 成本规模 |
|---|---|---|---|
| ① 预训练 | 只做下一个 token 预测。语言、知识和推理能力在这里形成 | 数万亿 token | 数千块 GPU，数月 |
| ② 监督微调 (SFT) | 教会问答格式，而不是新能力 | 数万到数十万段对话 | 几块到几十块 GPU，数天 |
| ③ 对齐 (RLHF / DPO) | 引导模型产生更受偏好的回答 | 偏好对 | 与 ② 相当或更多 |

知识在 ① 中进入模型；② 和 ③ 决定它如何呈现。这就是“通过微调注入内部知识”通常会失败、检索（RAG）才是正确工具的原因；微调适用于格式、语体和领域词汇。

| 策略 | 切分什么 | 通信 | 何时使用 |
|---|---|---|---|
| DP — 数据并行 | 批次 | 每步一次梯度 AllReduce | 模型能放进一块 GPU |
| ZeRO / FSDP | 阶段 1 优化器 → 2 + 梯度 → 3 + 参数 | 每个阶段都增加 | 模型放不下——首选 |
| TP — 张量并行 | 层内的矩阵 | 每层一次 AllReduce——非常重 | 仅限 NVLink 域内 |
| PP — 流水线并行 | 层块 | 只在阶段边界——轻 | 跨节点扩展 |
| SP — 序列并行 | 序列长度 | 中等 | 长上下文训练 |
| EP — 专家并行 | MoE 专家 | All-to-All | MoE 模型 |

行之有效的组合：节点内用 TP，跨节点用 PP 或 FSDP。把 TP 推过节点边界，即使有 InfiniBand 吞吐也会崩溃——具体数字见 [GPU Topology]({{ '/readings/gpu-topology/#in-numbers-zh' | relative_url }})。

**MoE** 把每个 token 路由到它的 top-k 专家。显存随总参数量增长，计算量随激活参数量增长：一个总量 200B、激活 20B 的模型，计算起来像 20B，却仍需要 200B 的显存。“它是 MoE，所以便宜”只说对了一半。

<div class="note" markdown="1">
**此处实测。** 一台 Pod、两块 GPU 上的数据并行（[集群实验 01]({{ '/cluster/' | relative_url }})）：每步约 400 MB 的 FP32 梯度。经 NVLink 时 all-reduce 约需 2 ms，双卡扩展效率 0.91；经 PCIe 并由主机中转时约需 26 ms，而计算只有 6.5 ms，双卡扩展效率 0.21。
</div>

## 推理与服务
{: #inference-zh }

训练成本是一次性的。推理成本伴随产品的整个生命周期，它决定了单位经济效益。

| | Prefill | Decode |
|---|---|---|
| 处理方式 | 并行处理整个提示词 | 一次一个 token |
| 瓶颈 | 计算受限 | 显存带宽受限 |
| 指标 | TTFT——首 token 时间 | TPOT / ITL——token 间延迟 |
| 杠杆 | Chunked prefill、prefix caching | 量化、批处理、speculative decoding |
| 7B 的量级 | 1,000 token 的提示词 ≈ 35 ms | 每 token：计算 0.035 ms，访存 4.2 ms |

0.035 ms 的算术对 4.2 ms 的读取——相差 120 倍。这就是批处理不是可选项的原因：必须让许多请求共享一次权重读取，GPU 才物有所值。一些长上下文服务现在把 prefill 和 decode 放在不同的 GPU 池上（disaggregated serving），因为两者的特性会相互干扰。

| 技术 | 机制 | 效果 |
|---|---|---|
| Continuous batching | 一有空位就接纳新请求 | 吞吐 2–5 倍 |
| PagedAttention | 像操作系统分页一样按块管理 KV cache | 收回因碎片损失的 60–80% 显存 |
| Prefix caching | 复用共享提示词前缀的 KV | 大幅降低 RAG 和 agent 的 TTFT |
| Speculative decoding | 小的草稿模型提出候选；大模型一次前向验证 | 2–3 倍，输出完全相同 |
| FlashAttention | 分块融合 kernel；分数矩阵从不写入 HBM | 显存 O(n²)→O(n)，2–4 倍 |
| 量化 | FP8/INT8 权重（AWQ、GPTQ），FP8 KV cache | 显存减半，速度更快 |
| Chunked prefill | 拆分长提示词并与 decode 交错执行 | 长请求不再阻塞短请求 |

一个 **kernel** 就是在 GPU 上启动的一个函数；每次启动要花费数微秒，更重要的是要经过一次 HBM 往返。把 RMSNorm 和残差融合为一个 kernel 可以省掉一次完整的写入和读取——在带宽受限的工作上值 2–3 倍。`torch.compile` 会自动完成这件事；OpenAI 的 Triton 是编写这些 kernel 的语言（不要与 NVIDIA 的 Triton Inference Server 混淆，后者是一个服务前端）。

**三个指标：** TTFT（感知到的响应速度）、TPOT/ITL（阅读速度；对人来说 20–30 tok/s 就够了）、吞吐（单位成本）。TTFT 和吞吐此消彼长——更大的批次既提高吞吐，也增加单个请求的延迟——所以要按工作负载分别设定目标。

| 技术栈 | 特点 | 何时使用 |
|---|---|---|
| vLLM | PagedAttention 的发源地，OpenAI 兼容 API，默认 continuous batching | 默认选择 |
| SGLang | RadixAttention prefix caching，结构化输出 | Agent 和 RAG 工作负载 |
| TensorRT-LLM | NVIDIA 自家方案；性能最高，需按模型构建引擎 | 模型固定，追求极致性能 |
| Triton Inference Server | 多模型、多框架的前端 | 一个端点后面挂多个模型 |
| Ollama / llama.cpp | GGUF，CPU 和边缘设备 | 本地、演示 |

推理模型会成倍增加输出 token，而 decode 吞吐就是产品成本——所以要按每个请求的预期 token 数来估算成本，而不是按每 token 单价。

<div class="note" markdown="1">
**此处实测。** 这些实验用 vLLM 提供服务（[Serverless 实验 03]({{ '/serverless/' | relative_url }})、推理扫描实验）。在冷启动的 Serverless worker 上，同样的镜像和模型，仅 vLLM 的 CUDA graph 捕获在一台主机上就花了 9 s，在其他主机上花了 62–73 s（C19）——用来消除启动开销的手段，本身在每次冷启动时都要付出代价。
</div>

## 运维——在 Runpod 上的情况
{: #operations-zh }

**版本矩阵。** 主机驱动 → CUDA toolkit → 容器。容器内的 CUDA 版本必须不高于主机驱动所支持的版本；在 Runpod 上，镜像由你选，驱动由主机定。

<div class="note" markdown="1">
**此处实测。** 一个 16 GB/24 GB 的 Serverless 池分配到了 RTX PRO 6000 Blackwell 的 MIG 切片（sm_120）；CUDA 12.6 的 PyTorch 镜像只支持到 sm_90，worker 因 `no kernel image is available` 而退出（[Serverless 实验 02]({{ '/serverless/' | relative_url }})）。控制台现在把 GPU 分为 *Previous* 和 *Latest generation*，后者要求 CUDA 12.8+ 的镜像。
</div>

**该看什么。** 不是 `utilization.gpu`，而是 SM 占用率和显存带宽利用率。`nvidia-smi` 的 GPU-Util 是有 kernel 驻留的时间占比，所以一个只用到设备 1% 的 kernel 也会显示 100%。

<div class="note" markdown="1">
**此处实测。** 在 2× RTX 4090 运行期间，控制台的 Telemetry 显示两块 GPU 都是 **100%**，而双卡的训练速度只有理想值的五分之一——那些 kernel 是在等待 PCIe 的 NCCL（[截图]({{ '/cluster/' | relative_url }})）。
</div>

| 症状 | 原因与解决办法 |
|---|---|
| 显存看似空闲却 CUDA OOM | 碎片 → `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` |
| 性能突然下降 | 过热或功耗降频 → `nvidia-smi -q -d PERFORMANCE` |
| Xid 错误 | 内核日志：13/31 应用故障，48/63/64 ECC，79 GPU 从总线上掉线 |
| NCCL 超时 | 拓扑或网卡接口 → `NCCL_DEBUG=INFO`、`nvidia-smi topo -m`；在 Instant Cluster 上设置 `NCCL_SOCKET_IFNAME=ens1` |
| 冷启动长达数分钟 | 拉取模型权重 → 不要把权重放进镜像（见下文） |
| 训练 MFU 低于 30% | 数据加载、通信或批次过小 → 按阶段 profile |

**冷启动。** 把权重打包进几十 GB 的镜像，拉取就要几分钟；应把权重放在镜像之外，从缓存或卷中加载。`safetensors` 配合 mmap 只按需载入所需的张量。在 Serverless 上，平台提供了其中三种手段：端点的 **Model** 字段在主机上缓存 Hugging Face 权重，network volume 在 worker 之间保存权重，FlashBoot 保留已停止 worker 的状态以便快速重启。

<div class="note" markdown="1">
**此处实测。** 推理扫描实验的 vLLM 端点，日志中记录的每一次冷启动都创建了新容器，并重新下载了 14.19 GiB 的权重，无论 FlashBoot 开启与否（C17）。开启 FlashBoot 且空闲超时为 5 s 时，间隔 15 s 和 30 s 的请求复用了同一个容器（`delayTime` 1.9 和 1.3 s）；间隔达到 60 s 起，每个请求都会得到一个新容器，耗时 97–104 s（C22）。Model 2026-11-07 把 FlashBoot 设为 Standard 后，30–120 秒的间隔也复用了容器（1.1–1.2 秒）——复用窗口变长了（C34）。 把权重放在 network volume 上反而更慢——见 [Storage]({{ '/readings/storage/#model-weights-zh' | relative_url }})（C35）。 字段和冷启动各阶段见 [Serverless]({{ '/serverless/' | relative_url }})。
</div>

## 成本
{: #cost-zh }

```
每 1M 输出 token 的推理成本 = (每小时价格 ÷ 3600) ÷ 吞吐 (tok/s) × 1,000,000
```

7B FP8 在一块 H100 SXM 上，使用 continuous batching 达到 3,000 tok/s：1,000,000 ÷ 3,000 = 333 s = 0.093 h，× USD 3.99 = **每 1M 输出 token 约 USD 0.37**。把它与 API 定价对比，自托管的盈亏平衡点就出来了。

**实际成本 = 每小时价格 ÷ 实际利用率。** 一块 USD 3.99 的 GPU 只用了 20% 的时间，实际成本约为每小时 USD 20。这就是 Serverless 和自动扩缩容的理由，也是冷启动成为核心指标的原因。

Runpod Pod 每 GPU 小时价格，于 2026-11-07 从目录读取：

| GPU | 显存 | Secure Cloud | Community Cloud |
|---|---|---|---|
| L4 | 24 GB | 0.59 | 0.44 |
| RTX 4090 | 24 GB | 0.89 | 0.34 |
| L40S | 48 GB | 1.09 | 0.79 |
| A100 SXM | 80 GB | 1.79 | 1.39 |
| H100 PCIe | 80 GB | 2.89 | 1.99 |
| RTX PRO 6000 | 96 GB | 2.49 | 1.69 |
| H100 SXM | 80 GB | 3.99 | 2.69 |
| H200 SXM | 141 GB | 5.29 | 3.59 |
| B200 | 180 GB | 7.99 | 5.98 |
| B300 | 288 GB | 8.99 | 6.94 |

| 形式 | 价格 | 风险 |
|---|---|---|
| 按需 | 基准 | 无 |
| Spot / community | 更便宜——上表中低 22–62% | 可能被抢占或保障较弱；必须做 checkpoint |
| 预留 / 承诺使用 | 便宜 30–50% | 锁定 1–3 年，有代际更替风险 |
| 自建 | 长期看最低 | 场地、电力、散热、折旧、人力 |

一台 8×H100 服务器约 USD 250–300k；摊到三年，在不计电力、场地和人力的情况下是每 GPU 小时 USD 1.2–1.5。只有能在三年内保持 60% 以上的利用率，自建才划算——大多数团队做不到。而且 NVIDIA 每年更新一次架构，应基于 CUDA、CUTLASS 和 Triton 来构建，而不是把精度和显存假设写死。

<div class="note" markdown="1">
**此处实测。** Community Cloud 更便宜，但一台带公网 IP 创建的 Community RTX 4090 Pod 在 15 分钟内始终没有拿到公网 IP，也没有 SSH 端口（C7）；[集群]({{ '/cluster/' | relative_url }})和 [Pod]({{ '/pod/' | relative_url }}) 实验都在 Secure Cloud 上运行。
</div>

## 术语表
{: #glossary-zh }

| 术语 | 领域 | 含义 |
|---|---|---|
| AllReduce | 分布式 | 在所有 GPU 之间求和并分发结果的 NCCL 集合通信；数据并行训练的每一步都要做 |
| AWQ / GPTQ | 推理 | 训练后权重量化，利用激活统计保留关键通道 |
| BF16 | 精度 | 16 位，具有 FP32 的指数范围；训练默认值 |
| BPE | Tokenizer | Byte-Pair Encoding；把高频字节对合并成子词词表 |
| busbw / algbw | 诊断 | nccl-tests 的输出；用 busbw 判断链路利用率 |
| Continuous batching | 推理 | 一有空位就接纳新请求；吞吐 2–5 倍 |
| CUDA core | 硬件 | 标量 FMA 单元；通用，做矩阵乘很慢 |
| CUDA Graph | 优化 | 捕获 kernel 启动序列以便重放；消除 batch 1 decode 中的启动开销 |
| DCGM | 运维 | Data Center GPU Manager；导出 GPU 遥测数据 |
| FlashAttention | Kernel | 以分块融合 kernel 实现注意力；[n×n] 矩阵从不写入 HBM |
| FSDP | 分布式 | Fully Sharded Data Parallel；PyTorch 原生，类似 ZeRO-3 |
| GEMM | 计算 | General Matrix Multiply；tensor core 唯一能执行的形式 |
| GQA / MQA | 架构 | Grouped- / Multi-Query Attention；更少的 KV head，cache 缩小 4–8 倍 |
| Gradient checkpointing | 训练 | 在反向时重算激活值而不是保存它们；显存下降，计算量 +30% |
| HBM | 硬件 | High Bandwidth Memory——GPU 的显存；2–8 TB/s |
| KV cache | 推理 | 保存之前 token 的 K 和 V；推理显存中的主导项 |
| LoRA / QLoRA | 训练 | 在冻结基座上加低秩 adapter；QLoRA 再加上 4 位 NF4 基座 |
| MBU / MFU | 指标 | 实际与理论带宽 / FLOPS 之比；大规模时 40–50% 的 MFU 属于正常 |
| MIG / MPS | 运维 | 硬件分区 / 进程共享——见 [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }}) |
| MoE | 架构 | Mixture of Experts；显存随总参数量增长，计算量随激活参数量增长 |
| NCCL | 分布式 | NVIDIA Collective Communications Library |
| NVLink 域 | 硬件 | 经 NVSwitch 全互连的 GPU；TP 度的上限 |
| PagedAttention | 推理 | 基于块的 KV cache 管理；vLLM 的核心 |
| Prefill / Decode | 推理 | 并行处理提示词与逐 token 生成；瓶颈相反 |
| Roofline | 性能 | 按算术强度把工作划分为计算受限或访存受限 |
| Speculative decoding | 推理 | 草稿模型提出候选，目标模型一次前向验证；2–3 倍，输出完全相同 |
| Tensor core | 硬件 | 矩阵乘单元；低精度输入，FP32 累加 |
| TF32 | 精度 | 19 位格式，让 Ampere+ 的 tensor core 运行 FP32 矩阵乘——PyTorch 矩阵乘中默认关闭 |
| TTFT / TPOT / ITL | 指标 | 首 token 时间 / 每输出 token 时间 / token 间时间 |
| vLLM | 服务 | PagedAttention 加 continuous batching；事实上的默认引擎 |
| ZeRO | 分布式 | DeepSpeed 的切分方案：阶段 1 优化器，2 梯度，3 参数 |
| 2:4 sparsity | 精度 | 每四个权重中有两个为零；宣传用的 FLOPS 通常假设了它 |

</div>

<div class="lang" data-lang="ja" markdown="1">

## 日本語

GPU は、メモリ階層と 2 種類の実行ユニットとして捉えると最も考えやすくなります。以下のサイジングと最適化の議論はすべて、この 1 つの枠組みから導かれます。そのうえで 4 つの式が「このモデルには何が必要か」という問いのほぼすべてをカバーし、3 つの計算機で数値を暗記せずに実際に計算できます。

概念とスペックの数値は一般的なもので、ベンダーの資料によるものです。**ここで測定したもの**のボックスは、これらのラボが Runpod で実際に実行した結果で、一般則が 1 台の実機と出会う場所です。全体を通して、学習と推論は分けて考えてください。メモリ、ボトルネック、GPU の選び方が両者で正反対になるからです。

## GPU ハードウェア
{: #hardware-ja }

### 2 種類の実行ユニット

| | CUDA コア | Tensor コア |
|---|---|---|
| 処理の単位 | スカラー FMA、a×b+c | 行列ブロックの積和、D = A×B + C |
| 命令あたりの MAC 数 | 1 | 数百〜数千 |
| H100 SXM 上の数 | 16,896 | 528 |
| H100 のスループット | 67 TFLOPS（FP32） | 989（FP16）/ 1,979（FP8） |
| できること | 何でも。分岐、超越関数 | 行列積のみ |
| 使い方 | 通常の CUDA C++ の演算 | cuBLAS / CUTLASS / Triton 経由 |

ユニット数は 32 分の 1 で、スループットは 15–30 倍です。同じ MAC を CUDA コアで行うと、毎回命令フェッチ、デコード、レジスタのトラフィックのコストを払います。Tensor コアはそのオーバーヘッドを 1 命令内の数千の演算で償却します。

<div class="warn" markdown="1">
**「Tensor コアのほうが単純に優れている」という要約は誤りです。** 両者は競合しません。Softmax、RMSNorm、RoPE、活性化関数、残差加算、KV キャッシュのインデックス処理、サンプリングは Tensor コアでは実行できず、すべて CUDA コアで実行されます。そして Tensor コアが速くなるほど、その残りの部分がボトルネックになります。実際の最適化作業の多くは、GEMM ではなく GEMM の間のすき間にあります。
</div>

### メモリ階層

```
レジスタ             数十 KB/SM        数十 TB/s
L1 / 共有メモリ      ~256 KB/SM        ~20 TB/s
L2 キャッシュ        50 MB (H100)      ~5 TB/s
HBM (VRAM)           80–288 GB         2–8 TB/s     ← LLM のボトルネック
ホスト RAM           数 TB             ~64 GB/s (PCIe 5.0 x16)
```

### ルーフライン — どちら側にいるか

演算強度 = FLOPs ÷ 移動したバイト数。H100 SXM での分岐点は 989 TFLOPS ÷ 3.35 TB/s ≈ **295 FLOP/byte** です。これより下ならメモリ律速、上なら演算律速です。

- バッチ 1 の LLM デコード：演算強度は 2 前後で、H100 の演算能力の 1% 未満です。バッチ処理でスループットが何倍にもなるのはこのためです。
- 長いプロンプトの LLM プリフィル：数百で、演算律速です。Tensor コアが真価を発揮するのはここです。
- RMSNorm、残差加算：1–2 で、純粋なメモリ律速です。カーネル融合が存在する理由です。

### 現行のラインナップ（2026.09 時点のスペック）

| GPU | メモリ | 帯域幅 | NVLink | TDP | 主な用途 |
|---|---|---|---|---|---|
| L4 | 24 GB | 0.30 TB/s | — | 72 W | 軽い推論、動画 |
| RTX 4090 | 24 GB | 1.01 TB/s | — | 450 W | 開発、QLoRA |
| L40S | 48 GB | 0.86 TB/s | — | 350 W | 中規模の推論 |
| A100 80GB SXM | 80 GB | 2.04 TB/s | 600 GB/s | 400 W | コスト効率の良い学習 |
| H100 PCIe | 80 GB | 2.00 TB/s | 600 GB/s | 350 W | 汎用 |
| H100 SXM | 80 GB | 3.35 TB/s | 900 GB/s | 700 W | 学習の標準 |
| RTX PRO 6000 | 96 GB | ~1.8 TB/s | — | 600 W | ワークステーションでの推論 |
| H200 SXM | 141 GB | 4.80 TB/s | 900 GB/s | 700 W | 長コンテキストの推論 |
| B200 | 180 GB | ~8 TB/s | 1.8 TB/s | ~1000 W | 現世代の学習 |
| B300 | 288 GB | ~8 TB/s | 1.8 TB/s | ~1400 W | 大規模モデル |
| GB200/GB300 NVL72 | 72 GPU のドメイン | — | ラック全体 | ~130 kW/ラック | 最先端、液冷 |

覚えておくべき 3 点です。

1. **SXM と PCIe。** 3.35 TB/s 対 2.00 TB/s、そして 900 GB/s の NVLink 対 2 枚をつなぐブリッジです。マルチ GPU 学習では、SXM 以外では通信がボトルネックになります。
2. **L40S と RTX 系には NVLink がありません。** モデル並列が必要なモデルには使えず、1 枚に収まるモデル向けです。
3. **Blackwell 以降は、電力と冷却が本当の制約です。** Runpod のようなクラウドでは、それはあなたの問題ではなく価格と在庫として現れます。ただし、最新の製品ほど入手しにくいのはこのためです。

### 公称容量と実際に使える容量

「H100 80GB」でテンソルに 80 GB 使えるわけではありません。差は 3 か所で生じます。

**① 物理容量と製品スペック**

| GPU | 物理構成 | 物理容量の合計 | スペック | 理由 |
|---|---|---|---|---|
| H100 SXM | HBM3 16GB × 6 サイト、5 つが有効 | 96 GB | 80 GB | 歩留まりのため 1 スタックを無効化 |
| H200 SXM | HBM3e 24GB × 6 | 144 GB | 141 GB | 行の冗長化と内部予約（非公開） |
| B200 | HBM3e、2 スタックに 8 チップ | 192 GB | 180–192 GB | SKU とプロバイダによって異なる。Runpod は 180 GB と表示 |

**② `nvidia-smi` が報告する値** — 単位は MiB です。NVIDIA の「80GB」は実質 80 GiB（10 進で 85.9 GB）です。`torch.cuda.get_device_properties(0).total_memory` はバイト単位なので、1024³ で割ると一致します。

```
A100 80GB   81,920 MiB  =  80.0 GiB
H100 80GB   81,559 MiB  =  79.6 GiB
A100 40GB   40,536 MiB  =  39.6 GiB
```

**③ テンソルを割り当てる前に消費されるもの**

| 消費元 | サイズ | 備考 |
|---|---|---|
| CUDA コンテキスト | 300–600 MB | プロセスごと。複数プロセスでは倍増する |
| cuDNN / cuBLAS のワークスペース | 数百 MB〜数 GB | カーネルの選択によって変わる |
| NCCL バッファ | 数百 MB | マルチ GPU の場合のみ |
| アロケータの断片化 | 5–10% | 可変長シーケンスで悪化する |

HBM の製品（A100、H100、H200、B200 — オンダイ ECC）では、ECC のコストは目に見えません。L40S や RTX A6000 のような GDDR の製品では、ECC を有効にすると 16 分の 1（6.25%）を失い、48 GB がおよそ 45 GB になります。

**サイジングの上限 = 公称値 × 0.90〜0.93。** H100 80GB なら 72–74 GB を前提に設計します。FP8 の 70B（重み 70 GB）が紙の上では「80 GB に収まる」のに、実際には起動しないのはこのためです。

<div class="note" markdown="1">
**ここで測定したもの。** Runpod Secure Cloud の Pod での `nvidia-smi`、2026-11-07（[クラスタラボ 01]({{ '/cluster/' | relative_url }})）：A100-SXM4-80GB は **81,920 MiB**、RTX 4090 は **24,564 MiB**。
</div>

### インターコネクト

| 経路 | 帯域幅 | 備考 |
|---|---|---|
| PCIe 4.0 x16 | 32 GB/s | 旧世代のサーバー |
| PCIe 5.0 x16 | 64 GB/s | 現行 |
| NVLink 4（Hopper） | 900 GB/s | GPU 間を直接接続 |
| NVLink 5（Blackwell） | 1.8 TB/s | |
| NVSwitch | ノード内のフルメッシュ | DGX / HGX |
| InfiniBand NDR | 400 Gb/s = 50 GB/s | ノード間 |
| RoCE v2 | Ethernet ベース | 安価だがチューニングが難しい |

集合通信（AllReduce、AllGather、ReduceScatter、Broadcast）は NCCL が担います。データ並列学習は毎ステップ勾配の AllReduce を行い、その量はパラメータ数に比例します。FP16 の 7B モデルならステップあたり 14 GB です。64 GB/s の PCIe ではこれを運びきれないのはこのためです。

FP32 の TFLOPS は LLM のワークロードについてほとんど何も教えてくれません。重要な数値は 3 つです。実際に使う精度での密な Tensor コアのスループット、HBM の容量、HBM の帯域幅です。学習では Tensor コアのスループットと NVLink です。推論ではまず容量と帯域幅です。デコードは帯域幅律速なので、FP8 の数値がそこそこ良い L40S でも、単一モデルの推論では A100 に負けます。GDDR6 で 864 GB/s だからです。

<div class="note" markdown="1">
**ここで測定したもの。** GPU 2 基、Pod 1 台、同じ 1 億 100 万パラメータの DDP ジョブ（[クラスタラボ 01]({{ '/cluster/' | relative_url }})、2026-11-07）：RTX 4090 のペアは NUMA ノードをまたぐ PCIe（`SYS`）で、NCCL はホストメモリを経由し、all-reduce は **15.6 GB/s**、2 枚での学習は 1 枚より **2.4 倍遅く**なりました。A100 SXM のペアは `NV12` で **201 GB/s**、スケーリングは 91% でした。トポロジーの詳細は [GPU Topology]({{ '/readings/gpu-topology/' | relative_url }})にあります。
</div>

## 精度
{: #precision-ja }

精度を変えるだけで、同じシリコンでスループットが 15 倍変わります。そして精度を下げる本当の理由は、速度よりもメモリであることが多いのです。

| 形式 | ビット数 | パラメータあたり | 使われる場所 |
|---|---|---|---|
| FP32 | 32 | 4 B | オプティマイザのマスター重み。演算経路になることはまれ |
| TF32 | 19（32 として格納） | 4 B | Ampere 以降、許可されていれば FP32 の行列積をこれで高速化 |
| FP16 | 16 | 2 B | 指数の範囲が狭く、ロススケーリングが必要 |
| BF16 | 16 | 2 B | FP32 と同じ指数範囲。現在の学習の既定 |
| FP8（E4M3 / E5M2） | 8 | 1 B | Hopper 以降。推論の標準になりつつある |
| INT8 | 8 | 1 B | 学習後の量子化（SmoothQuant、AWQ） |
| NF4 / INT4 | 4 | 0.5 B | QLoRA。ここで品質の劣化が目に見えてくる |
| FP4 / FP6 | 4 / 6 | 0.5 / 0.75 B | Blackwell で新たに追加 |

**同じ H100 SXM で精度を変えた場合**

| 精度 | 密な TFLOPS | FP32 比 |
|---|---|---|
| FP64 | 34 | 0.5× |
| FP32（CUDA コア） | 67 | 1× |
| TF32（Tensor コア） | 495 | 7.4× |
| FP16 / BF16 | 989 | 14.8× |
| FP8 | 1,979 | 29.5× |

### dense と sparse — 1 つの言葉、2 つの意味

**スループットの数値では**、「dense（密）」は 2:4 構造化スパース性なしを意味します。Ampere 以降、重みが 4 つずつのグループで非ゼロが最大 2 つなら、Tensor コアはゼロをスキップでき、同じ時間で 2 倍の行列積をこなします。スペックシートの数値が 2 倍になるのはこのためです（H100 FP8：密で 1,979、スパースで 3,958）。これを得るには、モデルをこのパターンに枝刈りして再学習し、cuSPARSELt か TensorRT で実行する必要があります。本番の LLM でこれを行うことはまれで、そもそもデコードは帯域幅律速です。スペックは密の数値で比較してください。「H100 は 4 ペタフロップス」はほぼ必ず FP8 スパースの値です。

**モデル名の横では**、「dense」は Mixture of Experts ではないことを意味します。すべてのトークンがすべてのパラメータを通ります（Llama 3 70B）。一方 MoE は各トークンを上位 k 個のエキスパートに振り分けます（Mixtral 8×7B、DeepSeek-V3）。

### Tensor コアの世代

| 世代 | アーキテクチャ | 追加されたもの |
|---|---|---|
| 第 1 世代 | Volta（V100） | FP16 |
| 第 2 世代 | Turing（T4） | INT8、INT4 |
| 第 3 世代 | Ampere（A100） | TF32、BF16、構造化スパース性 |
| 第 4 世代 | Hopper（H100/H200） | FP8、Transformer Engine、非同期 WGMMA |
| 第 4 世代 | Ada（L40S、RTX 40） | FP8。ただし FP32 累算の経路はレートが制限されている |
| 第 5 世代 | Blackwell（B200/B300、RTX PRO 6000） | FP4/FP6、第 2 世代 Transformer Engine |

Transformer Engine は実行時にレイヤーごと・テンソルごとに FP8 か BF16 を選び、スケーリング係数を管理します。FP8 での学習が実用的なのはこのおかげです。

<div class="warn" markdown="1">
**Tensor コアが遊んでしまう理由。** Tensor コアはスイッチで有効にするものではなく、条件が満たされたときに使われ、満たされなければ黙ってフォールバックします。純粋な FP32 で学習すると、H100 で 989 ではなく 67 TFLOPS になります。`allow_tf32 = False`（PyTorch の行列積の既定）では、FP32 の行列積でさえ Tensor コアを使いません。隠れ次元が 8 や 16 の倍数でないと遅いカーネルが選ばれます（語彙が 32,000 から 32,768 にパディングされるのはこのためです）。cuBLAS や CUTLASS を通らない自作カーネルは、Tensor コアに到達しません。
</div>

<div class="note" markdown="1">
**ここで測定したもの。** クラスタラボのモデルは、TF32 オフの素の FP32 で動きます。GPU 1 基では、RTX 4090 が毎秒 **39,453** サンプル、A100 SXM が **23,132** サンプルで学習しました。A100 が負けたのは Tensor コアが遊んでいたからで、4090 のほうが FP32 の CUDA コアのスループットが高いのです。A100 の強みは BF16/TF32 とリンクであって、FP32 ではありません。
</div>

精度を下げるのは、速度よりもメモリのためであることが多いです。デコードは帯域幅律速なので、重みあたりのバイト数を半分にするとトークンレートはほぼ 2 倍になり、KV キャッシュの余地も空きます。8 ビット未満では品質の低下が現れ始めるので、4 ビットは出荷前に自分の評価データで確認してください。

## サイジングの式
{: #sizing-ja }

4 つの式があれば、「7B には何が必要か」という問いに、正しい条件を聞き返したうえで数値を出して答えられます。

```
① 学習メモリ = 16N バイト (FP16 + AdamW) · 8-bit Adam なら 10N · LoRA は 2N + α
② 学習 FLOPs  = 6 × params × tokens     (順伝播 2N + 逆伝播 4N)
   推論 FLOPs = 2 × params × tokens
③ トークンあたりの KV キャッシュ = 2 × layers × KV heads × head_dim × 要素あたりのバイト数
④ デコードの上限 = HBM 帯域幅 ÷ モデルのバイト数      (単一ストリーム、tok/s)
```

同じ 7B でも、方法によって 8 GB から 110 GB 超まで変わります。だから最初の質問は常に、フルファインチューニングか PEFT か、精度をどこまで下げられるか、最終的にどのコンテキスト長で提供するか、です。

### ① 学習メモリの行き先

| 構成要素 | バイト数 | 7B の場合 | 存在する理由 |
|---|---|---|---|
| FP16 の重み | 2N | 14 GB | 順伝播と逆伝播の計算 |
| FP16 の勾配 | 2N | 14 GB | 逆伝播の出力 |
| FP32 のマスター重み | 4N | 28 GB | 精度を落とさずに更新する |
| Adam の 1 次モーメント m | 4N | 28 GB | オプティマイザの状態 |
| Adam の 2 次モーメント v | 4N | 28 GB | オプティマイザの状態 |
| **小計** | **16N** | **112 GB** | これに加えてアクティベーション |

7B のフルファインチューニングは 80 GB のカード 1 枚には収まりません。ZeRO-3 か FSDP で 2 枚が最低ラインで、アクティベーションの余裕を考えると 4 枚が現実的です。

AdamW はすべてのパラメータについて 2 つの履歴を保持します。**m** は最近の勾配の移動平均、**v** はその分散で、どちらも FP32 です。パラメータあたり 8 バイトで、112 GB のうち 84 GB がオプティマイザ関連なのはこのためです。**8-bit Adam**（bitsandbytes）は m と v を 8 ビットで保存します。その 56 GB が 14 GB になり、合計は約 70 GB に下がります。品質の低下は十分小さいので、日常的に有効にされています。

| 手法 | 効果 | コスト |
|---|---|---|
| 8-bit Adam | オプティマイザ 8N → 2N、合計 16N → 10N | ほぼなし |
| 勾配チェックポイント | アクティベーションのメモリが大きく減る | 計算が約 30% 増える |
| ZeRO-1 / -2 / -3、FSDP | オプティマイザ、次に勾配、次にパラメータをシャーディング | 段階ごとに通信が増える |
| LoRA | 学習対象が 0.1–1% に減る | 表現力が限られる |
| QLoRA NF4 | 4 ビットで凍結したベース | 学習が遅くなる |
| CPU / NVMe オフロード | メモリの問題は解決する | スループットが崩壊する。最後の手段 |

### ③ KV キャッシュ — 推論のメモリ問題

| モデル | アテンションの形 | トークンあたり | 32k コンテキスト、リクエスト 1 件 |
|---|---|---|---|
| Llama-2-7B | MHA · 32 レイヤー · KV ヘッド 32 · head_dim 128 | 512 KB | 16 GB |
| Llama-3-8B | GQA · 32 レイヤー · KV ヘッド 8 · head_dim 128 | 128 KB | 4 GB |
| Llama-3-70B | GQA · 80 レイヤー · KV ヘッド 8 · head_dim 128 | 320 KB | 10 GB |

GQA で 4 分の 1 になります。最近のモデルがすべて GQA か MQA を使うのはこのためで、FP8 の KV キャッシュにするとさらに半分になります。

<div class="note" markdown="1">
**ここで測定したもの。** 推論スイープ（[FINDINGS](https://github.com/litkhai/runpod-hols/blob/main/inference-characterization/FINDINGS.md)）は、1 つの vLLM イメージを 9 種類の GPU で実行しました。vLLM のプリエンプションカウンタ（KV キャッシュが満杯になって追い出されたリクエスト）が増えたのは、**KV キャッシュが最も小さい 3 つの GPU だけ**でした。RTX 4090、L4、L40 です（C6）。KV キャッシュが 100 万トークン以上を保持する A100、H100、H200 では、プロンプトトークンの 97–100% がプレフィックスキャッシュから提供されました（C21）。
</div>

### 5 つのワークロード

| ワークロード | 7B の場合 | 何が変わるか | いつ使うか |
|---|---|---|---|
| 推論 | 14 GB + KV | 何も変えない。そのまま使う | サービスの運用 |
| フル FT（AdamW） | 112 GB | すべてのパラメータ | ドメインの語彙そのものが異なるとき |
| フル FT（8-bit Adam） | ~70 GB | すべてのパラメータ、軽いオプティマイザ | 同上、GPU が足りないとき |
| LoRA | ~19 GB | パラメータの 0.1–1% | ほとんどの要件はここで終わる |
| QLoRA | ~9 GB | 0.1–1%、ベースも圧縮 | 1 枚のカードでの実験 |

**LoRA** は元の重みを凍結し、その横に 2 つの小さな行列を置いて学習します。

```
通常       y = W · x            W 全体を学習 (4096×4096 = 16.8M params)
LoRA       y = W · x + B·A·x    W は凍結。A (4096×16) と B (16×4096) だけを学習
                                → 131K params、元の 0.8%
```

真ん中の 16 が **ランク** で、16〜64 が一般的な範囲です。凍結したベースには勾配もオプティマイザの状態も不要なのでメモリが激減し、結果は数十 MB のアダプタファイル 1 つになります。**QLoRA** はさらに凍結したベースを 4 ビット NF4 に圧縮し、各計算の間だけ FP16 に逆量子化します。ベースは 14 GB から 3.5 GB に下がり、7B のファインチューニングが 24 GB のカード 1 枚に載りますが、速度が犠牲になります。

<div class="calc" data-calc="vram" markdown="0">
  <div class="calc-hd"><b>VRAM サイジング</b><span>CALCULATOR 01</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>パラメータ数（B）</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>ワークロード</label><select data-f="mode"><option value="inf">推論</option><option value="lora">LoRA</option><option value="qlora">QLoRA（4 ビット）</option><option value="full">フル FT（AdamW）</option><option value="full8">フル FT（8-bit Adam）</option></select></div>
      <div><label>重みの精度</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1">FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>レイヤー数</label><input data-f="L" type="number" value="32" min="1"></div>
      <div><label>KV ヘッド数</label><input data-f="kh" type="number" value="8" min="1"></div>
      <div><label>head_dim</label><input data-f="hd" type="number" value="128" min="8"></div>
      <div><label>コンテキスト長</label><input data-f="ctx" type="number" value="8192" min="128" step="512"></div>
      <div><label>同時リクエスト数</label><input data-f="bs" type="number" value="8" min="1"></div>
      <div><label>KV の精度</label><select data-f="kp"><option value="2">FP16</option><option value="1">FP8</option></select></div>
    </div>
    <div class="calc-out">
      <div><span>重み（GB）</span><b data-o="w">–</b></div>
      <div><span>勾配 + オプティマイザ（GB）</span><b data-o="o">–</b></div>
      <div><span>KV キャッシュ（GB）</span><b data-o="k">–</b></div>
      <div><span>アクティベーション + オーバーヘッド（GB）</span><b data-o="a">–</b></div>
      <div class="hi"><span>合計（GB）</span><b data-o="t">–</b></div>
    </div>
    <div class="calc-bar" data-o="bar"><i></i><i></i><i></i><i></i></div>
    <div class="calc-key"><span><s class="k1"></s>重み</span><span><s class="k2"></s>勾配 + オプティマイザ</span><span><s class="k3"></s>KV キャッシュ</span><span><s class="k4"></s>アクティベーション</span></div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ④ デコードの上限

単一ストリームのトークンレートは、1 秒間に重みを何回読めるかで決まります。トークンを 1 つ生成するたびに、モデル全体を HBM から 1 回読み出すからです。

| 構成 | モデルのバイト数 | 上限 | 現実的な値（~70%） |
|---|---|---|---|
| H100 SXM（3.35 TB/s）上の 7B FP16 | 14 GB | 239 tok/s | ~167 |
| H100 SXM 上の 7B FP8 | 7 GB | 479 tok/s | ~335 |
| 2×H100（6.7 TB/s）上の 70B FP16 | 140 GB | 48 tok/s | ~34 |

<div class="calc" data-calc="decode" markdown="0">
  <div class="calc-hd"><b>デコードのスループットと推論コスト</b><span>CALCULATOR 02</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>GPU（Runpod Secure、2026-11-07）</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU 数</label><input data-f="n" type="number" value="1" min="1" max="8"></div>
      <div><label>パラメータ数（B）</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>重みの精度</label><select data-f="wp"><option value="2">FP16 / BF16</option><option value="1" selected>FP8 / INT8</option><option value="0.5">INT4</option></select></div>
      <div><label>同時リクエスト数</label><input data-f="b" type="number" value="32" min="1"></div>
      <div><label>平均コンテキスト長</label><input data-f="ctx" type="number" value="4096" min="128" step="512"></div>
      <div><label>トークンあたりの KV（KB）</label><input data-f="kv" type="number" value="128" min="1"></div>
    </div>
    <div class="calc-out">
      <div><span>単一ストリーム（tok/s）</span><b data-o="s">–</b></div>
      <div><span>帯域幅の上限（tok/s）</span><b data-o="bw">–</b></div>
      <div><span>演算の上限（tok/s）</span><b data-o="cl">–</b></div>
      <div class="hi"><span>総スループット（tok/s）</span><b data-o="t">–</b></div>
      <div class="hi"><span>出力 100 万トークンあたり（USD）</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

### ② 学習の時間とコスト

**MFU**（Model FLOPs Utilization）は、達成した FLOPS をピークで割ったものです。よくチューニングされた大規模学習は 40–50% に収まり、30% 未満なら何かがおかしいということです。

<div class="calc" data-calc="train" markdown="0">
  <div class="calc-hd"><b>学習の時間とコスト</b><span>CALCULATOR 03</span></div>
  <div class="calc-bd">
    <div class="calc-grid">
      <div><label>パラメータ数（B）</label><input data-f="p" type="number" value="7" min="0.1" step="0.1"></div>
      <div><label>トークン数（B）</label><input data-f="tok" type="number" value="1" min="0.001" step="0.1"></div>
      <div><label>方法</label><select data-f="m"><option value="6">フル FT（6N）</option><option value="5">LoRA（~5N）</option></select></div>
      <div><label>GPU（Runpod Secure、2026-11-07）</label><select data-f="gpu" data-gpus="h100"></select></div>
      <div><label>GPU 数</label><input data-f="n" type="number" value="8" min="1"></div>
      <div><label>MFU（%）</label><input data-f="mfu" type="number" value="40" min="5" max="70"></div>
    </div>
    <div class="calc-out">
      <div><span>総計算量（EFLOPs）</span><b data-o="f">–</b></div>
      <div><span>GPU 時間</span><b data-o="gh">–</b></div>
      <div><span>実時間（時間）</span><b data-o="w">–</b></div>
      <div class="hi"><span>推定コスト（USD）</span><b data-o="c">–</b></div>
    </div>
    <div class="calc-verdict" data-o="verdict">–</div>
  </div>
</div>

<div class="note" markdown="1">
**これらの計算機について。** 一次近似です。実際の数値は、フレームワーク、バッチの構成、シーケンス長の分布、スケジューラによって変わります。重要なのはどの変数が支配的かであって、正確な数値ではありません。FLOPS は密の値で、Blackwell の数値は概算です。価格は Runpod Secure Cloud のオンデマンドの GPU 時間あたりで、2026-11-07 にカタログから読み取りました。
</div>

## Transformer の概要
{: #transformer-ja }

デコーダレイヤー 1 つを最初から最後まで。何が Tensor コアで実行され、何が CUDA コアで実行されるか：

```
x                                        入力 [batch, seq, 4096]
h  = RMSNorm(x)                          CUDA
q  = h @ W_q ;  k = h @ W_k ;  v = h @ W_v   TENSOR  QKV 射影
q, k = RoPE(q, k)                        CUDA
k, v = KVCache.append(k, v)              CUDA    メモリ移動
s  = q @ kᵀ / √head_dim                  TENSOR  アテンションスコア
s  = causal_mask(s) ; p = softmax(s)     CUDA
o  = p @ v                               TENSOR  重み付き和
o  = o @ W_o                             TENSOR
x  = x + o                               CUDA    残差
h  = RMSNorm(x)                          CUDA
g  = h @ W_gate ;  u = h @ W_up          TENSOR  FFN
f  = SiLU(g) * u                         CUDA    活性化
x  = x + (f @ W_down)                    TENSOR + CUDA
── 32 回繰り返した後 ──
logits = RMSNorm(x) @ W_lm_head          TENSOR  32,000 語彙のスコア
token  = sample(logits)                  CUDA
```

FLOPs のほぼすべては Tensor コア上の GEMM です。それ以外はすべてメモリ律速です。

| 演算 | トークンあたりの移動バイト数（7B） | 演算強度 | 性質 |
|---|---|---|---|
| RMSNorm | ~1.6 MB | < 1 | リダクション、メモリ律速 |
| RoPE | ~0.7 MB | ~2 | メモリ律速 |
| 活性化（SwiGLU） | ~2.1 MB | ~1 | 要素ごとの演算で最大のテンソル |
| 残差 | ~1.6 MB | 0.17 | 極端なメモリ律速。H100 の分岐点の 1,700 分の 1 |
| Softmax | コンテキストに比例 | < 1 | 特殊関数ユニットとリダクション |
| KV のインデックス処理 | バッチ × コンテキストに比例 | ≈ 0 | 純粋なデータ移動 |
| サンプリング | バッチ × 語彙 | ソート | 分岐が多い |

実時間に占める割合は状況によって変わります。バッチ 1 のデコードでは重みの読み出しが支配的で、実際のコストはカーネル起動のオーバーヘッドです（レイヤーあたり十数個のカーネル × 32 レイヤー × 全トークン）。これを取り除くのが CUDA Graph です。プリフィルと学習では、アクティベーションがバッチ × シーケンスに比例し、この処理が実時間の 30–40% に達します。ここではカーネル融合が最大の手段です。FlashAttention はアテンションに対する同じ発想で、[n×n] のスコア行列が HBM に到達しないため、アテンションのメモリが O(n²) から O(n) になります。

トークンは BPE のサブワードです。語彙が十分にカバーしていない文字体系（多くのモデルでは韓国語、中国語、日本語を含む）では、同じ内容に 2〜3 倍のトークンがかかることがあり、価格とコンテキストの上限の両方に響きます。

## 学習
{: #training-ja }

目的は 1 つだけです。次のトークンを予測することです。損失 = −log P(正解トークン)。パープレキシティ = exp(損失) で、おおよそ「モデルが何個の選択肢の間で迷っているか」です。テキストそのものがラベルになります。1 つずらせば入力と正解になるので、インターネット規模のデータが使えるようになりました。

1 ステップは、**順伝播**（バッチを通してロジットと損失を得る。Tensor コア）、**逆伝播**（すべてのパラメータについての損失の勾配。順伝播の約 2 倍の計算）、**オプティマイザによる更新**（AdamW。だからパラメータごとに 2 つの追加の状態がある）です。サイジングの式の 16N のメモリと 6N の計算はここから直接出てきます。推論には順伝播しかないので、2N と 2N になります。

| 段階 | 何をするか | データ | コストの規模 |
|---|---|---|---|
| ① 事前学習 | 次トークン予測のみ。言語、知識、推論はここで形成される | 数兆トークン | 数千 GPU、数か月 |
| ② 教師ありファインチューニング（SFT） | 質問と回答の形式を教える。新しい能力ではない | 数万〜数十万の対話 | 数〜数十 GPU、数日 |
| ③ アラインメント（RLHF / DPO） | 好ましい応答へ誘導する | 選好ペア | ② と同等かそれ以上 |

知識は ① で入り、② と ③ はそれがどう表に出るかを形作ります。「社内の知識を注入するためにファインチューニングする」がたいてい失敗し、検索（RAG）が正しい手段なのはこのためです。ファインチューニングは形式、文体、ドメインの語彙のためのものです。

| 戦略 | 何を分割するか | 通信 | いつ使うか |
|---|---|---|---|
| DP — データ並列 | バッチ | ステップごとの勾配 AllReduce | モデルが GPU 1 基に収まる |
| ZeRO / FSDP | ステージ 1 オプティマイザ → 2 + 勾配 → 3 + パラメータ | ステージごとに増える | モデルが収まらない — 第一の選択肢 |
| TP — テンソル並列 | レイヤー内の行列 | レイヤーごとの AllReduce — 非常に重い | NVLink ドメイン内のみ |
| PP — パイプライン並列 | レイヤーのブロック | ステージの境界でのみ — 軽い | ノードをまたいだスケーリング |
| SP — シーケンス並列 | シーケンス長 | 中程度 | 長コンテキストの学習 |
| EP — エキスパート並列 | MoE のエキスパート | All-to-All | MoE モデル |

実用的な組み合わせは、ノード内で TP、ノード間で PP か FSDP です。TP をノードの境界の外まで広げると、InfiniBand でもスループットが崩壊します。数値は [GPU Topology]({{ '/readings/gpu-topology/#in-numbers-ja' | relative_url }})にあります。

**MoE** は各トークンを上位 k 個のエキスパートに振り分けます。メモリは総パラメータ数に、計算はアクティブなパラメータ数に比例します。総 200B / アクティブ 20B のモデルは 20B のように計算しますが、VRAM は 200B 分必要です。「MoE だから安い」は半分しか正しくありません。

<div class="note" markdown="1">
**ここで測定したもの。** GPU 2 基の Pod 1 台でのデータ並列（[クラスタラボ 01]({{ '/cluster/' | relative_url }})）：ステップあたり約 400 MB の FP32 勾配です。NVLink ではその all-reduce に約 2 ms かかり、ペアは 0.91 でスケールしました。ホストを経由する PCIe では、計算 6.5 ms に対して約 26 ms かかり、ペアは 0.21 でスケールしました。
</div>

## 推論とサービング
{: #inference-ja }

学習のコストは一度きりです。推論のコストはプロダクトが存続する限り発生し、ユニットエコノミクスを決めます。

| | プリフィル | デコード |
|---|---|---|
| 処理 | プロンプト全体を並列に | 1 トークンずつ |
| ボトルネック | 演算律速 | メモリ帯域幅律速 |
| 指標 | TTFT — 最初のトークンまでの時間 | TPOT / ITL — トークン間のレイテンシ |
| 手段 | チャンク化プリフィル、プレフィックスキャッシュ | 量子化、バッチ処理、投機的デコーディング |
| 7B での体感 | 1,000 トークンのプロンプト ≈ 35 ms | トークンあたり：計算 0.035 ms、メモリ 4.2 ms |

計算 0.035 ms に対して読み出し 4.2 ms、120 倍の差です。だからバッチ処理は任意ではありません。GPU がコストに見合うには、多くのリクエストが 1 回の重みの読み出しを共有しなければなりません。長コンテキストのサービスの中には、両者の性質が干渉し合うため、プリフィルとデコードを別々の GPU プールに置くもの（disaggregated serving）も出てきています。

| 手法 | 仕組み | 効果 |
|---|---|---|
| Continuous batching | スロットが空いた瞬間に新しいリクエストを受け入れる | スループット 2–5 倍 |
| PagedAttention | OS のページングのように KV キャッシュをブロック単位で管理する | 断片化で失われていたメモリの 60–80% を回収 |
| プレフィックスキャッシュ | 共通のプロンプトプレフィックスの KV を再利用する | RAG やエージェントで TTFT を大きく削減 |
| 投機的デコーディング | 小さなドラフトモデルが提案し、大きなモデルが 1 パスで検証する | 2–3 倍、出力は同一 |
| FlashAttention | タイル化した融合カーネル。スコア行列が HBM に触れない | メモリ O(n²)→O(n)、2–4 倍 |
| 量子化 | FP8/INT8 の重み（AWQ、GPTQ）、FP8 の KV キャッシュ | メモリ半分、速度向上 |
| チャンク化プリフィル | 長いプロンプトを分割してデコードと交互に処理する | 長いリクエストが短いリクエストをブロックしなくなる |

**カーネル** は GPU 上で起動される 1 つの関数です。起動ごとに数マイクロ秒かかり、さらに重要なのは HBM の往復が発生することです。RMSNorm と残差を 1 つのカーネルに融合すると、書き込みと読み出しが丸ごと 1 回ずつ省けます。帯域幅律速の処理では 2–3 倍の価値があります。`torch.compile` はこれを自動化します。OpenAI の Triton はそうしたカーネルを書く言語です（サービングのフロントエンドである NVIDIA の Triton Inference Server と混同しないでください）。

**3 つの指標：** TTFT（体感の応答性）、TPOT/ITL（読む速さ。人間には 20–30 tok/s で十分）、スループット（単価）。TTFT とスループットはトレードオフの関係にあり、バッチを大きくするとスループットと個々のレイテンシの両方が上がります。ワークロードごとに別々の目標を設定してください。

| スタック | 特徴 | いつ使うか |
|---|---|---|
| vLLM | PagedAttention の発祥、OpenAI 互換 API、既定で continuous batching | 既定の選択肢 |
| SGLang | RadixAttention によるプレフィックスキャッシュ、構造化出力 | エージェントと RAG のワークロード |
| TensorRT-LLM | NVIDIA 純正。最高性能、モデルごとのエンジンビルド | 固定モデル、最大性能 |
| Triton Inference Server | マルチモデル、マルチフレームワークのフロントエンド | 1 つのエンドポイントの背後に多数のモデル |
| Ollama / llama.cpp | GGUF、CPU とエッジ | ローカル、デモ |

推論モデルは出力トークンを何倍にも増やし、デコードのスループットがプロダクトのコストになります。だから、トークンあたりの価格ではなく、リクエストあたりの想定トークン数でコストをモデル化してください。

<div class="note" markdown="1">
**ここで測定したもの。** これらのラボは vLLM でサービングしています（[Serverless ラボ 03]({{ '/serverless/' | relative_url }})、推論スイープ）。コールドな Serverless worker では、同じイメージとモデルで、vLLM の CUDA Graph キャプチャだけで、あるホストでは 9 秒、他のホストでは 62–73 秒かかりました（C19）。起動オーバーヘッドの対策そのものが、コールドスタートのたびに支払われるのです。
</div>

## Runpod に当てはめた運用
{: #operations-ja }

**バージョンの組み合わせ。** ホストのドライバ → CUDA ツールキット → コンテナ。コンテナ内の CUDA は、ホストのドライバがサポートするバージョン以下でなければなりません。Runpod ではイメージはあなたが選び、ドライバはホストが決めます。

<div class="note" markdown="1">
**ここで測定したもの。** 16 GB/24 GB の Serverless プールが RTX PRO 6000 Blackwell の MIG スライス（sm_120）を割り当てました。CUDA 12.6 の PyTorch イメージは sm_90 までしか対応しておらず、worker は `no kernel image is available` で落ちました（[Serverless ラボ 02]({{ '/serverless/' | relative_url }})）。現在コンソールは GPU を *Previous* と *Latest generation* に分けており、後者には CUDA 12.8 以上のイメージが必要です。
</div>

**何を見るか。** `utilization.gpu` ではなく、SM 占有率とメモリ帯域幅の使用率です。`nvidia-smi` の GPU-Util はカーネルが常駐していた時間の割合なので、デバイスの 1% しか使わないカーネルでも 100% と表示されます。

<div class="note" markdown="1">
**ここで測定したもの。** 2× RTX 4090 の実行中、コンソールの Telemetry は 2 基とも **100%** を示していましたが、ペアの学習速度は理想の 5 分の 1 でした。カーネルは PCIe を待つ NCCL だったのです（[スクリーンショット]({{ '/cluster/' | relative_url }})）。
</div>

| 症状 | 原因と対処 |
|---|---|
| メモリが空いているように見えるのに CUDA OOM | 断片化 → `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` |
| 突然の性能低下 | 熱または電力によるスロットリング → `nvidia-smi -q -d PERFORMANCE` |
| Xid エラー | カーネルログ：13/31 はアプリケーションの障害、48/63/64 は ECC、79 は GPU がバスから外れた |
| NCCL のタイムアウト | トポロジーまたはインターフェース → `NCCL_DEBUG=INFO`、`nvidia-smi topo -m`。Instant Clusters では `NCCL_SOCKET_IFNAME=ens1` を設定 |
| 数分かかるコールドスタート | モデルの重みの取得 → 重みをイメージに入れない（下記） |
| 学習の MFU が 30% 未満 | データローダ、通信、またはバッチが小さすぎる → フェーズごとにプロファイル |

**コールドスタート。** 数十 GB のイメージに焼き込んだ重みは、取得に数分かかります。重みはイメージの外に置き、キャッシュかボリュームから読み込んでください。mmap を使う `safetensors` なら、必要なテンソルだけがページインされます。Serverless では、プラットフォームがこのうち 3 つの手段を提供しています。エンドポイントの **Model** フィールドは Hugging Face の重みをホストにキャッシュし、ネットワークボリュームは worker をまたいで重みを保持し、FlashBoot は停止した worker の状態を保持して高速に再起動します。

<div class="note" markdown="1">
**ここで測定したもの。** 推論スイープの vLLM エンドポイントで記録されたコールドスタートはすべて、FlashBoot のオン・オフにかかわらず、新しいコンテナを作成して 14.19 GiB の重みを再ダウンロードしました（C17）。FlashBoot をオンにしてアイドルタイムアウトを 5 秒にすると、15 秒と 30 秒の間隔のリクエストは同じコンテナを再利用しました（`delayTime` 1.9 秒と 1.3 秒）。60 秒の間隔からは、毎回新しいコンテナで 97–104 秒かかりました（C22）。Model 2026-11-07 に FlashBoot を Standard にしたところ、30〜120 秒の間隔でもコンテナが再利用されました（1.1〜1.2 秒）。再利用の幅が広がっています（C34）。 重みを network volume に置くとさらに遅くなりました——[Storage]({{ '/readings/storage/#model-weights-ja' | relative_url }}) を参照（C35）。 フィールドとコールドスタートの各段階については [Serverless]({{ '/serverless/' | relative_url }}) を参照してください。
</div>

## コスト
{: #cost-ja }

```
出力 100 万トークンあたりの推論コスト = (時間あたりの価格 ÷ 3600) ÷ スループット (tok/s) × 1,000,000
```

H100 SXM 1 基で FP8 の 7B を continuous batching で 3,000 tok/s 出す場合：1,000,000 ÷ 3,000 = 333 秒 = 0.093 時間、× USD 3.99 = **出力 100 万トークンあたり約 USD 0.37** です。これを API の価格と比べれば、セルフホストの損益分岐点が見えてきます。

**実効コスト = 時間あたりの価格 ÷ 実際の使用率。** USD 3.99 の GPU を 20% の時間しか使わなければ、実質的に時間あたり約 USD 20 かかります。これが Serverless とオートスケーリングを使う理由であり、コールドスタートが重要な指標である理由です。

Runpod の Pod の GPU 時間あたりの価格、2026-11-07 にカタログから読み取り：

| GPU | VRAM | Secure Cloud | Community Cloud |
|---|---|---|---|
| L4 | 24 GB | 0.59 | 0.44 |
| RTX 4090 | 24 GB | 0.89 | 0.34 |
| L40S | 48 GB | 1.09 | 0.79 |
| A100 SXM | 80 GB | 1.79 | 1.39 |
| H100 PCIe | 80 GB | 2.89 | 1.99 |
| RTX PRO 6000 | 96 GB | 2.49 | 1.69 |
| H100 SXM | 80 GB | 3.99 | 2.69 |
| H200 SXM | 141 GB | 5.29 | 3.59 |
| B200 | 180 GB | 7.99 | 5.98 |
| B300 | 288 GB | 8.99 | 6.94 |

| 形態 | 価格 | リスク |
|---|---|---|
| オンデマンド | 基準 | なし |
| スポット / コミュニティ | 安い — 上の表では 22–62% | プリエンプションまたは保証が弱い。チェックポイントが必須 |
| リザーブド / コミット | 30–50% 安い | 1–3 年の拘束、世代交代のリスク |
| 自社構築 | 長期的には最安 | スペース、電力、冷却、減価償却、人員 |

8×H100 サーバーはおよそ USD 25–30 万です。3 年間で、電力、スペース、人件費を除いて GPU 時間あたり USD 1.2–1.5 になります。セルフホストが勝つのは、3 年間 60% 以上の使用率を維持できる場合だけで、ほとんどのチームにはできません。そして NVIDIA が毎年アーキテクチャを更新する以上、精度やメモリの前提をハードコードするのではなく、CUDA、CUTLASS、Triton を前提に構築してください。

<div class="note" markdown="1">
**ここで測定したもの。** Community Cloud は安価ですが、パブリック IP を指定して作成した Community の RTX 4090 Pod は、15 分以内にパブリック IP も SSH ポートも得られませんでした（C7）。[クラスタ]({{ '/cluster/' | relative_url }})と [Pod]({{ '/pod/' | relative_url }}) のラボは Secure Cloud で実行しています。
</div>

## 用語集
{: #glossary-ja }

| 用語 | 分野 | 意味 |
|---|---|---|
| AllReduce | 分散 | すべての GPU にわたって合計し、結果を配布する NCCL の集合通信。データ並列学習の毎ステップで行われる |
| AWQ / GPTQ | 推論 | アクティベーションの統計を使って重要なチャネルを保持する、学習後の重み量子化 |
| BF16 | 精度 | FP32 と同じ指数範囲を持つ 16 ビット。学習の既定 |
| BPE | トークナイザ | Byte-Pair Encoding。頻出するペアを結合してサブワード語彙を作る |
| busbw / algbw | 診断 | nccl-tests の出力。リンクの使用率は busbw で判断する |
| Continuous batching | 推論 | スロットが空いた瞬間に新しいリクエストを受け入れる。スループット 2–5 倍 |
| CUDA コア | ハードウェア | スカラー FMA ユニット。汎用だが行列積は遅い |
| CUDA Graph | 最適化 | カーネル起動の列をキャプチャして再生する。バッチ 1 のデコードで起動オーバーヘッドを取り除く |
| DCGM | 運用 | Data Center GPU Manager。GPU のテレメトリを出力する |
| FlashAttention | カーネル | タイル化した融合カーネルとしてのアテンション。[n×n] 行列が HBM に到達しない |
| FSDP | 分散 | Fully Sharded Data Parallel。PyTorch ネイティブで、ZeRO-3 に相当 |
| GEMM | 演算 | General Matrix Multiply。Tensor コアが実行する唯一の形 |
| GQA / MQA | アーキテクチャ | Grouped- / Multi-Query Attention。KV ヘッドを減らし、キャッシュを 4–8 分の 1 にする |
| 勾配チェックポイント | 学習 | アクティベーションを保存せず逆伝播で再計算する。メモリは減り、計算は +30% |
| HBM | ハードウェア | High Bandwidth Memory。GPU の VRAM で、2–8 TB/s |
| KV キャッシュ | 推論 | 過去のトークンの K と V を保存したもの。推論メモリの支配的な項 |
| LoRA / QLoRA | 学習 | 凍結したベース上の低ランクアダプタ。QLoRA は 4 ビット NF4 のベースを加える |
| MBU / MFU | 指標 | 達成値と理論値の比（帯域幅 / FLOPS）。大規模では MFU 40–50% が普通 |
| MIG / MPS | 運用 | ハードウェア分割 / プロセス共有。[GPU Topology]({{ '/readings/gpu-topology/' | relative_url }})を参照 |
| MoE | アーキテクチャ | Mixture of Experts。メモリは総パラメータ数に、計算はアクティブなパラメータ数に比例 |
| NCCL | 分散 | NVIDIA Collective Communications Library |
| NVLink ドメイン | ハードウェア | NVSwitch のフルメッシュでつながった GPU 群。TP の次数の上限 |
| PagedAttention | 推論 | ブロック単位の KV キャッシュ管理。vLLM の中核 |
| プリフィル / デコード | 推論 | プロンプトの並列処理と 1 トークンずつの生成。ボトルネックが正反対 |
| ルーフライン | 性能 | 演算強度によって処理を演算律速かメモリ律速かに分類する |
| 投機的デコーディング | 推論 | ドラフトが提案し、ターゲットが 1 パスで検証する。2–3 倍、出力は同一 |
| Tensor コア | ハードウェア | 行列積ユニット。低精度の入力、FP32 で累算 |
| TF32 | 精度 | Ampere 以降の Tensor コアで FP32 の行列積を実行できる 19 ビット形式。PyTorch の行列積では既定でオフ |
| TTFT / TPOT / ITL | 指標 | 最初のトークンまで / 出力トークンあたり / トークン間の時間 |
| vLLM | サービング | PagedAttention と continuous batching。事実上の既定エンジン |
| ZeRO | 分散 | DeepSpeed のシャーディング：ステージ 1 はオプティマイザ、2 は勾配、3 はパラメータ |
| 2:4 スパース性 | 精度 | 4 つの重みのうち 2 つがゼロ。マーケティング上の FLOPS はたいていこれを前提とする |

</div>
