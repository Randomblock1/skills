# GPU sympathy — Triton and PyTorch

Load this only when the target is PyTorch model/training/inference code or a Triton
kernel. Also read the physical backend's file (CUDA, HIP, Metal) for ISA and profiler
details. The mechanism catalog is in `TECHNIQUES.md` at the skill root.

## PyTorch — where the time actually goes

Order of investigation (most pipelines are broken at the top, not the bottom):

1. **Sync points** — `.item()`, `.cpu()`, `.numpy()`, `print(t)`, `float(t)`, `bool(t)`,
   `if t.any():`, `tensor.tolist()`, `torch.cuda.synchronize()`, `torch.mps.synchronize()`,
   `nonzero()`/`masked_select` (data-dependent shapes), CPU-side `assert` on device
   values, per-step logging of a device scalar. In `torch.profiler` they appear as
   `cudaStreamSynchronize` / `cudaMemcpyAsync DtoH` with an idle GPU stream after them.
   Fix: accumulate on device, read back every N steps, `non_blocking=True`.
2. **Launch-bound small ops** — a forest of tiny kernels with gaps between them:
   `torch.compile` (fusion) and `mode="reduce-overhead"` (CUDA graphs) are the tools.
   Graphs require static shapes and no CPU-side data dependence; each new shape = new
   graph.
3. **Input pipeline** — `DataLoader(num_workers=…, pin_memory=True, persistent_workers=
   True, prefetch_factor=…)`; `.to(device, non_blocking=True)` so the H2D overlaps.
   Profile shows the GPU idle while `enumerate(loader)` runs.
4. **Layout / precision** — `channels_last` for conv nets; `autocast(dtype=bfloat16)`;
   `torch.set_float32_matmul_precision("high")` (TF32) or `torch.backends.cuda.matmul.
   allow_tf32 = True`; `torch.backends.cudnn.benchmark = True` for fixed shapes;
   avoid `.contiguous()` copies by choosing layouts once.
5. **Memory** — `torch.cuda.memory_summary()`, `torch.cuda.max_memory_allocated()`;
   allocator fragmentation → `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`;
   `torch.cuda.empty_cache()` in a loop is a sync and a non-finding.
6. **Only then kernel internals** — and only for kernels that dominate the profiler's
   table.

### Verification

- Timeline: `with torch.profiler.profile(activities=[ProfilerActivity.CPU,
  ProfilerActivity.CUDA], record_shapes=True, with_stack=True) as p: …` →
  `p.key_averages().table(sort_by="cuda_time_total")` and
  `p.export_chrome_trace("trace.json")` (open in Perfetto / `chrome://tracing`). Read GPU
  stream gaps first.
- Compile diagnostics: `torch._dynamo.explain(fn)(*args)` (graph breaks and reasons);
  `TORCH_LOGS="graph_breaks,recompiles,inductor"`; `TORCH_COMPILE_DEBUG=1` dumps the
  generated Triton kernels to `torch_compile_debug/` — apply the Triton section below
  to them. `torch._inductor.config.max_autotune=True`, or `mode="max-autotune"`.
- Benchmark: `torch.utils.benchmark.Timer(stmt, globals).blocked_autorange()` (handles
  warm-up and sync); never `time.time()` around an async launch.
- Attention: `torch.nn.attention.sdpa_kernel([SDPBackend.FLASH_ATTENTION])` to force/
  verify the backend; a fallback to the math path is a bandwidth finding.
- Backends: ROCm reuses `torch.cuda.*`; MPS has partial op coverage
  (`PYTORCH_ENABLE_MPS_FALLBACK=1` hides CPU round-trips — find them in the profiler),
  no CUDA graphs, unified memory (no pinning).

### What torch.compile already does (don't propose it by hand)

Pointwise/reduction fusion, dead-op removal, layout planning inside a graph, CUDA-graph
capture, autotuned matmul selection. It will **not**: remove your sync points, fix a
DataLoader, fuse across a graph break, change dtypes, or beat cuBLAS on GEMM.

## Triton — the catalog with the knobs exposed

