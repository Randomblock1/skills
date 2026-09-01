# Technique catalog — GPU

Each entry: **mechanism → idiomatic shape → pays off when**. Mechanisms are
vendor-independent; the concrete shapes, attributes, tool commands, and per-generation
facts live in `references/backend-<name>.md` — read only the one matching the target.
Distilled from the NVIDIA CUDA C++ Best Practices and Programming Guides, Nsight Compute
docs, Volkov *Better Performance at Lower Occupancy* (GTC 2010), Williams/Waterman/
Patterson *Roofline*, Kirk & Hwu *PMPP* (4th ed.), Horace He *Making Deep Learning Go
Brrrr*, Simon Boehm's SGEMM ladder, AMD ROCm HIP performance guides and rocprof-compute
docs, Apple WWDC Metal-on-Apple-silicon sessions, the Arm Mali Best Practices guide,
CubeCL/wgpu/Triton/PyTorch docs. Vendor peak figures below are **ceilings** for roofline
arithmetic; real kernels reach a fraction (a well-tuned H100 FP16 GEMM lands around
70–75% of the spec number).

Contents: machine model · machine classes (dGPU / iGPU / APU / unified / Mali) · numbers
· catalog (global memory, on-chip & occupancy, control flow, compute, host↔device
pipeline, framework-level, concurrency) · already-free list · won't-do list ·
per-backend pointers.

## The machine model in one paragraph

A GPU is a bandwidth machine with a huge register file. Each SM/CU keeps many warps
(NVIDIA: 32 lanes; AMD CDNA: 64; AMD RDNA: 32; Apple: 32; Arm Mali Valhall: 16)
resident and switches among them for free, so a warp stalled ~hundreds of ns on DRAM
costs nothing *if* another warp is ready. Two quantities therefore decide almost
everything: **bytes moved per unit of useful work** (arithmetic intensity, FLOP/byte)
and **parallelism in flight** (occupancy × ILP per thread). Cache is small and shared,
prefetching is manual (async copies), branch prediction does not exist — lanes that
disagree serialize. Everything in the catalog reduces to: move fewer, wider, aligned
bytes; keep reused data on-chip; keep lanes agreeing; keep enough independent work
resident; and stop paying launch/transfer/sync tax per iteration.

## Machine classes

Decide this before any arithmetic. The class fixes which bandwidth applies and whether a
transfer step exists at all.

| Class | Transfer step? | Memory bandwidth (order) | Techniques that apply | Don't propose |
|---|---|---|---|---|
| **Discrete GPU over PCIe** (NVIDIA/AMD/Intel cards) | Yes — every byte crosses PCIe (≈16 / 32 / 64 GB/s one-way for Gen3/4/5 x16) | HBM 2–8 TB/s; GDDR6/6X/7 0.4–1.8 TB/s | Pin host memory, overlap copy/compute on streams, keep data resident, batch launches, CUDA/HIP graphs | Zero-copy for bulk data (PCIe-speed reads per access) |
| **Integrated GPU / APU sharing DRAM** (Intel iGPU, AMD APU incl. Strix-class, Rockchip/Qualcomm SoCs) | No — host-coherent/zero-copy possible | Shared LPDDR5/DDR5 ≈ 50–100 GB/s, split with the CPU; power/thermal budget shared | Fusion (every DRAM byte is scarce), smaller working sets, fp16, avoid copies entirely | Pinned memory, async transfer, "raise occupancy to hide DRAM" (bandwidth-bound, not latency-bound) |
| **Apple silicon** (M-series unified memory, TBDR) | No — `.shared` storage mode buffers | 68 GB/s (M1) → 546 GB/s (M4 Max) → 800 GB/s (Ultra); see backend-metal | Fusion, `Shared` buffers, `half`, threadgroup-memory frugality (occupancy) | Any transfer step; `.managed` (Intel-Mac only) |
| **Coherent CPU–GPU** (Grace Hopper NVLink-C2C, MI300A) | Migration or ATS access instead of copies | HBM plus a coherent link (≈900 GB/s C2C) | Prefetch/advise hints, locality — keep hot pages on the device | Naive host copies; assuming zero cost for CPU-resident pages |
| **CUDA/HIP managed memory on a discrete card** | Page migration on fault | Device bandwidth once resident; fault storms otherwise | `cudaMemPrefetchAsync`, `cudaMemAdvise` (`SetReadMostly`, `SetPreferredLocation`, `SetAccessedBy`), XNACK on AMD | Treating managed memory as free zero-copy |
| **Embedded Mali** (e.g. RK3588 Mali-G610, Valhall) | No — unified, tile-based | LPDDR4x/5 ≈ 30–100 GB/s total, thermally throttled | fp16/`mediump`, workgroup multiples of 16 (64 typical), ≤32 registers/thread, small tiles | Large working sets, fp32-everywhere, desktop-sized workgroups |

