# GPU sympathy — NVIDIA CUDA (C++)

Load this only when the target is CUDA C++ (or PTX-level tooling). The mechanism catalog
is in `TECHNIQUES.md` at the skill root; this file has the concrete shapes and commands.

## Machine facts

- Warp = 32 lanes. Global memory: 32 B sectors, 128 B L1 lines; transactions must be
  naturally aligned to 32/64/128 B. Shared memory: 32 banks × 4 B (128 B/clk), unified
  with L1 in a configurable carve-out.
- Per SM (typical, verify with `cudaGetDeviceProperties`): 64 K 32-bit registers, 255
  registers/thread max, 2048 threads / 64 warps, 32 blocks, 48 KB static shared per
  block; opt-in dynamic shared up to ≈99 KB (Ampere) / ≈227 KB (Hopper) via
  `cudaFuncSetAttribute(k, cudaFuncAttributeMaxDynamicSharedMemorySize, bytes)`.
- Generations that change the catalog: **Ampere** (async copy `cp.async`, L2
  persistence, TF32); **Hopper** (TMA bulk copies, thread-block clusters + distributed
  shared memory, WGMMA, FP8); **Blackwell** (FP4, `tcgen05` MMA). Compute-capability-
  specific features need `-arch=sm_90a` style targets.
- L1 caching of global *loads* is architecture-dependent (default off on several
  generations); L2 always caches. Don't reason about L1 hits for global data.
- FP64 on consumer (GeForce) parts is 1/32–1/64 of FP32; data-center parts are 1/2.

## Idiomatic shapes

- **Coalesced + vectorized loads**: `const float4* __restrict__ in` with the allocation
  from `cudaMalloc` (256 B-aligned) and an index of `blockIdx.x*blockDim.x+threadIdx.x`;
  scalar tail for `n % 4`. `reinterpret_cast<float4*>` is fine only when the base is
  16 B-aligned — check `cudaMallocPitch` for 2D.
- **Read-only cache**: `const T* __restrict__` lets nvcc pick `LDG.E.CONSTANT`; `__ldg(p)`
  forces it when aliasing can't be proven.
- **Launch bounds**: `__global__ void __launch_bounds__(256, 2) k(...)` = max 256
  threads/block, want ≥2 blocks/SM → caps registers so two blocks fit. Use only after
  `-Xptxas -v` shows the register count blocks the target occupancy.
- **Occupancy API**: `cudaOccupancyMaxActiveBlocksPerMultiprocessor(&n, k, block, smem)`
  and `cudaOccupancyMaxPotentialBlockSize(&minGrid, &block, k, smem)` — use these instead
  of the spreadsheet.
- **Warp collectives**: `__shfl_down_sync(0xffffffff, v, off)` butterfly; cooperative
  groups `cg::tiled_partition<32>(block)` → `tile.shfl_down`, `cg::reduce(tile, v,
  cg::plus<T>())`; `__syncwarp()` before collectives after divergence.
- **Warp-aggregated atomic**: `unsigned m = __activemask(); int leader = __ffs(m)-1; ...
  if (lane == leader) atomicAdd(ctr, __popc(m));` — check SASS first; nvcc often does it.
- **Shared tiling**: `__shared__ float tile[32][33];` (pad) or `tile[32][32]` with an
  XOR swizzle on the column; `__syncthreads()` between load and use.
- **Async copy**: `cuda::memcpy_async(block, smem_dst, gmem_src, bytes, pipeline)` with
  `cuda::pipeline` (Ampere+); Hopper TMA via CUTLASS/CuTe rather than raw PTX.
- **L2 persistence** (Ampere+): `cudaDeviceSetLimit(cudaLimitPersistingL2CacheSize, n)`;
  `cudaStreamSetAttribute(stream, cudaStreamAttributeAccessPolicyWindow, &attr)` with
  `attr.accessPolicyWindow.{base_ptr,num_bytes,hitRatio,hitProp=cudaAccessPropertyPersisting}`.
- **Host pipeline**: `cudaMallocHost`/`cudaHostAlloc` (pinned), `cudaHostRegister` for
  existing buffers; `cudaMemcpyAsync(..., stream)` + per-chunk streams;
  `cudaMallocAsync(&p, bytes, stream)` / `cudaFreeAsync` (stream-ordered pool);
  `cudaEventRecord`/`cudaStreamWaitEvent` for dependencies; CUDA graphs via
  `cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal)` … `cudaStreamEndCapture`
  → `cudaGraphInstantiate` → `cudaGraphLaunch`.
