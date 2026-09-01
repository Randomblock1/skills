# GPU sympathy — Vulkan compute, Arm Mali (embedded), Intel Xe notes

Load this only when the target is raw Vulkan/SPIR-V compute, or runs on an embedded
Arm Mali GPU (RK3588-class SoCs and Android devices), or on Intel integrated/Arc
graphics. wgpu/CubeCL on Vulkan reads this alongside `backend-rust.md`. The mechanism
catalog is in `TECHNIQUES.md` at the skill root.

## Vulkan compute — API-level facts (any vendor)

- **Subgroup size is a property, not a constant**: `VkPhysicalDeviceSubgroupProperties.
  subgroupSize` = 32 (NVIDIA, AMD RDNA wave32, Apple via MoltenVK), 64 (AMD CDNA/GCN),
  16 (Mali Valhall), 8/16/32 (Intel). `VK_EXT_subgroup_size_control` pins it per pipeline
  and reports `minSubgroupSize`/`maxSubgroupSize`; `gl_SubgroupSize` in the shader.
  Subgroup ops (`subgroupAdd`, `subgroupShuffleDown`, `subgroupBallot`, …) are core
  since Vulkan 1.1 — feature-check `supportedOperations`.
- **Workgroup size** via specialization constants (`layout(local_size_x_id = 0)`) so one
  SPIR-V serves several GPUs; keep `maxComputeWorkGroupInvocations` (≥128 guaranteed,
  256–1024 typical) and `maxComputeSharedMemorySize` (≥16 KB guaranteed, 32–64 KB
  typical) in mind.
- **Memory types decide the transfer story**: on a discrete card, `DEVICE_LOCAL` for
  resident data plus a `HOST_VISIBLE | HOST_COHERENT` staging buffer and
  `vkCmdCopyBuffer`; on unified-memory devices (Mali, APUs, Apple/MoltenVK) a
  `DEVICE_LOCAL | HOST_VISIBLE` type usually exists — zero-copy, no staging. Look at
  `vkGetPhysicalDeviceMemoryProperties` before proposing either. Small (≈256 MB)
  BAR-mapped `DEVICE_LOCAL | HOST_VISIBLE` heaps exist on discrete cards (ReBAR larger)
  — fine for uploads, PCIe-speed for reads.
- **Sync tax**: `vkQueueWaitIdle` / `vkDeviceWaitIdle` per frame, a `vkWaitForFences`
  on the just-submitted fence, or mapping the result buffer every iteration serializes
  CPU and GPU. Ring 2–3 frames of command buffers/fences; use timeline semaphores.
  Batch dispatches into one command buffer with pipeline barriers only where a real
  dependency exists (`VK_ACCESS_SHADER_WRITE_BIT → SHADER_READ_BIT`, compute→compute
  stage); a full `MEMORY` barrier between every dispatch is a common hidden cost.
- **Precision extensions**: `VK_KHR_16bit_storage` + `VK_KHR_shader_float16_int8` for
  real fp16 arithmetic (`float16_t`); `RelaxedPrecision` (`mediump`) is a hint that
  Mali honours and desktop parts mostly ignore.
- **Verification**: `vulkaninfo` (limits, subgroup size, memory heaps);
  `VK_LAYER_KHRONOS_validation` (correctness, sync hazards with `VK_LAYER_SETTINGS`
  synchronization validation); RenderDoc for capture + dispatch timings; vendor tools
  for ISA/counters (Nsight Graphics, Radeon GPU Profiler + RGA `rga -s vk-spv-offline
  -c gfx1100 --isa out.txt k.spv`, Mali Offline Compiler below, Intel GPA);
  `vkCmdWriteTimestamp` pairs scaled by `timestampPeriod` for GPU time.
  SPIR-V hygiene: `spirv-val`, `spirv-opt -O`, `spirv-dis` (SPIRV-Tools) — the compiler
  gate's first artifact; the vendor ISA is the second.

## Arm Mali (Valhall / 5th-gen; RK3588 = Mali-G610 MP4)

### Machine facts

- **Warp width 16** (Valhall and 5th-gen; Bifrost was 4/8). Workgroup size a multiple of
  16; **64 is the usual default**, up to 256 for reductions; larger workgroups mostly
  cost barrier stalls without adding parallelism.
- **Unified, tile-based**, sharing the SoC's LPDDR with the CPU: RK3588 has a 64-bit
  LPDDR4x/LPDDR5 bus ≈ 30–45 GB/s **total**, shared with 8 CPU cores and the NPU.
  Memory bandwidth is the limiter for almost every compute kernel; fusion and fp16
  storage are the wins. Passive thermal throttling on most boards — clocks drop under
  sustained load, so benchmark warm and long.