**When not to use the GPU at all** — compute the break-even before porting a CPU loop:
`bytes_in+out ÷ interconnect_BW + launches × ~5 µs` versus the CPU time. A problem that
finishes on the CPU in under a few hundred µs, is transfer-dominated, or is inherently
serial stays on the CPU; a CPU with AVX-512/NEON on data already in L2 often wins
outright. "Keep it on the CPU" is a finding.

## Numbers to do the arithmetic against (verify for the exact part)

- **Sector/line granularity** — NVIDIA: global memory moves in 32 B sectors, 4 sectors per
  128 B L1 line; a warp reading 32 consecutive 4 B words = 4 sectors (ratio 4.0, ideal);
  fully scattered = 32 sectors for the same 128 useful bytes (8× waste). AMD CDNA/RDNA:
  64 B cache lines at L2 (128 B on some parts); same principle. Apple/Mali: tile-based,
  cache-line details are opaque — reason in "contiguous per SIMD-group" terms.
- **Shared/LDS banks** — NVIDIA: 32 banks × 4 B, one word per bank per cycle (128 B/clk);
  AMD CDNA: 32 banks × 4 B, conflicts assessed per phase. Same-address broadcast is free.
- **Bandwidth ceilings (spec)** — H100 SXM 3.35 TB/s HBM3 (PCIe variant ≈2 TB/s); H200
  4.8 TB/s; MI300X 5.3 TB/s (256 MB Infinity Cache in front); consumer GDDR cards
  0.4–1.8 TB/s; Apple M-series 68–800 GB/s; LPDDR SoCs 30–100 GB/s.
- **Compute ceilings (spec, dense)** — H100 SXM: FP16/BF16 tensor ≈989 TFLOPS, FP8 ≈1979,
  TF32 ≈495, FP32 ≈67, FP64 ≈34 (FP64 tensor ≈67). MI300X: FP16 matrix ≈1307, FP32
  ≈163, FP64 ≈82. Consumer cards: FP64 is 1/32–1/64 of FP32. Ridge point = peak
  FLOP/s ÷ peak B/s ≈ **200–400 FLOP/byte** on data-center parts for the matrix
  precision (H100 FP16 ≈ 295).
- **Arithmetic-intensity ladder** — elementwise / norm / softmax ≈ 1–3 FLOP/B (always
  memory-bound; only fusion helps); batch-1 LLM decode GEMV ≈ 1; batch-32 decode ≈ 32
  (still memory-bound); prefill / training GEMM ≈ 100s (compute-bound); flash-attention
  prefill ≈ 50–200.
- **Interconnect, one-way per direction** — PCIe 3/4/5 x16 ≈ 15.8 / 31.5 / 63 GB/s;
  NVLink 3/4/5 per GPU aggregate bidirectional 600 / 900 / 1800 GB/s (halve for one-way).
  Vendors often quote bidirectional; check which.
- **Pinned vs pageable** — pageable `cudaMemcpy` stages through a driver buffer and
  caps around 3–4 GB/s on Gen3; pinned reaches the link rate (≈2× or better).
  `cudaMemcpyAsync` from *pageable* memory silently degrades to synchronous.
