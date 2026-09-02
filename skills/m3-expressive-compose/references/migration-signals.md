# Migration signals — detectable "not yet expressive" patterns

Verified: 2026-08-23 against material3 1.5.0-alpha26 API signatures.

This is the audit payload. Each entry is an observable pattern in Compose source, the API that owns
it, and what the hand-rolled version actually loses. Work from what you find in the code rather than
walking the list top to bottom — the list is an index, not a checklist to apply.

**Before writing any finding**, check the reachability column against the project's material3
version. Signals marked *1.5-alpha* are not fixable on the stable BOM; those become a single
dependency finding, not twenty separate ones. See SKILL.md § The version gate.

## Grep starting points

```bash
# hand-rolled shapes and sizes
rg -n 'RoundedCornerShape\(|CircleShape' --glob '*.kt'
rg -n '\.height\((?:32|40|56|96|136)\.dp\)|\.size\(48\.dp\)' --glob '*.kt'
# hand-rolled motion
rg -n 'tween\(|spring\(|animateDpAsState|animateFloatAsState|keyframes\(' --glob '*.kt'
# emphasis by weight override
rg -n 'fontWeight\s*=\s*FontWeight\.(Bold|Medium|SemiBold|ExtraBold)' --glob '*.kt'
# color escapes
rg -n 'Color\(0x|Color\.(Red|Blue|Green|Gray|White|Black)' --glob '*.kt'
# theme root and motion wiring
rg -n 'MaterialTheme\(|MaterialExpressiveTheme\(|motionScheme' --glob '*.kt'
# deprecated component APIs
rg -n 'SearchBar\(\s*query|rememberModalBottomSheetState|rememberStandardBottomSheetState|ListItem\(\s*headlineContent|LocalRippleConfiguration|TonalToggleButton' --glob '*.kt'
```

Read the surrounding composable before judging any hit. A literal corner radius on a bespoke brand
element is not a defect; the same literal on a `Card` is.

## Theme and foundations

| # | Signal | Replacement | What is lost | Reach |
|---|---|---|---|---|
| 1 | `MaterialTheme(` at the app root with no `motionScheme` argument | `MaterialExpressiveTheme(...)`, or keep `MaterialTheme` and pass `motionScheme = MotionScheme.expressive()` | Every component silently animates with `MotionScheme.standard()`. This is the single highest-leverage one-line change in the whole list. | 1.5-alpha |
| 2 | `RoundedCornerShape(4/8/12/16/28.dp)` | `MaterialTheme.shapes.extraSmall` / `small` / `medium` / `large` / `extraLarge` | Theming: a shape override at the theme no longer reaches the component. | 1.4 |
| 3 | `RoundedCornerShape(20/32/48.dp)` | `shapes.largeIncreased` (20) / `.extraLargeIncreased` (32) / `.extraExtraLarge` (48) | These literals are a tell that the author wanted an expressive token and did not know it existed. | 1.5-alpha |
| 4 | `tween(300)`, `spring(dampingRatio = 0.8f, stiffness = 380f)`, `animateDpAsState(animationSpec = tween(...))` | `MaterialTheme.motionScheme.defaultSpatialSpec()` / `fastSpatialSpec()` / `slowSpatialSpec()` for bounds, shape, offset; `defaultEffectsSpec()` / `fastEffectsSpec()` / `slowEffectsSpec()` for color and alpha | A hand-written spring at damping 0.6–0.9 is re-deriving the token values by hand, and will not follow a scheme swap. Note these are **functions**, not properties. | 1.5-alpha |
| 5 | `typography.titleLarge.copy(fontWeight = FontWeight.Bold)`, or `Text(fontWeight = FontWeight.Medium)` for emphasis | `MaterialTheme.typography.titleLargeEmphasized` — 15 emphasized styles exist, one per role | Emphasized styles adjust tracking and line height too, not just weight. A `copy()` gets weight alone and looks slightly wrong at display sizes. | 1.5-alpha |
| 6 | `MaterialTheme.typography.copy(displayLarge = …, displayMedium = …, …)` repeated across 15–30 styles to apply one font | `Typography(fontFamily = MyFontFamily)` — the constructor overload merges a family into every style | Hundreds of lines, and every new style added upstream is missed. | 1.5-alpha |
| 7 | `Color(0xFF...)` or `Color.Blue` inside a composable | A `MaterialTheme.colorScheme` role | Dynamic color, dark mode, and the three user contrast levels all break. See SKILL.md § Never emit color values. | 1.4 |
| 8 | `MaterialExpressiveTheme()` with no `colorScheme`, in an app that supports dark mode | Supply a scheme explicitly | **There is no `expressiveDarkColorScheme()`.** Bare `MaterialExpressiveTheme` defaults to `expressiveLightColorScheme()` regardless of system theme — a light app in dark mode. | 1.5-alpha |

## Components that carry behaviour

These are the findings worth leading with, because the hand-rolled version is missing interaction
behaviour rather than just a token.

