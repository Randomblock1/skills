# Foundations — shape, motion, typography, color

Verified: 2026-08-23 against material3 1.5.0-alpha26 (`tokens/ShapeTokens.kt`,
`ExpressiveMotionTokens.kt`, `StandardMotionTokens.kt`) and the 1.4.0 frozen API.

The four token systems, and how to tell a correct usage from a hand-rolled one. Every value here is
safe to quote **except** colors, which this file deliberately does not contain — see § Color.

## Shape

Eight corner values on `MaterialTheme.shapes`. The three marked new exist only in the 1.5 alpha line;
in 1.4.0 `Shapes` has the five-parameter constructor and `ShapeDefaults` has five members.

| Accessor | Radius | Typical use |
|---|---|---|
| `shapes.extraSmall` | 4.dp | Chips, snackbars |
| `shapes.small` | 8.dp | Text fields, menus |
| `shapes.medium` | 12.dp | Cards |
| `shapes.large` | 16.dp | FAB, navigation drawer |
| `shapes.largeIncreased` | 20.dp | *new* — expressive step between large and extra-large |
| `shapes.extraLarge` | 28.dp | Dialogs, bottom sheets |
| `shapes.extraLargeIncreased` | 32.dp | *new* — expressive containers |
| `shapes.extraExtraLarge` | 48.dp | *new* — large expressive surfaces, hero containers |

Same eight on `ShapeDefaults` (`.ExtraSmall`, `.Small`, `.Medium`, `.Large`, `.LargeIncreased`,
`.ExtraLarge`, `.ExtraLargeIncreased`, `.ExtraExtraLarge`). `ShapeTokens` additionally has
`CornerFull` (= `CircleShape`), `CornerNone` (= `RectangleShape`), and directional variants
(`CornerLargeTop`, `CornerLargeStart`, `CornerLargeEnd`, `CornerExtraLargeTop`, `CornerExtraSmallTop`).

**Constructor trap.** The three new corners are appended at the end, not inserted in visual order:

```kotlin
Shapes(extraSmall, small, medium, large, extraLarge, largeIncreased, extraLargeIncreased, extraExtraLarge)
```

Constructing positionally in visual order silently mis-assigns three values. Use named arguments.

### Shape as a state signal

M3 Expressive uses shape change — not just color — to communicate state. Two mechanisms:

**Round ↔ square on press.** Both round and square buttons share the same pressed shape; the radius
depends on size. Per-size square and pressed corner values:

| Size | Square corner | Pressed corner |
|---|---|---|
| XS | 12.dp | 8.dp |
| S | 12.dp | 8.dp |
| M | 16.dp | 12.dp |
| L | 28.dp | 16.dp |
| XL | 28.dp | 16.dp |

**Round ↔ square on selection.** Toggle buttons change their *resting* shape from round (unselected)
to square (selected). If the unselected resting shape is square, the selected shape is round — the
contrast is what carries the signal, not the direction.

Do not hand-animate either. Pass a shapes bundle with `pressedShape` and `checkedShape`
(`ButtonShapes`, `ToggleButtonShapes`, `IconButtonShapes`, `ChipShapes`, `ListItemShapes`,
`DragHandleShapes`, `MenuItemShapes`) and the component handles interruption and retargeting.
Shape-as-only-signal fails for low-vision users, so pair it with a color or icon change.

### Arbitrary shapes

`MaterialShapes` provides 35 named `RoundedPolygon`s (`Cookie9Sided`, `Sunny`, `Clover4Leaf`,
`Ghostish`, …) — full list in `api-surface.md`. Convert with `RoundedPolygon.toShape()`, animate
between two with `Morph(a, b).toPath(progress)`. Both are `@ExperimentalMaterial3ExpressiveApi`, and
`rememberAnimatedShape` does not exist.

## Motion

