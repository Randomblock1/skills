---
name: android-architecture-review
description: >
  Review and decide Android architecture in Kotlin — state ownership, effects, error propagation,
  Compose performance, module boundaries and visibility, and the 2026 toolchain (AGP 9, KSP vs KAPT,
  Room 3, R8 strict keep rules, version catalogs). Use this whenever Android or Kotlin work involves
  auditing an existing codebase, reviewing a change before merge, or choosing between architectural
  options: "review my ViewModel", "is this the right place for this logic", "why does this screen
  recompose", "my effect fires twice after rotation", "should this be internal or public", "our
  Gradle build broke after upgrading", "we're hitting release-only crashes", "how should this module
  depend on that one". Reach for it even when the request does not name architecture — a symptom
  description usually is one. Not for Material Design, theming, or component styling — that is the
  m3-expressive-compose skill.
---

# Android architecture review

Verified: 2026-08-23. Per-file `Verified:` dates below; treat version-specific claims older than a
Compose BOM or AGP major as suspect and confirm against release notes.

This skill is deliberately narrow. It does **not** restate the Android architecture guide, UDF, state
hoisting, `collectAsStateWithLifecycle`, or "use Room not SharedPreferences" — that material is
already well represented in any capable model, and Google's own skills repo explicitly declines to
cover "well-established areas where LLMs are already proficient, such as basic Jetpack Compose best
practices." What is here is the residue: mechanisms that are easy to get subtly wrong, decision
procedures for review, and 2026 toolchain facts that postdate or contradict common knowledge.

## Core principle

Three invariants generate most of the correct answers, so reason from these when the router below
does not have an entry:

1. **State has one lowest responsible owner.** Every piece of state belongs at the lowest scope that
   can still serve every reader. Pushing it higher creates false coupling; pushing it lower
   duplicates it.
2. **Errors are mapped at a boundary, not caught where convenient.** Platform exceptions belong to
   the data source; the repository is where they become domain errors; the UI layer sees explicit
   state.
3. **Visibility is the narrowest that compiles.** Kotlin defaults to `public`, and in a multi-module
   project that default is usually wrong.

## Procedure

1. **Read the project's own conventions first.** Open a sibling ViewModel, a sibling repository, and
   the version catalog before forming any opinion. What the codebase already does is the baseline.
2. **Confirm scope, and fail fast if it is wrong.** Before mapping modules, check that the thing you
   were pointed at is production code. If Compose appears only under `samples/` or `demos/`, narrow
   the scope and say so rather than scoring demo code.
3. **Gather evidence before diagnosing.** For a performance question that means one measured
   user-visible transition, not a scan for suspicious code. For a correctness question it means
   reading the call sites, not just the declaration.
4. **Check for a false lead.** The most common failure of this kind of review is a finding that is
   technically true and practically irrelevant. Ask explicitly whether the current code is already
   correct for its context before writing it up.
5. **Apply the smallest correction at the boundary where the problem starts.** A recomposition
   problem caused by a mutable data contract is fixed at the contract, not by adding `@Stable` at the
   consumer.
6. **Order findings by consequence** — crashes and data loss, then correctness, then performance,
   then structure, then style.
7. **Stop.** When no evidence-backed issue remains, say so. See § Finish gates.

## Existing code wins

Before introducing any new mechanism, look for the one the project already has. The easy miss is
*duplicating* an existing mechanism instead of widening it — a second `Result` wrapper, a second
dispatcher provider, a second error type for the same failures.

If existing code contradicts a documented best practice, follow the code and **flag the
inconsistency** as a separate finding. Never silently override a project's architecture in the course
of doing something else. A review that leaves the codebase internally inconsistent has made it worse
even if every individual change was defensible.

The official architecture guidance is also not Clean Architecture, and Google says so directly:
"concepts from other architectures may not apply here." Watch for findings that are really imported
dogma — a mandatory domain layer, a repository interface in the domain module, entity-to-model
mapping at every hop — and label them as preferences rather than defects.

## Symptom router

Keyed on what you can observe, not on topic names.

