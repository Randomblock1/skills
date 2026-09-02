# Expressive API surface — verified inventory

Verified: 2026-08-23 against AndroidX metalava signature files
(`compose/material3/material3/api/current.txt` at 1.5.0-alpha27-dev, and the frozen
`1.4.0-beta03.txt`), plus `tokens/*.kt` for values. Release notes were used only for dates.

Use this file when you need an exact name, signature, or stability status. Compose Material 3 has
churned hard across the 1.5 alphas, so a plausible-sounding API name is a real risk — when a symbol
is not listed here, verify it against the project's actual dependency rather than assuming.

## Contents

- [Versions](#versions)
- [What is stable vs experimental](#what-is-stable-vs-experimental)
- [Theming: MaterialExpressiveTheme](#theming-materialexpressivetheme)
- [MotionScheme](#motionscheme)
- [Buttons and ButtonDefaults](#buttons-and-buttondefaults)
- [ToggleButton](#togglebutton)
- [ButtonGroup](#buttongroup)
- [SplitButton](#splitbutton)
- [FAB and FAB menu](#fab-and-fab-menu)
- [Loading and progress](#loading-and-progress)
- [MaterialShapes and morphing](#materialshapes-and-morphing)
- [Floating toolbars](#floating-toolbars)
- [Navigation](#navigation)
- [App bars](#app-bars)
- [Search](#search)
- [Lists and menus](#lists-and-menus)
- [Everything else](#everything-else)
- [Naming traps](#naming-traps)
- [Renames and removals](#renames-and-removals-across-the-15-alphas)

## Versions

| Artifact | Stable | Pre-release |
|---|---|---|
| `androidx.compose.material3:material3` | **1.4.0** (Aug 12 2026) | **1.5.0-alpha26** |
| `material3-adaptive-navigation-suite` | 1.4.0 | 1.5.0-alpha26 |
| `material3-window-size-class` | 1.4.0 | 1.5.0-alpha26 |
| `material3-ripple` (new) | — | 1.5.0-alpha24+ |
| `androidx.compose.material3.adaptive:adaptive*` | **1.3.0** | — |
| `androidx.graphics:graphics-shapes` | **1.1.0** | — |
| `androidx.compose:compose-bom` | **2026.08.00** | — |

Facts that matter:

- **There is no `material3-expressive` artifact.** All expressive APIs live in
  `androidx.compose.material3:material3`.
- `material3-adaptive-navigation-suite` is versioned **with material3** (1.4.0 / 1.5.0-alpha26), not
  with `adaptive` (1.3.0). Easy to get wrong in a version catalog.
- `graphics-shapes` arrives **transitively** — material3 declares `api("androidx.graphics:graphics-shapes")`,
  so `RoundedPolygon` and `Morph` need no extra dependency.
- The `compileSdk 37` requirement was **removed** in 1.5.0-alpha23.

## What is stable vs experimental

At tip, only four areas still carry `@ExperimentalMaterial3ExpressiveApi`:

1. `LoadingIndicator` / `ContainedLoadingIndicator` (all overloads) and `LoadingIndicatorDefaults`
2. `MaterialShapes` (class and `Companion`)
3. The bridge functions `Morph.toPath(...)`, `RoundedPolygon.toPath(...)`, `RoundedPolygon.toShape(...)`
4. `PullToRefreshDefaults.LoadingIndicator(...)` and its two color properties

**Everything else expressive has graduated.** `@ExperimentalMaterial3Api` (a different annotation)
is still needed for `AppBarWithSearch`, tooltips, bottom sheets and `BottomSheetScaffold`,
`MultiAspectCarousel`, `ComposeMaterial3Flags`, and one member each of `TextFieldDefaults` /
`OutlinedTextFieldDefaults`.

Do not assert stability from a release note alone. `MaterialShapes` and `LoadingIndicator` were
promoted to stable and then **reverted** in alpha19; `AppBarWithSearch` had its experimental tag
**re-added** in alpha24. Check the annotation in the version the project targets.

## Theming: MaterialExpressiveTheme

```kotlin
@Composable
public fun MaterialExpressiveTheme(
    colorScheme: ColorScheme? = null,
    motionScheme: MotionScheme? = null,
    shapes: Shapes? = null,
    typography: Typography? = null,
    content: @Composable () -> Unit,
)
```

Stable at tip; absent from 1.4.0. Promoted in 1.5.0-alpha18.

**It does less than its name suggests.** From the source: when not already inside an expressive
theme it delegates to `MaterialTheme` with `colorScheme ?: expressiveLightColorScheme()` and
`motionScheme ?: MotionScheme.expressive()`, but `shapes ?: Shapes()` and `typography ?: Typography()`
— the *same* defaults as plain `MaterialTheme`. So:

- What it actually gives you: `expressiveLightColorScheme()` and `MotionScheme.expressive()`.
- What it does **not** gate: the shape scale and the emphasized type styles are available under
  plain `MaterialTheme` too. There is an in-source TODO for expressive typography defaults.
- It is **optional**. No expressive component requires it. `ButtonGroup`,
  `HorizontalFloatingToolbar`, `FloatingActionButtonMenu` all work under plain `MaterialTheme` —
  they just animate with `MotionScheme.standard()`.

Two traps:

- **No `expressiveDarkColorScheme()` exists.** Bare `MaterialExpressiveTheme` yields a *light*
  scheme regardless of system theme. Dark mode needs your own `ColorScheme` or `dynamicDarkColorScheme`.
- **Nesting inherits rather than resets.** An inner `MaterialExpressiveTheme` sees
  `LocalUsingExpressiveTheme == true` and falls back to current theme values, so you cannot
  re-apply expressive defaults deeper in the tree by nesting.

`MaterialTheme` gained a motion-aware overload `MaterialTheme(colorScheme, motionScheme, shapes,
typography, content)` alongside the legacy four-arg form. Also new: `MaterialTheme.Values` (holder
with `colorScheme`, `typography`, `shapes`, `motionScheme`, defaulting `motionScheme = standard()`)
and `MaterialTheme.LocalMaterialTheme`.

## MotionScheme

```kotlin
@Immutable
public interface MotionScheme {
    public fun <T> defaultSpatialSpec(): FiniteAnimationSpec<T>
    public fun <T> fastSpatialSpec(): FiniteAnimationSpec<T>
    public fun <T> slowSpatialSpec(): FiniteAnimationSpec<T>
    public fun <T> defaultEffectsSpec(): FiniteAnimationSpec<T>
    public fun <T> fastEffectsSpec(): FiniteAnimationSpec<T>
    public fun <T> slowEffectsSpec(): FiniteAnimationSpec<T>
    public companion object {
        public fun standard(): MotionScheme
        public fun expressive(): MotionScheme
    }
}
```

Accessor: `MaterialTheme.motionScheme`. Stable at tip. Exactly six members, all **functions, not
properties**, generic in `T` — call sites read `MaterialTheme.motionScheme.fastSpatialSpec<Float>()`
or rely on inference.

**Spatial** specs animate shape and bounds (position, size, rotation, corner radius) and overshoot.
**Effects** specs animate color and alpha and must not overshoot.

Token values, from `ExpressiveMotionTokens.kt` and `StandardMotionTokens.kt` (damping / stiffness):

| spec | expressive | standard |
|---|---|---|
| `defaultSpatialSpec` | 0.8 / 380 | 0.9 / 700 |
| `fastSpatialSpec` | 0.6 / 800 | 0.9 / 1400 |
| `slowSpatialSpec` | 0.8 / 200 | 0.9 / 300 |
| `defaultEffectsSpec` | 1.0 / 1600 | 1.0 / 1600 |
| `fastEffectsSpec` | 1.0 / 3800 | 1.0 / 3800 |
| `slowEffectsSpec` | 1.0 / 800 | 1.0 / 800 |

The effects specs are **identical** between schemes — expressive differs only in spatial motion
(lower damping, springier). Useful when someone asks why a scheme swap "did nothing" to a fade.

Speed guidance: default for partial-screen animations (sheets, expanding rails); fast for small
components (switches, buttons); slow for full-screen. Per-element override is possible by providing
a different scheme via `CompositionLocal` for that subtree.

## Buttons and ButtonDefaults

`ButtonDefaults` is fully stable at tip. Container heights:

| Size | Member | Value |
|---|---|---|
| XSmall | `ExtraSmallContainerHeight` | 32.dp |
| Small | **`MinHeight`** | 40.dp (36.dp under precision-pointer sizing) |
| Medium | `MediumContainerHeight` | 56.dp |
| Large | `LargeContainerHeight` | 96.dp |
| XLarge | `ExtraLargeContainerHeight` | 136.dp |

Content padding: `ContentPadding` (legacy), `ExtraSmallContentPadding`, `SmallContentPadding`,
`MediumContentPadding`, `LargeContentPadding`, `ExtraLargeContentPadding`, plus
`ButtonWithIconContentPadding`, `TextButtonContentPadding`, `TextButtonWithIconContentPadding`.

Icon sizes: `IconSize` (18, legacy), `ExtraSmallIconSize` (20), `SmallIconSize` (20),
`MediumIconSize` (24), `LargeIconSize` (32), `ExtraLargeIconSize` (40).

Icon spacing: `IconSpacing` (8), `ExtraSmallIconSpacing` (4), `MediumIconSpacing` (8),
`LargeIconSpacing` (12), `ExtraLargeIconSpacing` (16). `MinWidth` = 58.dp.

Shape properties (all `@Composable`): `shape`, `squareShape`, `pressedShape`, `elevatedShape`,
`filledTonalShape`, `outlinedShape`, `textShape`, `extraSmallPressedShape`, `mediumPressedShape`,
`largePressedShape`, `extraLargePressedShape`. Resolved: `shape` = full/circle; `squareShape` = 12dp
at XS/S, large at M, extra-large at L/XL; `pressedShape` = 8dp at XS/S, medium at M, large at L/XL.

**The idiomatic path is the size-derived helpers**, not picking members by hand:

```kotlin
ButtonDefaults.shapes(): ButtonShapes
ButtonDefaults.shapes(shape: Shape?, pressedShape: Shape?): ButtonShapes
ButtonDefaults.shapesFor(buttonHeight: Dp): ButtonShapes
ButtonDefaults.contentPaddingFor(buttonHeight: Dp, hasStartIcon: Boolean, hasEndIcon: Boolean): PaddingValues
ButtonDefaults.iconSizeFor(buttonHeight: Dp): Dp
ButtonDefaults.iconSpacingFor(buttonHeight: Dp): Dp
@Composable ButtonDefaults.textStyleFor(buttonHeight: Dp): TextStyle
```

## ToggleButton

Stable, promoted alpha19. Composables: `ToggleButton`, `ElevatedToggleButton`,
`FilledTonalToggleButton`, `OutlinedToggleButton`.

```kotlin
ToggleButton(
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
    buttonSize: ToggleButtonSize = …,
    enabled: Boolean = true,
    icon: (@Composable () -> Unit)? = null,
    shapes: ToggleButtonShapes = …,
    colors: ToggleButtonColors = …,
    elevation: ToggleButtonElevation? = …,
    border: BorderStroke? = …,
    contentPadding: PaddingValues = …,
    interactionSource: MutableInteractionSource? = null,
    content: @Composable RowScope.() -> Unit,
)
```

`ToggleButtonSize` is a `@JvmInline value class` wrapping `height: Dp`; its companion exposes
`ExtraSmall`, `Small`, `Medium`, `Large`, `ExtraLarge`.

Four defaults objects (added alpha26): `ToggleButtonDefaults`, `ElevatedToggleButtonDefaults`,
`FilledTonalToggleButtonDefaults`, `OutlinedToggleButtonDefaults`. Each has `colors()`,
`contentPaddingFor(...)`, `elevation(...)`, `shapesFor(ToggleButtonSize | Dp)`, and properties
`IconSize`, `IconSpacing`, `MinHeight`, `shape`, `pressedShape`, `checkedShape`, `size`.
`OutlinedToggleButtonDefaults` adds `border(enabled, checked)`.

`ToggleButtonShapes(shape, pressedShape, checkedShape)`. Use `shapesFor` — plain `shapes` was
deprecated in alpha25 and is gone at tip.

## ButtonGroup

Stable, promoted alpha22.

```kotlin
ButtonGroup(
    overflowIndicator: @Composable (ButtonGroupMenuState) -> Unit,
    modifier: Modifier = Modifier,
    expandedRatio: Float = …,
    horizontalArrangement: Arrangement.Horizontal = …,
    verticalAlignment: Alignment.Vertical = …,
    content: ButtonGroupScope.() -> Unit,
)
```

`ButtonGroupScope` (a `sealed interface`) provides `clickableItem(onClick, label, icon, weight,
enabled)`, `toggleableItem(checked, label, onCheckedChange, icon, weight, enabled)`,
`customItem(buttonGroupContent, menuContent)`, `Modifier.weight(Float)`,
`Modifier.align(Alignment.Vertical)`, and `Modifier.animateWidth(interactionSource)` /
`animateWidth(interactionSource, compressionLimit: Dp)`.

`ButtonGroupDefaults`: `OverflowIndicator(menuState, …)`, `connectedLeadingButtonShapes(...)`,
`connectedMiddleButtonShapes(...)`, `connectedTrailingButtonShapes(...)` (each returning
`ToggleButtonShapes`), plus `ConnectedSpaceBetween`, `ExpandedRatio`, `HorizontalArrangement` and
the individual connected shape properties. State: `ButtonGroupMenuState`.

## SplitButton

Stable, graduated alpha20.

⚠️ **Use `SplitButtonLayout`.** The alpha25 release note says `SplitButtonLayout` was deprecated in
favour of `SplitButton`, but the code at tip declares `SplitButtonLayout` with no `@Deprecated` and
contains **no `SplitButton` composable at all**. Trust the code; re-verify against the exact alpha.

```kotlin
SplitButtonLayout(
    leadingButton: @Composable () -> Unit,
    trailingButton: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    spacing: Dp = SplitButtonDefaults.Spacing,
)
```

`SplitButtonDefaults` supplies the halves: `LeadingButton`, `TonalLeadingButton`,
`ElevatedLeadingButton`, `OutlinedLeadingButton`; `TrailingButton` (both an `onClick` and a
`checked`/`onCheckedChange` overload), `TonalTrailingButton`, `ElevatedTrailingButton`,
`OutlinedTrailingButton`. Sizing: `ExtraSmallContainerHeight` … `ExtraLargeContainerHeight`, per-size
`*LeadingButtonContentPadding` / `*TrailingButtonContentPadding` / `*TrailingButtonIconSize` /
`*InnerCornerSize` / `*InnerCornerSizePressed`, plus `OuterCornerSize`, `LeadingIconSize`,
`TrailingIconSize`, `Spacing`. Helpers `leadingButtonContentPaddingFor(Dp)`,
`leadingButtonIconSizeFor(Dp)`, `leadingButtonShapesFor(Dp)` and the `trailingButton*` equivalents.
`SplitButtonShapes(shape, pressedShape?, checkedShape?)`.

Note `SplitButtonDefaults` *does* have `SmallContainerHeight` — unlike `ButtonDefaults`.

## FAB and FAB menu

All stable, graduated alpha19.

```kotlin
FloatingActionButtonMenu(expanded, button, modifier, horizontalAlignment,
                         content: FloatingActionButtonMenuScope.() -> Unit)
FloatingActionButtonMenuScope.FloatingActionButtonMenuItem(onClick, text, icon, modifier,
                         containerColor, contentColor)
ToggleFloatingActionButton(checked, onCheckedChange, modifier,
                         containerColor: (Float) -> Color, contentAlignment,
                         containerSize: (Float) -> Dp, containerCornerRadius: (Float) -> Dp,
                         content: ToggleFloatingActionButtonScope.() -> Unit)
```

`ToggleFloatingActionButtonScope` exposes `checkedProgress: Float`, which is what the
progress-parameterised lambdas consume. `ToggleFloatingActionButtonDefaults` supplies them:
`animateIcon(checkedProgress, color, size)`, `containerColor(initial, final)`, `containerSize()` /
`containerSizeMedium()` / `containerSizeLarge()`, `containerCornerRadius()` and its Medium/Large
variants, `iconColor(...)`, `iconSize()` and variants.

Also `Modifier.animateFloatingActionButton(visible, alignment, targetScale, scaleAnimationSpec,
alphaAnimationSpec)`. FAB sizes: `SmallFloatingActionButton`, `FloatingActionButton`,
`MediumFloatingActionButton`, `LargeFloatingActionButton`, and the four extended variants
(`SmallExtendedFloatingActionButton` … `LargeExtendedFloatingActionButton`).

## Loading and progress

`LinearWavyProgressIndicator`, `CircularWavyProgressIndicator`, `WavyProgressIndicatorDefaults` are
**stable** (alpha18). Prefer these.

`LoadingIndicator` and `ContainedLoadingIndicator` remain `@ExperimentalMaterial3ExpressiveApi` —
promoted to stable and then reverted in alpha19.

```kotlin
@ExperimentalMaterial3ExpressiveApi @Composable
fun LoadingIndicator(modifier, color, polygons: List<RoundedPolygon>)
fun LoadingIndicator(progress: () -> Float, modifier, color, polygons)
fun ContainedLoadingIndicator(modifier, containerColor, indicatorColor, containerShape, polygons)
fun ContainedLoadingIndicator(progress: () -> Float, …)
```

`LoadingIndicatorDefaults`: `ContainerWidth`, `ContainerHeight`, `IndicatorSize`,
`IndeterminateIndicatorPolygons`, `DeterminateIndicatorPolygons`, `indicatorColor`,
`containedIndicatorColor`, `containedContainerColor`, `containerShape`.

## MaterialShapes and morphing

`MaterialShapes` is an `@ExperimentalMaterial3ExpressiveApi abstract sealed class` whose companion
holds **35 named `RoundedPolygon` properties**:

`Arch`, `Arrow`, `Boom`, `Bun`, `Burst`, `Circle`, `ClamShell`, `Clover4Leaf`, `Clover8Leaf`,
`Cookie4Sided`, `Cookie6Sided`, `Cookie7Sided`, `Cookie9Sided`, `Cookie12Sided`, `Diamond`, `Fan`,
`Flower`, `Gem`, `Ghostish`, `Heart`, `Oval`, `Pentagon`, `Pill`, `PixelCircle`, `PixelTriangle`,
`Puffy`, `PuffyDiamond`, `SemiCircle`, `Slanted`, `SoftBoom`, `SoftBurst`, `Square`, `Sunny`,
`Triangle`, `VerySunny`.

Bridge functions, all experimental:

```kotlin
fun Morph.toPath(progress: Float, path: Path = …, startAngle: Int = …): Path
@Composable fun RoundedPolygon.toPath(startAngle: Int = …): Path
@Composable fun RoundedPolygon.toShape(startAngle: Int = …): Shape
```

From `androidx.graphics.shapes` (1.1.0 stable): `RoundedPolygon(...)` factories over
`numVertices` / `vertices: FloatArray` / `features`, plus `RoundedPolygon.Companion.circle` /
`pill` / `pillStar` / `star` / `rectangle`; `Morph(start, end)` with `asCubics(progress)` /
`forEachCubic(progress) {}` / `calculateBounds(...)`; `CornerRounding(radius, smoothing)` and
`CornerRounding.Unrounded`; `Cubic` / `MutableCubic`; `Feature`; `PointTransformer`;
`SvgPathParser.parseFeatures(svgPath)`; `RoundedPolygon.transformed(Matrix)`.

⚠️ **`rememberAnimatedShape` does not exist** anywhere in material3 or graphics-shapes. If a blog
post shows it, it was an earlier alpha or Wear-specific. The supported paths are
`Morph(a, b).toPath(progress)` inside a custom `Shape`, or the built-in `pressedShape` /
`checkedShape` slots on `ButtonShapes` / `ToggleButtonShapes` / `IconButtonShapes` / `ChipShapes` /
`ListItemShapes` / `DragHandleShapes` / `MenuItemShapes`.

## Floating toolbars

Stable, graduated around alpha22–alpha23.

```kotlin
HorizontalFloatingToolbar(expanded, modifier, colors, contentPadding, scrollBehavior, shape,
                          leadingContent, trailingContent,
                          expandedShadowElevation, collapsedShadowElevation,
                          content: @Composable RowScope.() -> Unit)
HorizontalFloatingToolbar(expanded, floatingActionButton, modifier, colors, contentPadding,
                          scrollBehavior, shape, floatingActionButtonPosition, animationSpec,
                          expandedShadowElevation, collapsedShadowElevation, content)
VerticalFloatingToolbar(…)  // same two shapes, ColumnScope
rememberFloatingToolbarState(initialOffsetLimit, initialOffset, initialContentOffset)
```

Types: `FloatingToolbarColors`, `FloatingToolbarState`, `FloatingToolbarScrollBehavior`,
`FloatingToolbarExitDirection`, `FloatingToolbarHorizontalFabPosition`,
`FloatingToolbarVerticalFabPosition`.

`FloatingToolbarDefaults`: `StandardFloatingActionButton(...)`, `VibrantFloatingActionButton(...)`,
`standardFloatingToolbarColors()` / `vibrantFloatingToolbarColors()`, `animationSpec()`,
`exitAlwaysScrollBehavior(exitDirection, state, snapAnimationSpec, flingAnimationSpec)`,
`Modifier.floatingToolbarVerticalNestedScroll(expanded, onExpand, onCollapse, …)`, the four
enter/exit transitions, and `ContainerShape`, `ContainerSize`, `ContentPadding`, `ScreenOffset`,
`ScrollDistanceThreshold`, and the four elevation constants.

## Navigation

Both families are **stable and already in 1.4.0** — the only expressive components reachable on the
stable BOM.

```kotlin
WideNavigationRail(modifier, state: WideNavigationRailState, shape, colors, header, windowInsets,
                   arrangement, contentPadding, content)
ModalWideNavigationRail(modifier, state, hideOnCollapse, collapsedShape, expandedShape, colors,
                   header, expandedHeaderTopPadding, windowInsets, arrangement,
                   expandedProperties: ModalWideNavigationRailProperties, contentPadding, content)
WideNavigationRailItem(selected, onClick, icon, label, railExpanded, modifier, enabled,
                   iconPosition: NavigationItemIconPosition, colors, interactionSource, indicatorPadding)
rememberWideNavigationRailState(initialValue: WideNavigationRailValue)

ShortNavigationBar(modifier, containerColor, contentColor, windowInsets,
                   arrangement: ShortNavigationBarArrangement, content)
ShortNavigationBarItem(selected, onClick, icon, label, modifier, enabled,
                   iconPosition: NavigationItemIconPosition, colors, interactionSource)
```

`WideNavigationRailState` is an interface with `suspend expand()`, `collapse()`, `toggle()`,
`snapTo(target)`, and `currentValue` / `targetValue` / `isAnimating`.
`ShortNavigationBarArrangement`: `Centered`, `EqualWeight`. `NavigationItemIconPosition`: `Top`,
`Start`. `WideNavigationRailItemDefaults.iconPositionFor(railExpanded)` picks the right one.

`NavigationItemColors` gained `selectedTextColorTopIconPosition` /
`selectedTextColorStartIconPosition` in alpha26 — an accessibility contrast fix.

## App bars

All stable: `TopAppBar`, `MediumFlexibleTopAppBar`, `LargeTopAppBar`, `LargeFlexibleTopAppBar`,
`TwoRowsTopAppBar`, `FlexibleBottomAppBar`, plus `FlexibleContentPadding`,
`FlexibleBottomAppBarHeight`, `FlexibleHorizontalArrangement`, `FlexibleFixedHorizontalArrangement`.

The distinguishing expressive feature is the **`subtitle` slot** with `titleHorizontalAlignment`:

```kotlin
TopAppBar(title, modifier, navigationIcon, actions, expandedHeight, windowInsets, colors,
          scrollBehavior, contentPadding)
TopAppBar(title, subtitle, modifier, navigationIcon, actions, titleHorizontalAlignment,
          expandedHeight, windowInsets, colors, scrollBehavior, contentPadding)   // expressive
MediumFlexibleTopAppBar(title, modifier, subtitle, navigationIcon, actions,
          titleHorizontalAlignment, collapsedHeight, expandedHeight, windowInsets, colors, scrollBehavior)
LargeFlexibleTopAppBar(…same…)
TwoRowsTopAppBar(title: (Boolean) -> Unit, modifier, subtitle: ((Boolean) -> Unit)?, …)
FlexibleBottomAppBar(modifier, containerColor, contentColor, contentPadding,
          horizontalArrangement, expandedHeight, windowInsets, scrollBehavior, content)
```

`TwoRowsTopAppBar`'s title and subtitle take a `Boolean` (expanded) rather than being plain slots.
`TopAppBarScrollBehavior` went stable in alpha17; `pinnedScrollBehavior` / `enterAlwaysScrollBehavior`
now accept a `ScrollableState`. `BottomAppBar` went stable in alpha26.

`AppBarRow` / `AppBarColumn` (in 1.4.0) with `AppBarRowScope` / `AppBarColumnScope`, `maxItemCount`,
`AppBarMenuState`, `AppBarOverflowIndicator` — overflow-aware action rows.

## Search

The state-based API is current; the boolean-expanded APIs are deprecated.

```kotlin
rememberSearchBarState(initialValue, animationSpecForExpand, animationSpecForCollapse): SearchBarState
rememberContainedSearchBarState(…)
rememberSearchBarWithGapState(…)      // renamed from rememberWithGapSearchBarState in alpha18
rememberSearchBarScrollState(initialScrollOffsetLimit, initialScrollOffset, initialContentOffset)
SearchBar(state, inputField, modifier, shape, colors, tonalElevation, shadowElevation)
ExpandedFullScreenSearchBar(state, inputField, modifier, collapsedShape, colors, …, content)
ExpandedFullScreenContainedSearchBar(…)
ExpandedDockedSearchBar(state, inputField, …, properties: PopupProperties, content)
ExpandedDockedSearchBarWithGap(state, inputField, …, dropdownShape, dropdownGapSize, dropdownScrimColor, …)

@ExperimentalMaterial3Api
AppBarWithSearch(state, inputField, modifier, navigationIcon, actions, shape,
                 colors: AppBarWithSearchColors, tonalElevation, shadowElevation,
                 contentPadding, windowInsets, scrollBehavior: SearchBarScrollBehavior?)
```

Deprecated: `SearchBar(query, onQueryChange, onSearch, active, onActiveChange, …)`,
`SearchBar(inputField, expanded, onExpandedChange, …)`, both `DockedSearchBar` overloads, and
`TopSearchBar` (superseded by `AppBarWithSearch`). In alpha26 scroll-offset variables moved from
`SearchBarScrollBehavior` onto a new `SearchBarScrollState`.

## Lists and menus

**Lists.** `ListItem` now has five overloads — non-interactive, `onClick`, `selected`/`onClick`,
`checked`/`onCheckedChange`, plus the **deprecated** legacy `ListItem(headlineContent = …)`. A
parallel **`SegmentedListItem`** family (four overloads, `shapes: ListItemShapes` required) handles
grouped and segmented lists. Types: `ListItemShapes(shape, selectedShape, pressedShape, focusedShape,
hoveredShape, draggedShape)`, `ListItemColors`, `ListItemElevation`, and `ListItemDefaults` with
`shapes()`, `ContentPadding`, `SegmentedGap`. Expressive list items left experimental in alpha23. A
flag guards a height fix: `ComposeMaterial3Flags.isExpressiveListItemHeightBasedOnTextLinesFixEnabled`.

**Menus.** Promoted alpha19. The expressive `DropdownMenuItem` takes `(onClick, text, shape,
modifier, leadingIcon, trailingContent, supportingText, enabled, colors, horizontalArrangement,
contentPadding, interactionSource)` — note `trailingContent` (renamed from `trailingIcon` in alpha25)
and the required `shape`. New: `DropdownMenuGroup(shapes: MenuGroupShapes, …)`, `DropdownMenuPopup`,
`DropdownMenuPopupPositionProvider` + `rememberDropdownMenuPopupPositionProvider` +
`MenuAnchorPosition` (`Above`/`Below`/`Start`/`End`/`Left`/`Right`/`Custom`) enabling cascading
submenus, `MenuGroupShapes`, `MenuItemShapes`, `SelectableMenuItemColors`,
`MenuDefaults.DropdownMenuGroupLabel` (renamed from `MenuDefaults.Label` in alpha23),
`MenuDefaults.selectableItemColors` / `selectableItemVibrantColors`. `ExposedDropdownMenu` is now an
extension on `ExposedDropdownMenuBoxScope` (alpha26).

## Everything else

- **Expressive icon buttons.** `IconButtonDefaults.extraSmallContainerSize()` …
  `extraLargeContainerSize()`, each taking an `IconButtonWidthOption` (`Narrow` / `Uniform` /
  `Wide`), plus per-size `*IconSize`, `*RoundShape`, `*SquareShape`, `*PressedShape`,
  `*SelectedRoundShape`, `*SelectedSquareShape`, and `shapes()` / `toggleableShapes()`.
- **`VerticalDragHandle`** + `VerticalDragHandleDefaults`, `DragHandleShapes`, `DragHandleSizes`,
  `DragHandleColors`.
- **`ScrollField`** + `ScrollFieldState` / `ScrollFieldColors` / `ScrollFieldDefaults`, and a
  non-interactive scrollbar (`NonInteractiveScrollbarDefaults`).
- **Expressive text fields.** `TextFieldDefaults.roundedShape` and `TextFieldDefaults.tonalColors()`
  (same on `OutlinedTextFieldDefaults`), added alpha21. `TextFieldLabelPosition` gained `Inside` and
  `Cutout`; `.Attached` deprecated. `OutlinedTextFieldDefaults.contentPadding()` deprecated for
  `contentPaddingWithLabel()` / `contentPaddingWithoutLabel()`.
- **Chip shape morphing.** `ChipShapes`, plus `FilterChip` / `ElevatedFilterChip` / `InputChip`
  overloads with morphing (alpha18).
- **Expressive `TimePicker`** (alpha23) with a scroll variant (alpha24), `TimePickerShapes`,
  `TimePickerDialogDefaults`, `TimePickerSelectionMode`, `TimePickerDisplayMode`.
- **`MultiAspectCarousel`** (`MultiAspectCarouselScope`, `MultiAspectCarouselItemDrawInfo` — both
  still `@ExperimentalMaterial3Api`).
- **Inset focus rings.** `RippleThemeConfiguration` / `LocalRippleThemeConfiguration` stable since
  alpha18; `RippleConfiguration` deprecated; new `material3-ripple` library in alpha24.
- **Bottom sheets unified.** `rememberBottomSheetState` (alpha20) replaces
  `rememberModalBottomSheetState` / `rememberStandardBottomSheetState`. `BasicAlertDialog` graduated
  alpha25.
- **`ComposeMaterial3Flags`** (`@ExperimentalMaterial3Api`) — runtime flags including
  `isPrecisionPointerComponentSizingEnabled`, `isExpressiveListItemHeightBasedOnTextLinesFixEnabled`,
  `isBottomSheetPartiallyExpandedDeterministicEnabled`, `isUpdatedTimepickerToggleEnabled`, and
  several styling fixes.

## Naming traps

These are the ones that produce plausible-but-wrong code:

- **No `ButtonDefaults.SmallContainerHeight`.** The small size is `MinHeight`.
  (`SplitButtonDefaults` *does* have `SmallContainerHeight`.)
- **No `ButtonDefaults.SmallIconSpacing`** and **no `smallPressedShape`** — plain `pressedShape` *is*
  the small one.
- **`MotionScheme`'s members are functions**, not properties: `fastSpatialSpec()`, not
  `fastSpatialSpec`.
- **`Shapes`' three new corners are appended at the end** of the constructor:
  `Shapes(extraSmall, small, medium, large, extraLarge, largeIncreased, extraLargeIncreased,
  extraExtraLarge)`. Positional construction in visual order silently mis-assigns.
- **No `expressiveDarkColorScheme()`.**
- **No `rememberAnimatedShape`.**
- **No `Material3ExpressiveApi` annotation** — the alpha19 note mentions one, but only
  `ExperimentalMaterial3Api` and `ExperimentalMaterial3ExpressiveApi` are declared.
- **Sizes are not constant.** `ButtonDefaults.MinHeight` is 36.dp rather than 40.dp under
  precision-pointer sizing. Never hardcode a "known" component height.

## Renames and removals across the 1.5 alphas

Each of these breaks a build at the version boundary, so check them when a project bumps alphas.

| From | To | Alpha |
|---|---|---|
| `TonalToggleButton` | `FilledTonalToggleButton` | 25 |
| `ToggleButtonDefaults.shapes` | `shapesFor` | 25 |
| `DropdownMenuItem(trailingIcon = …)` | `trailingContent` | 25 |
| `MenuDefaults.Label` | `MenuDefaults.DropdownMenuGroupLabel` | 23 |
| `rememberWithGapSearchBarState` | `rememberSearchBarWithGapState` | 18 |
| `rememberModalBottomSheetState` / `rememberStandardBottomSheetState` | `rememberBottomSheetState` | 20 |
| scroll offsets on `SearchBarScrollBehavior` | `SearchBarScrollState` | 26 |
| `SplitButtonDefaults.InnerCornerSize` | `SmallInnerCornerSize` | (hidden deprecation) |
| `ListItemDefaults.Elevation` / `.shape` | `ListItemElevation` / `ListItemShapes` | — |
| `TextFieldLabelPosition.Attached` | `Inside` / `Cutout` | 21 |
| `OutlinedTextFieldDefaults.contentPadding()` | `contentPaddingWithLabel()` / `contentPaddingWithoutLabel()` | 21 |
| `SmallButtonContentPadding` | removed | 19 |
| `ComponentOverride` APIs | removed | 23 / 25 |
| deprecated experimental `WideNavigationRail` overloads | removed | 20 |
| `shouldUsePrecisionPointerComponentSizing` | removed | 20 |
| `transformOriginState` on `DropdownMenuPopupPositionProvider` | removed | 22 |