The physics system replaced fixed easing curves with springs for *components*. Legacy easing and
duration tokens are still valid for *transitions* (enter, exit, shared-axis) and as a fallback.

### Schemes

Two presets: **expressive** (the opinionated default — use for most products, especially hero
moments) and **standard** (more functional, minimal bounce — for utilitarian products). Custom
schemes are possible by implementing `MotionScheme`.

The scheme is chosen once at the product level and applied to all tokens, which is what makes a swap
cheap. Per-element override is possible via `CompositionLocal` for a subtree.

### Spring specs

Six specs, split two ways. **Spatial** animates things that move or change size — position,
rotation, bounds, corner radius — and deliberately overshoots and settles. **Effects** animates
color and opacity, where overshoot would be wrong. Three speeds each.

| Spec | expressive (damping / stiffness) | standard |
|---|---|---|
| `defaultSpatialSpec()` | 0.8 / 380 | 0.9 / 700 |
| `fastSpatialSpec()` | 0.6 / 800 | 0.9 / 1400 |
| `slowSpatialSpec()` | 0.8 / 200 | 0.9 / 300 |
| `defaultEffectsSpec()` | 1.0 / 1600 | 1.0 / 1600 |
| `fastEffectsSpec()` | 1.0 / 3800 | 1.0 / 3800 |
| `slowEffectsSpec()` | 1.0 / 800 | 1.0 / 800 |

**The effects specs are identical between schemes.** Expressive differs only in spatial motion. This
explains a common confusion: swapping to expressive appears to do nothing to a fade or a color
transition, because it genuinely does nothing to those.

Speed selection: **default** for animations that partially cover the screen (bottom sheet, expanding
rail); **fast** for small components (switch handle, button); **slow** for full-screen. The token
resolves to different absolute values per device class, so "fast" is fast *for a watch* on a watch.

Access via `MaterialTheme.motionScheme.fastSpatialSpec()` — a function call, generic in `T`.

### Reduced motion

Spring physics does not exempt an app from honouring the system animation scale. When the scale is 0,
transition instantly rather than animating quickly; a 100ms spring is still motion to someone who
turned motion off. This is a hard gate on any expressive review.

### Web conversion

If motion has to be mirrored on web, springs convert to curves (expressive fast spatial ≈
`cubic-bezier(0.42, 1.67, 0.21, 0.90)` at 350ms; expressive default spatial ≈
`cubic-bezier(0.38, 1.21, 0.22, 1.00)` at 500ms). Curves cannot handle interruption or gestures the
way springs do, so treat this as a fallback, not parity.

## Typography

Five roles × three sizes: Display, Headline, Title, Body, Label (L/M/S). Roboto and Roboto Flex are
the correct default typefaces for Material on Android — advice to avoid Roboto comes from generic
web-design guidance and does not apply here.

### Emphasized styles

Fifteen `*Emphasized` variants, one per base role, on `MaterialTheme.typography`:
`displayLargeEmphasized`, `displayMediumEmphasized`, `displaySmallEmphasized`,
`headlineLargeEmphasized`, `headlineMediumEmphasized`, `headlineSmallEmphasized`,
`titleLargeEmphasized`, `titleMediumEmphasized`, `titleSmallEmphasized`, `bodyLargeEmphasized`,
`bodyMediumEmphasized`, `bodySmallEmphasized`, `labelLargeEmphasized`, `labelMediumEmphasized`,
`labelSmallEmphasized`.

Stable, but only in the 1.5 alpha line — `displayLargeEmphasized` does not exist in 1.4.0.

Use these instead of `style = titleLarge.copy(fontWeight = FontWeight.Bold)`. The emphasized styles
adjust tracking and line height as well as weight, so the hand-rolled `copy()` looks subtly wrong,
most visibly at display sizes. Apply them to selected and active states, primary actions, headlines
that need to carry, and unread or important content.

Note that `MaterialExpressiveTheme` does **not** currently substitute an expressive typography
default (there is a source TODO), so emphasized styles are opt-in per call site under either theme.