| Symptom in the code or the report | Read |
|---|---|
| ViewModel exposes `MutableStateFlow` publicly, or many unrelated flows | `references/state-and-effects.md` |
| An effect fires twice, or is lost after rotation or process death | `references/state-and-effects.md` |
| Navigation, snackbar, or toast triggered from state | `references/state-and-effects.md` |
| A UI state class with a dozen constructor params, or `copy()` producing invalid combinations | `references/state-and-effects.md` |
| A composable takes 6+ lambdas, or lambdas thread through several layers | `references/state-and-effects.md` |
| `try/catch` in a use case or ViewModel; `IOException` reaching the UI | `references/data-layer-and-errors.md` |
| Two error types for the same failure; `Result<Result<T>>` | `references/data-layer-and-errors.md` |
| Room, DAOs, `@TypeConverter`, migrations, KAPT on Room | `references/data-layer-and-errors.md` + `references/toolchain-2026.md` |
| A screen recomposes visibly, or scroll janks | `references/compose-performance.md` |
| `@Stable` / `@Immutable` annotations, stability config files | `references/compose-performance.md` |
| `onSizeChanged` / `onGloballyPositioned` writing state read during composition | `references/compose-performance.md` |
| Lambdas inside `items {}`, `pointerInput {}`, `draggable {}` | `references/compose-performance.md` |
| `public` declarations in a feature module; module cycles; a `common` module everything depends on | `references/modularization-and-visibility.md` |
| Build broke after an AGP or Kotlin upgrade; KAPT; version catalog questions | `references/toolchain-2026.md` |
| A crash only in release builds; ProGuard or R8 keep rules; obfuscation | `references/toolchain-2026.md` |
| "Audit our codebase", "review this repo", producing a report | `references/audit-procedure.md` |

## House defaults

These are **preferences, not correctness**. State them as such, and defer to whatever the project
already uses. Their only purpose is to answer "what should we pick" when a project has no precedent
and the user wants a recommendation rather than a survey.

DI: Hilt with KSP. Async: coroutines and Flow. Persistence: Room 3. Networking: Retrofit with
kotlinx.serialization, or Ktor for multiplatform. Images: Coil. Paging: Paging 3. Background:
WorkManager. Build: Kotlin DSL with a version catalog and convention plugins. Testing: JUnit 5,
Turbine for flows, Robolectric or Compose UI tests for the UI layer.

Before recommending any dependency or version, verify it exists: the exact Maven coordinates, that
the target actually supports it (never assume a Jetpack library works in `commonMain`), and that the
API shape you are about to use exists in that version. If you cannot verify, emit the snippet with a
`// verify latest version` comment rather than inventing a coordinate — a hallucinated dependency
costs more than an unresolved one.

## Finish gates

Stop and report when:

- Every finding has file:line evidence and a named mechanism, and the remaining candidates are style
  preferences.
- For a review-only request, no evidence-backed issue remains. **Report that no change is needed.**
  Do not invent product requirements, and do not manufacture a refactor to justify the review.
- The next step requires a decision only the user can make — a dependency addition, a breaking API
  change, a product behaviour choice. Present the options and stop.

## Worked scenarios

**Finding worth making.** A ViewModel exposes `val uiState = MutableStateFlow(UiState())` as `public`
and the composable calls `viewModel.uiState.value = …` on a click. Two defects: the UI mutates state
it does not own, so the invariants in the ViewModel can be bypassed; and there is no single place to
audit transitions. Expose `StateFlow` via `asStateFlow()`, and add an intent function per event.

**Finding worth making.** A `LaunchedEffect(Unit)` inside a composable calls
`analytics.logScreenView()`. It refires on every configuration change, so the screen appears twice in
analytics for every rotation. The effect needs to be keyed on something stable, or moved to the
ViewModel's `init`, or gated by a flag in saved state — which one depends on whether "once per screen
entry" or "once per session" is intended, and that is a product question worth asking.

**Counterexample — no change needed.** A composable holds `var expanded by remember { mutableStateOf(false) }`
for a local disclosure arrow. It does not need hoisting to the ViewModel, a state holder class, or
saved-state persistence. Nobody else reads it and nothing breaks if it resets. Report no change.

**Counterexample — no change needed.** A `suspend fun` in a repository does not take a
`CoroutineScope` and does not launch anything. That is correct: a suspend function inherits the
caller's scope, and adding an internal scope to make it "properly asynchronous" would break
cancellation. Report no change.

**Counterexample — measured, then dismissed.** A profile screen recomposes four times on open. The
cause is that the displayed model genuinely changed four times as data arrived from cache then
network. Adding stability annotations or a `derivedStateOf` would lower the count without improving
anything the user sees. The finding, if any, is about the data layer emitting intermediate states —
not about Compose.

**A finding that is really a version finding.** A module applies
`org.jetbrains.kotlin.kapt` for an annotation processor. On AGP 9 this is incompatible with built-in
Kotlin and will fail the build. The fix is not "migrate everything to KSP today" — it is
`com.android.legacy-kapt` on that one module as a bridge, plus a note on which processor still lacks
KSP support. See `references/toolchain-2026.md`.
