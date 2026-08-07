# Mechanical sympathy — C / C++

Load this only when the target code is C or C++. The mechanism catalog is in
`TECHNIQUES.md` at the skill root; this file has the concrete shapes.

## Field layout

- **Declaration order is guaranteed** — pack fields manually: order hot fields first,
  mind alignment and padding. `alignas(N)` / `__attribute__((aligned))` control
  alignment explicitly.
- `[[likely]]` / `[[unlikely]]` (C++20) hint branch prediction on hot/rare paths;
  older code uses `__builtin_expect`.

## Bounds checks

- **None to elide** — out-of-bounds is UB, so the compiler assumes it can't happen and
  optimizes accordingly. Your cost is correctness, not speed.

## Branchless selection

- `std::min`/`std::max` vs `fmin`/`fmax` differ in NaN semantics — pick deliberately
  (the f-forms are NaN-safe single instructions).
- Compilers emit cmov for data-dependent branches when profitable; verify it actually
  did at `-O2` before claiming it.

## Cold-path outlining

- `[[gnu::cold]]` / `__attribute__((cold))` keep rare paths out of the hot loop body.

## Cache alignment & false sharing

- `alignas(64)` on a field/struct guarantees cache-line alignment; per-thread counters
  on one line ping-pong in M state.
- **Prefetching**: `__builtin_prefetch` / `_mm_prefetch` can hide DRAM latency for
  data-dependent strides the hardware prefetcher can't follow — use only after
  profiling shows a real stall.

## SIMD & intrinsics

- `<immintrin.h>` (x86), `<arm_neon.h>` (Arm), and `<ammintrin.h>` (AMD) expose
  vendor intrinsics; `<experimental/simd>` (std::simd) is the portable alternative.
- Auto-vectorization needs the right shape: contiguous arrays, no aliasing
  (`restrict`/`__restrict__`), and `-O2`/`-O3` with the target ISA enabled.

## Build flags

- `-march=native` for machine-local builds only (enable the machine's SIMD).
- `-flto` for link-time optimization; `-O3` + `-funroll-loops` carefully (measure).
- PGO via `-fprofile-generate` / `-fprofile-use`; Clang/GCC both support it.
- Sanitizers (`-fsanitize=address,undefined`) for correctness runs — never in the
  hot-release build.

## Pre-sizing

- `std::vector::reserve` before known-size bulk ingest avoids realloc-copy churn.

## Concurrency

- `std::atomic` on its own line/cache line to avoid false sharing; per-thread
  accumulation merged once beats a shared atomic per item.

## Notes

- Copies become `memcpy`; moves are cheap; small trivially-copyable types travel in
  registers — don't add pointer indirection for them.