| # | Signal | Replacement | What is lost | Reach |
|---|---|---|---|---|
| 9 | A `Row` of `Button`/`OutlinedButton` acting as one connected cluster, with per-end `RoundedCornerShape(topStart = …, bottomStart = …)` | `ButtonGroup(overflowIndicator) { clickableItem(...) / toggleableItem(...) / customItem(...) }` with `ButtonGroupDefaults.connectedLeadingButtonShapes()` / `connectedMiddleButtonShapes()` / `connectedTrailingButtonShapes()` and `Modifier.animateWidth(interactionSource)` | Press-morph, the width animation that makes a group read as connected, and overflow when the group outgrows its width. | 1.5-alpha |
| 10 | `Button(modifier = Modifier.height(56.dp), contentPadding = PaddingValues(horizontal = 24.dp))` — a hand-built size variant | `ButtonDefaults.MediumContainerHeight` with `contentPaddingFor(h)`, `shapesFor(h)`, `iconSizeFor(h)`, `iconSpacingFor(h)`, `textStyleFor(h)` | Five coordinated values per size, and the pressed-shape mapping. Also: `MinHeight` is 36.dp rather than 40.dp under precision-pointer sizing, so a hardcoded 40 is wrong on some devices. | 1.5-alpha |
| 11 | `Button` + `Modifier.toggleable`, or `IconToggleButton` standing in for a labelled toggle | `ToggleButton` / `ElevatedToggleButton` / `FilledTonalToggleButton` / `OutlinedToggleButton`, `buttonSize = ToggleButtonSize.Medium`, `ToggleButtonDefaults.shapesFor(buttonSize)` | The round↔square resting-shape change on selection, which is how M3E signals selected state. | 1.5-alpha |
| 12 | `Row { Button(onClick); IconButton(Icons.Default.ArrowDropDown) }` faking a split action | `SplitButtonLayout(leadingButton = { SplitButtonDefaults.LeadingButton(...) }, trailingButton = { SplitButtonDefaults.TrailingButton(checked, onCheckedChange) { … } })` | Correct inner-corner geometry and its pressed variant, plus the spacing token. | 1.5-alpha |
| 13 | `FloatingActionButton` plus a hand-rolled `AnimatedVisibility` column of mini FABs (a speed dial) | `FloatingActionButtonMenu(expanded, button = { ToggleFloatingActionButton(...) }) { FloatingActionButtonMenuItem(...) }`, with `ToggleFloatingActionButtonDefaults.animateIcon(...)` and `Modifier.animateFloatingActionButton(...)` | Staggered item entry, the FAB's own morph, scrim and back handling, and correct focus order. | 1.5-alpha |
| 14 | A custom `Surface(shape = CircleShape, shadowElevation = …) { Row { IconButton… } }` floating pill, or `BottomAppBar` used as a floating cluster | `HorizontalFloatingToolbar` / `VerticalFloatingToolbar` with `FloatingToolbarDefaults.exitAlwaysScrollBehavior(...)` or `Modifier.floatingToolbarVerticalNestedScroll(...)`; `vibrantFloatingToolbarColors()` | Scroll-linked collapse and expand, the elevation pair, and the FAB-attached layout variant. | 1.5-alpha |
| 15 | `MediumTopAppBar` / `LargeTopAppBar` with `Column { Text(title); Text(subtitle) }` crammed into the `title` slot | `MediumFlexibleTopAppBar` / `LargeFlexibleTopAppBar`, or `TopAppBar`'s subtitle overload; plus `titleHorizontalAlignment` | A real `subtitle` slot with correct type roles and collapse behaviour. The crammed `Column` mis-sizes on scroll. | 1.5-alpha |
| 16 | `actions = { IconButton(); IconButton(); IconButton(); IconButton() }` with no overflow handling | `AppBarRow(maxItemCount = 3, overflowIndicator = { AppBarOverflowIndicator(it) }) { … }`, or `AppBarColumn` | Actions silently truncate or collide on narrow windows and at large font scales. | 1.4 |
| 17 | `NavigationRail` on expanded windows, or a custom side nav with `animateDpAsState(width)` | `WideNavigationRail` + `rememberWideNavigationRailState()` (`expand()` / `collapse()` / `toggle()`), or `ModalWideNavigationRail` for the overlay case; items via `WideNavigationRailItem(railExpanded = …, iconPosition = WideNavigationRailItemDefaults.iconPositionFor(railExpanded))` | The expanded state entirely, and the icon-position switch that goes with it. | 1.4 |
| 18 | `NavigationBar` + `NavigationBarItem` | `ShortNavigationBar` + `ShortNavigationBarItem`, choosing `ShortNavigationBarArrangement.Centered` vs `EqualWeight` and `NavigationItemIconPosition.Top` vs `.Start` | The arrangement and icon-position choices; also a text-contrast fix that landed on the new item colors. | 1.4 |
| 19 | `CircularProgressIndicator()` / `LinearProgressIndicator()` for indeterminate busy states | `CircularWavyProgressIndicator` / `LinearWavyProgressIndicator` (stable). `LoadingIndicator()` / `ContainedLoadingIndicator()` are the shape-morphing variants but remain `@ExperimentalMaterial3ExpressiveApi` — they were promoted to stable and then reverted, so gate this recommendation. | The wavy track is the M3E treatment; the flat one now reads as pre-expressive. | 1.5-alpha |
| 20 | `IconButton(modifier = Modifier.size(48.dp))` | `IconButtonDefaults.mediumContainerSize(IconButtonWidthOption.Uniform)` with `mediumRoundShape` / `mediumPressedShape` / `mediumIconSize` | The width options (`Narrow` / `Uniform` / `Wide`) and press-morph. Note XS and S icon buttons still need a 48×48dp touch target even when the container is smaller. | 1.5-alpha |

