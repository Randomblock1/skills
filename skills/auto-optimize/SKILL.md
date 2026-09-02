---
name: auto-optimize
description: >-
  Autonomously optimize a concrete, measurable target in an existing codebase —
  runtime, latency, accuracy, loss, recall, throughput, memory, cost, solution
  quality, any number you can move in a known direction. Carves the code into an
  editable computational core and a frozen measurement harness (metric + correctness
  tests + fixtures, never edited), sets a baseline, then runs a keep-or-revert
  experiment loop on a git branch: hypothesize, commit, measure, keep wins, revert
  regressions, log everything. Use whenever the user wants to make X faster, smaller,
  or more accurate, optimize or tune an algorithm, query, model, kernel, simulation,
  or pipeline, beat a baseline, minimize or maximize a metric, run an autoresearch-style
  or overnight self-improvement loop, or let an agent iterate on a measurable result on
  its own — even if they never say "optimize". The right tool any time success is
  defined by a number and there is existing code to improve.
---

# auto-optimize

## What this is

A method for turning an existing codebase into an autonomous optimization loop. Inspired by Karpathy's `autoresearch`, generalized so it works on any problem where success is a measurable number: a faster algorithm, a lower-loss model, a higher-recall search, a more accurate simulation, a cheaper query plan.

The whole method rests on one structural idea: **split the code into a part the agent may rewrite freely (the computational core) and a part that is frozen and trusted (the harness — the metric, the correctness checks, the test fixtures).** The agent optimizes the core; the harness is the impartial referee that says whether each change actually helped and didn't break anything. If the agent could edit the referee, the score would become meaningless — so keeping that boundary intact is the single most important thing in this whole skill.

The original `autoresearch` repo was already architected this way (a frozen `prepare.py` referee, an editable `train.py`). Real codebases almost never are. So the work here is in two stages: **first build and freeze the harness, then run the loop.** Don't skip to the loop. A loop with no trustworthy referee just produces confident-looking garbage.

## The mental model

```
   ┌─────────────────────────────────────────────┐
   │  FROZEN HARNESS  (the agent never edits this) │
   │   • fixed inputs / fixtures / seeds           │
   │   • correctness gate (must stay true)         │
   │   • metric computation (the score)            │
   │   • prints a parseable summary block          │
   └───────────────────────┬───────────────────────┘
                            │ runs & measures
                            ▼
   ┌─────────────────────────────────────────────┐
   │  EDITABLE CORE  (the agent rewrites freely)   │
   │   • the algorithm / model / query / sim       │
   │     whose number we are trying to move        │
   └─────────────────────────────────────────────┘

   LOOP:  hypothesize → edit core → commit → run harness →
          correctness pass? metric improved beyond noise?
          → keep (advance branch)  or  revert (git reset) → log → repeat
```

## Phase 1 — Scope the problem (do this with the user)

You cannot optimize what you can't measure, and you can't measure honestly without deciding what "still correct" means. Pin down all four of these before writing any code. Ask the user where it's genuinely ambiguous; propose sensible defaults rather than interrogating them.

1. **The objective metric.** One scalar, and a direction. "Lower median runtime", "higher recall@10", "lower val loss", "smaller peak memory". If the user names several, pick one *primary* objective and treat the rest as constraints (e.g. "minimize runtime *subject to* memory ≤ 2 GB and all tests passing"). A single number is what makes keep-or-revert decisions unambiguous.

2. **The correctness gate.** What must remain true for a result to count at all? This is the part `autoresearch` barely needed (its only gate was "doesn't crash") but most problems do. A 10× faster sort that returns wrong order is worth nothing. Find or write the checks that define "still correct": existing unit tests, a reference implementation to diff against, output invariants, a golden file. A metric improvement only counts if the correctness gate passes. If it fails, the change is discarded no matter how good the number looks.