- **Launch overhead** — ≈3–7 µs per kernel launch on the CPU side, plus a few µs of
  inter-kernel gap; a Python-side Triton/PyTorch launch adds tens to hundreds of µs of
  interpreter and dispatch time. 100 serialized tiny kernels ≈ 0.3–0.7 ms of pure tax.
- **Latency ladder** — registers ≈ free; shared/L1 ≈ 20–30 cycles; L2 ≈ 200 cycles;
  DRAM ≈ 400–800 cycles (hundreds of ns). This is what occupancy/ILP must cover.
- **Occupancy limits (NVIDIA, typical)** — 64 K 32-bit registers per SM, 255 max per
  thread, 64 warps (2048 threads) per SM, 32 blocks per SM, 48 KB static shared per
  block (more via opt-in dynamic shared, up to ≈227 KB on Hopper). AMD: VGPR budget per
  SIMD decides waves/SIMD (up to 8); 64 KB LDS per CU on CDNA3. Query rather than assume.

## Global memory access

- **Coalescing** — the load/store unit merges a warp's addresses into the minimum set of
  aligned sectors; anything not stride-1-per-lane multiplies sectors. Shape: lane `i`
  touches `base + i` (unit stride across the warp), `base` 32/128 B aligned; 2D data via
  pitched allocations so each row starts aligned. Pays on **every** global-memory kernel
  whose per-lane stride ≠ 1 — the single highest-priority item in every vendor guide.
  Verify with sectors/request (NVIDIA target 4.0 for 4 B loads, 8.0 for 8 B, 16.0 for
  16 B).
- **AoS → SoA** — consecutive lanes reading one field of a struct touch every N-th word;
  a per-field array makes them contiguous. Shape: `float x[N], y[N], z[N]` or a
  `Line<T>`/`float4` layout when *all* fields are consumed together (that is already
  contiguous — leave it). Pays when lanes each read a subset of a struct's fields.