- **No dedicated shared memory**: `shared`/`var<workgroup>` storage is backed by the
  normal L1/L2 cache path, so "tile through shared memory" yields far less than on
  desktop parts and each `barrier()` is expensive. Arm's guidance: prefer direct cached
  loads with good locality; use workgroup memory only for real cross-thread exchange.
  This entry flips the catalog's shared-tiling default — say so in the report.
- **Registers**: ≤32 work registers per thread keeps full thread occupancy; 33–64
  halves it. `malioc` reports the count and the resulting max threads.
- **Arithmetic**: 16-wide FMA unit; **packed fp16/int16 runs at 2× fp32 rate, int8 4×**
  — `mediump`/`float16_t` on storage *and* math is a genuine throughput and bandwidth
  win here, unlike on desktop where it's mostly bandwidth. SFU (transcendentals, rcp,
  rsqrt) is 4-wide (¼ rate). Integer division/modulo is slow — use `uint`, powers of
  two, precomputed reciprocals. CVT (conversion) pipeline is separate — mixing widths in
  a loop costs conversions; `malioc` lists FMA/CVT/SFU cycles per pipeline.
- **L2**: 512 KB–2 MB configurable per SoC (G610 on RK3588 ≈ 2 MB shared by 4 cores);
  no L3. Working sets beyond L2 stream from LPDDR.
- **CSF** (Command Stream Frontend, Valhall gen4+): three hardware queues (compute,
  vertex, fragment); compute and graphics overlap; driver launch overhead is higher
  than desktop — batch dispatches per command buffer.
- **Access patterns**: 16 B-aligned `vec4` loads per thread; contiguous across the
  16-wide warp; textures/images have a separate cached path that can beat buffers for
  2D neighbourhood reads (stencils, CV filters).
- **Drivers on RK3588**: vendor blob (libmali, Vulkan 1.2, OpenCL 2.1) vs mainline
  Panthor + Mesa PanVK/Panfrost — feature and performance differ; record which one the
  numbers came from. The 6-TOPS NPU (RKNN/RKLLM) is a separate unit — int8 inference
  belongs there, not on the GPU.

### Verification commands

- **Mali Offline Compiler**: `malioc -c Mali-G610 --vulkan --compute k.spv` (or `.comp`
  GLSL) → *Work registers*, *Uniform registers*, *Stack spilling* (must be none),
  *Max threads*, per-pipeline cycle estimates (Arith FMA / CVT / SFU, Load/Store,
  Texture), the **bound pipeline**, shortest/longest path, *16-bit arithmetic %* (how
  much of the math is actually fp16), and warnings like "Has side-effects" / "Uniform
  computation" (hoistable). This is the compiler gate on Mali — no ISA dump needed.
- **Arm Streamline** (`gatord` on the board, Streamline on the host) / **Performance
  Advisor**: counters *Mali Core Active Cycles*, *Mali Core Warps*, *Mali External Bus
  Read/Write Bytes* (the DRAM traffic — compare to the useful-bytes figure), *L2 Cache
  Read Misses*, *Mali Compute Cycles*, tiler/fragment split. Confirms memory- vs
  ALU-bound and reveals throttling (clock counter).
- RenderDoc (Linux/Android) for Vulkan compute capture and per-dispatch time;
  `vulkaninfo` for the `subgroupSize == 16` check.
- Timing with `vkCmdWriteTimestamp`; run ≥60 s to see the throttled steady state.

## Intel Xe (integrated and Arc discrete) — brief

- Subgroup/SIMD width 8/16/32 selectable (`VK_EXT_subgroup_size_control`; SYCL
  `reqd_sub_group_size`); Xe cores with 16 vector engines; shared local memory 64–128 KB
  per Xe core; L1 shared with SLM.
- Integrated: shares DRAM (zero-copy USM `host`/`shared` allocations, `HOST_VISIBLE |
  DEVICE_LOCAL` Vulkan types); Arc discrete: PCIe transfer story applies, ReBAR matters.
- fp16 at 2× fp32; XMX matrix engines on Arc/Xe-HPG+ (oneDNN, `joint_matrix`).
- Verification: Intel VTune (GPU Compute/Media Hotspots, GPU Roofline), `unitrace` /
  `ze_tracer` for Level Zero timelines, `IGC_ShaderDumpEnable=1` to dump the Intel
  Graphics Compiler ISA, Intel GPA for Vulkan captures.
