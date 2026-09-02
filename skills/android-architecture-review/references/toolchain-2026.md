# Toolchain, 2026

Verified: 2026-08-23. This is the highest-drift file here — every version-specific claim should be
re-checked against release notes if a new AGP, Kotlin, or Compose BOM major has shipped since.

Facts that postdate or contradict widely-reproduced knowledge. This is where a review adds the most,
because the failure modes are build-breaking or release-only and the wrong answer is confidently
available everywhere.

**Read the project's versions before applying anything here.** Open `gradle/libs.versions.toml` and
the module `build.gradle.kts` files first. Guidance keyed to AGP 9 is noise on an AGP 8 project.

## AGP 9 and built-in Kotlin

AGP 9 brings built-in Kotlin support, and that breaks KAPT.

**`org.jetbrains.kotlin.kapt` is incompatible with built-in Kotlin and must be removed.** For a
processor that has no KSP implementation, apply **`com.android.legacy-kapt`** to that single module,
versioned with the same version as AGP.

Three qualifications that matter:

- **Never project-wide.** It is a per-module escape hatch, not a migration deferral for the whole
  build.
- **Never for Room.** Room 3 is KSP-only; there is no Java codegen path to fall back to.
- **Do not set `android.disallowKotlinSourceSets=false`** to work around it. That suppresses the
  symptom and leaves a build that will break harder later.

Version gates Google states for AGP 9: **KSP ≥ 2.3.6**, **Hilt ≥ 2.59.2**. After migrating, remove
the now-obsolete flags: `android.builtInKotlin`, `android.newDsl`, `android.uniquePackageNames`,
`android.enableAppCompileTimeRClass`.

## R8 strict full-mode keep rules

The highest-value finding in this file, because it produces **release-only crashes** and the class
appears in `seeds.txt`, so the obvious diagnostic says everything is fine.

AGP 9 enables `strictFullModeForKeepRules`. Under it, **`-keep class A` no longer keeps A's
constructor.** A rule that used to keep a reflectively-instantiated class now keeps the class and
lets its constructor be removed, so reflection fails at runtime in release and works in debug.

Where this bites: anything reflectively instantiated — serialization models, `Parcelable` creators,
Room entities in some configurations, and anything constructed by name.

The fix is to name the members:

```proguard
-keep class com.example.Model { <init>(...); }
```

Audit any `-keep class` rule without a member specification. In a review, "you have keep rules that
predate strict full mode" is worth stating even without a reproduction, because the failure is
invisible until release.

## Room 3

Artifacts moved to **`androidx.room3:room3-*`**. Room 3.0.1 stable, July 2026. Four breaking facts:

- `@TypeConverter` → **`@ColumnTypeConverter`** (renamed in 3.0.0-rc01)
- **`@DaoReturnTypeConverter(s)`** replaces the built-in Paging, RxJava, Guava, and LiveData
  integrations
- **KSP only** — no Java codegen, so KAPT is not possible at all
- **A `SQLiteDriver` is now required** to build a `RoomDatabase`

Models reliably emit the pre-3.0 forms, so these are worth checking whenever Room appears.

## KSP over KAPT

KSP is faster (it reads Kotlin symbols rather than generating Java stubs) and is the only supported
path for Room 3 and current Hilt. A project still on KAPT for a processor that has a KSP
implementation is carrying build time for nothing. Migration is usually a plugin swap plus
`ksp(...)` in place of `kapt(...)`.

The genuine blocker is a processor with no KSP support. That is what `com.android.legacy-kapt`
exists for, per module.

## Version catalogs

`gradle/libs.versions.toml` as the single source of truth. Bundles for groups that move together
(Compose, Room, testing). Plugin aliases too, not just libraries.

Findings: versions hardcoded in module build files alongside a catalog that also declares them —
two sources that will diverge. And a catalog with the same library declared twice under different
aliases, which is how two versions of one library end up on the classpath.

Never invent a coordinate or a version. Verify that the artifact and version exist and that the API
shape you are about to use is in that version; if you cannot, emit `// verify latest version` rather
than a plausible guess. A hallucinated dependency costs more debugging time than an unresolved one.

## Gradle hygiene

- Kotlin DSL, not Groovy, for new work — type safety and IDE completion in build files are worth the
  migration.
- Configuration cache and build cache on. A build that cannot use the configuration cache usually has
  a specific fixable cause worth finding.
- `implementation` over `api` by default (see `modularization-and-visibility.md`).
- Convention plugins once module count grows past a handful.
- Do not read the environment or run commands at configuration time — it defeats the configuration
  cache.

## Compose compiler

The Compose compiler moved into the Kotlin repository and versions with Kotlin, so the standalone
`composeOptions { kotlinCompilerExtensionVersion }` block is obsolete on current setups. Configure via
the `composeCompiler { }` block — that is where `featureFlags`, `stabilityConfigurationFiles`,
`reportsDestination`, and `metricsDestination` live.

## Deprecated patterns still widely reproduced

Worth flagging when they appear, because they signal a codebase or a habit that has not been revisited:

| Pattern | Current |
|---|---|
| KAPT for Room or Hilt | KSP |
| Groovy `build.gradle` for new modules | Kotlin DSL |
| `composeOptions { kotlinCompilerExtensionVersion }` | `composeCompiler { }` |
| `enableStrongSkippingMode` | `featureFlags.add(ComposeFeatureFlag.StrongSkipping.disabled())` |
| `Navigation 2` for new work | Navigation 3 |
| `AsyncTask`, `Loader`, `startActivityForResult` | Coroutines, `ActivityResultContracts` |
| `findViewById` / `Fragment`-first architecture in new code | Compose |
| `LiveData` in new Kotlin code | `StateFlow` / `Flow` |
| `SharedPreferences` on the main thread | DataStore |
| `fallbackToDestructiveMigration()` in release | Tested migrations |
| `allowMainThreadQueries()` | Suspend DAO functions |

`compileSdk` should track the latest stable; `targetSdk` moves deliberately with behaviour-change
review. Note the `compileSdk 37` requirement for material3 was **removed** in 1.5.0-alpha23, so a
project that bumped only for that can revert.

## Where to go instead

For AGP 9 migration, Navigation 3, edge-to-edge, R8 analysis, and XML-to-Compose migration, Google
publishes dedicated skills at [android/skills](https://github.com/android/skills) (Apache-2.0). They
are authoritative and more detailed than this file. Prefer them over paraphrase when the task is
specifically one of those migrations.