3. **The editable surface vs. the frozen surface.** Name the specific files/functions that *are* the computational core (the agent may rewrite these) and everything else that is off-limits (the harness, the metric, the tests, the fixtures, the data prep). When in doubt, freeze it. The default posture is: a small, explicit editable set; everything else frozen. See `references/harness-patterns.md` for how this split typically falls for algorithms, search/queries, ML models, and simulations.

4. **Comparability controls.** Two runs are only comparable if the conditions are held fixed — same inputs, same seeds, same budget. `autoresearch` fixed a 5-minute wall-clock budget so every experiment was judged on equal footing; do the analogous thing for your problem. Fix the input set, fix random seeds, and decide how to handle measurement noise (for anything timing-based, run several trials and take the median — wall-clock is noisy and you don't want to "keep" a change that was really just a lucky run). Prefer stable metrics where you can: operation counts, token counts, and deterministic scores beat raw wall-clock.

Write the conclusions down in a short `OPTIMIZE.md` at the repo root (objective, direction, correctness gate, editable files, frozen files, how to run, noise handling). This is your contract with yourself for the rest of the run, and it's what lets the user — or a fresh agent — understand the setup later.

## Phase 2 — Build and freeze the harness

The harness is one entry point that runs the core on the fixed inputs, checks correctness, computes the metric, and prints a summary you can parse. Build it as a **separate file from the core** so the editable/frozen boundary is a file boundary, not a matter of willpower.

Requirements for the harness:

- **It computes the metric and the correctness gate itself** — never the core. The core must not be able to report its own score or decide its own correctness, the same way a student doesn't grade their own exam. If the only place that knows the right answer is inside the file you're editing, the score is gameable.
- **It's deterministic and comparable.** Fix seeds and inputs. For timing, run N trials (e.g. 5–11) and report the median plus spread.
- **It prints a parseable summary block.** End every run with a fenced, greppable block so the loop can read one line instead of scrolling output. Use the convention in `assets/harness_template.py`:

  ```
  ===METRICS===
  objective: 1.234567
  correctness: PASS
  <secondary>: <value>
  ===END===
  ```

- **It owns the inputs.** Put fixtures/seeds in frozen files the core can't read-and-special-case. If the core can see the exact test inputs, a lazy optimization is to memorize their answers — which is cheating, not optimizing. See `references/integrity.md`.

Then **freeze it.** Since this skill requires git:

1. Confirm the repo is a git repo (`git status`). If not, tell the user this skill needs version control and ask them to `git init` (or do it with their okay) — the loop relies on commits and `git reset` for keep-or-revert.
2. Create a fresh experiment branch: `git checkout -b auto-optimize/<tag>` (propose a tag from today's date, e.g. `auto-optimize/jun25`). The branch must not already exist.
3. Commit the harness, fixtures, tests, and `OPTIMIZE.md` on this branch as the starting point. Record in `OPTIMIZE.md` exactly which files are frozen. From here on, **only the editable-core files get touched.** If you ever feel the urge to edit a frozen file to make a run pass, that's a signal the change is wrong, not the harness.
4. **Smoke-test the harness on the unmodified core**: run it once, confirm it prints the summary block and that correctness PASSes. If the harness can't even score the original code, fix the harness now — before the loop, while editing it is still allowed.

## Phase 3 — Establish the baseline

Run the harness on the untouched core and record the result as the baseline experiment. Every future experiment is judged against the best-kept result so far, and the baseline is the first entry. Confirm correctness PASSes here — if the original code doesn't pass its own gate, stop and resolve that with the user, because nothing downstream is meaningful otherwise.

Initialize a `results.tsv` log (tab-separated; commas break in free-text descriptions). Keep it untracked by git (`echo results.tsv >> .gitignore` or just don't `git add` it) so it survives the resets in the loop:

```
commit	objective	correctness	status	description
a1b2c3d	1.234567	PASS	keep	baseline
```

Columns: short commit hash, objective value (use a sentinel like `0` or `NA` for crashes), correctness (PASS/FAIL), status (`keep` / `discard` / `crash`), and a short description of what the experiment tried.

## Phase 4 — The optimization loop

This is the autonomous part. Once setup is confirmed, run it without pausing.

```
LOOP:
  1. Note current git commit (the best-kept state).
  2. Form a hypothesis and edit ONLY the core to test it.
  3. git commit the change (one experiment = one commit).
  4. Run the harness, redirecting output:  <run cmd> > run.log 2>&1
     (redirect — don't let raw output flood your context or use tee).
  5. Parse the result:  grep -A20 "===METRICS===" run.log
  6. If no summary block, it crashed: `tail -n 50 run.log` for the traceback.
  7. Decide:
       • correctness FAIL or crash  → discard. `git reset --hard <prev commit>`.
       • correctness PASS and objective improved beyond the noise margin → KEEP.
         The branch advances; this commit is the new baseline.
       • correctness PASS, objective equal or worse → discard and reset,
         UNLESS the change is a genuine simplification (see below).
  8. Append a row to results.tsv.
  9. Go to 1.
```

**The keep-or-revert decision** is the engine. Keeping only real, correct improvements and reverting everything else is what makes the branch a monotonic climb toward a better number, and it's what lets you safely try bold ideas — a bad one just gets discarded. Be honest about the noise margin: if runtime varies ±5% run-to-run, a 2% "win" is noise; don't keep it.

**Simplicity is a tiebreaker, like in `autoresearch`.** All else equal, simpler is better. A change that *removes* code and holds the metric flat is a keep (it's a simplification win). A tiny metric gain that adds a big pile of hacky complexity is usually a discard — weigh the gain against the complexity cost. Clean wins compound; clever messes rot.

**Crashes:** if it's something dumb (typo, missing import in your own edit), fix and rerun. If the idea is fundamentally broken, log `crash`, revert, and move on. Don't sink more than a few attempts into one stubborn idea.

**Budget/timeouts:** if a run is supposed to take ~T and it's running far past that (e.g. 2× the expected budget), kill it and treat it as a failed experiment — a change that blows the time/resource budget isn't a valid result.

**Autonomy — don't stop to ask.** Once the loop has begun, keep going until the user interrupts you. Don't pause to ask "should I continue?" or "is this a good place to stop?" — the user may have started this expecting to come back to a log of completed experiments (the classic case: they're asleep, or away for hours). If you run out of obvious ideas, think harder instead of stopping: re-read the core for new angles, revisit papers or docs referenced in the code, combine previous near-misses, try a more radical rewrite, attack a different bottleneck. The loop ends when the human ends it.

When the user does come back (or asks for a summary), give them the best result, the delta from baseline, and the most informative kept/discarded experiments from `results.tsv`.

## Integrity — the one thing not to get wrong

Every instruction above is in service of one property: **the number has to mean something.** The fastest way to a great-looking score is to cheat — special-case the test inputs, weaken the correctness check, let the core compute its own metric, edit a "frozen" file just this once. None of that produces a real improvement, and all of it is easy to do by accident when you're heads-down chasing a number. The file boundary and the frozen harness exist precisely so that you can chase the number hard without fooling yourself. Before keeping any surprising win, sanity-check that it's real (see `references/integrity.md` for the common failure modes and quick checks). A modest honest gain beats a huge fake one every time.

## Reference files

- `references/harness-patterns.md` — how the editable/frozen split, the metric, and noise control typically look for **algorithms, search/queries, ML models, and simulations**. Read the section matching the user's problem when scoping Phase 1 and building Phase 2.
- `references/integrity.md` — concrete ways an optimization loop fools itself (Goodharting, test memorization, metric leakage, silent correctness erosion) and fast checks to catch them. Read it before trusting a surprising result.
- `assets/harness_template.py` — a minimal, language-agnostic-in-spirit harness skeleton (load fixed inputs → run core → check correctness → measure → print summary block). Adapt it; don't treat it as fixed.
