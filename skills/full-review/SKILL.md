---
name: full-review
description: >-
  Thorough, patterns-tuned code review of the current working diff (default) or a
  named scope — a diff-hygiene pass plus ten dimensions (correctness/concurrency,
  error handling, resource lifecycle, config/build/env, docs freshness, dead code &
  dead feature wiring, test quality, type/immutability safety, accessibility, and
  simplification) with a mandatory verify-before-report protocol and a typed
  evidence bar. Use whenever the user asks to "review", "review my changes/diff/PR/
  branch", do a "full review" or "thorough review", or wants a pre-PR check. Not
  for writing new features.
---

# Full review

A comprehensive but disciplined review. The value is not the checklist — it is the
**verification**. Most raised findings that turn out wrong are plausible-but-false;
this skill exists to catch real issues AND to refuse to report noise.

## 1. Resolve scope

Default: the **uncommitted working diff** (`git diff HEAD`, staged + unstaged).
Confirm what you're reviewing, then adapt if the user named something else:

- "current changes" / no scope → `git diff HEAD` (+ list untracked files worth reviewing).
- "the branch" / "the PR" / pre-PR → `git diff main...HEAD` (or the repo's default branch).
- a commit / range / paths → review exactly that.

On a long-lived branch, check the diff for foreign changes first: if `main...HEAD`
pulls in files from other teams' already-landed work (history divergence), diff against
the merge-base / restrict to the paths this branch actually touches, and say so.

Read the surrounding code, not just the diff hunks — several failure classes below
(lock scope, dead wiring, config) are only visible with the full function/file in view.
Read the nearest `CLAUDE.md`/`AGENTS.md` and honor its conventions.

**Calibrate depth to scope.** A small focused diff (≲300 lines) is a single careful
read. For a large or multi-package diff, don't serialize a deep read of everything —
fan out: spawn one subagent per cluster of dimensions (or per subsystem) in parallel,
then merge. And see §4 on delegating the correctness axes so you're not re-deriving
what `/code-review` already does well.

## 2. Diff hygiene (always, first)

Before the dimensions, ask of every hunk: **should this be in the diff at all?**
This is the broadest class of feedback human reviewers give, and it's cheap to check:

- Lockfile / generated-artifact churn with no stated reason; personal helper files,
  editor/AI artifacts, debug leftovers.
- Dead on arrival: stubs defined but never wired (RPCs, flags, helpers with no
  caller or reader), empty branches.
- Rebase artifacts: duplicated blocks, re-introduced previously-deleted code.
- Out-of-scope changes riding along → recommend splitting or dropping them.

## 3. Review dimensions

Go through **all** of these. They are ordered by how often they surface real bugs.
For each, the *tells* are concrete shapes to grep the diff for — not vague prompts.

**A. Correctness & concurrency** *(highest-yield)*
- Read-decide-mutate that runs **outside the lock** that protects the state — especially
  one method in a family (`start`/`begin`/`complete`) that guards/dispatches outside a
  lock the others hold inside it. Check guard check + field read + dispatch are atomic.
- Snapshot/serialize methods reading a sequence counter or shared field outside the
  critical section → stale-state-with-new-seq races.
- Sequence/high-water-mark state (`lastSeq`, cursors) that isn't **reset on reconnect**
  after a backend restart.
- Watch/version primitives read without advancing the seen-version (`borrow` vs
  `borrow_and_update`) → predicate stuck permanently true/false.
- Saturating vs wrapping arithmetic mismatches across platforms; off-by-one; unclamped
  lengths copied into fixed buffers.
- Wall-clock time used for durations/timeouts where the clock can jump (RTC-less
  devices, NTP steps) — should be monotonic.
- Synchronous/CPU-heavy work (encoding, disk IO) running directly on an async event
  loop, stalling every other coroutine.

**B. Error handling that masks the real failure**
- Over-broad `except`/`catch` swallowing a narrower error (`except ImportError` also
  eats `ModuleNotFoundError`; bare `except Exception` hiding an `AttributeError`).
  Discriminate on the specific error (e.g. `exc.name`) before re-raising a friendly one.
- External/RPC/IO call inside a **polling loop** with no guard → one transient error
  kills the loop. Wrap and return a status.
- Misclassified failures (e.g. infra/tester error reported as a device/user failure).
- Silent retry: an error path that doesn't advance a clock/cursor and re-attempts the
  same failing op every tick with no log.
- Discarded results: async call not `await`ed, or a `{ok:false}` return ignored, leaving
  the user stuck with no error surfaced.
- Wrong log **severity** for a real failure (info where warning/error is due).
- Indexing `params[0]` / first element without a non-empty check.
- Re-wrapping a specific error into a generic one, discarding the code/context/
  remediation the original carried.
- Wrong-variable/copy-paste defects in error messages and logs (`items[0].name` where
  the loop variable was meant; a reject path logging "cancel") — cheap to verify, real.
- **Retries or client timeouts on non-idempotent operations**: retry-on-timeout of an
  append-only write (server mints a new ID per call), or a client-side timeout that
  abandons the request while server-side work completes → duplicate submissions.

**C. Resource lifecycle**
- Handles/sockets/cameras/files opened, then a later step in the same setup can raise →
  leak. Guard with `try/except BaseException: close(); raise`.
- Sockets left un-drained/desynced on an error frame → close so callers reconnect.
- Whole collections materialized in memory when a stream/generator would do (watch for
  buffers sized by time × rate on constrained hardware).

**D. Config / build / environment assumptions**
- Generated artifacts (proto bindings, codegen) not wired into the dev/deploy target →
  clean checkout fails to import.
- Build prerequisites that omit config files (`vite.config`, `tsconfig`, etc.) → stale
  artifacts served after a config-only change.
- Compiler/arch flags (`target-cpu=native`) that defeat runtime feature dispatch.
- CI that claims (in a comment) to run a linter/check it doesn't actually run.
- Version guards that disagree between README and Makefile/CI.
- Declared runtime dependencies never actually imported.

**E. Docs & comments freshness**
- READMEs/docstrings referencing renamed or deleted symbols.
- **Change-relative language** ("now", "previously", "not in this branch",
  "kept for back-compat") — belongs in the PR body, not the code. Rewrite to present
  tense; on an undeployed branch, delete the back-compat shim outright rather than
  documenting it.
- Comments making a claim that's false at the defaults (cost/timing assertions);
  off-by-one identifiers in docstrings; missing safety/invariant docs on unsafe APIs.
- Example/placeholder config values (in `*.example`, sample env, docs) that are
  **identical to the field's default** — they teach the operator nothing; show a
  recommended non-default value instead.

**F. Dead code & dead feature wiring**
- Branches/conditions that are provably always-false given the callers; empty branches.
- **Circular dead wiring**: a feature whose only populator is its own inert helper, or
  that writes to a private object never copied into what the reader reads. Trace the
  data path end-to-end before assuming a feature works.
- A value emitted/published by one side (backend flag, wire field, event) that no
  consumer ever renders or reads — and the reverse: a client/UI surface promising
  behavior the backend never implements. The feature silently doesn't exist either way.
- Unused fixtures/flags/helpers/CLI options; god-files mixing many unrelated concerns
  (suggest a split); duplicated blocks worth extracting into one helper.

**G. Test quality (not just coverage)**
- Fakes that diverge from reality (a mock exception not subclassing the real base; fake
  defaults non-zero where real protos default to 0/false) — masks or fabricates behavior.
- Tautological assertions (`assert_called_once()` that can't distinguish 1 vs 2 args).
- A regression test that doesn't actually reproduce the bug it guards.
- A test whose name/comment claims to exercise a path it never enters — e.g. an
  assertion identical to one made earlier, with the unit under test never re-invoked;
  it verifies nothing beyond the earlier check.
- Tests mislabeled (integration that's a unit test; a `main()`/print script as a test).
- Duck-typed stand-ins where a real type/proto should be constructed.
- Genuinely missing coverage on a new transport/contract (does the event actually reach
  the client?).

**H. Type & immutability safety**
- Mutable defaults (shared proto/list/dict instances) as default arguments.
- In-place mutation (`.shift()`, mutating shared lists/objects) that breaks an otherwise
  immutable state-update pattern → aliasing bugs.

**I. Accessibility (frontend diffs)**
- Missing `aria-label`/`aria-live`/roles; controls with no accessible name; a bare
  unloaded `<img>` during a loading state with no placeholder/spinner.

**J. Simplification & reuse**
- Existing helper/util that already does this; hand-repeated patterns; cryptic
  one-liners that a named helper would clarify. Only when it genuinely reduces
  complexity — don't add speculative abstraction that fights existing ownership (e.g.
  extracting a class that then needs the parent's lock).

## 4. Verify before reporting (mandatory)

This is the part that makes the review trustworthy. For **every** candidate finding:

1. **Refute it first.** Try to prove it's *not* a bug. Read the actual code path,
   callers, and defaults. A large fraction of plausible findings are false — pre-existing
   behavior, intentional, already-handled, or on unmodified lines. For any
   "missing check/guard" claim, read **one frame up and one frame down** before
   reporting — the single most common false positive is a guard that already exists
   in the caller or callee.
2. **Root-cause, don't pattern-match.** If a linter-style finding looks off (e.g. a
   "malformed path"), check whether the surprising thing is deliberate before "fixing"
   it. Claims that a comparison, threshold, or polarity is **inverted** need the
   domain/spec semantics confirmed first — sensor, hardware, and domain code often
   inverts the naive reading.
3. **Apply the evidence bar by finding type:**
   - *Correctness* findings need a **concrete failure scenario** — input/state → wrong
     output — reachable in the system's real operating envelope (a 49-day counter wrap
     during a seconds-long window isn't). Can't write one → downgrade to an open
     question or drop.
   - *Convention/consistency* findings (style, naming, a11y, docs form) instead need a
     **cited standard** — the repo's style guide or the file's dominant pattern — plus a
     real violation, and are reported batched (§5), never as a nit flood.
   - *Race* findings must name **both concurrent execution contexts** — the two call
     paths that actually overlap. A real race always can; if you can't, it's an open
     question, not a finding.
   - *Migration/back-compat* findings require that the surface has actually **shipped**
     (deployed / on main). Unshipped surfaces are exempt from expand-contract ceremony
     and compat shims.
4. **Severity comes after verification** — never from how alarming the pattern sounds.
   "Critical" requires the demonstrated failure scenario.
5. **Don't report** what a linter/typechecker/compiler/CI already catches, pure style
   nits, or issues outside the diff's scope (note pre-existing ones separately, briefly).
6. For performance claims, never trust a single before/after (thermal/process drift);
   require an interleaved A/B or say the number is unverified.
7. Preserve load-bearing ordering and documented tradeoffs; call them out, don't "fix".
   Odd-looking sequencing is often deliberate — when in doubt, ask (§5 Open questions),
   don't assert.
8. For surprising claims about external packages (typosquat, wrong API, "this library
   doesn't do that"), check the live registry/docs — your knowledge may predate the
   package or release.

**Amplify confirmed findings:** when a defect is confirmed in one member of a family of
parallel implementations (sibling RPCs/handlers, per-entity files, per-platform ports),
sweep the siblings for the same shape — replicated code replicates defects.

On a **large scope** (multi-week branch, hundreds of files), scale the verification the
same way the finding worked: one independent verifier subagent per candidate (verdict:
confirmed/plausible/refuted, with a proving quote), then one final **gap-sweep** agent
that re-reads the diff asking only "what's missing from this list?" — sweeps reliably
surface a couple of real findings the primary pass missed. On refactors, have a verifier
trace old→new API contracts (signatures, return/exception behavior) against all call
sites.

**Delegate the correctness axes on large/high-risk diffs.** Dimensions A–C (and J)
overlap heavily with the built-in `/code-review`, which does correctness + simplification
faster and with its own verification. On a big or high-stakes change, run `/code-review`
(or `/code-review ultra` for a multi-agent cloud pass) for those axes and concentrate
this skill's own effort on the dimensions it *doesn't* cover — D (config/build),
E (docs freshness), F (dead wiring), G (test quality), H (type/immutability),
I (accessibility) — which is empirically where this skill adds findings a
correctness-only pass structurally cannot. On a small diff, just do all ten yourself.

## 5. Report

Report **every verified finding — no cap, no truncation** — as plain chat markdown
(not via a reporting tool, unless explicitly asked to post PR comments). If the list is
long, the severity grouping is the compression; don't drop verified findings for brevity.
Convention-sweep results appear as **one grouped finding per sweep** with a file:line
list — never dozens of separate findings.

Group findings by **severity**, most severe first. Each finding:

- `[dimension] file:line` — one-sentence problem.
- **Failure scenario:** concrete trigger → wrong result.
- **Fix:** the specific change (or "recommend" if not applying).
- **Confidence:** confirmed / plausible.

For the highest-stakes correctness findings, when practical, include a **runnable
failing test** instead of prose — it doubles as the verification.

Then three further sections:

- **Deferrable improvements:** real improvements that are out of scope for this diff
  (robustness upgrades, refactors). Offer them as ticket suggestions, not findings.
- **Open questions:** suspicious-but-unproven items framed as questions ("who frees
  this on failure?"), clearly separated from verified findings.
- **Considered and refuted:** candidates you killed and why, so the user sees the
  coverage, not just the hits.

End with what you checked but found clean, so scope is visible. Do not apply fixes
unless the user asked (or invoked with a fix intent); default is report-only.
