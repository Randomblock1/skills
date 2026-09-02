# Modularization and visibility

Verified: 2026-08-23.

## Visibility is the narrowest that compiles

Kotlin defaults to `public`, and in a multi-module project that default is usually wrong — a `public`
symbol joins the module's API surface, whether or not anyone outside the module ever calls it. Once it
is there, it constrains refactoring, appears in generated documentation, and gets depended on by
accident.

Start `private`. Widen to `internal` only when another file in the *same module* needs it. Widen to
`public` only when a *different module* actually consumes it.

**The correction that matters most:** "it is rendered by a composable in this module" does **not**
require `public`. `internal` is visible to the whole module, across every file in it. This is the
single most common over-widening in Compose codebases, because the mental model of "the UI needs it"
gets mistaken for "the outside needs it".

For a module that exposes a public API: the **interface is `public`, the implementation class is
`internal`**. The implementation is DI-bound and never named from another module, so making it public
exposes a type nobody should reference and invites someone to reference it.

Findings worth writing up:

| Pattern | Finding |
|---|---|
| `public` data classes and composables throughout a feature module | Feature modules typically need one or two public entry points. Everything else is `internal`. |
| A `public` implementation class alongside its interface | Make the implementation `internal`. |
| `internal` on a single-module project | Harmless but meaningless — `internal` equals `public` when there is one module. Not worth a finding on its own. |
| `@VisibleForTesting` widening production visibility | Prefer testing through the public surface, or move the test into the same module so `internal` suffices. |

## Module boundaries

Dependencies point **inward and downward**: app → feature → domain → data → core. No cycles, and no
sibling-to-sibling feature dependencies. A feature that needs another feature's screen needs a
navigation contract, not a direct dependency.

Common structural findings:

- **A `common` or `utils` module everything depends on.** It becomes a dependency magnet: every
  change to it rebuilds the world, and it accumulates unrelated code because it is the only place two
  modules can share anything. Split by concern.
- **Feature-to-feature dependency.** Usually solved with a navigation contract or an interface in a
  shared module, implemented in the owning feature.
- **A god module** — a `data` module holding every repository for every feature. Fine early, a build
  bottleneck later. Split when it becomes the reason builds are slow, not on principle.
- **`api` where `implementation` would do.** `api` leaks the transitive dependency into consumers'
  compile classpath and slows incremental builds. Use `implementation` unless the type genuinely
  appears in your own public signatures.

## When to modularize

Modularization buys build parallelism, enforced boundaries, and dynamic delivery. It costs
indirection, more Gradle configuration, and cross-module refactoring friction.

A single-module app with a clean package structure and an eye on `internal` is a perfectly good
answer for a small team. The signals that it is time: build times that hurt, more than a handful of
engineers colliding in the same files, or a genuine need for dynamic feature delivery.

Splitting into fifteen modules on day one, before the boundaries are known, produces modules that
mirror an early guess and then have to be re-cut. If someone asks whether to modularize and there is
no build-time pain and no team-size pressure, the honest answer is "not yet".

## Convention plugins

Once there is more than a handful of modules, per-module `build.gradle.kts` files drift. Convention
plugins in `build-logic` (or `buildSrc`) centralise the Android, Kotlin, and Compose configuration so
each module declares only what is distinctive about it.

The tell that they are needed: the same `compileSdk`, `jvmTarget`, and Compose block copy-pasted
across ten files, already inconsistent in two of them.