- **Vectorized loads/stores** — one 128-bit `LDG.128` / `global_load_dwordx4` moves 16 B
  per lane per instruction: fewer instructions, more bytes in flight per warp. Shape:
  `float4`/`int4`/`Line<f32, 4>`/`vec4<f32>` on 16 B-aligned pointers with a scalar tail.
  Pays when each lane owns ≥4 contiguous elements and alignment is provable — the
  compiler will not widen loads it cannot prove aligned (see won't-do list).
- **Read-only / constant / texture paths** — data that is read-only for the kernel's
  lifetime can route through the read-only (texture) cache; an address every lane reads
  identically belongs in constant memory (broadcast). Shape: `const T* __restrict__`,
  `__ldg`, `__constant__`, `constant` address space (Metal), uniform buffers (Vulkan/
  WGSL). Pays for reused read-only tables and lookup data; hurts for streamed-once data.
- **L2 residency / access-policy windows** — mark a region that is reused across launches
  (a weight matrix, a LUT) to persist in L2 (Ampere+). Pays when the region fits the
  persisting carve-out and is re-read by many kernels.
- **Reuse across lanes via shared, not repeated global loads** — a stencil/halo, a
  convolution window, a GEMM tile: each global byte should enter the SM once. Shape:
  cooperative tile load → barrier → compute from on-chip. Pays when the per-element reuse
  factor is >1; this is the move that lifts a kernel off the memory roof.

## On-chip memory and occupancy

- **Shared/LDS/threadgroup tiling** — stage the reused tile on-chip once; raises
  arithmetic intensity by the reuse factor. Pays on GEMM, stencils, convolution,
  transpose, histogram. Cost: a barrier per tile and occupancy pressure — size the tile
  so ≥2 blocks fit per SM.
- **Bank-conflict avoidance** — lanes hitting different words in the same bank
  serialize (up to 32×). Shape: pad a 32-wide tile to 33 (`tile[32][33]`) or XOR-swizzle
  the column index; 8/16 B accesses split into phases that are conflict-free within
  each. Pays on column-wise or power-of-two-strided shared access (transposes, tiled
  GEMM B-operand). Verify with the bank-conflict counter, not by inspection.
- **Register budget and spills** — over the per-thread register cap the compiler spills
  to local memory (global-backed, cached, slow). Shape: read the `-Xptxas -v` / ISA
  `.vgpr_spill_count` line; cap with `__launch_bounds__`/`maxnreg`/`amdgpu_waves_per_eu`
  only after confirming spills exist. Pays only when the kernel actually spills — forcing
  fewer registers on a non-spilling kernel *creates* spills.
- **Occupancy is a means, not a goal (Volkov)** — latency is covered by many warps
  **or** by independent instructions inside one thread (ILP). Volkov's SGEMM ran
  1.6× faster at 33% occupancy with 8× smaller blocks than at 67%; the fastest kernels
  hold several outputs per thread in registers. Shape: unroll the per-thread work so
  each thread issues several independent loads/FMAs before consuming; then choose the
  block size with the occupancy API. Pays when the kernel is latency-bound *and* has
  reuse per thread. "Raise occupancy" alone is a proposal only when the profiler shows
  it is latency-bound at low occupancy with nothing else in flight.
- **Warp shuffles / subgroup ops for reductions and scans** — exchange registers within
  a warp without shared memory or a barrier. Shape: butterfly `__shfl_down_sync` /
  `simd_sum` / `subgroupAdd` / `wave_shuffle`, then one shared-memory step per block,
  then one atomic per block. Pays on every reduction, prefix-scan, and argmax; beats a
  shared-memory tree by removing barriers.
- **Async copy / prefetch to shared** — Ampere+ `cp.async` / `cuda::memcpy_async`,
  Hopper TMA, Triton `num_stages`: load tile *k+1* while computing tile *k*, without
  parking data in registers. Pays on tiled kernels where load and compute phases
  alternate (software pipelining).

## Control flow

- **Divergence** — a warp issues one instruction stream; when lanes disagree, each taken
  path executes serially with the others masked, cost ≈ linear in the number of distinct
  paths and independent of occupancy. Shape: make the condition warp-uniform (branch on
  block/warp index, on a value all lanes share, or on a *sorted/compacted* work list so
  each warp takes one path). Pays when the branch splits lanes *within* a warp on
  data-dependent values; a branch every lane takes identically is free.
- **Predication vs branching** — short bodies compile to predicated instructions (both
  sides executed under a mask) — cheap; long divergent bodies do not. Shape: keep
  divergent bodies tiny (a select, a clamp); move heavy per-lane work behind a
  compaction step. Pays when a divergent body is long.
- **Don't early-exit from the middle of a coalesced pattern** — `return` on some lanes
  leaves survivors touching scattered sectors and disables the vector path. Shape: guard
  with a mask/select and keep the memory pattern intact; handle the tail with a bounded
  last block.
- **Reconvergence is not free on Volta+** — independent thread scheduling lets lanes
  interleave but does not remove the penalty; use `__syncwarp()` before warp-collective
  ops after a divergent region.

## Compute

- **FMA contraction** — `x*y+z` becomes one FMA by default; writing `fma()` by hand is
  style, not speed (it *is* required if you need the contraction guaranteed for
  correctness).
- **Fast-math intrinsics** — `__expf`, `__sinf`, `__fdividef`, `rsqrtf`, `--use_fast_math`
  (or Metal's default fast-math, `-ffast-math` in HIP) trade ULPs, denormal handling,
  and NaN semantics for throughput. Pays on transcendental-heavy kernels with a stated
  tolerance; every proposal ships with a tolerance test.
- **Integer division and modulo** — by a runtime divisor they are multi-instruction
  sequences; by a compile-time constant they become multiply-shift; by a power of two,
  a mask. Shape: make block/tile sizes `constexpr`/`comptime`, precompute reciprocals,
  restructure index math. Pays in index-heavy kernels (2D/3D unravelling per element).
- **Precision and throughput** — consumer parts run FP64 at 1/32–1/64 of FP32; FP16/
  BF16 with FP32 accumulate doubles bandwidth-per-element and unlocks matrix units.
  Shape: `half`/`bf16` storage, `float` accumulators; TF32 for FP32 matmuls where a
  10-bit mantissa is acceptable. Pays on memory-bound kernels (halves the bytes) and on
  GEMM/conv (tensor cores).
- **Tensor / matrix cores** — dedicated MMA units execute small fixed tiles per warp
  (FP16 `m16n8k16`, `m16n16k16` WMMA; FP8 `m16n8k32`; AMD MFMA/WMMA shapes; Apple
  `simdgroup_matrix` 8×8). Shape: M, N, K multiples of 8 (FP16) / 16 (FP8), operands
  16 B-aligned, use the library (cuBLAS/rocBLAS/MPS/`tl.dot`/CubeCL matmul) — hand-rolled
  MMA is a last resort. Pays on GEMM/conv with aligned dims; misaligned or tiny tiles
  fall back to the slow SIMD path silently, so *check the profiler's tensor-pipe
  utilization*.
- **Atomics contention** — many lanes hitting one address serialize at L2. Shape:
  privatize (per-block shared-memory histogram, per-warp partials), then one combine;
  warp-aggregate with a leader election (`__ffs(__activemask())`, one atomic per warp).
  Pays on histograms, counters, scatter-adds with skewed keys; the compiler already
  aggregates *simple* `atomicAdd` on NVIDIA (see already-free list) — check before
  proposing.
- **Reductions and scans** — tree in shared memory → shuffle within warp → multi-pass or
  one atomic per block; avoid a lane-0-does-everything final loop. Use the vendor
  primitive library (CUB, rocPRIM, hipCUB, MPS, Metal `simd_*`) for sort/scan/reduce —
  hand-rolled radix sort is a project, not an optimization.
- **Elementwise chains → fusion** — every pointwise/norm/softmax op is memory-bound at
  ≈1–3 FLOP/B; N separate kernels read and write the tensor N times. Shape: one kernel
  that reads once, applies the chain, writes once (`torch.compile`, a Triton kernel, a
  CubeCL fused kernel, one Metal compute pass). Pays whenever ≥2 elementwise ops share
  an operand — this is where most real-world GPU time hides, not in the matmuls.
- **GEMM tiling ladder** — naive → coalesced → shared-memory tile → register tile
  (several outputs per thread) → vectorized loads → double-buffered/async → MMA.
  Measure each rung as % of the vendor BLAS; stop when the library wins.

## Host↔device pipeline (discrete GPUs)

- **Pinned host memory** — the DMA engine streams only page-locked pages; pageable
  buffers are staged through a driver bounce buffer at a fraction of the link rate, and
  `cudaMemcpyAsync` from pageable memory silently becomes synchronous. Shape:
  `cudaMallocHost`/`hipHostMalloc`/`cudaHostRegister` for reused staging buffers; keep
  pinned totals well under host RAM. Pays on repeated transfers ≳1 MB; pinning for a
  one-off small copy costs more than it saves.
- **Overlap copy and compute on streams** — copy engines run concurrently with the SMs
  when work sits on different non-default streams and the host memory is pinned. Shape:
  chunk the input; per chunk `{H2D, kernel, D2H}` on its own stream (double/triple
  buffering); ~3 streams saturate PCIe. Pays when transfer time is a meaningful fraction
  of compute (up to ≈2–3× pipeline throughput).
- **Avoid hidden synchronization** — `cudaDeviceSynchronize`, `cudaMalloc`/`cudaFree`
  in the loop, legacy default-stream `cudaMemcpy`, PyTorch `.item()`/`.cpu()`/
  `print(tensor)`/`.numpy()`/`torch.cuda.synchronize()`, `assert` on a device value,
  wgpu `buffer.map_async` + `device.poll(Wait)` per frame. Each one drains the queue and
  puts the CPU back on the critical path. Shape: allocate once, use events for
  dependencies, keep scalars on the device (e.g. loss accumulators) and read them back
  every N iterations.
- **Memory pools** — `cudaMallocAsync` (stream-ordered allocator, CUDA 11.2+), PyTorch's
  caching allocator, wgpu buffer reuse, Metal `MTLHeap`: allocation inside a
  per-frame/per-iteration loop is a synchronizing malloc. Pays on any loop that allocates.
- **Launch tax and graphs** — each launch is ≈3–7 µs of CPU work plus inter-kernel gap;
  a graph of many kernels replays with one launch and no gaps (CUDA/HIP graphs,
  `torch.compile(mode="reduce-overhead")`, Metal indirect command buffers). Pays when
  launch-bound: many short kernels, small batches, LLM decode. **≈0 benefit** for long
  compute-bound kernels or when shapes change every iteration (graphs freeze pointers and
  sizes — one graph per shape).
- **Persistent / batched kernels** — one launch that loops over work items beats a launch
  per item; merge many small independent problems into one batched launch. Pays when the
  per-launch problem is under ≈100 µs.
- **Zero-copy on unified memory** — on Apple silicon, APUs, and Mali the "transfer" is a
  pointer; allocate in the shared storage mode and skip the copy entirely. The only
  cost left is DRAM bandwidth, which is the scarce resource — fuse harder.

## Framework-level (PyTorch / Triton / JAX)

- **`torch.compile` (Inductor)** — fuses adjacent pointwise/reduction ops into generated
  Triton kernels and can capture CUDA graphs. Shape: `mode="reduce-overhead"` for
  graphs, `"max-autotune"` for Triton-tuned matmuls; hunt graph breaks with
  `torch._dynamo.explain` / `TORCH_LOGS="graph_breaks,recompiles"`. Pays on
  elementwise-heavy models and small-batch/decode workloads; the first call compiles.
- **Memory format** — `channels_last` for convnets gives tensor-core-friendly layout;
  `.contiguous()` is a full copy, so plan layouts rather than fixing them per op.
- **Mixed precision** — `autocast` (FP16/BF16 compute, FP32 master weights),
  `torch.set_float32_matmul_precision("high")` / `allow_tf32` for FP32 matmuls.
- **Input pipeline** — `DataLoader(pin_memory=True)` + `.to(device, non_blocking=True)`
  so the copy overlaps the previous step; `cudnn.benchmark=True` for fixed shapes.
- **Sync points** — the same list as the host pipeline above; `torch.profiler` shows them
  as gaps in the GPU stream with a `cudaStreamSynchronize` / `aten::item` above.
- **Hand-written Triton vs Inductor** — Inductor already emits good fused elementwise/
  reduction kernels; write Triton for fusions it can't discover (custom attention,
  matmul + epilogue, gather-heavy ops). Don't wrap an already-tuned Triton kernel in
  `torch.compile`.
- **Triton's knobs are the catalog in disguise** — `BLOCK_SIZE` = tile, `num_warps` =
  parallelism per block, `num_stages` = software-pipeline depth, `tl.load(mask=)` =
  tail handling without divergence, `tl.dot` = MMA. `@triton.autotune` over a config list
  keyed on shape is the occupancy/tile search made explicit.
- **Library-first** — cuBLAS/cuDNN/CUTLASS, rocBLAS/MIOpen, MPS/MPSGraph, CUB/rocPRIM:
  already tiled, MMA-aware, and per-arch tuned. A hand-rolled GEMM that beats them is a
  research result, not a review finding.

## Concurrency and multi-GPU (brief)

- **Streams and events** — express dependencies with events, not global syncs; keep
  independent kernels on separate streams so small ones fill gaps.
- **Overlap communication with compute** — issue the all-reduce for layer *N* while
  computing layer *N-1*'s backward (NCCL/RCCL on their own stream). The sympathy point
  is the overlap, not the collective algorithm.

## The machine already does this (don't propose it)

- **Coalescing is automatic** — the LSU merges a warp's requests into aligned sectors;
  make addresses contiguous, never hand-pack. Manual "gather into a buffer then load"
  adds a pass.
- **FMA contraction is on by default** (nvcc, hipcc, Metal, Triton). Hand-written `fma()`
  is a correctness tool, not a speedup.
- **Small constant-trip loops are unrolled**; the compiler also schedules instructions
  and allocates registers — don't propose manual scheduling.
- **L2 caches everything; L1 caching of global loads is per-architecture** (off by
  default for global loads on several generations). Don't assume L1 hits for global
  data without checking the backend file.
- **Read-only path selection** for `const T* __restrict__` is automatic on NVIDIA; `__ldg`
  is a hint for when aliasing can't be proven.
- **Warp-uniform branches are free** — a condition identical across lanes is one
  branch; no need to "hoist the if out of the kernel".
- **Reconvergence bookkeeping** (Volta+ independent thread scheduling) is the
  hardware's; you only add `__syncwarp()` before collectives.
- **Latency hiding across warps** is the scheduler's job — supply parallelism; don't
  propose software prefetch into registers unless the profiler shows long-scoreboard
  stalls at high occupancy (then async copy is the tool).
- **Warp-aggregated atomics** are emitted automatically by nvcc (CUDA 9+) for simple
  `atomicAdd` with uniform addresses; check SASS before proposing the leader-election
  pattern.
- **GEMM/conv/reduce/sort in the vendor libraries** are already tiled, vectorized,
  double-buffered, and MMA-aware — call them.
- **On unified memory (Apple, APU, Mali, MI300A) there is no copy to eliminate** —
  pinned memory, async transfer, and "keep it resident" are non-findings there.
- **Bounds-masked tails** (`tl.load(mask=)`, `if (i < n)` at the end) are the intended
  idiom, not divergence to remove — the mask is warp-uniform except in the last block.

## The compiler will NOT do for you (real opportunities)

- **Restructure data** — no AoS→SoA, no padding a pitch, no hot/cold split, no
  transposing a layout so lanes become contiguous.
- **Tile through shared memory** — a naive global-memory loop stays naive; staging,
  barriers, and double-buffering are yours.
- **Pad or swizzle away bank conflicts.**
- **Fuse across launches** — separate kernels (or separate PyTorch eager ops) never
  merge, except through `torch.compile`/XLA/Triton or by hand.
- **Pin memory, overlap streams, or reorder your host loop** — the runtime does exactly
  what the call sequence says; a synchronous copy stays synchronous.
- **Remove divergence** — sorting/compacting work so warps agree is an algorithmic
  change.
- **Widen loads without provable alignment** — `float*` with unknown alignment gets
  scalar `LDG.32`; you must use `float4`/`Line<T,4>`/`vec4` and align the allocation.
- **Fast-math** — precise `expf`/division stay precise unless you opt in.
- **Pick block size / launch bounds / occupancy** — the launch configuration is a runtime
  argument; use the occupancy API or autotune.
- **Strength-reduce runtime integer division** — only compile-time divisors become
  shifts/multiplies.
- **Fix uncoalesced patterns caused by your index math** — the compiler faithfully
  emits the scatter you wrote.
- **Choose the right precision** — FP64 on a consumer card, FP32 where BF16 would do:
  your call, your bytes.

## Per-backend notes

The catalog above is mechanism-first. Concrete shapes, attributes, tool commands, and
per-generation facts live in `references/backend-<name>.md`; read only the one matching
the target:
[CUDA](references/backend-cuda.md) (NVIDIA, C++),
[HIP / ROCm](references/backend-hip.md) (AMD),
[Metal](references/backend-metal.md) (Apple silicon),
[Rust GPU](references/backend-rust.md) (CubeCL, wgpu/WGSL, rust-gpu, cudarc/cust),
[Triton / PyTorch](references/backend-triton-pytorch.md),
[Vulkan / Mali](references/backend-vulkan-mali.md) (embedded, RK3588-class, Intel Xe
notes). A PyTorch model on ROCm reads Triton/PyTorch *and* HIP; a CubeCL kernel on an
AMD card reads Rust *and* HIP.
