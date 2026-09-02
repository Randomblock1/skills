# Compose performance

Verified: 2026-08-23. Strong-skipping semantics verified against the Compose compiler docs and
`ComposeFeatureFlag` API.

The mechanisms that are easy to get confidently wrong. Read this when a screen visibly recomposes,
scroll janks, or someone is reaching for `@Stable`.

## Diagnose before repairing

Measure one user-visible transition and identify which runtime axis causes the work, then apply the
smallest correction at the phase or boundary where that axis begins. Then **check for a false lead**:
a screen that recomposes because its displayed model actually changed is behaving correctly.
Lowering a recomposition count that nobody perceives is not an improvement, and stability annotations
added for that reason are a promise you now have to keep for no benefit.

Generate compiler reports from **release** builds. Debug builds add Live Literals, which distort skip
behaviour and will send you after phantom problems.

## Strong skipping — what it actually does

Default since Kotlin 2.0.20. Two effects:

**Comparison semantics.** Unstable parameters are compared by instance (`===`); stable parameters by
`equals`. So a composable with unstable parameters can now skip — it just needs the same instance.

**Lambda memoization, with a specific scope.** Strong skipping wraps every **capturing** lambda
literal written inside a `@Composable` function in `remember(captures) { … }`. Capture-less lambdas
are already compiler-emitted singletons and are **not** wrapped — there is nothing to key on.

That scope restriction is the part that gets missed, and it produces the gaps below.

### Where auto-memoization does not apply

These are not `@Composable` scopes, so lambdas written inside them are not auto-remembered:

- `LazyListScope.items { }` and `LazyGridScope.items { }` — and everything else in a lazy scope
- `Modifier.pointerInput { }`
- `Modifier.draggable { }`
- `Modifier.scrollable { }`
- Plain object expressions

Inside these, a `remember(key)` is needed manually if the allocation matters. In a lazy list, hoist
per-item inputs with `remember(item.id) { … }` rather than annotating the model type — the item
lambda is the actual allocation site.

### Opting out

```kotlin
composeCompiler {
    featureFlags.add(ComposeFeatureFlag.StrongSkipping.disabled())
}
```

The legacy `enableStrongSkippingMode` property is `@Deprecated("Use the featureFlags option
instead")`. The deprecated form is still widely reproduced, so it is worth checking which one a
project uses — and worth not emitting.

## Stability, and the order of repair

When an annotation makes a false promise, **fix the data contract first**; only then decide whether
an annotation is still needed. Removing a `@Stable` from a type with an accidentally mutable
contract avoids an incorrect compiler promise, but it does not make the state safe or observable —
the underlying bug is that mutations are invisible to Compose.

Order:

1. Replace mutable non-snapshot properties with immutable data, or with snapshot-observable state.
2. Re-evaluate under strong-skipping comparison semantics — the problem may no longer exist.
3. Retain or add `@Stable` / `@Immutable` only if it is still truthful and still necessary.

Which annotation: `@Immutable` when every property is effectively immutable and `equals` describes
all observable state. `@Stable` for types whose mutable state is Compose-observable via
`MutableState`, so a change notifies composition.

For third-party immutable types, use a stability configuration file:

```kotlin
composeCompiler { stabilityConfigurationFiles.add(project.layout.projectDirectory.file("stability.conf")) }
```

Only list types you are willing to promise are immutable. Listing a mutable type — `java.util.Date`
is the classic — tells the compiler to skip on a value that can change underneath it, and the symptom
is stale UI that no amount of state debugging explains, because the recomposition never happens.

`List<T>` is unstable because the interface permits mutation. `kotlinx.collections.immutable`'s
`ImmutableList` is the honest fix; annotating a class that holds a `List` is not.

## Back-writing

Writing observable state in one phase that invalidates an earlier or the current phase. Compose runs
composition → layout → draw; a write that goes backwards schedules extra invalidation passes, often
cascading into sibling lazy items.

The recognisable case: row A captures its size via `onSizeChanged` and writes it to state; row B
reads that state in its composable body (`Modifier.height(state.dp)`). Layout has back-written into
composition, so every layout pass triggers a new composition pass.

The fix is to apply the constraint in the **measure** phase rather than reading measurement state in
a sibling's composable body — a custom layout, `SubcomposeLayout` where genuinely needed, or
`IntrinsicSize` where it fits.

More generally: prefer `remember(keys) { … }` for derived read-only snapshots, and reserve
`mutableState*` writes for event callbacks and effects — not for rebuilding derived data during
composition. `derivedStateOf` is for expensive derivations from snapshot state, not a default wrapper.

Note that hoisting lambdas with `remember` does **not** fix back-writing or cross-row measurement
bugs. They are different problems with different fixes, and conflating them is why "I added remember
everywhere and it did not help" is a common report.

## Deferred reads

Read state as late as possible. `Modifier.offset { }` (lambda form) reads during layout;
`Modifier.offset()` (value form) reads during composition. For a value that changes every frame —
scroll offset, animation progress — the lambda form keeps the invalidation in layout instead of
recomposing.

Same idea for `graphicsLayer { }` and for passing `() -> T` instead of `T` when the value changes far
more often than the structure around it.

## Recomposition scope

A composable is the invalidation unit. Reading a frequently-changing state at the top of a large
composable invalidates all of it; moving the read into a small child confines the work. This is why
extracting a child composable sometimes fixes performance with no other change — it created a
smaller invalidation scope.

Conversely, wrapping everything in tiny composables has its own cost. The goal is scopes that match
how often things actually change.

## Lazy lists

- Stable, unique `key = { it.id }`. Without it, insertions and removals recompose everything after
  the change point and animations attach to the wrong items.
- `contentType` for heterogeneous lists, so Compose reuses compatible slots.
- Do not nest a scrollable in the same direction as its parent.
- Avoid `fillMaxSize()` on items inside a lazy list — it fights the lazy measurement.
- Keep item content cheap. Decoding, formatting, and sorting belong above the list.

## Baseline profiles

A baseline profile is usually the largest startup and first-scroll win available, and it is
configuration rather than code. Generate with the Macrobenchmark library over the real critical user
journey. R8 in release plus a baseline profile is the standard pairing.

Startup measurement must come from a release build — debug is not indicative, and a debug measurement
is the most common reason a startup investigation goes nowhere.
