# GPU sympathy — Rust GPU ecosystem

Load this only when the target is Rust: CubeCL kernels, wgpu/WGSL compute, rust-gpu
(SPIR-V), or raw driver bindings (cudarc, cust). Also read the file for the physical
backend underneath (CUDA, HIP, Metal, Vulkan/Mali) — the ISA and profiler are theirs.
The mechanism catalog is in `TECHNIQUES.md` at the skill root.

APIs in this space move fast; when a name below doesn't match the crate version in
`Cargo.lock`, trust `cargo doc --open` over this file.

## What "safe, idiomatic" means here

- Host side is ordinary safe Rust: typed buffers, bounds-checked slices, `Vec` reuse
  across iterations, no `unsafe` transmutes to fake a `[f32]` → `[f32x4]` view — use the
  framework's line/vector type.
- Kernel side: CubeCL `#[cube]` bodies and rust-gpu kernels are borrow-checked Rust;
  WGSL is a separate language with mandatory bounds clamping. `launch_unchecked` /
  `unsafe` launches are the analogue of unchecked indexing — propose them only after
  the profiler shows the bounds checks are the cost, and say so.
- Vectorization, coalescing, and tiling are expressed through the framework's types
  (`Line<T>`, `vec4<f32>`, `SharedMemory`, `var<workgroup>`), never through pointer
  casts.

## CubeCL (`cubecl` crate — Burn's compute layer)

- **Model**: `#[cube(launch)]` (bounds-checked) / `#[cube(launch_unchecked)]` functions
  in real Rust, JIT-compiled per backend: `CudaRuntime`, `HipRuntime`, `WgpuRuntime`
  (Vulkan / Metal / WebGPU via wgpu), `CpuRuntime` (SIMD). One source, every machine
  class — but the *numbers* still come from the physical backend.
- **Vocabulary map**: CubeCL "cube" = block/threadgroup; "unit" = thread; "plane" =
  warp/wavefront/SIMD-group (`plane_sum`, `plane_max`, `plane_broadcast`, `plane_dim()`
  for the width — it is 32 on NVIDIA/RDNA/Apple and **64 on CDNA**, so never hard-code);
  `ABSOLUTE_POS`, `UNIT_POS`, `CUBE_POS`, `CUBE_DIM` for indexing; `CubeCount` /
  `CubeDim` at launch; `SharedMemory::<F>::new(n)` + `sync_units()` for tiling.
- **The three pillars are the catalog**:
  - **Vectorization / `Line<T>`** — `Array<Line<F>>` with a line size (1/2/4/8) set on the
    launch argument (`ArrayArg::from_raw_parts::<F>(&handle, len, line_size)`); each
    unit then loads a whole line = the 128-bit vector load. Line size must divide the
    contiguous dimension; a line size of 1 on a hot array is the first thing to check.
  - **Comptime** — `#[comptime]` parameters and `comptime!` blocks specialize the kernel
    at JIT time: constant tile sizes, unrolled loops (`#[unroll]`), constant divisors
    (the strength-reduction entry), and branch elimination on shape properties.
  - **Autotune** — `cubecl::tune` benchmarks candidate kernels/configs per shape key and
    caches the winner; this is the block-size/tile search made explicit. Propose it
    when the best config is shape-dependent, not as a substitute for fixing coalescing.
- **Matrix units**: `cubecl::cmma` (cooperative matrix) targets tensor cores / MFMA /
  simdgroup_matrix; the `cubecl-linalg`/matmul components already use it — check before
  hand-writing.
- **Host pipeline**: `client.create(bytes)` / `client.read_one(handle)` — a read is a
  device→host sync; keep it out of the per-iteration loop. Handles are reference-
  counted; reuse buffers across launches rather than `create` per frame. `client.sync()`
  is the explicit barrier.
- **Verification**: set the CubeCL debug logging env var (`CUBECL_DEBUG_LOG=1`, or
  `CUBECL_DEBUG_OPTION=debug|profile` on newer versions — confirm in the crate's
  README) to dump the generated CUDA C / HIP / WGSL / SPIR-V source and per-kernel
  timings; then apply the physical backend's compiler gate to that source (`-Xptxas -v`
  on the CUDA source, naga/RenderDoc on WGSL). Feature flags select the runtime
  (`cubecl = { features = ["cuda"|"hip"|"wgpu"] }`).
- **Gotchas**: shape-dependent `comptime` values recompile per distinct shape (JIT storm
  on dynamic shapes — key autotune on shape *class*); `Line` size > 1 with an
  unaligned offset silently falls back or errors depending on backend; `plane_*` ops
  need a full plane active.

## wgpu (WGSL compute) — Vulkan / Metal / DX12 / WebGPU

- **Kernel shape**: `@compute @workgroup_size(64)` (1D; 8×8 or 16×16 for 2D) —
  multiples of 32 for desktop, of 16 for Mali; `@builtin(global_invocation_id)`,
  `local_invocation_id`, `workgroup_id`; `var<workgroup> tile: array<f32, 64>;` +
  `workgroupBarrier()`; `vec4<f32>` storage arrays for vector loads; `enable f16;` (+
  `Features::SHADER_F16`) for `f16`/`vec4<f16>` — the fp16 storage win on Mali/Apple.
- **Subgroups** (native only, not WebGPU-portable yet): `Features::SUBGROUP` →
  `enable subgroups;` in WGSL, `subgroupAdd`, `subgroupMax`, `subgroupShuffleDown`,
  `subgroupBallot`, `@builtin(subgroup_size)`, `@builtin(subgroup_invocation_id)`. The
  size is a runtime builtin (32 / 64 / 16 / 8 depending on GPU) — write reductions
  against it, not a constant.
