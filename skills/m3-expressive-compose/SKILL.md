---
name: m3-expressive-compose
description: >
  Audit and implement Material 3 Expressive in Jetpack Compose (and Wear Compose Material 3).
  Use this whenever Android UI work touches Material Design, M3, M3 Expressive, Material You,
  MaterialTheme, MaterialExpressiveTheme, motion schemes, shape morphing, dynamic color, or the
  expressive component set (ButtonGroup, ToggleButton, SplitButtonLayout, FloatingActionButtonMenu,
  LoadingIndicator, floating toolbars, WideNavigationRail, ShortNavigationBar, flexible top app bars,
  emphasized type styles). Use it for reviewing an existing Compose codebase against M3E guidance,
  for deciding whether a screen looks right, and for building new expressive UI. Reach for it even
  when the request does not name Material — "does my app follow Android design guidelines", "make
  this screen feel more modern", "my button animation looks off", "review my Compose theme", and
  "why does this look like stock Material" are all this skill. Not for Android architecture, DI,
  persistence, or build config — that is a separate concern.
---

# Material 3 Expressive in Compose

Verified: 2026-08-23 against `androidx.compose.material3` 1.4.0 stable and 1.5.0-alpha26.

Most requests here are really review requests: someone has built a screen and wants to know whether
it is right. So the default mode is audit, and the default output is findings with file:line
evidence and a named replacement API — not a rewritten screen.

## Core principle

Expressive is a set of *first-class APIs*, not a look you approximate. Almost every "not yet
expressive" codebase is one that hand-rolled something Material now ships: a `RoundedCornerShape`
literal where a shape token exists, a `spring(0.8f, 380f)` where `motionScheme` exists, a `Row` of
buttons where `ButtonGroup` exists. So the highest-value finding is almost never "add more
expression" — it is "you already built this; here is the API that owns it."

That reframing matters because hand-rolled equivalents are not merely verbose. They miss the
behaviours the real component carries: shape morph on press, spring interruption and retargeting,
overflow handling, and correct semantics for TalkBack.

## The version gate — establish this first

**`androidx.compose.material3:material3` 1.4.0 stable contains almost none of the expressive
layer.** Verified against the frozen `1.4.0-beta03` API signature file. Absent from 1.4.0:
`MaterialExpressiveTheme`, `MotionScheme`, `expressiveLightColorScheme`, `MaterialShapes`, the
`*Emphasized` type styles, `shapes.largeIncreased` / `.extraLargeIncreased` / `.extraExtraLarge`,
`ButtonGroup`, `ToggleButton`, `SplitButtonLayout`, `LoadingIndicator`, `FloatingToolbar`,
`FloatingActionButtonMenu`, `MediumFlexibleTopAppBar`, the wavy progress indicators.

Present in 1.4.0: `WideNavigationRail`, `ModalWideNavigationRail`, `ShortNavigationBar`,
`ShortNavigationBarItem`, `AppBarRow` / `AppBarColumn`, `SearchBarState`.

Read `gradle/libs.versions.toml` and the module `build.gradle.kts` before anything else, because
this single fact determines whether your findings are code changes or a dependency change:

```kotlin
implementation(platform("androidx.compose:compose-bom:2026.08.00"))
implementation("androidx.compose.material3:material3:1.5.0-alpha26") // must override the BOM
```

If the project is on the stable BOM, say so plainly and lead with the dependency finding. Do not
bury twenty unactionable API recommendations above it. If the project cannot take an alpha — a
common and legitimate constraint — then the honest answer is that expressive is not available yet,
and the review should fall back to what *is* reachable: shape and type tokens already in 1.4.0,
`WideNavigationRail`, `ShortNavigationBar`, correct color-role pairing, and accessibility.

## Procedure

1. **Read the versions.** `libs.versions.toml`, the material3 dependency, `compileSdk`. Note whether
   expressive APIs are reachable at all. Everything downstream is conditioned on this.
2. **Find the theme root.** Locate `MaterialTheme(` / `MaterialExpressiveTheme(` and read the
   `ColorScheme`, `Typography`, and `Shapes` it supplies. A theme that hardcodes hex colors, or that
   omits `motionScheme`, sets the ceiling for every screen — fix it before individual components.
3. **Scan for the migration signals.** `references/migration-signals.md` is the audit payload: 24
   grep-able anti-patterns, each with the exact replacement API. Work from observable code, not from
   a topic checklist.
4. **Check for a false lead.** Before writing a finding, ask whether the hand-rolled version is
   actually correct for its context. A `RoundedCornerShape(4.dp)` on a custom brand element that is
   deliberately not a Material component is not a defect. A `tween` driving a one-off decorative
   loop that no user interrupts does not need a motion token. Reporting these wastes the reader's
   attention and trains them to distrust the rest of the list.
5. **Judge the design, not just the API.** Correct token usage can still produce a bad screen —
   usually by making everything loud. `references/design-guidelines.md` carries the intensity levels
   and the hero-moment constraint that decide this.
