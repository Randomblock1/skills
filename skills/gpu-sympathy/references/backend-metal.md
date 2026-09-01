# GPU sympathy — Apple Metal (Apple silicon)

Load this only when the target is Metal Shading Language compute on Apple silicon (or
PyTorch MPS / CubeCL-wgpu on a Mac — read this alongside that backend's file). The
mechanism catalog is in `TECHNIQUES.md` at the skill root; this file has the concrete
shapes and commands.

## Machine facts

- **Unified memory**: CPU and GPU share one physical pool. There is no host↔device copy
  to optimize; buffers with `MTLResourceStorageModeShared` are visible to both sides.
  `.private` (GPU-only, can be faster for GPU-resident data; needs a blit to read back),
  `.memoryless` (tile-only render targets), `.managed` exists for Intel Macs only.
- **Bandwidth is the budget** (spec, unified LPDDR): M1 68 GB/s, M1 Pro 200, M1 Max 400,
  M1/M2/M3 Ultra 800; M2 100, M2 Pro 200, M2 Max 400; M3 100, M3 Pro 150, M3 Max
  300/400; M4 120, M4 Pro 273, M4 Max 410/546. Shared with the CPU — fuse harder than on
  a discrete card.
- **SIMD-group width 32** (`threadExecutionWidth`); max 1024 threads per threadgroup
  (`maxTotalThreadsPerThreadgroup`); **32 KB threadgroup memory** per threadgroup
  (`maxThreadgroupMemoryLength`). Query, don't assume.
- **TBDR** (tile-based deferred rendering) with on-chip tile memory; for pure compute
  the practical consequences are: unified memory, aggressive threadgroup-memory limits,
  and that occupancy is governed by registers *and* threadgroup memory per core.
- **Occupancy is sensitive to threadgroup memory**: allocating the full 32 KB limits a
  core to one threadgroup; a matmul measured on an M-series part ran ≈250 GFLOPS with
  32 KB tiles vs ≈400 GFLOPS with 8 KB — leave room for several threadgroups. Apple's
  guidance: 1–2 K concurrent threads per core is "very good occupancy".
- Generations: M1/M2 (Apple7/8 family), M3/M4 (Apple9: dynamic caching of register/
  threadgroup allocation, hardware ray tracing, mesh shading), later parts add Metal 4
  tensor APIs (`MTLTensor`) for ML — check the installed SDK.
- `half` (fp16) is a first-class fast type; use it for storage and where precision
  allows. Metal enables fast-math by default (`-ffast-math`; disable with
  `-fno-fast-math` or per-kernel `[[fast_math(false)]]`-style options in newer SDKs).

## Idiomatic shapes

- **Buffers**: `device.makeBuffer(length:options: .storageModeShared)`; write from the
  CPU via `contents()`; no blit needed. Use `.storageModePrivate` for scratch the CPU
  never reads; `MTLHeap` to sub-allocate and avoid per-frame `makeBuffer`.
- **Argument buffers / bindless** for many small resources; `MTLResourceOptions
  .hazardTrackingModeUntracked` + explicit fences when Metal's automatic hazard tracking
  serializes independent dispatches.
- **Dispatch**: `dispatchThreads(_:threadsPerThreadgroup:)` (non-uniform grids, no tail
  branch needed) vs `dispatchThreadgroups`; choose `threadsPerThreadgroup` as a multiple
  of `threadExecutionWidth` (e.g. 256 = 8 SIMD-groups). `[[max_total_threads_per_
  threadgroup(N)]]` on the kernel caps registers like `__launch_bounds__`.
- **Vector types**: `float4`/`half4`/`packed_float3` in `device` buffers; align structs
  to 16 B for vector loads.
- **Address spaces**: `device` (global RW), `constant` (read-only, broadcast-optimized —
  use for uniforms/LUTs every thread reads), `threadgroup` (shared), `thread` (private).
- **SIMD-group ops** (Metal 2+): `simd_sum`, `simd_max`, `simd_prefix_inclusive_sum`,
  `simd_shuffle_down`, `simd_ballot`, `simd_is_first`; `threadgroup_barrier(mem_flags::
  mem_threadgroup)` only when threadgroup memory is involved — use SIMD ops for
  intra-warp reductions and skip the barrier.
- **Matrix units**: `simdgroup_matrix<T, 8, 8>` with `simdgroup_load` / `simdgroup_
  multiply_accumulate` / `simdgroup_store` (`half`/`float`); prefer MPS
  (`MPSMatrixMultiplication`) or MPSGraph for GEMM/conv, and Metal 4 tensor ops where
  available.
- **Tile shaders** (`[[tile]]` kernels, imageblocks) when a compute stage consumes a
  render pass's output — keeps data on-chip instead of a round trip to DRAM.
- **Command buffers**: batch many dispatches into one `MTLCommandBuffer`, encode with a
  single `MTLComputeCommandEncoder` where possible, avoid `waitUntilCompleted()` per
  frame — use `addCompletedHandler` and triple-buffered resources. Indirect command
  buffers (`MTLIndirectCommandBuffer`) replay encoded dispatches (the CUDA-graph
  analogue).

## Verification commands

- Compile offline and inspect: `xcrun -sdk macosx metal -c k.metal -o k.air &&
  xcrun -sdk macosx metallib k.air -o k.metallib`; `xcrun metal -S k.metal` emits
  LLVM IR (AIR) for the compiler gate (check for `fmuladd`, vector loads, spills are not
  visible here — use the profiler).
- **Xcode GPU Frame/Workload Capture** → Metal Debugger → *Shader Profiler* (per-line
  cost), *Performance* tab counters: occupancy, ALU/memory limiter, threadgroup-memory
  and register usage, bandwidth. `Product → Profile → Metal System Trace` (Instruments)
  for the timeline: command-buffer gaps, CPU encoding time, GPU idle — this is where
  Amdahl lives.
- `MTL_SHADER_VALIDATION=1` (env) for out-of-bounds/race checks; `MTL_DEBUG_LAYER=1`.
- Timing: `commandBuffer.gpuStartTime` / `gpuEndTime` after `waitUntilCompleted()`
  outside the hot loop; `MTLCounterSampleBuffer` for per-dispatch timestamps.
- Metal Performance HUD (`MTL_HUD_ENABLED=1`) for live frame/GPU time on macOS 13+.

## Gotchas

- Proposing pinned memory, `memcpy` overlap, or "keep it on the GPU" is a non-finding —
  there is nothing to copy. The scarce resource is DRAM bandwidth shared with the CPU.
- Large `threadgroup` arrays are the most common occupancy killer; halve the tile before
  touching anything else.
- Reading a `.shared` buffer from the CPU while the GPU writes it is a data race unless
  the command buffer has completed (or you fence); `.private` needs a blit to read.
- `float` atomics on `device` memory are limited (integer atomics broad; float atomic
  add on newer families only) — privatize reductions.
- PyTorch MPS: op coverage is incomplete (`PYTORCH_ENABLE_MPS_FALLBACK=1` silently runs
  unsupported ops on the CPU — a hidden sync + copy per op; find them with
  `torch.profiler`), no CUDA graphs, `torch.compile` support is partial. Sync points are
  `torch.mps.synchronize()`, `.item()`, `.cpu()`.
