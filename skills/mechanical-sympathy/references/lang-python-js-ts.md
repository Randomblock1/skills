# Mechanical sympathy — Python / JS / TS

Load this only when the target code is Python, JavaScript, or TypeScript (i.e. running
under CPython, PyPy, V8/JSC/SpiderMonkey). The mechanism catalog is in
`TECHNIQUES.md` at the skill root; this file has the concrete shapes.

## What does NOT transfer

- **Struct layout, branchless-selection, cmov, `#[cold]`-style tricks** — the
  runtime/JIT owns codegen. Don't propose layout or branch-level changes here.
- Manual memory-prefetch and cache-line padding are meaningless at this level.

## Python (CPython)

- **The interpreter loop is the bottleneck.** Per-element Python calls are the enemy;
  the durable wins are *fewer passes* and *bulk operations*.
- **NumPy / vectorized ops** — express the hot loop as a whole-array operation
  (broadcasting, `ufunc`s). A native NumPy pass beats a Python loop by 100×+.
- **Numba / Cython / Pythran** — JIT or compile the numeric core to native code
  (`@njit`, typed Cython). Best when the loop can't be vectorized.
- **Avoid per-call allocation** — reuse buffers/lists; prefer `array`/`bytearray`/
  NumPy arrays over Python lists of objects for dense numeric data.
- **PyPy** — great for pure-Python loops but interfaces poorly with NumPy; don't mix
  unless you've benchmarked.
- Profile with `cProfile`/`scalene`/`py-spy` before optimizing; `timeit` for micro.

## JavaScript / TypeScript (V8, JSC, SpiderMonkey)

- **The JIT (TurboFan/Maglev on V8) optimizes hot functions** — but only if they stay
  *type-stable*. The single highest-yield rule: **keep shapes monomorphic**.
- **Consistent object shapes** — always construct objects with the same key order;
  avoid ad-hoc adding/removing properties in hot paths (forces polymorphic ICs and
  deopt).
- **Typed arrays** (`Float64Array`, `Int32Array`, `Uint8Array`) for numeric hot loops —
  they give contiguous, unboxed storage and SIMD-friendly access, unlike plain arrays
  of boxed doubles.
- **Stable numeric types** — don't mix int/float/string in one variable across
  iterations (deopt); use `for` loops over typed arrays rather than `forEach`/
  spread (allocation + polymorphic call sites).
- **Avoid allocation in the loop** — `splice`, spreads, and object literals in a hot
  loop all allocate; preallocate and mutate.
- **`BigInt` is slow** — keep to `Number` unless you truly need the range.

## Where mechanical sympathy DOES apply

- **Memory traffic is still memory traffic** — fewer passes over big arrays, and
  sequential access patterns, still win at the hardware level; the way to express them
  is bulk/vectorized operations rather than per-element loops.
- **Allocation-free steady state** is the same idea — the JIT/GC makes it less
  explicit, but per-frame/per-sample allocations still cost (GC pressure, cache
  misses).
- **The "map the traffic" step is language-independent** — tag rate classes and count
  bytes touched; then pick the *algorithmic* fix the runtime supports (vectorize,
  fuse passes, preallocate).
