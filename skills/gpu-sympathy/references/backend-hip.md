# GPU sympathy — AMD HIP / ROCm

Load this only when the target runs on an AMD GPU (HIP C++, or PyTorch/Triton/CubeCL on
ROCm — read this alongside that backend's file). The mechanism catalog is in
`TECHNIQUES.md` at the skill root; this file has the concrete shapes and commands.

## Machine facts

- **Wavefront size differs by family**: CDNA (MI100/200/300, data-center) and GCN =
  **64** lanes; RDNA (RX 6000/7000/9000, consumer) = **32** by default (wave32), with
  wave64 available but not the HIP default. Code that hard-codes 32 (mask constants,
  shuffle widths, reduction trees) is wrong on CDNA. Use `warpSize` (runtime device
  constant) or `__AMDGCN_WAVEFRONT_SIZE` (compile-time, per target).
- Compute unit: 4 SIMD units; up to 8 waves per SIMD (32 per CU) limited by VGPR use.
  VGPR file per SIMD lane ≈ 512 registers on CDNA (unified VGPR+AGPR), 256 on older
  parts — occupancy steps down in bands (e.g. ≤64 VGPRs → 8 waves, ≤128 → 4, …); the
  compiler prints the resulting `Occupancy` in the ISA comments.
- LDS (shared memory): 64 KB per CU on CDNA3 (MI300), 32 banks × 4 B, 128 B/clk;
  conflicts assessed per phase (for wave64 `ds_*_b128`, 8 lanes per phase). Newer CDNA
  parts have larger LDS — query `hipDeviceProp_t::sharedMemPerBlock`.
- Cache lines 64 B (L2 128 B on some parts); MI300X has a 256 MB Infinity Cache in front
  of 5.3 TB/s HBM3 and is built from XCD chiplets — L2 is per XCD, so cross-XCD sharing
  is not "free L2".
- MI300A is an APU: CPU and GPU share HBM (unified) — no transfer step; MI300X is a
  discrete card over PCIe/Infinity Fabric.
- Matrix cores: MFMA instructions on CDNA (`v_mfma_*`), WMMA on RDNA3+; shapes and
  types differ per family — use rocBLAS/hipBLASLt/CK (Composable Kernels) or Triton.
- Memory coherence: **coarse-grained** (`hipMalloc`, device-cached, visible at sync
  points) vs **fine-grained** (`hipHostMalloc` default, `hipMallocManaged` with XNACK,
  `hipExtMallocWithFlags(hipDeviceMallocFinegrained)`) — fine-grained bypasses some
  caching and is slower for bulk kernels; atomics across CPU/GPU need it.
- Managed memory page faulting requires **XNACK** enabled (`HSA_XNACK=1` and a kernel
  driver/target that supports it, `gfx90a:xnack+` style targets); without it,
  `hipMallocManaged` allocations are migrated up-front and GPU page faults are fatal.

## Idiomatic shapes

- HIP mirrors the CUDA API: `hipMalloc`, `hipMemcpyAsync`, `hipHostMalloc` (pinned),
  `hipStreamCreate`, `hipEventRecord`, `hipMallocAsync`, `hipGraph*`, `hipLaunchKernelGGL`
  or `<<<>>>`. The catalog's host-pipeline entries translate 1:1.
- `__launch_bounds__(maxThreadsPerBlock, minBlocksPerCU)` works; the AMD-specific
  attribute is `__attribute__((amdgpu_waves_per_eu(min, max)))` to steer VGPR
  allocation, and `__attribute__((amdgpu_flat_work_group_size(min, max)))`.
- Wave collectives: `__shfl_down(v, off)` (width defaults to `warpSize`), `__ballot`,
  `__any`, `__all` — mask-less in HIP (no `_sync` suffix); `__lane_id()`. Reductions
  should loop `for (off = warpSize/2; off > 0; off >>= 1)`, never `16`.
- `__builtin_amdgcn_*` intrinsics and rocWMMA for matrix ops; prefer library calls.
- Vector loads: `float4`, or `__builtin_nontemporal_load` for streamed-once data; look
  for `global_load_dwordx4` in the ISA to confirm.
- Shared tiling identical to CUDA (`__shared__`, `__syncthreads()`); pad to
  `[64][65]` style for wave64 column access.
- Fast math: `-ffast-math` (clang) or `-fgpu-flush-denormals-to-zero`; intrinsics
  `__expf`, `__fdividef`, `rsqrtf`, `__builtin_amdgcn_rcpf`.

## Verification commands

- Device inventory: `rocminfo` (gfx target, wavefront size, CU count),
  `rocm-smi --showmeminfo vram --showclocks`.
- ISA + resource usage: `hipcc -O3 --offload-arch=gfx942 -save-temps k.cpp` → the
  `*.s` file has per-kernel metadata: `.vgpr_count`, `.sgpr_count`, `.agpr_count`,
  `.vgpr_spill_count`, `.sgpr_spill_count`, `.group_segment_fixed_size` (LDS bytes),
  and a `; Occupancy: N` comment. Any non-zero spill count on a hot kernel is a finding.
  Look for `global_load_dwordx4` (vectorized), `scratch_load`/`scratch_store` (spills),
  `v_fma_f32`/`v_pk_fma_f32` (contraction), `ds_read_b128` (LDS vector), `s_waitcnt`
  density (memory latency exposure), `v_cndmask` (predication).
  `-Rpass-analysis=kernel-resource-usage` prints the same at compile time without temps.
- Alternative disassembly: `roc-obj-ls a.out` / `roc-obj-extract` then
  `llvm-objdump -d --mcpu=gfx942 file.co`.
- Kernel profile: `rocprofv3 --kernel-trace --stats -- ./app` (per-kernel time and
  counts); counters via `rocprofv3 --pmc FETCH_SIZE WRITE_SIZE SQ_WAVES ... -- ./app`.
  Roofline, LDS bank-conflict rate, VGPR/occupancy, and memory-chart analysis:
  `rocprof-compute profile -n run -- ./app` then `rocprof-compute analyze -p
  workloads/run/<gfx>` (formerly Omniperf; sections for Speed-of-Light, roofline,
  LDS "Bank Conflict Rate", "Wavefront occupancy limiters").
- Timeline: `rocprofv3 --kernel-trace --memory-copy-trace --hip-trace --output-format
  pftrace -- ./app` → open in Perfetto; look at gaps, copies, and sync calls.
  `rocprof-sys` (formerly Omnitrace) for whole-app timelines.
- Timing: `hipEventRecord`/`hipEventElapsedTime` after warm-up.

## Portability gotchas (CUDA → HIP)

- Warp-size-32 assumptions: masks `0xffffffff`, `__shfl` offsets starting at 16,
  `blockDim.x == 32` reductions, bank-conflict padding computed for 32 lanes.
- `__shfl_sync(mask, …)` has no mask in HIP; the CUDA mask semantics don't exist.
- Shared-memory bank-conflict math is per phase on wave64 — a pattern conflict-free on
  NVIDIA can conflict here and vice versa; use the counter.
- `hipDeviceSynchronize`, `hipMalloc`/`hipFree` in loops, and pageable `hipMemcpyAsync`
  carry the same hidden-sync costs as CUDA.
- Occupancy API exists (`hipOccupancyMaxActiveBlocksPerMultiprocessor`) but the VGPR
  banding differs from NVIDIA's linear model — read the compiler's `Occupancy` line.
- PyTorch on ROCm reuses the `torch.cuda.*` namespace (`torch.cuda.is_available()` is
  `True` on AMD); Triton on ROCm emits AMDGCN — `num_warps` is still "warps" of 64.
