# Technique catalog

Each entry: **mechanism → idiomatic shape in your language → pays off when**. Distilled from
Bakhvalov, *Performance Analysis and Tuning on Modern CPUs* (2nd ed., chapter refs below),
[Algorithmica HPC](https://en.algorithmica.org/hpc/),
[perf-ninja-rs](https://github.com/grahamking/perf-ninja-rs), and
[branchless binary search](https://pythonspeed.com/articles/branchless-binary-search/).
The mechanisms are language-independent; the source examples skew Rust/C++. Where a fact
genuinely varies by language — struct layout, bounds checks, build flags — see
[Per-language notes](#per-language-notes) at the bottom.

## Memory & layout (ch. 8)

- **Sequential access** — the stream prefetcher hides DRAM latency only for linear (or
  constant-stride) address streams. Iterate in storage order; restructure loops
  (interchange) so the inner loop is unit-stride. Pays on any working set past L2.
- **Reason in cache lines, not elements** — a load costs a 64 B line; a 40 B struct scanned
  for one 4 B field wastes 90% of the traffic. Compute *useful bytes ÷ touched bytes* for
  every hot scan.
- **AoS → SoA** — one dense array per field makes single-field scans ~size-of-struct/4×
  cheaper and unlocks vectorization. Costs a length-invariant across parallel arrays and
  complicates whole-record access (export paths!). Pay only when one field dominates the
  scans.
- **Hot/cold structure split** — the cheap middle path: move fields the hot loop never
  reads into a parallel cold array. Most of SoA's win, a fraction of its ripple.
- **Width reduction / quantization** — smaller elements = more per line. `f32`/`float`
  history for plotting, `u32`/`int` ids, bitfields. Pays exactly like SoA: bandwidth on
  big scans.
- **Container by physical layout, not Big-O** — flat arrays and deques beat pointer-chasing
  maps and lists for scans even with worse asymptotics at realistic n. Hash-map lookups in
  an inner loop with constant keys → resolve indices once outside (hoist the hash).
- **Eytzinger layout / branchless binary search** — for repeated binary search over big
  sorted arrays: BFS order makes the probe sequence prefetchable; a branchless (cmov)
  probe with clean duplicate semantics (e.g. Rust `partition_point`, C++ `lower_bound`
  that compiles to cmov).
- **Pre-size known growth** — reserve capacity before a known-size bulk ingest (e.g. Rust
  `Vec::with_capacity`/`reserve_exact`, C++ `std::vector::reserve`, Go `make([]T, 0, n)`)
  kills the doubling-realloc cascade. Trivial; always worth it on import paths.

## Allocation (ch. 8.2)

- **Allocation-free steady state** — grep per-frame/per-sample paths for allocations:
  string building (`format!`, f-strings, `toString`), array copies/`collect`, `.clone()` /
  value copies, heap boxing. Each is a malloc in the loop. Serialize to a writer/buffer,
  not an intermediate string; pass references/slices/indices, not owned copies; don't
  heap-allocate a scalar just to fit a batch-shaped API (add the scalar case).
- **Note what the compiler can't elide** — an allocation that crosses a channel, a
  dynamic-dispatch boundary (`dyn`/virtual), or FFI always happens; one consumed locally
  often folds away. Check before claiming either.

## Branches (ch. 10; branchless-binary-search)

- **Classify predictability first** — a branch costs ~15–20 cycles only when mispredicted.
  Loop-invariant flags, wrap-once ring conditions, and 99/1 error checks predict
  perfectly: leave them. Rewrite only data-dependent 50/50-ish branches in hot loops.
- **Branch → arithmetic/selection** — min/max that compile to the single IEEE instruction
  (NaN-skipping), boolean-as-index arithmetic, a `select`/cmov hint where the toolchain
  offers one. Beware: cmov trades a possible flush for an unconditional data dependency —
  measure on predictable data too.
- **Branch → lookup table** — replace an if-cascade classifying a small integer domain
  with a const array index. Pays when the cascade mispredicts.
- **Cold-path outlining** — keep error/rare paths in cold/never-inline functions (Rust
  `#[cold]`, C/C++ `[[gnu::cold]]`, Go `//go:noinline` where needed) so the hot loop body
  stays small and I-cache/µop-cache resident (ch. 11).

## Compute & ILP (ch. 9)

- **Break dependency chains** — a reduction is latency-bound on one accumulator; use 2–4
  independent accumulators folded at the end (integers: exact; floats: changes rounding —
  do it deliberately). This, not "unrolling", is what unrolling is for.
- **Strength reduction** — division is the one arithmetic op still expensive (int `div`
  ~20-40 cycles, `divss` ~11 vs `mulss` ~4). Runtime-divisor `%` in a loop → countdown
  counter; float `/ CONST` → `* (1.0 / CONST)` const (see the won't-do list below).
- **LICM & unswitching by hand when the compiler can't** — hoisting a hash lookup, a
  dynamic-dispatch resolution (downcasts, virtual calls), or an allocation is beyond the
  compiler; hoisting pure arithmetic isn't. Only hand-hoist what has a side effect or
  type barrier.
- **Loop fusion** — N passes extracting different fields from the same array = N× the
  traffic; one pass with a fixed-size array extractor touches each line once. Fuse only
  loops over the same range with no cross-iteration dependence; count write streams too —
  nine output streams from one fused loop can be worse than nine clean passes.
- **Autovectorization-friendly shapes** — iterate contiguous arrays/slices (not indexed
  ring buffers); split into a vectorizable body + scalar tail (Rust `chunks_exact`, C/C++
  range-for over arrays); avoid index tracking where position doesn't matter (argmin/
  argmax defeats SIMD; when position doesn't matter — e.g. sub-pixel plot buckets — drop
  it and fold pure min/max).

## Concurrency (ch. 13)

- **False sharing** — two threads writing fields on one cache line ping-pong it in M state.
  Pad with 64-byte-aligned wrappers or restructure. Only matters for genuinely concurrent
  frequent writes; channel-based handoff designs are immune by construction.
- **Accumulate privately, publish in batches** — per-thread partials merged once beat a
  shared atomic counter bumped per item.
- **Message shape = arrival shape** — size channel messages to what the producer actually
  produces per wakeup (one sample → a scalar, a packet → a fixed array); don't batch what
  never arrives in bursts.

## Build-level (ch. 11; perf-ninja LTO/PGO labs)

- Link-time optimization (LTO) and single codegen units enable cross-module inlining and
  better layout for zero source change; costs build time. Rust: `lto = "thin",
  codegen-units = 1`; C/C++: `-flto`; Go: no LTO flag (whole-program compilation, limited
  cross-package inlining). Target the local CPU for machine-local builds only (Rust
  `target-cpu=native`, C/C++ `-march=native`). PGO exists but rarely earns its pipeline
  in small tools.

## The machine already does this (don't propose it)

- **Field packing** — Rust reserves the right to reorder struct fields, so a padding-free
  struct can't be shrunk by manual reordering there; C/C++/Go preserve declaration order,
  so manual field ordering is on you. `#[repr(C)]` in Rust *disables* the automatic
  reordering.
- **Dead-store elimination** — zero-init-then-overwrite compiles identically to
  write-once (a `from_fn`/`map`-style initializer is style, not speed).
- **Predicted branches are free** — loop-invariant conditions, wrap-once ring-buffer
  branches, monotonic checks: ~0 cost after the first iterations.
- **Prefetcher handles ring buffers** — a sequential scan of a deque/ring buffer is two
  linear runs, same physical bytes. No cache win there, only (maybe) bounds-check/SIMD
  wins.
- **Bounds-check elision** — idiomatic iteration over arrays/slices compiles checkless in
  Rust and Go; so does indexing after an explicit sub-slice. C/C++ have no checks to
  elide.
- **Copies become `memcpy`**, moves are cheap, small value types travel in registers.

## The compiler will NOT do for you (real opportunities)

- **Float `x / CONST` → `x * (1/CONST)`** — not without fast-math (1 ulp difference);
  verified empirically. Write the reciprocal constant yourself.
- **Fuse loops separated by heap allocation or side effects** — each allocation/
  temporary collection is a fusion barrier.
- **Restructure your data** — no AoS→SoA, no hot/cold splitting, no shrinking a type that
  is serialized, exported (`pub`/`public`), or crosses a library/module boundary.
- **Elide allocations that cross channels/FFI/virtual-dispatch boundaries.**
- **Vectorize argmin/argmax or wrapping-index loops** — remove the index tracking or the
  ring arithmetic first.
- **Un-hash your loop-invariant hash-map lookups or un-dispatch your per-row downcasts** —
  type barriers and side effects block LICM; hoist by hand.

## Per-language notes

The catalog above is mechanism-first. The language-specific shapes — struct layout
guarantees, bounds-check elision, cold-path attributes, build flags — live in
`references/lang-<lang>.md`; read only the one matching the target code:
[Rust](references/lang-rust.md), [C/C++](references/lang-c-cpp.md),
[Go](references/lang-go.md), [Python/JS/TS](references/lang-python-js-ts.md).
