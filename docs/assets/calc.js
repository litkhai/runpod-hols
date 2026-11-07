/* Sizing calculators for /readings/gpu-llm-basics/ (#58).
 *
 * Each language block carries its own copy of the markup; this script binds
 * every `.calc[data-calc]` it finds through data attributes, so ids never
 * collide across the four blocks. First-order approximations: the point is
 * which variable dominates, not an exact figure.
 *
 * /readings/gpu-llm-basics/ 의 계산기 (#58). 언어 블록마다 마크업이 따로
 * 있고, 이 스크립트가 data 속성으로 각 `.calc[data-calc]` 를 묶는다.
 */
(function () {
  'use strict';

  // Dense TFLOPS and bandwidth from vendor datasheets; price is Runpod Secure
  // Cloud on-demand per GPU-hour, read from the GraphQL catalogue 2026-11-07.
  // 연산 성능·대역폭은 제조사 자료, 가격은 2026-11-07 Runpod Secure Cloud 시간당.
  var GPUS = [
    { id: 'l4',    name: 'L4 24GB',           vram: 24,  bw: 0.30, fp16: 121,  fp8: 242,  price: 0.59 },
    { id: '4090',  name: 'RTX 4090 24GB',     vram: 24,  bw: 1.01, fp16: 165,  fp8: 330,  price: 0.89 },
    { id: 'l40s',  name: 'L40S 48GB',         vram: 48,  bw: 0.86, fp16: 181,  fp8: 366,  price: 1.09 },
    { id: 'a100',  name: 'A100 SXM 80GB',     vram: 80,  bw: 2.04, fp16: 312,  fp8: 624,  price: 1.79 },
    { id: 'h100p', name: 'H100 PCIe 80GB',    vram: 80,  bw: 2.00, fp16: 756,  fp8: 1513, price: 2.89 },
    { id: 'h100',  name: 'H100 SXM 80GB',     vram: 80,  bw: 3.35, fp16: 989,  fp8: 1979, price: 3.99 },
    { id: 'pro6k', name: 'RTX PRO 6000 96GB', vram: 96,  bw: 1.80, fp16: 503,  fp8: 1007, price: 2.49 },
    { id: 'h200',  name: 'H200 SXM 141GB',    vram: 141, bw: 4.80, fp16: 989,  fp8: 1979, price: 5.29 },
    { id: 'b200',  name: 'B200 180GB',        vram: 180, bw: 8.00, fp16: 2250, fp8: 4500, price: 7.99 },
    { id: 'b300',  name: 'B300 288GB',        vram: 288, bw: 8.00, fp16: 2250, fp8: 5000, price: 8.99 }
  ];

  var T = {
    en: {
      fits: 'Fits on <b>1 × {gpu}</b> ({h} GB headroom). ',
      nofit: 'Will not fit on one GPU: <b>{nh} × H100 80GB</b> or <b>{nb} × B200 180GB</b>. ',
      shardTrain: 'Shard with ZeRO-3 / FSDP. ',
      shardInf: 'Shard with tensor parallelism — that needs NVLink, so SXM-class parts only. ',
      ratio: 'That is <b>{r}×</b> the weight footprint.',
      lora: ' LoRA would bring it to roughly {g} GB.',
      kv: 'KV cache is <b>{p}%</b> of the total, at {kb} KB per token.',
      oom: '<b class="calc-bad">Out of VRAM</b> — needs {need} GB, has {have} GB. Cut batch or context, or add GPUs. ',
      using: 'Using {need} / {have} GB of VRAM. ',
      bound: 'Bound by <b>{what}</b>. Each decode step reads <b>{gb} GB</b>: {w}% weights, {k}% KV cache. ',
      bw: 'memory bandwidth', comp: 'compute',
      kvDom: 'KV reads now exceed weight reads — GQA, KV quantisation or a shorter context helps more than a bigger batch.',
      wDom: 'Weight reads still dominate, so a larger batch buys throughput almost linearly.',
      tOom: '<b class="calc-bad">Out of memory</b> — this method needs about {need} GB, only {have} GB is there. Use at least {n} GPUs, or LoRA. ',
      tFits: 'Memory about {need} / {have} GB — fits. ',
      tScale: 'Assumes {s}% scaling efficiency across {n} GPUs. ',
      tWall: 'Wall clock {wall}, cost {cost}. ',
      hours: '{v} hours', days: '{v} days',
      tMfu: 'Raising MFU from {m}% to 50% would bring the cost to ${c}.'
    },
    ko: {
      fits: '<b>{gpu} 1장</b>에 들어갑니다 (여유 {h} GB). ',
      nofit: 'GPU 한 장에 안 들어갑니다. <b>H100 80GB {nh}장</b> 또는 <b>B200 180GB {nb}장</b>. ',
      shardTrain: 'ZeRO-3 / FSDP 로 나눠야 합니다. ',
      shardInf: '텐서 병렬로 나눠야 하고, 이는 NVLink 가 필요하므로 SXM 계열만 됩니다. ',
      ratio: '가중치 크기의 <b>{r}배</b>입니다.',
      lora: ' LoRA 로 바꾸면 약 {g} GB 로 줄어듭니다.',
      kv: 'KV 캐시가 전체의 <b>{p}%</b>, 토큰당 {kb} KB 입니다.',
      oom: '<b class="calc-bad">VRAM 부족</b> — {need} GB 가 필요한데 {have} GB 뿐입니다. 배치나 컨텍스트를 줄이거나 GPU 를 늘리세요. ',
      using: 'VRAM {need} / {have} GB 사용. ',
      bound: '<b>{what}</b>에 묶입니다. 디코드 한 스텝에 <b>{gb} GB</b> 를 읽습니다: 가중치 {w}%, KV 캐시 {k}%. ',
      bw: '메모리 대역폭', comp: '연산',
      kvDom: 'KV 읽기가 가중치 읽기를 넘었습니다. 배치를 키우기보다 GQA, KV 양자화, 짧은 컨텍스트가 효과적입니다.',
      wDom: '아직 가중치 읽기가 지배적이라 배치를 키우면 처리량이 거의 선형으로 늘어납니다.',
      tOom: '<b class="calc-bad">메모리 부족</b> — 이 방식은 약 {need} GB 가 필요한데 {have} GB 뿐입니다. GPU 를 {n}장 이상 쓰거나 LoRA 로 바꾸세요. ',
      tFits: '메모리 약 {need} / {have} GB — 들어갑니다. ',
      tScale: 'GPU {n}장 확장 효율 {s}% 를 가정했습니다. ',
      tWall: '소요 시간 {wall}, 비용 {cost}. ',
      hours: '{v}시간', days: '{v}일',
      tMfu: 'MFU 를 {m}% 에서 50% 로 올리면 비용은 ${c} 가 됩니다.'
    },
    zh: {
      fits: '<b>1 × {gpu}</b> 即可容纳（余量 {h} GB）。',
      nofit: '单卡放不下：需要 <b>{nh} × H100 80GB</b> 或 <b>{nb} × B200 180GB</b>。',
      shardTrain: '用 ZeRO-3 / FSDP 切分。',
      shardInf: '用张量并行切分——这需要 NVLink，因此只能用 SXM 级别的卡。',
      ratio: '是权重大小的 <b>{r} 倍</b>。',
      lora: '改用 LoRA 约降到 {g} GB。',
      kv: 'KV cache 占总量的 <b>{p}%</b>，每个 token {kb} KB。',
      oom: '<b class="calc-bad">显存不足</b>——需要 {need} GB，只有 {have} GB。减小 batch 或上下文，或增加 GPU。',
      using: '显存使用 {need} / {have} GB。',
      bound: '瓶颈是<b>{what}</b>。每个 decode 步读取 <b>{gb} GB</b>：权重 {w}%，KV cache {k}%。',
      bw: '内存带宽', comp: '算力',
      kvDom: 'KV 读取已超过权重读取——GQA、KV 量化或更短的上下文比更大的 batch 更有效。',
      wDom: '权重读取仍占主导，因此增大 batch 几乎线性提升吞吐。',
      tOom: '<b class="calc-bad">内存不足</b>——该方式约需 {need} GB，只有 {have} GB。至少用 {n} 块 GPU，或改用 LoRA。',
      tFits: '内存约 {need} / {have} GB——放得下。',
      tScale: '假设 {n} 块 GPU 的扩展效率为 {s}%。',
      tWall: '耗时 {wall}，成本 {cost}。',
      hours: '{v} 小时', days: '{v} 天',
      tMfu: '把 MFU 从 {m}% 提到 50%，成本将降到 ${c}。'
    },
    ja: {
      fits: '<b>{gpu} 1 基</b>に収まります（余裕 {h} GB）。',
      nofit: 'GPU 1 基には収まりません：<b>H100 80GB × {nh}</b> または <b>B200 180GB × {nb}</b>。',
      shardTrain: 'ZeRO-3 / FSDP で分割します。',
      shardInf: 'テンソル並列で分割します。NVLink が必要なので SXM 系のみです。',
      ratio: '重みの <b>{r} 倍</b>です。',
      lora: 'LoRA にすれば約 {g} GB になります。',
      kv: 'KV キャッシュが全体の <b>{p}%</b>、1 トークンあたり {kb} KB です。',
      oom: '<b class="calc-bad">VRAM 不足</b>——{need} GB 必要で {have} GB しかありません。バッチかコンテキストを減らすか、GPU を増やしてください。',
      using: 'VRAM {need} / {have} GB を使用。',
      bound: '<b>{what}</b>で律速されます。デコード 1 ステップで <b>{gb} GB</b> を読みます：重み {w}%、KV キャッシュ {k}%。',
      bw: 'メモリ帯域', comp: '演算',
      kvDom: 'KV の読み出しが重みの読み出しを上回りました。バッチを増やすより GQA、KV 量子化、短いコンテキストが効きます。',
      wDom: 'まだ重みの読み出しが支配的なので、バッチを増やすとスループットはほぼ線形に伸びます。',
      tOom: '<b class="calc-bad">メモリ不足</b>——この方式は約 {need} GB 必要で {have} GB しかありません。GPU を {n} 基以上にするか LoRA にしてください。',
      tFits: 'メモリ約 {need} / {have} GB——収まります。',
      tScale: 'GPU {n} 基でスケーリング効率 {s}% を仮定。',
      tWall: '所要時間 {wall}、費用 {cost}。',
      hours: '{v} 時間', days: '{v} 日',
      tMfu: 'MFU を {m}% から 50% に上げると費用は ${c} になります。'
    }
  };

  function fmt(v, d) {
    if (!isFinite(v)) return '–';
    d = (d === undefined) ? 1 : d;
    if (v >= 1000) return Math.round(v).toLocaleString('en-US');
    return v.toFixed(d);
  }
  function tpl(s, o) { return s.replace(/\{(\w+)\}/g, function (_, k) { return o[k]; }); }
  function gpuById(id) {
    for (var i = 0; i < GPUS.length; i++) if (GPUS[i].id === id) return GPUS[i];
    return GPUS[5];
  }

  function bind(box) {
    var lang = (box.closest('.lang') || {}).getAttribute ? box.closest('.lang').getAttribute('data-lang') : 'en';
    var t = T[lang] || T.en;
    var f = function (k) { return box.querySelector('[data-f="' + k + '"]'); };
    var o = function (k) { return box.querySelector('[data-o="' + k + '"]'); };
    var num = function (k, def) { var v = parseFloat(f(k).value); return isFinite(v) ? v : def; };
    var kind = box.getAttribute('data-calc');

    box.querySelectorAll('select[data-gpus]').forEach(function (sel) {
      GPUS.forEach(function (g) {
        var op = document.createElement('option');
        op.value = g.id; op.textContent = g.name + ' · $' + g.price.toFixed(2) + '/hr';
        if (g.id === sel.getAttribute('data-gpus')) op.selected = true;
        sel.appendChild(op);
      });
    });

    function vram() {
      var P = Math.max(0.01, num('p', 7)), mode = f('mode').value, wp = parseFloat(f('wp').value);
      var L = Math.max(1, num('L', 32)), kh = Math.max(1, num('kh', 8)), hd = Math.max(1, num('hd', 128));
      var ctx = Math.max(1, num('ctx', 8192)), bs = Math.max(1, num('bs', 1)), kp = parseFloat(f('kp').value);
      var N = P * 1e9, GB = 1e9, training = mode !== 'inf';
      f('wp').disabled = training;
      var wBytes = mode === 'inf' ? N * wp : (mode === 'qlora' ? N * 0.5 : N * 2);
      var optBytes = 0;
      if (mode === 'full') optBytes = N * 14;                     // grad 2N + master 4N + m 4N + v 4N
      if (mode === 'full8') optBytes = N * 8;                     // grad 2N + master 4N + 8-bit m,v 2N
      if (mode === 'lora' || mode === 'qlora') optBytes = N * 0.005 * 16;
      var kvPerTok = 2 * L * kh * hd * kp;
      var kvBytes = training ? 0 : kvPerTok * ctx * bs;
      var wGB = wBytes / GB, oGB = optBytes / GB, kGB = kvBytes / GB;
      var aGB = training ? (0.2 * (N * 2 / GB) + 2) : (0.05 * wGB + 1.5);
      var tGB = wGB + oGB + kGB + aGB;
      o('w').textContent = fmt(wGB);
      o('o').textContent = training ? fmt(oGB) : '—';
      o('k').textContent = training ? '—' : fmt(kGB);
      o('a').textContent = fmt(aGB);
      o('t').textContent = fmt(tGB);
      var bar = o('bar').children, parts = [wGB, oGB, kGB, aGB];
      for (var i = 0; i < 4; i++) bar[i].style.width = (tGB > 0 ? parts[i] / tGB * 100 : 0) + '%';
      var single = null;
      for (var j = 0; j < GPUS.length; j++) if (GPUS[j].vram >= tGB) { single = GPUS[j]; break; }
      var msg;
      if (single) msg = tpl(t.fits, { gpu: single.name, h: fmt(single.vram - tGB) });
      else {
        msg = tpl(t.nofit, { nh: Math.ceil(tGB / (80 * 0.9)), nb: Math.ceil(tGB / (180 * 0.9)) });
        msg += training ? t.shardTrain : t.shardInf;
      }
      if (training) {
        msg += tpl(t.ratio, { r: fmt(tGB / (P * 2), 1) });
        if (mode === 'full') msg += tpl(t.lora, { g: fmt(P * 2 + 0.2 * P * 2 + 2) });
      } else {
        msg += tpl(t.kv, { p: fmt(tGB > 0 ? kGB / tGB * 100 : 0, 0), kb: fmt(kvPerTok / 1024, 0) });
      }
      o('verdict').innerHTML = msg;
    }

    function decode() {
      var g = gpuById(f('gpu').value), n = Math.max(1, num('n', 1)), P = Math.max(0.01, num('p', 7));
      var wp = parseFloat(f('wp').value), bs = Math.max(1, num('b', 1)), ctx = Math.max(1, num('ctx', 4096));
      var kvKB = Math.max(1, num('kv', 128));
      var N = P * 1e9, wBytes = N * wp, kvPerTok = kvKB * 1024;
      var bwTotal = g.bw * n * 1e12, vramTotal = g.vram * n;
      var stepBytes = wBytes + bs * kvPerTok * ctx, stepBytes1 = wBytes + kvPerTok * ctx;
      var single = bwTotal * 0.7 / stepBytes1;
      var bwTp = bwTotal * 0.7 / stepBytes * bs;
      var compTp = (wp >= 2 ? g.fp16 : g.fp8) * n * 1e12 * 0.30 / (2 * N);
      var total = Math.min(bwTp, compTp);
      var cost = (g.price * n / 3600) / total * 1e6;
      o('s').textContent = fmt(single, 0);
      o('bw').textContent = fmt(bwTp, 0);
      o('cl').textContent = fmt(compTp, 0);
      o('t').textContent = fmt(total, 0);
      o('c').textContent = '$' + (cost < 1 ? cost.toFixed(3) : cost.toFixed(2));
      var need = (wBytes + bs * kvPerTok * ctx) / 1e9 + 1.5;
      var msg = need > vramTotal ? tpl(t.oom, { need: fmt(need), have: vramTotal }) : tpl(t.using, { need: fmt(need), have: vramTotal });
      msg += tpl(t.bound, { what: bwTp <= compTp ? t.bw : t.comp, gb: fmt(stepBytes / 1e9),
                            w: fmt(wBytes / stepBytes * 100, 0), k: fmt((1 - wBytes / stepBytes) * 100, 0) });
      msg += (1 - wBytes / stepBytes) > 0.5 ? t.kvDom : t.wDom;
      o('verdict').innerHTML = msg;
    }

    function train() {
      var P = Math.max(0.01, num('p', 7)), D = Math.max(0.0001, num('tok', 1)), mult = parseFloat(f('m').value);
      var g = gpuById(f('gpu').value), n = Math.max(1, num('n', 1));
      var mfu = Math.min(70, Math.max(5, num('mfu', 40))) / 100;
      var flops = mult * P * 1e9 * D * 1e9;
      var gpuHr = flops / (g.fp16 * 1e12 * mfu) / 3600;
      var scale = n === 1 ? 1 : (n <= 8 ? 0.92 : 0.82);
      var wall = gpuHr / (n * scale), cost = gpuHr * g.price;
      var money = function (c) { return '$' + (c < 100 ? c.toFixed(0) : Math.round(c).toLocaleString('en-US')); };
      o('f').textContent = fmt(flops / 1e18, flops / 1e18 < 10 ? 2 : 0);
      o('gh').textContent = fmt(gpuHr, gpuHr < 10 ? 1 : 0);
      o('w').textContent = fmt(wall, wall < 10 ? 1 : 0);
      o('c').textContent = money(cost);
      var need = (mult === 6 ? P * 16 : P * 2.5) + 2, have = g.vram * n;
      var msg = need > have ? tpl(t.tOom, { need: fmt(need), have: have, n: Math.ceil(need / (g.vram * 0.9)) })
                            : tpl(t.tFits, { need: fmt(need), have: have });
      if (n > 1) msg += tpl(t.tScale, { s: Math.round(scale * 100), n: n });
      msg += tpl(t.tWall, { wall: wall < 24 ? tpl(t.hours, { v: fmt(wall, 1) }) : tpl(t.days, { v: fmt(wall / 24, 1) }), cost: money(cost) });
      msg += tpl(t.tMfu, { m: Math.round(mfu * 100), c: Math.round(cost * mfu / 0.5).toLocaleString('en-US') });
      o('verdict').innerHTML = msg;
    }

    var run = { vram: vram, decode: decode, train: train }[kind];
    if (!run) return;
    box.querySelectorAll('[data-f]').forEach(function (el) {
      el.addEventListener('input', run);
      el.addEventListener('change', run);
    });
    run();
  }

  function init() { document.querySelectorAll('.calc[data-calc]').forEach(bind); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