## Shape morphing and per-state shapes

| # | Signal | Replacement | What is lost | Reach |
|---|---|---|---|---|
| 21 | `animateFloatAsState(if (pressed) 8f else 20f)` feeding a `RoundedCornerShape` | Pass a `ButtonShapes` / `ToggleButtonShapes` / `IconButtonShapes` / `ChipShapes` / `ListItemShapes` carrying `pressedShape` (and `checkedShape`) | Morph-on-press is built in and interruption-safe. The hand-rolled version stutters when taps come fast. | 1.5-alpha |
| 22 | A custom `Shape` or hand-authored `Path` for blob, star, scallop, or cookie avatars and badges | `MaterialShapes.Cookie9Sided` (35 named shapes) with `RoundedPolygon.toShape()`; animate two with `Morph(a, b).toPath(progress)` | Correct rounding and smoothing. Both are `@ExperimentalMaterial3ExpressiveApi`. **`rememberAnimatedShape` does not exist** — do not suggest it. | 1.5-alpha |

## Deprecated APIs still in use

These are unambiguous — the old form is deprecated, so there is no judgment call.

| # | Signal | Replacement | Reach |
|---|---|---|---|
| 23 | `SearchBar(query = …, active = …, onActiveChange = …)` or `SearchBar(inputField, expanded, onExpandedChange)` | `rememberSearchBarState()` + `SearchBar(state, inputField)` + `ExpandedFullScreenSearchBar` / `ExpandedDockedSearchBar`. `TopSearchBar` → `AppBarWithSearch` (`@ExperimentalMaterial3Api`). | 1.4 (state API), rest 1.5-alpha |
| 24 | `ListItem(headlineContent = { … })` | The newer `ListItem(...) { content }` overloads; `SegmentedListItem(shapes = ListItemDefaults.shapes(...))` with `ListItemDefaults.SegmentedGap` for grouped lists | 1.5-alpha |
| 25 | `rememberModalBottomSheetState()` / `rememberStandardBottomSheetState()` | `rememberBottomSheetState()` | 1.5-alpha |
| 26 | `LocalRippleConfiguration` / `RippleConfiguration` | `LocalRippleThemeConfiguration` / `RippleThemeConfiguration` — this is what carries inset focus rings | 1.5-alpha |
| 27 | `TonalToggleButton` | `FilledTonalToggleButton` (renamed in alpha25) | 1.5-alpha |
| 28 | `DropdownMenuItem(trailingIcon = …)` | `trailingContent` on the expressive overload (renamed alpha25); the expressive overload also requires `shape` | 1.5-alpha |
| 29 | `OutlinedTextField(shape = RoundedCornerShape(16.dp), colors = TextFieldDefaults.colors(...))` hand-tuned toward the expressive look | `TextFieldDefaults.roundedShape` and `TextFieldDefaults.tonalColors()` (same members on `OutlinedTextFieldDefaults`) | 1.5-alpha |
| 30 | `TextFieldLabelPosition.Attached` | `TextFieldLabelPosition.Inside` or `.Cutout` | 1.5-alpha |
| 31 | `ComponentOverride` APIs referenced anywhere | Removed entirely. Their presence means the project is pinned to an old alpha and should move. | — |

## Accessibility regressions expressive tends to introduce

Expressive encourages larger, bolder, more animated UI, and each of those has a failure mode. Check
these on any screen that was recently made more expressive, because they are the ones that turn a
prettier screen into a worse one.

- **Labels removed for a cleaner look.** Icon-only navigation and icon-only primary actions measurably
  hurt task success. Keep labels; if space is the problem, that is a layout finding, not a licence to
  drop text.
- **Contrast lost to tonal enthusiasm.** 4.5:1 for body text, 3:1 for large text and meaningful
  non-text. Outlined and text buttons are measured on the *label*; filled, tonal, and elevated on the
  *container*. Arbitrary role pairings (`tertiary` on `surfaceVariant`) are where this breaks.
- **Touch targets shrunk to match a smaller container.** Expressive XS and S sizes reduce the visible
  container, not the 48×48dp minimum target.
- **Motion with no reduced-motion path.** Honour the system animation scale; when it is 0, transition
  instantly rather than animating fast. Spring-based motion does not exempt you from this.
- **Shape morph as the only state signal.** Round→square on selection is a real affordance but it is
  not sufficient alone — pair it with a color or icon change so it survives grayscale and low vision.
- **200% font scale.** Button labels should still fit two lines at 200%. Emphasized display styles at
  large scale are where layouts break first.
