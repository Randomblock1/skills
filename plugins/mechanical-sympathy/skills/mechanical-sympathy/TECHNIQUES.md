# Technique catalog

Each entry: **mechanism → safe-Rust idiom → pays off when**. Distilled from Bakhvalov,
*Performance Analysis and Tuning on Modern CPUs* (2nd ed., chapter refs below),
[Algorithmica HPC](https://en.algorithmica.org/hpc/),
[perf-ninja-rs](https://github.com/grahamking/perf-ninja-rs), and
[branchless binary search](https://pythonspeed.com/articles/branchless-binary-search/).

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
- **Width reduction / quantization** — smaller elements = more per line. `f32` history for
  plotting, `u32` ids, bitfields. Pays exactly like SoA: bandwidth on big scans.
- **Container by physical layout, not Big-O** — `Vec`/`VecDeque` beat pointer-chasing maps
  and lists for scans even with worse asymptotics at realistic n. `HashMap` lookups in an
  inner loop with constant keys → resolve indices once outside (hoist the hash).
- **Eytzinger layout / `partition_point`** — for repeated binary search over big sorted
  arrays: BFS order makes the probe sequence prefetchable; `partition_point` gives the
  branchless (cmov) probe with clean duplicate semantics.
- **Pre-size known growth** — `Vec::with_capacity` / `reserve_exact` before a known-size
  bulk ingest kills the doubling-realloc cascade. Trivial; always worth it on import paths.

## Allocation (ch. 8.2)

- **Allocation-free steady state** — grep per-frame/per-sample paths for `collect`,
  `to_vec`, `to_string`, `format!`, `vec![x]`, `clone`. Each is a malloc in the loop.
  Serialize with `to_writer` not `to_string`; pass slices/indices not owned copies; don't
  heap-wrap a `Copy` value to fit a batch-shaped API (add the scalar enum variant).
- **Note what LLVM can't elide** — an allocation that crosses a channel, `Box<dyn>`, or
  FFI boundary always happens; one consumed locally often folds away. Check before
  claiming either.

## Branches (ch. 10; branchless-binary-search)

- **Classify predictability first** — a branch costs ~15–20 cycles only when mispredicted.
  Loop-invariant flags, wrap-once ring conditions, and 99/1 error checks predict
  perfectly: leave them. Rewrite only data-dependent 50/50-ish branches in hot loops.
- **Branch → arithmetic/selection** — `f32::min`/`max` (single instruction, NaN-skipping),
  bool-as-usize indexing, `std::hint::select_unpredictable` (Rust ≥1.88) for genuine
  cmov. Beware: cmov trades a possible flush for an unconditional data dependency —
  measure on predictable data too.
- **Branch → lookup table** — replace an if-cascade classifying a small integer domain
  with a const array index. Pays when the cascade mispredicts.
- **Cold-path outlining** — keep error/rare paths in `#[cold]`/`#[inline(never)]`
  functions so the hot loop body stays small and I-cache/µop-cache resident (ch. 11).

## Compute & ILP (ch. 9)

- **Break dependency chains** — a reduction is latency-bound on one accumulator; use 2–4
  independent accumulators folded at the end (integers: exact; floats: changes rounding —
  do it deliberately). This, not "unrolling", is what unrolling is for.
- **Strength reduction** — division is the one arithmetic op still expensive (int `div`
  ~20-40 cycles, `divss` ~11 vs `mulss` ~4). Runtime-divisor `%` in a loop → countdown
  counter; float `/ CONST` → `* (1.0 / CONST)` const (see the won't-do list below).
- **LICM & unswitching by hand when the compiler can't** — hoisting a hash lookup, a
  dynamic-dispatch resolution (`downcast_ref` chains), or an allocation is beyond LLVM;
  hoisting pure arithmetic isn't. Only hand-hoist what has a side effect or type barrier.
- **Loop fusion** — N passes extracting different fields from the same array = N× the
  traffic; one pass with an `[T; N]` extractor touches each line once. Fuse only loops
  over the same range with no cross-iteration dependence; count write streams too — nine
  output streams from one fused loop can be worse than nine clean passes.
- **Autovectorization-friendly shapes** — iterate slices (not indexed ring buffers),
  `chunks_exact` for the vector body + `remainder` for the tail, avoid `enumerate`-driven
  index tracking (argmin/argmax defeats SIMD; when position doesn't matter — e.g.
  sub-pixel plot buckets — drop it and fold pure min/max).

## Concurrency (ch. 13)

- **False sharing** — two threads writing fields on one cache line ping-pong it in M state.
  Pad with `#[repr(align(64))]` wrappers or restructure. Only matters for genuinely
  concurrent frequent writes; mpsc-style handoff designs are immune by construction.
- **Accumulate privately, publish in batches** — per-thread partials merged once beat a
  shared atomic counter bumped per item.
- **Message shape = arrival shape** — size channel messages to what the producer actually
  produces per wakeup (one sample → scalar variant, a packet → fixed array); don't batch
  what never arrives in bursts.

## Build-level (ch. 11; perf-ninja LTO/PGO labs)

- `[profile.release] lto = "thin", codegen-units = 1` — cross-crate inlining and better
  layout for zero source change; costs build time. `target-cpu=native` for
  machine-local builds only. PGO exists but rarely earns its pipeline in small tools.

## The machine already does this (don't propose it)

- **rustc reorders struct fields** — a padding-free struct can't be shrunk by reordering;
  `#[repr(C)]` is what *disables* this.
- **Dead-store elimination** — zero-init-then-overwrite compiles identically to
  write-once (`array::from_fn` is style, not speed).
- **Predicted branches are free** — loop-invariant conditions, wrap-once ring-buffer
  branches, monotonic checks: ~0 cost after the first iterations.
- **Prefetcher handles ring buffers** — a sequential `VecDeque` scan is two linear runs;
  `as_slices()` yields the same physical bytes. No cache win there, only (maybe)
  bounds-check/SIMD wins.
- **Bounds-check elision** — iterator chains and `for x in &slice` compile checkless;
  so does indexing after an explicit `let s = &v[a..b]` slice.
- **Copies become `memcpy`**, moves are free, small `Copy` types travel in registers.

## The compiler will NOT do for you (real opportunities)

- **Float `x / CONST` → `x * (1/CONST)`** — not without fast-math (1 ulp difference);
  verified empirically. Write the reciprocal constant yourself.
- **Fuse loops separated by heap allocation or side effects** — each `collect`/`Vec` is a
  fusion barrier.
- **Restructure your data** — no AoS→SoA, no hot/cold splitting, no shrinking a type that
  is serialized, `pub`, or crosses a crate boundary.
- **Elide allocations that cross channels/FFI/dyn boundaries.**
- **Vectorize argmin/argmax or wrapping-index loops** — remove the index tracking or the
  ring arithmetic first.
- **Un-hash your loop-invariant `HashMap` lookups or un-dispatch your per-row downcasts** —
  type barriers and side effects block LICM; hoist by hand.
