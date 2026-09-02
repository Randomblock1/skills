# Audit procedure

Verified: 2026-08-23.

How to review a whole codebase rather than a single file, and produce a report someone will act on.

## Scope gate — fail fast

Before mapping modules or reading source, confirm the target is what you think it is:

```bash
rg -l 'androidx\.compose' --glob 'build.gradle*' --glob '*.toml'
rg -l '@Composable|setContent \{' --glob '*.kt' | head -30
fd -e kts -e gradle --glob 'build.gradle*' | head -40
cat gradle/libs.versions.toml 2>/dev/null | head -60
```

If Compose appears only under `samples/`, `demos/`, or `benchmark/`, narrow the scope and say so.
Scoring demo code as production is the fastest way to produce a report the team dismisses entirely —
and rightly, because it shows you did not look.

Then read, in order: the version catalog, the app module's build file, one representative feature
module's build file, and the module dependency graph. These four establish what guidance even applies.

## Read before judging

**Do not score from search hits.** A grep for `Color(0x` finds a hit in a `Preview` function, in a
generated theme file, and in a genuine violation, and only one of those is a finding. Open the file.

For each category you intend to report on, read at least two or three representative files. If you
cannot, mark the category's confidence as low rather than guessing — a report that says "I did not
get far enough into the data layer to judge it" is more useful than a confident wrong score.

## Cite the mechanism

**Every finding needs a mechanism or an official source, not an assertion.** "Prefer `internal`" is
an opinion; "Kotlin defaults to `public`, so this joins the module's API surface and constrains
refactoring" is a reason. Where a documented rule exists — Room 3 requiring KSP, R8 strict keep rules
dropping constructors — cite it, because the reader's next move is to verify.

No trust-me findings. They are the ones that get argued about instead of fixed, and they undermine
the findings that are solid.

## Do not apply library standards to app code

A public library needs stable APIs, exhaustive KDoc, binary compatibility, and explicit API mode. An
app screen does not. Applying library-grade API-quality checks to app code produces a long list of
findings nobody will act on, and it buries the real ones.

Apply API-quality checks mainly to: reusable internal components, design-system pieces, shared UI
building blocks, and anything published as a module API. For leaf app code, the bar is correctness and
readability.

## Severity, not scores

Numeric scores invite argument about the number rather than the finding, and a "7/10 for typography"
tells nobody what to do on Monday. Use consequence-ordered severity:

- **Critical** — crashes, data loss, security. Release-only R8 failures live here. So does a leaked
  `Context` in something long-lived.
- **Correctness** — wrong behaviour under a real condition: rotation, process death, cancellation,
  slow network, no network.
- **Performance** — measured, user-visible. Unmeasured performance findings are speculation; label
  them as such or leave them out.
- **Structure** — boundaries, visibility, duplication. Real but rarely urgent.
- **Style** — naming, formatting, ordering. Usually a linter's job, not a review's.

## Report shape

```
# Android architecture review — <target>

## Scope
What I read, what I did not, versions in play, confidence.

## Critical
### <finding> — <file>:<line>
Current: <quoted code>
Problem: <the mechanism, and the condition that triggers it>
Fix: <concrete change>

## Correctness
## Performance
## Structure

## What is already right
<brief, and only where load-bearing>

## Open questions
<decisions that are the team's to make, not yours>
```

The scope section is what makes the report trustworthy. A reviewer who states what they did not read
is believable about what they did.

## When there is nothing to report

Say so. "I read the four ViewModels in `feature/checkout`, the repository layer, and the version
catalog. State ownership is correct, effects use a buffered channel collected with `repeatOnLifecycle`,
and the error boundary sits at the repository. I found nothing worth changing" is a complete and
valuable answer.

Manufacturing findings to fill a report is the characteristic failure of automated review. It trains
the reader to skim, which means the one real finding in the next report gets skimmed too. An empty
critical section is a good outcome, not an incomplete one.

## Useful sweeps

Starting points only — every hit needs the file opened.

```bash
# state ownership
rg -n 'val \w+ = MutableStateFlow|var \w+ by mutableStateOf' --glob '*.kt'
rg -n 'GlobalScope|\.value\s*=' --glob '*.kt'
# effects
rg -n 'LaunchedEffect\(Unit\)|MutableSharedFlow|collectAsState\(\)' --glob '*.kt'
# error boundaries
rg -n 'catch \(e: Exception\)|runCatching|catch \(e: IOException\)' --glob '*.kt'
# leaks
rg -n 'class \w*ViewModel.*(Context|Activity|NavController|View)' --glob '*.kt'
# visibility
rg -n '^(public )?(data )?class |^(public )?fun ' --glob '*.kt' | rg -v 'internal|private' | head -40
# build and release risk
rg -n 'kapt|kotlin-kapt' --glob 'build.gradle*'
rg -n '^-keep class [^{]*$' --glob '*.pro' --glob 'proguard*'
rg -n 'fallbackToDestructiveMigration|allowMainThreadQueries' --glob '*.kt'
rg -n 'kotlinCompilerExtensionVersion|enableStrongSkippingMode' --glob 'build.gradle*'
```

## Declare what you capped

If the review bounded its own coverage — top N findings, one module of six, no test files read — say
so explicitly. Silent truncation reads as "I covered everything", and that is the one claim a review
must never make falsely.
