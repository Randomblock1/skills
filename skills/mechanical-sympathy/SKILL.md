---
name: mechanical-sympathy
description: Mechanical sympathy for hot code — find, verify, and rank CPU-friendly improvements (cache-friendly layout, branchless selection, allocation-free steady state) in safe code. Use when the user mentions mechanical sympathy or cache/branch/allocation behavior, asks why a loop or per-frame path is slow, or wants a hot path reviewed for how it treats the CPU. Not for metric-driven optimize-until-target loops (use auto-optimize).
---

# Mechanical sympathy

The CPU rewards predictable branches, linear address streams, dense data, and a quiet
allocator. This skill finds where code fights that grain and proposes safe fixes — each one
**proved or dropped**, never assumed. The deliverable is a verified, honestly-rated idea
list; do not edit code unless the user asks.

Definitions, technique catalog, and the two machine-facts lists live in
[TECHNIQUES.md](TECHNIQUES.md) — read it before step 2, and read the one matching
`references/lang-<lang>.md` for your target language.

## 1. Map the traffic

**Traffic = bytes touched × frequency.** Walk the code and tag every loop and data path
with its rate class: per-element × stream rate, per-frame, per-user-action, or once
(*cold*). Estimate bytes touched from the real container element sizes (compute the
actual element size in your language — `size_of`/`sizeof`/layout, don't guess).
Multiply out.

Completion: every loop in scope carries a rate class and a bytes-touched figure, and the
dominant traffic path is identified by arithmetic, not vibes. Most codebases have exactly
one cliff; find it before proposing anything.

## 2. Match techniques

Shortlist catalog entries whose *pays-off-when* condition matches the dominant paths.
*Cold* paths only earn trivial-complexity changes (or none — "cold, leave it" is a
finding). Check the **already-free list** in TECHNIQUES.md first so you don't propose what
the machine already does.

Completion: each shortlisted technique names the concrete `file:line` it would apply to.

## 3. Prove or drop

Adversarially verify every candidate; default stance is *drop*. Five gates, all must pass:

- **Read gate** — the cited code actually does what the idea claims. Read it.
- **Safety gate** — expressible in safe, idiomatic code; no `unsafe`, no lint fights.
- **Compiler gate** — *the compiler didn't get there first.* When the claim is about
  codegen (dead stores, bounds checks, constant folds, vectorization), compile a minimal
  repro with optimizations on and look at the assembly. TECHNIQUES.md lists what the
  compiler reliably does and what it provably won't.
- **Hardware gate** — the mechanism survives the real machine: a branch costs only if
  mispredicted; an access pattern is hostile only if the prefetcher can't follow it
  (sequential ring-buffer scans are two linear runs — fine); a working set is slow only if
  it misses cache. Do the arithmetic against real cache sizes.
- **Honesty gate** — impact rated against the traffic map: high / medium / low /
  **negligible — craft only**, and the last is a legitimate, stated rating.

Completion: every survivor has `file:line`, mechanism, honest impact, and complexity;
every kill keeps a one-line reason. The kills go in the report — *why an idea fails* is
half the lesson.

## 4. Report

Rank survivors by impact, then teaching value, then inverse complexity. Report three
lists: verified ideas (with sketches), dropped ideas (with reasons), and the
**already-sympathetic inventory** — things the code does right that a future refactor
must not regress. If the user then asks to apply changes, take them top-ranked-first and
re-verify each with a measurement or assembly diff after landing.
