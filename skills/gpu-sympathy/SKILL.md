---
name: gpu-sympathy
description: Mechanical sympathy for GPU code — find, verify, and rank GPU-friendly improvements (coalesced/vectorized access, on-chip tiling, occupancy vs ILP, divergence, launch and transfer overhead, fusion) in kernels, host-side pipelines, and framework code on any GPU (NVIDIA, AMD, Apple, Arm Mali, Intel; discrete, integrated, APU, unified memory). Use whenever the user mentions CUDA, HIP/ROCm, Metal, wgpu/WGSL, CubeCL, rust-gpu, Triton, torch.compile, Vulkan compute, kernels, warps/wavefronts, occupancy, shared/threadgroup memory, PCIe transfers, or asks why a kernel or GPU pipeline is slow, whether a workload belongs on the GPU, or wants GPU code reviewed for how it treats the hardware — even if they never say "GPU". CPU-side hot code → mechanical-sympathy; metric-driven optimize-until-target loops → auto-optimize.
---

# GPU sympathy

The GPU rewards wide, aligned, coalesced memory traffic, data that stays on-chip once
fetched, and enough work in flight to cover latency. It hides latency with *parallelism*
— many resident warps, or independent instructions per thread — not with branch
prediction and prefetching. That is the one mental shift a CPU-tuned reviewer must make:
"keep the pipeline fed" becomes "keep enough warps in flight and move bytes in the fewest,
widest transactions." This skill finds where code fights that grain and proposes fixes,
each one **proved or dropped**, never assumed. The deliverable is a verified,
honestly-rated idea list; do not edit code unless the user asks.

Machine classes, the numbers table, the technique catalog, and the two machine-facts
lists live in [TECHNIQUES.md](TECHNIQUES.md) — read it before step 2 — plus the one
`references/backend-<name>.md` matching the target (see the pointer list at the bottom
of TECHNIQUES.md).

## 1. Identify the machine, then map the traffic

Classify the system first (TECHNIQUES.md → *Machine classes*): discrete over PCIe,
integrated/APU sharing DRAM, Apple unified memory, coherent CPU-GPU (Grace Hopper,
MI300A), or embedded Mali. This decides whether a transfer step even exists and which
bandwidth the arithmetic uses — proposing pinned memory on a unified-memory box is a
category error, not a low-impact idea.

**Traffic = bytes moved × frequency, at each level.** Three levels, three bandwidths:

- **Host↔device** — bytes crossing PCIe/NVLink per iteration (zero on unified memory).
- **Global memory** — sectors actually moved per kernel (NVIDIA: 32 B sectors, 128 B
  lines; see the backend file for the vendor's granularity). Compute *useful bytes ÷
  sectors touched* for every hot access pattern.
- **On-chip** — shared/LDS/threadgroup bytes and registers per block; these bound
  occupancy.

Tag every kernel, transfer, and launch with a rate class — per-element, per-warp,
per-launch, per-frame/iteration, per-transfer, or once (*cold*) — and a bytes figure.
For the dominant kernels compute arithmetic intensity (FLOP ÷ bytes) and place them on
the roofline against the real part's numbers. Take frequencies and wall-time shares from
a timeline (Nsight Systems, rocprofv3, Metal System Trace, `torch.profiler`), not from
reading the code: the kernel that looks worst is often 3% of the wall clock.

Completion: every kernel and transfer in scope carries a rate class, a bytes figure, and
a roofline placement (memory-, compute-, or launch-bound), and the dominant cliff is
identified by arithmetic. Most pipelines have exactly one — a transfer, a storm of tiny
launches, or one uncoalesced memory-bound kernel — and it is usually not inside a kernel.

## 2. Match techniques

Shortlist catalog entries whose *pays-off-when* condition matches the dominant paths.
Cold paths and kernels below a few percent of wall time earn only trivial-complexity
changes (or none — "cold, leave it" is a finding). Check the **already-free list** in
TECHNIQUES.md first so you don't propose what the hardware, compiler, or library already
does (hand-merged coalescing, manual FMA, hand-rolled GEMM).

Completion: each shortlisted technique names the concrete `file:line` (kernel, launch
site, or transfer) it would apply to.

## 3. Prove or drop

Adversarially verify every candidate; default stance is *drop*. Five gates, all must
pass:

- **Read gate** — the cited code actually does what the idea claims. Read the index
  math; read the launch configuration; read what the host loop synchronizes on.
- **Safety gate** — expressible in the target's portable idioms: framework vector
  types, launch bounds, cooperative-group/subgroup ops, storage-mode flags. No inline
  PTX/ISA, no `unsafe` pointer casts, no undefined-layout tricks, no fast-math without a
  tolerance check.
- **Compiler gate** — *the compiler didn't get there first.* Inspect the **final** ISA
  for the claim: SASS on NVIDIA (PTX is intermediate, not proof), `-save-temps` ISA on
  AMD, GPU-capture disassembly on Metal, naga output for wgpu/CubeCL, `.asm["ptx"]` for
  Triton. Look for vector loads (`LDG.128` / `global_load_dwordx4`), spills to
  local/scratch, FMA contraction, predication. TECHNIQUES.md lists what the toolchain
  reliably does and what it provably won't.
- **Hardware gate** — the mechanism survives the real machine, by arithmetic and then by
  a counter: sectors per request (target 4.0 for 4-byte loads on NVIDIA), occupancy
  math against the register/shared limits, roofline placement against the part's real
  bandwidth. A divergent branch costs only if lanes actually split; shared memory pays
  only if data is reused; "raise occupancy" pays only if the kernel is latency-bound
  and has no ILP to spare.
- **Honesty gate** — impact rated against the traffic map with Amdahl: a 2× win inside a
  kernel that is 3% of the timeline is **negligible — craft only**, and that is a
  legitimate, stated rating.

Completion: every survivor has `file:line`, mechanism, honest impact, and complexity;
every kill keeps a one-line reason. The kills go in the report — *why an idea fails* is
half the lesson, and on GPUs the most common kill is "already coalesced" or "not on the
critical path".

## 4. Report

Rank survivors by impact, then teaching value, then inverse complexity. Report three
lists: verified ideas (with sketches), dropped ideas (with reasons), and the
**already-sympathetic inventory** — things the code does right that a future refactor
must not regress (a coalesced layout, a pinned staging buffer, a fused kernel, an
allocation hoisted out of the frame loop).

If the user then asks to apply changes, take them top-ranked-first and re-verify each
after landing with a measurement: warm up first, time with device events (`cudaEvent`,
`triton.testing.do_bench`, `torch.utils.benchmark`, `MTLCommandBuffer` GPU timestamps),
run enough iterations that launch overhead isn't what you measured, and re-check
numerical results against a tolerance after any precision or fast-math change.