- **Model**: one program per `tl.program_id(axis)` = one block; `BLOCK_SIZE: tl.constexpr`
  = the tile; `offs = pid*BLOCK + tl.arange(0, BLOCK)`; `tl.load(ptr + offs, mask=offs <
  n, other=0.0)` = coalesced, vectorized, bounds-masked load in one line (the mask is
  the tail idiom — not divergence to remove). `tl.store` likewise. Block pointers /
  `tl.make_block_ptr` + `tl.advance` for 2D tiles; `tl.dot(a, b, acc)` = MMA (requires
  tile dims ≥16 and multiples of 16 for FP16).
- **Knobs**: `num_warps` (threads per block = 32 × num_warps on NVIDIA/RDNA, 64 × on
  CDNA), `num_stages` (software-pipeline depth: async-copy prefetch of tile k+1 …
  k+stages−1 — Ampere+/CDNA), `BLOCK_M/N/K` (tile → arithmetic intensity vs register/
  shared pressure), `GROUP_SIZE_M` (L2-aware program ordering for GEMM — the L2
  residency entry). `@triton.autotune(configs=[triton.Config({"BLOCK_M":128,
  "BLOCK_N":256,"BLOCK_K":64,"GROUP_SIZE_M":8}, num_stages=3, num_warps=8), …],
  key=["M","N","K"])` runs the occupancy/tile search per shape key.
- **Fusion is the point**: an elementwise chain, a softmax, a layernorm, a matmul +
  bias + activation epilogue each become one kernel that reads once and writes once.
  Inductor already generates these for standard ops — write Triton for fusions it
  can't see (custom attention variants, gather-heavy ops, fused optimizers).
- **Launch tax**: a Triton launch from Python costs tens to hundreds of µs of
  interpreter/dispatch time (argument specialization checks); for tiny problems that
  dominates. Cures: CUDA graphs (`torch.compile(mode="reduce-overhead")` or manual
  `torch.cuda.CUDAGraph`), batching, or persistent kernels. Graph capture freezes
  tensor pointers — allocate once.
- **Precision**: `tl.dot` on FP16/BF16 inputs with `acc` in `tl.float32`;
  `allow_tf32` / `input_precision` for FP32 inputs; `tl.math.exp2` + a log2e fold is
  cheaper than `exp`; integer index math with `tl.constexpr` divisors becomes shifts.
- **Verification**:
  - Compiled artifact: `k = kernel[grid](…)` returns a `CompiledKernel`; `k.asm["ptx"]`,
    `k.asm["ttgir"]` (Triton-GPU IR: shows layouts, `num_warps`, async copies),
    `k.asm["amdgcn"]` on ROCm; `k.n_regs`, `k.n_spills` — spills > 0 on a hot kernel
    → reduce `BLOCK_*`/`num_stages` or raise `num_warps`. Cache dir `~/.triton/cache`.
  - Env: `TRITON_PRINT_AUTOTUNING=1` (winning config per key), `MLIR_ENABLE_DUMP=1`
    (per-pass IR), `TRITON_CACHE_DIR`, `TRITON_INTERPRET=1` (run on CPU for correctness).
  - Bench: `triton.testing.do_bench(lambda: kernel[grid](…), warmup=25, rep=100)`
    returns ms with proper sync and L2 flushing options; `triton.testing.perf_report`
    for sweeps. Compare against `torch.matmul`/`F.softmax` as the library baseline.
  - Then run `ncu` / `rocprof-compute` on the generated kernel as for any CUDA/HIP
    kernel (sectors per request, tensor-pipe utilization, stall reasons).
- **Gotchas**: `BLOCK_SIZE` must be a power of two for `tl.arange`; `tl.dot` needs
  ≥16 in each dim; masks with `other=` on loads but stores need only `mask=`; non-
  contiguous PyTorch inputs must be handled via strides (`stride_am`, …) or `.contiguous()`
  once outside the hot loop; autotune's first call per key is slow — warm it up outside
  the benchmark.

## JAX / XLA (brief)

XLA fuses elementwise ops and can fuse into reductions and some matmul epilogues; `jax.
jit` traces once per shape/dtype (shape polymorphism costs recompiles). Sync points
are `.block_until_ready()`, `np.asarray(x)`, and Python control flow on device values.
`jax.profiler.trace` → Perfetto. Pallas is the Triton-like escape hatch.
