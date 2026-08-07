# Mechanical sympathy — Go

Load this only when the target code is Go. The mechanism catalog is in
`TECHNIQUES.md` at the skill root; this file has the concrete shapes.

## Field layout

- **Declaration order is preserved**; the compiler does not pack fields, so order hot
  fields first manually to minimize padding.
- No portable alignment attribute; pad structs manually for cache-line alignment.

## Bounds checks & BCE

- The compiler inserts bounds checks; its SSA pass performs **bounds-check elimination
  (BCE)** for accesses it can prove safe.
- Idiomatic range loops (`for i := range a`, `for _, v := range a`) are the shapes BCE
  handles best. Indexing `a[i]` by a computed index keeps a check unless provably in
  range.
- Getting a slice first (`s := a[lo:hi]`) then indexing `s[i]` lets BCE kick in.
- Hot loops that still carry checks can use `unsafe` pointer arithmetic **only** when
  you can prove bounds — it's the escape hatch, not the default.

## Branchless selection

- No portable cmov hint; the compiler decides. Min/max of ints/floats sometimes become
  branchless — verify in the generated SSA/assembly rather than assuming.

## Cold-path outlining

- `//go:noinline` where the compiler keeps inlining a rare path into the hot loop.
- `//go:nosplit` and `//go:nowritebarrierrec` exist for special cases — rarely needed.

## SIMD

- Go 1.26's `simd` / `archsimd` package (standard library) gives native vector
  operations with CPU feature detection — 30–50% gains on numeric loops are reported.
- `math/bits` and `golang.org/x/arch` provide optimized primitives; `math` functions
  are often assembly-optimized per-arch.

## Allocation

- **The GC pays for allocation** — fewer allocations beats cleverness. `make([]T, 0, n)`
  pre-sizes; reuse buffers; avoid `fmt.Sprintf` in hot loops.
- Escape analysis moves stack-eligible values off the heap; keep values stack-local
  where possible (don't let them escape into interfaces/pointers).

## Concurrency

- **Goroutines + channels** are cheap and hand off without false sharing by
  construction. Per-goroutine partials merged once beat a shared atomic per item.
- Watch false sharing: two goroutines writing adjacent fields on one cache line
  ping-pong it. Pad the struct manually.

## Build & runtime

- `-gcflags="-m"` shows escape analysis decisions; `-gcflags="-d=ssa/check_bce/debug=1"`
  shows bounds checks the compiler kept.
- Profile with `pprof` (cpu/mem) and tune with `-benchmem` benchmarks before claiming
  anything.

## Notes

- `go build` has no LTO flag — whole-program compilation with limited cross-package
  inlining. There's no `-march=native`; the runtime dispatches on CPU features at
  startup (e.g. which `math`/`crypto` assembly to use).