6. **Check accessibility.** Contrast, touch targets, motion-scale honouring, content descriptions.
   These are gates, not suggestions: an expressive screen that fails them is worse than the stock
   one it replaced.
7. **Order by impact and stop.** Theme-level findings, then components that carry behaviour
   (`ButtonGroup`, toolbars, FAB menu), then token substitutions, then polish. When the remaining
   findings are all cosmetic token swaps, you are done — say so rather than continuing to enumerate.

## Never emit color values

Material's published spec token tables render whichever token set the page has selected, which is
often **Google's own brand palette** — values like `#0B57D0` and `#F0F4F9`. Any scraped or
remembered "M3 button container color" hex is therefore probably Google Blue, not a baseline
Material value, and definitely not this app's brand.

So: colors come from `MaterialTheme.colorScheme` roles, and a theme is built with
`dynamicLightColorScheme` / `dynamicDarkColorScheme` on API 31+, or from Material Theme Builder
output, or `lightColorScheme` / `darkColorScheme` seeded by the brand. Never write a hex literal into
a component, and never quote one as a spec value. When a review needs to talk about color, name the
*role* (`primaryContainer`, `onSecondaryContainer`) and the pairing rule.

The `dp` values in this skill's references are safe to quote — sizes, corner radii, spacing, spring
constants. Colors are not.

## Signal router

Read the reference file that matches what you are actually looking at.

| Signal in the code or the request | Read |
|---|---|
| Auditing an existing screen or codebase; "is this right?" | `references/migration-signals.md` |
| Need an exact API name, signature, or stability status | `references/api-surface.md` |
| `RoundedCornerShape(N.dp)`, custom `Shape`, blob/star shapes, morph on press | `references/foundations.md` § Shape |
| `tween(`, `spring(`, `animate*AsState`, transitions feel wrong | `references/foundations.md` § Motion |
| `fontWeight =` overrides, `typography.copy(`, font family plumbing | `references/foundations.md` § Typography |
| Hex literals, `Color(0x`, dark mode wrong, contrast complaints | `references/foundations.md` § Color |
| Screen feels loud, cluttered, or flat; "make it more expressive" | `references/design-guidelines.md` |
| Per-component sizes, heights, corner values, variant choice | `references/component-specs.md` |
| Tablets, foldables, `NavigationRail`, window size classes, nav choice | `references/adaptive.md` |
| Wear OS, watch surface, `wear.compose.material3` | `references/wear.md` |

## Report format

For an audit, lead with the version verdict, then findings ordered by impact. Each finding:

```
### <what is wrong> — <file>:<line>
Current: <the actual code, quoted>
Replace with: <exact API, with the members named>
Why: <the behaviour or token the hand-rolled version misses>
Reachable: <yes | requires material3 1.5.0-alphaNN>
```

Close with what is already correct — briefly, and only where it is load-bearing. A reviewer who
lists only faults reads as unable to tell the difference.

When there are no real findings, say that. "The theme supplies `MotionScheme.expressive()`, shapes
come from tokens, and the four screens I read use component APIs rather than hand-rolled
equivalents — I found nothing worth changing" is a complete and useful answer. Inventing a token
swap to have something to report is the main failure mode of this kind of review.

## Worked examples

**A finding worth making.** A screen has `Row { OutlinedButton(shape = RoundedCornerShape(topStart
= 20.dp, bottomStart = 20.dp, topEnd = 0.dp, bottomEnd = 0.dp)) ; OutlinedButton(...) ;
OutlinedButton(shape = /* mirrored */) }`. This is `ButtonGroup` with
`ButtonGroupDefaults.connectedLeadingButtonShapes()` / `connectedMiddleButtonShapes()` /
`connectedTrailingButtonShapes()` and `Modifier.animateWidth(interactionSource)`. The hand-rolled
version is missing press-morph and the width animation that makes a connected group feel connected,
and it will drift the moment someone adds a fourth button.

**A finding not worth making.** A settings screen uses `Button(onClick = …) { Text("Save") }` with
no shape, size, or color arguments. That is already correct: it picks up `ButtonDefaults.shape`,
`MinHeight`, and the theme's color scheme. There is nothing to add, and adding
`shape = MaterialTheme.shapes.large` would actively make it wrong. Report no change.

**A finding that is really a version finding.** A screen hand-animates a speed-dial FAB with
`AnimatedVisibility` and three `SmallFloatingActionButton`s. `FloatingActionButtonMenu` owns this —
but if the project is on the stable BOM, the finding is "this needs material3 1.5.0-alpha26; here is
what it would become," not a patch that will not compile.

**Judgment, not API compliance.** A screen correctly uses `displayLargeEmphasized`,
`extraExtraLarge` corners, a vibrant floating toolbar, and `MotionScheme.expressive()` on six
elements. Every token is right and the screen is bad, because six hero moments means none. The
finding is to demote four of them — see `references/design-guidelines.md`.