- **Buffer layout rules** (WGSL std430-like): `vec3<f32>` is 16 B-aligned and 16 B wide
  in storage — pack as `vec4` or three scalars; struct members are aligned to their
  type's alignment; array stride ≥ element alignment. Mismatched Rust `#[repr(C)]`
  structs are the classic silent-garbage bug; use `bytemuck` + `encase`/`crevice` for
  layout, and check `naga`'s validation errors.
- **Dynamic offsets**: `min_storage_buffer_offset_alignment` = 256 B (default limit);
  `min_uniform_buffer_offset_alignment` = 256 B. Sub-allocate big buffers on those
  boundaries rather than creating buffers per dispatch.
- **Limits worth reading before proposing**: `max_compute_invocations_per_workgroup`
  (256 default), `max_compute_workgroup_storage_size` (16 KB default —
  `var<workgroup>` budget), `max_compute_workgroup_size_{x,y,z}`,
  `max_storage_buffer_binding_size`. Request higher limits at `request_device` when the
  adapter supports them.
- **Readback is the transfer step** (even on unified memory the API forces a copy): you
  cannot map a `STORAGE` buffer. Shape: staging buffer `BufferUsages::MAP_READ |
  COPY_DST`, `encoder.copy_buffer_to_buffer(src, 0, staging, 0, n)`, submit,
  `staging.slice(..).map_async(MapMode::Read, cb)`, `device.poll(PollType::Wait)` (older:
  `Maintain::Wait`). A `poll(Wait)` per frame is a full sync — pipeline with several
  staging buffers and poll for *last* frame's result. Uploads: `queue.write_buffer`
  (internally staged; fine for small/medium), or a persistent `MAP_WRITE | COPY_SRC`
  staging buffer for large streams.
- **Launch tax**: each `dispatch_workgroups` is cheap inside one `ComputePass`; the
  expensive things are `queue.submit` per dispatch and creating pipelines/bind groups per
  frame — build once, reuse, batch dispatches in one encoder.
- **Verification**: `naga` CLI (`cargo install naga-cli`; `naga k.wgsl k.spv` /
  `naga k.wgsl k.metal` / `--validate`) shows the translated SPIR-V/MSL/HLSL — the
  compiler gate's first step; then the physical backend's tools: RenderDoc (Vulkan
  backend, `WGPU_BACKEND=vulkan`), Xcode GPU capture (Metal backend, set
  `METAL_CAPTURE_ENABLED=1`), Nsight Graphics, or Mali Offline Compiler on the SPIR-V.
  GPU timing: `Features::TIMESTAMP_QUERY` + `QuerySet` (`QueryType::Timestamp`) with
  `ComputePassTimestampWrites`, scale by `queue.get_timestamp_period()`.
  `WGPU_POWER_PREF=high` picks the discrete adapter on dual-GPU machines.

## rust-gpu (Rust → SPIR-V)

- `#[spirv(compute(threads(64)))]` entry points, `spirv-std` for builtins (`global_
  invocation_id`, `workgroup` memory via `#[spirv(workgroup)]`, `arch::*` subgroup ops
  where the target supports them), built with `spirv-builder` / `cargo gpu`.
- Same layout and bounds rules as any SPIR-V consumer; the compiler gate is
  `spirv-dis k.spv` (SPIRV-Tools) → `spirv-opt -O` → `spirv-val`, then the driver's ISA
  view (RenderDoc, RGA for AMD, `malioc` for Mali).

## cudarc / cust (raw CUDA from Rust)

- **cudarc** — thin, safe-ish driver API: `CudaContext::new(ordinal)`, streams
  (`ctx.default_stream()` / `ctx.new_stream()`), `stream.alloc_zeros::<f32>(n)`,
  `stream.memcpy_stod` / `memcpy_dtoh`, pinned host memory via the context's pinned
  allocation API (needed for real async copies — the pageable-fallback rule applies),
  kernels from PTX (`cudarc::nvrtc::compile_ptx` at runtime or `Ptx::from_file`) loaded
  with `ctx.load_module` and launched through the builder API with
  `LaunchConfig { grid_dim, block_dim, shared_mem_bytes }` (`LaunchConfig::for_num_elems`
  picks a 1D config). Events, graphs, and cuBLAS/cuDNN bindings live behind feature
  flags. The kernel body is CUDA C — apply `backend-cuda.md` to it verbatim.
- **cust** (Rust-CUDA project) — `Module::from_ptx`, `Stream::new(StreamFlags::
  NON_BLOCKING)`, `DeviceBuffer`, `LockedBuffer` (pinned host), the `launch!` macro;
  `rustc_codegen_nvvm` compiles Rust kernels to PTX. Same catalog, same SASS check.
- In both, the Rust wrapper cannot hide CUDA's hidden syncs: `memcpy_dtoh` to a `Vec`
  is synchronous, `alloc` inside the loop synchronizes, and a `DeviceBuffer` dropped per
  iteration is a `cudaFree`.

## Mapping catalog entries to shapes

| Catalog entry | CubeCL | wgpu/WGSL |
|---|---|---|
| Vectorized load | `Array<Line<F>>`, line size 4 at launch | `array<vec4<f32>>` storage buffer |
| Shared tiling | `SharedMemory::<F>::new(N)` + `sync_units()` | `var<workgroup>` + `workgroupBarrier()` |
| Warp reduction | `plane_sum(v)` | `subgroupAdd(v)` (feature-gated) |
| Constant divisor / tile | `#[comptime]` param | `override` constants / `const` |
| Launch bounds | `CubeDim` chosen by autotune | `@workgroup_size` + limits |
| Pinned + async copy | reuse handles, avoid `read_one` per iter | staging ring, poll last frame |
| Compiler gate | dumped backend source → its toolchain | `naga` → RenderDoc/Xcode/`malioc` |
