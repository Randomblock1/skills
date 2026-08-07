---
name: trim-comments
description: Audit and trim the comments and docs in a codebase or directory so every comment earns its place — remove narration and history, keep and sharpen the "why", fix stale claims, and dedupe documentation. Use this whenever the user asks to review, trim, prune, clean up, shorten, or audit comments or docstrings, says comments are noisy/redundant/outdated, wants code made more readable, or asks for a docs-freshness pass over READMEs. Also use it when a code review should explicitly cover comments, not just code.
---

# Trim Comments

Make a codebase's comments and docs earn their place. The goal is **readable
code, not a deletion count**: a valid-but-bloated comment is a defect, a
missing why-comment is a defect, and a wrong comment is a bug. Most good edits
*shorten* or *fix* comments rather than delete them, and adding a comment or a
doc row is in-scope whenever it serves the reader.

Judge every comment by one question: **does it tell the next reader something
the code cannot?** Hardware quirks, protocol constraints, race explanations,
timing budgets, "why not the obvious way" — these are the point of comments.
Restating the code, narrating the edit history, or citing the ticket that
requested a shipped feature are not.

## Process

Run four phases in order. Don't skip the survey — trimming file-by-file
without a map produces inconsistent judgments across the codebase — and don't
start editing before the phase-2 checkpoint has had its reply.

### 1. Survey

Build a taxonomy of what's actually there before judging anything. For scopes
bigger than a handful of files, fan out subagents (comments in one, docs
inventory in another) and have them return categorized examples with
`file:line` references:

- narration (restates the code) · why-comments (keep) · banners/dividers ·
  TODO/FIXME · docstring quality · commented-out code · history framing
  ("previously", "now", "used to") · ticket/issue references · suppressions
  (`noqa`, `pragma`, `eslint-disable`)
- for docs: length, duplication between files, and claims worth spot-checking
  against the code (paths, commands, feature lists)

Also establish the **history baseline**: `git merge-base` with the default
branch. What "history" means depends on it (see the history rule below).

Expect the survey to change your plan. Many codebases don't have a
narration problem at all — the real work turns out to be stale docs, ticket
provenance, or duplicated tables. Trim what's actually wrong, not what the
category list predicts.

### 2. Present the plan and ask — before touching anything

After the survey, **stop and send one message, then wait for the reply**: the
survey's headline findings, the edits you intend per category, and your open
questions batched into a single round — each with a recommendation, so the
user can answer "defaults, except…" in one line.

This checkpoint is not optional ceremony. Comment judgments are taste-laden,
and the survey nearly always surfaces calls only the user can make: scope
boundaries (generated code, vendored dirs, sibling subprojects), conventions
that look deliberate (test section banners, divider styles), whether a
dead-looking block is intentionally parked, doc restructures that move
content between files. If you finish the survey with *no* questions, treat
that as a sign the survey was too shallow — go back and look at the borderline
cases again rather than proceeding.

The only reasons to skip the pause: the user explicitly asked for a one-shot
run ("just trim it, don't ask me"), or the scope is a file or two with purely
mechanical fixes. Everything else waits for the reply.

### 3. Edit

Once the user has replied, apply the category rules below with their answers
folded in. Match the surrounding style; when you shorten a comment, keep its
load-bearing facts and drop the rest.

### 4. Verify and report

Comment edits still break things: renamed tests, doctests, `# noqa` lines
that moved, coverage pragmas, docs whose anchors you changed. Run the test
suite and the formatter/linter the project uses. Report by category with
counts and net line delta, and report failures honestly — including
pre-existing ones you noticed but didn't cause.

## Category rules

**Remove**
- Comments that restate adjacent code ("increment the counter").
- Docstrings that only echo the symbol or file name (`"""Monitor tests."""`),
  and `Args:` entries that repeat a param's name/type without adding meaning —
  keep the summary line and any non-obvious argument.
- A pre-function comment duplicated by the docstring right below it.
- Commented-out code — **except** blocks that a live `TODO(<ticket>)` names as
  a restore target (intentionally parked paths, ideally with a paired disabled
  test), and commented lines in config *templates*, which are documentation.

**Keep**
- Genuine why-comments, even terse ones next to non-obvious logic.
- TODO/FIXME/HACK markers **with** their ticket numbers — never strip a ticket
  off an actionable marker.
- Annotated suppressions (`# noqa: BLE001 — reason`) and functional markers
  (a Makefile's `##@ Section` lines that drive `help`, shebangs, encoding
  pragmas).

**Fix — these are bugs, not style, so age and scope rules don't shield them**
- Comments referencing deleted files/symbols, wrong mechanisms, mis-numbered
  steps, or rationale copy-pasted onto code it doesn't describe. When a
  comment explains one specific line, move it next to that line.
- Docs describing removed features or commands that no longer work. Verify
  a sample of doc claims against the code before trusting the rest.

**Rewrite: history → present tense.** Comments describe current behavior, not
the change that produced it — no "now", "previously", "used to", "formerly".
For regression tests, split by the baseline you established in the survey:
history relative to the **default branch or a deployed release** may stay
(reworded toward a present-tense contract where possible); history that is
**internal to an unmerged branch** (introduced and fixed in the same branch)
is not a real regression — remove the framing and rename the test to state
the invariant it enforces.

**Ticket references outside TODO markers.** A shipped feature's comment should
not cite the ticket that requested it — that's provenance, and it lives in git
history and the PR. Strip the ref, keep the explanation. Two exceptions:
- A **still-open bug** the code works around may be cited, but collapse to
  **one anchor comment** stating the root cause and pointing at the
  mitigation; other affected sites keep prose only. If the fix is hardware or
  otherwise external, don't frame it as a code TODO — say the fix is in
  progress elsewhere. When an issue tracker is reachable, read the ticket
  before rewording; the code's framing of a ticket is often stale.
- A ticket carrying context that is genuinely non-obvious and exists nowhere
  else (a decision rationale recorded only there).

**Banners and dividers.** Section dividers in long files are navigation —
keep them, but slim multi-line banner boxes to a single line in the file's
existing divider style. Don't delete them wholesale (they're the in-file table
of contents) and don't add new ones.

**Docs**
- **One owner per fact.** When two docs maintain the same table or setup
  steps, pick the natural home, fold in whatever only the copy had, and make
  the other doc link to it. Near-identical code samples in one doc merge into
  one example with notes on the variants.
- Deferred/backlog feature lists belong in the issue tracker and in TODOs at
  the affected code — not in architecture docs, where they rot silently. A
  one-line "currently disabled, see <file>" note where readers would
  otherwise be confused is fine.
- Status/changelog sentences ("X and Y are implemented and enabled") describe
  the past — delete them.
- **Adding is part of the job**: a doc that claims completeness ("every key is
  documented below") must be made true; undocumented dirs, commands, or CLI
  entry points that the survey surfaced get at least a one-liner.

## Report format

End with a short summary grouped by category (fixed / removed / rewritten /
added / docs), with counts, the net line delta, and verification results. If
the user wants commits, split them by concern — comment fixes, ticket-ref
cleanup, banner slimming, and docs restructuring are separate commits, ordered
so links never point at files that don't exist yet.
