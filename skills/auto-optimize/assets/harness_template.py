#!/usr/bin/env python3
"""
Harness template for auto-optimize.

This is the FROZEN referee. Once the optimization loop starts, this file (and the
fixtures/reference it depends on) is not edited. It does three jobs the editable
core must never do for itself:

  1. Owns the fixed inputs / seeds  (so runs are comparable and the core can't
     special-case the eval inputs).
  2. Checks correctness independently (against a reference oracle / invariants).
  3. Computes the metric and prints ONE parseable summary block.

Adapt the marked sections to your problem. Keep the summary-block format identical
so the loop can grep it. This is Python for concreteness; the same structure works
in any language — the loop only depends on the ===METRICS===...===END=== block.
"""

import statistics
import time

# Import ONLY the editable core's public entry point. Everything that defines or
# measures success stays in this file (or other frozen files), never in the core.
from core import solve            # <-- the function/module the agent optimizes
from reference import solve_ref   # <-- frozen ground-truth oracle (often a copy
                                  #     of the original, unoptimized implementation)

# --- Fixed inputs: frozen, deterministic. The core does not get to see/choose these. ---
SEED = 1234
N_TRIALS = 7  # for timing-based metrics; median smooths out run-to-run noise


def make_inputs():
    """Build the fixed evaluation inputs. Deterministic given SEED."""
    import random
    rng = random.Random(SEED)
    # TODO: replace with inputs representative of real usage, including edge cases.
    return [[rng.randint(0, 10_000) for _ in range(1000)] for _ in range(50)]


# --- Correctness gate: independent of the core. A result counts only if this passes. ---
def check_correctness(inputs):
    """Return (passed: bool, detail: str). Diff the core against the reference oracle."""
    for x in inputs:
        if solve(list(x)) != solve_ref(list(x)):   # exact match; use a tolerance for floats
            return False, f"output mismatch on input of len {len(x)}"
    return True, "matches reference on all inputs"


# --- Metric: computed here, never by the core. ---
def measure(inputs):
    """Return the primary objective. Here: median wall-clock seconds (lower is better)."""
    solve(list(inputs[0]))  # warm up once (exclude import/JIT/cold-cache effects)
    times = []
    for _ in range(N_TRIALS):
        t0 = time.perf_counter()
        for x in inputs:
            solve(list(x))
        times.append(time.perf_counter() - t0)
    return statistics.median(times), (max(times) - min(times))


def main():
    inputs = make_inputs()
    passed, detail = check_correctness(inputs)
    objective, spread = (measure(inputs) if passed else (float("nan"), float("nan")))

    # One greppable block. The loop reads these lines; everything else is just logs.
    print("===METRICS===")
    print(f"objective: {objective:.6f}")          # primary number (here: seconds, lower better)
    print(f"correctness: {'PASS' if passed else 'FAIL'}")
    print(f"correctness_detail: {detail}")
    print(f"spread: {spread:.6f}")                 # noise margin: ignore 'wins' smaller than this
    print(f"n_trials: {N_TRIALS}")
    print("===END===")


if __name__ == "__main__":
    main()
