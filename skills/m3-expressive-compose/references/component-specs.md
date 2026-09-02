# Component specs — sizes, shapes, and variant choice

Verified: 2026-08-23 against m3.material.io component specs and material3 1.5.0-alpha26 token files.

Curated dimensional and behavioural specs, for when a review needs to check a concrete value or a
build needs to pick a variant. Colors are deliberately absent — see `foundations.md` § Color for why
a quoted hex is almost certainly wrong. Exact API member names are in `api-surface.md`.

Prefer the size-derived helpers (`ButtonDefaults.shapesFor(h)`, `contentPaddingFor(h)`,
`iconSizeFor(h)`) over reading a value from this table and hardcoding it. The table is for judging
whether existing code is right, not for copying numbers into new code — component sizes are not
constants and can shift with device sizing flags.

## Buttons

Two variants: **default** and **toggle**. Five color configurations: elevated, filled, tonal,
outlined, text. Five sizes: XS, S, M, L, XL. Two shapes: round (default) and square. Toggle buttons
do not have a text configuration.

| Size | Height | Icon | Icon spacing | Square corner | Pressed corner |
|---|---|---|---|---|---|
| XS | 32.dp | 20.dp | 4.dp | 12.dp | 8.dp |
| S | 40.dp (36 under precision-pointer sizing) | 20.dp | 8.dp | 12.dp | 8.dp |
| M | 56.dp | 24.dp | 8.dp | 16.dp | 12.dp |
| L | 96.dp | 32.dp | 12.dp | 28.dp | 16.dp |
| XL | 136.dp | 40.dp | 16.dp | 28.dp | 16.dp |

Round buttons are fully rounded at every size. Minimum width 58.dp. Small-button padding is now
16.dp — the old 24.dp is no longer recommended, since 16 matches the new sizes.

Icons are leading, before the label, at a 20.dp standard size for S and XS. Trailing icons are for
disclosure, not for the action's own meaning.

### Choosing a configuration

- **Filled** — the highest impact after a FAB. Important, final, flow-completing actions: Save, Join
  now, Confirm. Ideally one per screen.
- **Tonal** — a lower-priority action that needs slightly more weight than an outline would give.
  "Next" in onboarding is the canonical case.
- **Outlined** — medium emphasis, important but not primary. Pairs well beside a filled button to
  offer the alternative. Needs a simple background; do not place over images or video.
- **Text** — inside cards, dialogs, and snackbars, where a container would compete with the content.
  Align to the trailing edge in dialogs. Since there is no container at rest, the label color must be
  unmistakably not-body-text.
- **Elevated** — the tonal button plus a shadow. Use only when the button genuinely needs separation
  from a prominent background. For emphasis, prefer filled.

Toggle buttons are for binary state (Save, Favorite). Outlined icon when unselected, filled when
selected; round when unselected, square when selected, by default.

## Icon buttons

Same five sizes, plus three width options: `Narrow`, `Uniform`, `Wide`. Standard, filled, filled
tonal, and outlined configurations, each with round and square shapes and per-size pressed and
selected shapes.

**XS and S icon buttons must still have a 48×48dp touch target** even though the visible container is
smaller. This is the most-missed accessibility requirement in the expressive size scale.

## FABs

Sizes: small, standard, medium, large — plus four extended variants. FAB menu replaces the
hand-rolled speed dial: a `ToggleFloatingActionButton` that morphs, with menu items that stagger in.

The FAB is the highest-emphasis element on a screen. One per screen, for the screen's single most
important action. A screen with a FAB and a full-width filled button is competing with itself.

## Floating toolbars

Horizontal and vertical, each in a plain form and a FAB-attached form. Two color treatments:
standard and vibrant. They collapse and expand on scroll — either via
`exitAlwaysScrollBehavior(...)` or `Modifier.floatingToolbarVerticalNestedScroll(...)`. Two elevation
pairs, collapsed and expanded, with separate values for the FAB-attached case.

Use one instead of a hand-built floating pill of icon buttons, and instead of a `BottomAppBar`
pressed into service as a floating cluster. The scroll-linked behaviour is the point.

## App bars

Four heights: small, medium, large, plus the center-aligned form. The flexible variants
(`MediumFlexibleTopAppBar`, `LargeFlexibleTopAppBar`, `TwoRowsTopAppBar`) add the expressive
features: a real **subtitle slot** and `titleHorizontalAlignment`.

A `Column { Text(title); Text(subtitle) }` inside the `title` slot is the pattern to look for — it
mis-sizes during the collapse animation because the bar measures the title slot as one line.

Actions need overflow handling. `AppBarRow(maxItemCount = 3, overflowIndicator = { … })` collapses
extras into a menu; without it, four or more actions collide on narrow windows and at large font
scales.

## Button groups

For a set of related actions that read as one control. Standard (spaced) and connected (adjoining)
forms. Connected groups need the leading, middle, and trailing shape sets so the outer corners round
and the inner ones do not. `Modifier.animateWidth(interactionSource)` gives the pressed item a width
bump, which is what makes the group feel physical.

Groups handle their own overflow via an indicator, so they survive a narrow window better than a
hand-built `Row`.

## Navigation

| Window | Component | Notes |
|---|---|---|
| Compact | `ShortNavigationBar` | 3–5 destinations. `Centered` or `EqualWeight` arrangement; `Top` or `Start` icon position. |
| Medium | `WideNavigationRail`, collapsed | Rail with icon-above-label items |
| Expanded | `WideNavigationRail`, expanded, or a permanent drawer | `rememberWideNavigationRailState()` drives `expand()` / `collapse()` / `toggle()`; item icon position switches with the expanded state |
| Any, overlay | `ModalWideNavigationRail` | For temporary access without displacing content |

Keep destination order identical across all sizes. See `adaptive.md` for the fuller decision.

## Sheets and dialogs

**Bottom sheets** — standard (persistent, coexists with content) and modal (blocks, scrimmed). One
state API now: `rememberBottomSheetState()`. Extra-large top corners.

**Side sheets** — standard and modal, for supplementary content on wider windows. Prefer over a
bottom sheet when the window is Expanded and the content is a companion rather than a step.

**Dialogs** — basic and full-screen. Extra-large corners. Text buttons only, aligned to the trailing
edge, because the absence of a container unifies the actions with the dialog's text. A dialog with a
filled button is over-weighted for what a dialog is.

## Progress and loading

`LinearWavyProgressIndicator` and `CircularWavyProgressIndicator` are the expressive treatment and are
stable — the flat indicators now read as pre-expressive. Both determinate and indeterminate.

`LoadingIndicator` and `ContainedLoadingIndicator` use shape morphing through a polygon sequence and
remain experimental after a promotion was reverted. Gate any recommendation of them.

## Carousel

Multi-browse, uncontained, and hero layouts, plus `MultiAspectCarousel` for mixed item aspect ratios.
Carousels are a hero-moment device; two on one screen is one too many.

## Lists and menus

`ListItem` has interactive overloads (clickable, selectable, checkable) — the legacy
`ListItem(headlineContent = …)` form is deprecated. `SegmentedListItem` with a `ListItemShapes` bundle
and `ListItemDefaults.SegmentedGap` produces the grouped, card-like list that reads as expressive.

Menus gained groups, cascading submenus via anchor positions, supporting text per item, and
per-item shapes. The expressive `DropdownMenuItem` overload requires an explicit `shape`.

## Text fields

Filled and outlined. `TextFieldDefaults.roundedShape` and `tonalColors()` are the expressive visual
configuration — reach for those rather than hand-tuning a shape and a color set toward the same look.
Label position options are `Inside` and `Cutout`.
