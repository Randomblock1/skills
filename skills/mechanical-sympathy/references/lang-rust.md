# Mechanical sympathy — Rust

Load this only when the target code is Rust. The mechanism catalog is in
`TECHNIQUES.md` at the skill root; this file has the concrete shapes.

## Field layout

- rustc may **reorder struct fields** to eliminate padding; a padding-free struct can't
  be shrunk by manual reordering. `#[repr(C)]` *disables* the automatic reordering
  (needed for FFI or when order matters).
- `#[repr(align(N))]` and `#[repr(packed)]` exist for alignment/space control; packed
  fields can cause unaligned accesses.

## Bounds checks

- Iterator and slice iteration compiles checkless; so does indexing after an explicit
  sub-slice (`let s = &v[a..b]`). Indexing by computed values (`v[i]`) keeps a check
  unless the compiler can prove the range.
- `chunks_exact` / `windows` are the idiomatic shapes that vectorize and stay
  checkless.

## Branchless selection

- `std::hint::select_unpredictable` (Rust ≥1.88) emits a genuine cmov when the
  operand is data-dependent.
- `f32::min`/`f32::max` compile to the single IEEE min/max instruction (NaN-aware),
  unlike manual comparisons.

## Cold-path outlining

- `#[cold]` and `#[inline(never)]` keep rare paths out of the hot loop body so the
  I-cache/µop-cache stays resident.

## Allocator

- Swap the global allocator: `tikv-jemallocator` (Linux/macOS) or `mimalloc` via a
  `#[global_allocator]` static. Can be large wins for allocation-heavy programs.

## Build keys (`Cargo.toml`, `[profile.release]`)

- `lto = "thin"` / `"fat"` — whole-program optimization, 10–20%+ runtime wins, slower
  builds. `lto = false` leaves thin local LTO on; `lto = "off"` disables it.
- `codegen-units = 1` — one unit lets the compiler see more; costs compile time.
- `target-cpu = "native"` (or `RUSTFLAGS="-C target-cpu=native"`) — enables the
  machine's SIMD/AVX; only for machine-local builds.
- `panic = "abort"` — smaller/faster binary if you don't need unwinding.
- `opt-level = "z"` / `"s"` — binary-size targets.
- `strip = "symbols"` — release binaries are stripped by default since Rust 1.77.
- Alternative linkers (`lld`/`mold`) speed up the build with no runtime downside.
- PGO via `cargo-pgo`; not supported for `cargo install`-distributed binaries.

## Pre-sizing

- `Vec::with_capacity` / `reserve_exact` before known-size bulk ingest avoids the
  doubling-realloc cascade.

## SIMD

- Auto-vectorization happens on slice iteration when the shape is right; `std::simd`
  (portable SIMD) is available on nightly; `core::arch` gives per-ISA intrinsics
  (e.g. `_mm256_*` via target features).

## Concurrency

- `mpsc` channels hand off without false sharing by construction; per-thread partials
  merged once beat a shared atomic per item. Watch cross-thread cache-line writes —
  pad with `#[repr(align(64))]`.
