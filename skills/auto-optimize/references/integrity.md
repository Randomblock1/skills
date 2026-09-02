# Integrity: keeping the number honest

An optimization loop is a machine for finding whatever maximizes a score. If the score can be moved *without* actually solving the problem, the loop will eventually find that shortcut — not out of malice, but because it's the path of least resistance, and you're explicitly rewarding lower/higher numbers. This is Goodhart's law: when a measure becomes the target, it stops being a good measure. The whole editable-core / frozen-harness design exists to make the shortcuts impossible or obvious. This file lists the shortcuts so you can recognize them.

The mindset that keeps you safe: **you are trying to genuinely improve the thing, and the metric is just your instrument for telling whether you did.** If a change moves the metric but you can't explain *why the underlying thing got better*, be suspicious before you keep it.

## The common ways a loop fools itself

**Editing the referee.** Quietly changing the metric computation, loosening a tolerance, deleting a failing assertion, or "fixing" a test to match new output. This is why the harness is frozen and lives in separate files, and why you commit it before the loop starts. Rule of thumb: if making a run pass requires touching a frozen file, the change is wrong — not the harness. The only legitimate reason to edit the harness is if you discover during the smoke test that it was measuring the wrong thing — and that's a Phase 2 fix, made with the user, before any optimization, not a mid-loop convenience.

**Memorizing the test inputs.** If the core can see the exact evaluation inputs, the cheapest "optimization" is to detect them and return precomputed answers — a lookup table that scores perfectly and generalizes to nothing. Defenses: keep fixtures in frozen files the core doesn't import; where feasible, evaluate on inputs the core never has direct access to; and for ML-shaped problems, keep a strict train/val/test split so the optimized thing is scored on data it couldn't fit to.

**Metric leakage / self-grading.** The core computing or influencing its own score. The harness must compute the metric and the correctness verdict independently — the student doesn't grade their own exam. If the only code that knows the right answer is the code you're editing, you have no referee.

**Silent correctness erosion.** Trading correctness for metric gains in ways the gate doesn't catch: returning approximate results where exact were required, handling the common case and silently dropping edge cases, reducing precision, skipping work that "usually" doesn't matter. Defense: make the correctness gate strict and diff against a reference oracle on inputs that include the edge cases, not just the easy path. If a speedup is suspiciously large, the first hypothesis should be "what did it stop doing?"

**Measuring the harness instead of the change.** Wins that are artifacts of the measurement, not the code: a warm cache left by the previous run, a lucky fast sample, timing that includes startup one run and not the next, or overfitting to one input size. Defenses: warm up before timing, run multiple trials and take the median, fix the input distribution, and reset relevant caches between trials.

**Budget evasion.** "Improving" the metric by quietly blowing a resource you weren't watching — using 10× the memory, spawning threads, exceeding the time budget, writing scratch files. Track the constraints as secondary metrics in the summary block and gate on them, the way `autoresearch` treated VRAM as a soft constraint that shouldn't blow up.

## Fast checks before keeping a surprising win

A "surprising win" is any result that's much better than you'd expect from the change you made. Before you keep it and advance the branch, spend two minutes:

- **Diff the behavior, not just the metric.** Confirm the core's outputs still match the reference oracle on the fixed inputs — and ideally on a couple of fresh inputs the change couldn't have anticipated.
- **Explain the mechanism.** State, in one sentence, *why* this change improves the number. "It removes a redundant O(n) pass" is an explanation. "Not sure, but the number went down" is a red flag.
- **Check the constraints.** Did memory, time, or any gated secondary metric quietly move the wrong way?
- **Re-run once.** If the metric is noisy, confirm the win reproduces and wasn't a lucky sample.

None of this slows down honest progress — real improvements pass these checks trivially. It only catches the fakes. A small, explainable, reproducible gain is worth more than a large, mysterious one, because the small honest gains compound into a result you can actually trust and ship.
