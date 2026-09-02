# Harness patterns by problem type

The hard part of setting up auto-optimize on existing code is the same every time: decide what the **editable core** is, what the **frozen harness** measures, and how to keep runs **comparable and low-noise**. This file gives you a starting template for the four most common problem shapes. They're guides, not rules — most real tasks are a blend, and you should adapt.

For every type, the same three questions drive the setup:

- **Metric** — the single scalar you move, and the direction.
- **Correctness gate** — what must stay true for a result to count.
- **Editable vs. frozen** — what the agent may rewrite vs. what stays put.
- **Comparability / noise** — what to fix so two runs are judged fairly.

---

## Algorithms / functions (speed, memory, or quality of an exact computation)

The classic case: "make this function faster without changing what it returns."

- **Metric:** median wall-clock over fixed inputs, or — better when you can — a deterministic proxy like operation count, comparisons, allocations, or instructions. Deterministic proxies don't drift run-to-run, so prefer them; fall back to timing when the win is genuinely about constant factors or cache behavior.
- **Correctness gate:** the optimized function must produce identical (or within-tolerance) output to a **reference implementation** on the fixed inputs, plus any existing unit tests. Keep an untouched copy of the original as the reference oracle — diffing against it is the cleanest correctness check you can have.
- **Editable:** the function body / the module implementing the algorithm. **Frozen:** the reference oracle, the test suite, the input generator, the timer.
- **Comparability / noise:** fix the input set and its seed. Time multiple trials and take the median; report spread. Warm up once before timing to exclude import/JIT/cache-cold effects. Pin the input *size distribution* — a change that's faster on tiny inputs but slower on big ones isn't a win unless your fixed inputs reflect real usage.

---

## Search / queries / retrieval (latency and/or result quality)

E.g. "tune this SQL query / vector search / ranking function."

- **Metric:** often a pair — latency *and* quality. Pick one primary. If quality must not drop, make quality the **gate** (recall@k ≥ baseline) and optimize latency; or fix latency budget and maximize quality. Recall@k, nDCG, MRR, or exact-result-match are common quality scores.
- **Correctness gate:** results still satisfy the spec — same rows returned (for exact queries), or quality metric stays above a floor (for approximate/ranked retrieval) measured against a frozen ground-truth/relevance set.
- **Editable:** the query text, index choice, ranking function, retrieval parameters. **Frozen:** the dataset, the ground-truth relevance judgments, the query workload, the evaluator.
- **Comparability / noise:** fix the query workload and the dataset snapshot. For latency, control caches deliberately — decide warm vs. cold cache and measure consistently (a query that's only fast because of a warm cache from the previous run is measuring the cache, not the change). Run enough queries to average out per-query variance.

---

## ML / neural nets (loss, accuracy, or other model metrics)

The original `autoresearch` shape: optimize a model under a fixed training budget.

- **Metric:** validation loss / error / accuracy / F1 — a held-out score, never training-set score. `autoresearch` used `val_bpb` (bits per byte), chosen specifically because it's comparable across architectural changes (vocab-size-independent). Pick a metric that stays comparable when the agent changes model size, tokenization, etc.
- **Correctness gate:** runs without crashing, stays within the resource budget, and — crucially — **evaluates on a validation/test set the training code cannot see or fit to.** The split is the gate against overfitting.
- **Editable:** the model, optimizer, hyperparameters, training loop, data augmentation. **Frozen:** the data prep, the train/val/test split, the evaluation function, the budget (fixed steps or fixed wall-clock time).
- **Comparability / noise:** fix the budget (a fixed time budget makes any architecture comparable; a fixed step/epoch budget is more deterministic but less hardware-fair). Fix seeds where practical, but expect some run-to-run variance — keep only improvements clearly above that noise. Hold the val/test set constant and never let the agent touch it.

---

## Simulations / numerical methods (accuracy vs. reference, and/or runtime)

E.g. "make this physics/Monte-Carlo/solver run faster or more accurately."

- **Metric:** error against a trusted reference (analytic solution, high-resolution "truth" run, or experimental data), or runtime at fixed accuracy, or accuracy at fixed runtime. As with search, one of the pair is usually the gate.
- **Correctness gate:** the simulation stays physically/numerically valid — conserved quantities stay conserved, error vs. reference stays within tolerance, no NaNs/instability. These invariants are the gate; without them "faster" can just mean "wrong sooner."
- **Editable:** the solver, step size strategy, discretization, data structures, parallelization of the core compute. **Frozen:** the reference solution, the error metric, the scenario/initial conditions, the validation invariants.
- **Comparability / noise:** fix the scenario, initial conditions, and RNG seed (for stochastic sims, fix the seed *and* average over enough samples that the estimate is stable). Measure error and runtime on the same fixed scenario every time.

---

## General recipe (when it doesn't fit a box above)

1. **Find the number.** What does "better" mean, concretely, as a scalar with a direction? If the user can't name one, the task isn't ready for this skill — help them define it first.
2. **Find the oracle.** What independent source decides "still correct"? Existing tests, a reference implementation, invariants, golden outputs. If none exists, the most reliable move is to snapshot the current behavior on fixed inputs as the reference *before* you change anything — the original code is its own ground truth.
3. **Draw the boundary.** Smallest possible editable set; everything that defines or measures success is frozen and lives in separate files.
4. **Fix the conditions.** Same inputs, same seeds, same budget, every run. Decide noise handling explicitly.
5. **Make it greppable.** One parseable summary block per run (see `assets/harness_template.py`) so the loop reads a line, not a flood.