### Applying one font family

`Typography` has a constructor overload that merges a family into every style:

```kotlin
Typography(fontFamily = MyFontFamily)
```

Use this rather than `copy()`-ing 15 or 30 styles by hand. The manual version misses any style added
upstream and is where most theme files bloat.

## Color

**This file contains no hex values, on purpose.** Material's published spec token tables render
whichever token set the page has selected, which is frequently Google's own brand palette. A
remembered or scraped value like "M3 filled button container = #0B57D0" is Google Blue, not a
baseline Material value and certainly not this app's brand. Writing one into a theme produces an app
that looks like a Google product and breaks the moment dynamic color is enabled.

So color is always a *role*, never a value.

### Building a scheme

- **API 31+ with dynamic color:** `dynamicLightColorScheme(context)` /
  `dynamicDarkColorScheme(context)`, guarded by `Build.VERSION.SDK_INT >= Build.VERSION_CODES.S`.
- **Brand-seeded:** Material Theme Builder output, or `lightColorScheme()` / `darkColorScheme()`
  supplied from a seed.
- **Expressive:** `expressiveLightColorScheme()`. There is **no** `expressiveDarkColorScheme()` —
  a bare `MaterialExpressiveTheme` gives a light scheme in dark mode. Supply the dark scheme yourself.

### The roles

Accent families, each with an `on-` pair and a container pair: `primary` / `onPrimary` /
`primaryContainer` / `onPrimaryContainer`, and the same for `secondary` and `tertiary`.
`error` and its family are static — they do not shift with dynamic color.

Surfaces: `surface`, `onSurface`, `onSurfaceVariant` (lower-emphasis text and icons), the five-step
container ramp `surfaceContainerLowest` → `surfaceContainerHighest`, plus `surfaceDim` /
`surfaceBright` for maintaining relative brightness across light and dark, and
`inverseSurface` / `inverseOnSurface` / `inversePrimary` for snackbars and other contrasting elements.

Boundaries: `outline` for meaningful borders such as text-field outlines; `outlineVariant` for
decorative lines and dividers. Using `outline` for a divider is a common and visible error.

### Pairing

Only combine colors in their intended pairs — `primary` with `onPrimary`, `surfaceContainer` with
`onSurface`. Arbitrary pairings survive the default light theme and then fail in dark mode, under
dynamic color, and at the medium and high user contrast levels, which is why they are hard to catch
by eye. Other role pairs are legitimate when they hold a 3:1 container-to-label contrast — tertiary
on onTertiary, for instance — but that is a deliberate choice to verify, not a default.

Button color mappings, for review purposes: elevated is `surfaceContainerLow` container with
`primary` label; filled is `primary` with `onPrimary`; tonal is `secondaryContainer` with
`onSecondaryContainer`; outlined has no fill, `outlineVariant` stroke and `onSurfaceVariant` label;
text has `primary` label and no container at rest. Toggle variants swap to `primary`/`onPrimary` when
selected — except text, which has no toggle form.

### Elevation

Elevation in M3 is communicated primarily through **tonal surface color**, not shadows. Six levels
(0dp, 1dp, 3dp, 6dp, 8dp, 12dp), where 4 and 5 exist only as hover and focus increases. Use
`Surface`'s `tonalElevation`, and add `shadowElevation` only when an element genuinely needs
separation from a busy background such as an image. The elevated button style is the tonal button
plus a shadow, and the spec's own guidance is to use it only when necessary — for high emphasis,
prefer filled.

### Contrast gates

4.5:1 for body text, 3:1 for large text and meaningful non-text elements. Where the ratio is measured
depends on the component: filled, tonal, and elevated buttons are measured on the **container**;
outlined and text buttons on the **label**, since that is all there is at rest. High-contrast mode
reduces the palette sharply and shows focus rings — check that a screen still reads there.