- **Managed memory**: `cudaMallocManaged`; `cudaMemPrefetchAsync(p, bytes, dev, stream)`;
  `cudaMemAdvise(p, bytes, cudaMemAdviseSetReadMostly|SetPreferredLocation|SetAccessedBy,
  dev)`. Pascal+ launches without bulk migration and faults pages on demand — fault
  storms show as `Unified Memory` rows in Nsight Systems.
- **Fast math**: `--use_fast_math` (implies `-ftz=true -prec-div=false -prec-sqrt=false
  --fmad=true`) or per-call `__expf`, `__fdividef`, `rsqrtf`. `--fmad=true` is already the
  default.

## Verification commands

- Registers / spills / shared: `nvcc -O3 -arch=sm_90 -Xptxas -v k.cu` → look for
  `Used N registers`, `N bytes spill stores`, `N bytes smem`. Any spill line on a hot
  kernel is a finding; zero spills means "don't touch launch bounds".
- Final ISA (SASS, not PTX): `cuobjdump -sass a.out | less` or `nvdisasm -g k.cubin`.
  Look for `LDG.E.128` / `STG.E.128` (vectorized), `LDL`/`STL` (local = spill or
  register-indexed array), `FFMA` (contraction), `@P0` predication, `LDG.E.CONSTANT`
  (read-only path), `SHFL` (shuffles), `BAR.SYNC` count per tile.
- Kernel profile: `ncu --set full -k regex:<kernel> -c 1 ./app` (full sections) or
  `ncu --metrics <list> ./app`. Key metric names:
  - `l1tex__average_t_sectors_per_request_pipe_lsu_mem_global_op_ld.ratio` — **target
    4.0** for 4 B loads (8.0/16.0 for 8/16 B); higher = uncoalesced. Store variant ends
    `_op_st`.
  - `sm__warps_active.avg.pct_of_peak_sustained_active` — achieved occupancy.
  - `gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed` vs
    `sm__throughput.avg.pct_of_peak_sustained_elapsed` — memory- vs compute-bound.
  - `l1tex__data_bank_conflicts_pipe_lsu_mem_shared.sum` — shared bank conflicts.
  - `smsp__warps_issue_stalled_long_scoreboard...` (global latency),
    `..._short_scoreboard` (shared/L1), `..._mio_throttle` (shared bandwidth),
    `..._barrier` — the "Warp State" section names the bottleneck.
  - `sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_active` — are MMA units
    actually used.
  - Rules to read: "Uncoalesced Global Accesses", "Shared Memory Bank Conflicts",
    "Occupancy", "Roofline" (HBM roofline section; hierarchical via
    `--section SpeedOfLight_HierarchicalTensorRooflineChart`).
- Timeline / pipeline: `nsys profile --stats=true -o run ./app` → per-kernel wall share,
  gaps between kernels (launch-bound), `cudaMemcpy` rows (sync copies), page-fault rows.
  Amdahl lives here.
- Correctness: `compute-sanitizer --tool memcheck ./app`, `--tool racecheck` (shared
  memory races), `--tool synccheck`. Run after any tiling or barrier change.
- Timing: `cudaEventRecord(start)` … `cudaEventRecord(stop); cudaEventSynchronize(stop);
  cudaEventElapsedTime(&ms, start, stop)` after ≥10 warm-up launches.

## Build flags

- `-O3` (host) and `-Xptxas -O3` (default device); `-arch=sm_XX` or multiple `-gencode
  arch=compute_XX,code=sm_XX` — JIT from PTX on an unmatched arch costs startup and
  loses arch-specific codegen.
- `-lineinfo` for source-level attribution in ncu without disabling optimization;
  `-G` disables optimization (never profile with it).
- `--use_fast_math` only with a tolerance test; `-Xptxas -warn-spills`.
- `--maxrregcount=N` is global; prefer `__launch_bounds__` per kernel.

## Gotchas

- `cudaMemcpyAsync` from pageable host memory is synchronous with respect to the host.
- The legacy default stream synchronizes with all blocking streams; compile with
  `--default-stream per-thread` or use explicit non-blocking streams.
- `cudaMalloc`/`cudaFree` synchronize the device; allocation in a loop is a hidden sync.
- Register-indexed local arrays (`float a[8]; a[i]`) with dynamic `i` go to local memory
  (`LDL`); only fully-unrolled constant indices stay in registers.
- `__syncthreads()` inside divergent control flow is undefined behaviour.
- Graph capture fails on any synchronous call (`cudaMalloc`, `cudaMemcpy`, `printf`
  sync) inside the captured region.
