# Adaptive layout and navigation

Verified: 2026-08-23 against material3-adaptive 1.3.0 and material3 1.4.0 / 1.5.0-alpha26.

Expressive is an *adaptive* system — the I/O 2026 guidance frames the layout scaffold as the starting
point rather than a phone layout you later stretch. Reach for this file when the code assumes one
screen size, or when a review touches tablets, foldables, or desktop windows.

## Window size classes

| Class | Width | Typical device |
|---|---|---|
| Compact | < 600dp | Phone portrait |
| Medium | 600–839dp | Large phone landscape, small tablet portrait, unfolded inner display |
| Expanded | 840–1199dp | Tablet landscape, small desktop window |
| Large | 1200–1599dp | Desktop |
| Extra-large | ≥ 1600dp | Large desktop |

Drive layout from `WindowSizeClass` (`material3-window-size-class`), not from raw width comparisons
or device-type checks. Height classes exist too and matter for a landscape phone, where vertical space
rather than width is the constraint.

Note that a size class describes the *window*, not the device — a multi-window or freeform app can be
Compact on a tablet. Code that infers "tablet" from a size class is making an assumption that breaks
in split screen.

## Navigation per size class

| Class | Component | Rationale |
|---|---|---|
| Compact | `ShortNavigationBar` | Bottom placement is thumb-reachable; 3–5 destinations |
| Medium | `WideNavigationRail`, collapsed | Reclaims vertical space; leading edge is reachable |
| Expanded | `WideNavigationRail`, expanded, or a permanent drawer | Labels have room; the rail's expanded state exists for this |
| Any | `ModalWideNavigationRail` | Temporary access without displacing content |

`NavigationSuiteScaffold` (`material3-adaptive-navigation-suite`) selects and swaps these for you,
which is usually the right call — a hand-written `when (sizeClass)` around three navigation
components is a maintenance surface with no upside.

Two rules that survive every size: destination **order** is identical across classes, because screen
readers and keyboard navigation follow it; and the selected destination survives a size change.
A rotation that resets navigation to Home is a bug that only shows up on tablets.

## Canonical layouts

Three patterns cover most screens, and reaching for one of them is almost always better than
inventing a responsive layout.

**List-detail.** A list and a detail pane. Compact shows one at a time with navigation between;
Medium and up show both. `ListDetailPaneScaffold` handles the pane logic, back behaviour, and the
"nothing selected" state — which is the case hand-rolled versions forget.

**Supporting pane.** Primary content plus a secondary pane that supports it (comments, properties,
tools). The supporting pane docks beside the content on wide windows and moves below or into a sheet
on Compact. `SupportingPaneScaffold`.

**Feed.** A grid of equivalent items that reflows by column count. Use a lazy grid with adaptive
columns rather than a fixed count per breakpoint, so the layout degrades smoothly between classes
instead of jumping.

## Spacing

The 8dp spacing system: margins, padding, and gaps in multiples of 8, so layouts can adapt
programmatically to device type and density. Compact typically uses 16dp body margins, wider windows
24dp and up.

Spacing is where an otherwise-correct adaptive layout most often looks wrong at width — the same 16dp
margin that is right on a phone leaves a 1200dp window looking like a stretched phone.

## Content width

Do not let content fill an arbitrarily wide window. Text lines beyond roughly 840–1040dp become hard
to track, and a full-width button at 1600dp is absurd. Constrain the content column and either centre
it or pair it with a second pane. Buttons should be constrained or placed beside adjacent elements
rather than stretched.

## Edge-to-edge and insets

Lay out edge-to-edge and consume `WindowInsets` deliberately — via `Scaffold`'s padding values, or
`Modifier.windowInsetsPadding` / `safeDrawingPadding` where you need control. The failure modes are
recognisable: content under the status bar, a bottom bar under the navigation bar, and a text field
hidden by the IME.

Expressive components accept a `windowInsets` parameter (app bars, navigation bars and rails, sheets)
so they can extend their background behind a system bar while keeping content clear of it. Passing
`WindowInsets(0)` to silence a layout problem moves the bug rather than fixing it.

## Foldables

- Place no interactive content across the fold or hinge.
- Handle the posture change: an app that resets scroll position or loses form input on unfold is
  failing the same state-preservation contract as a rotation.
- Test the transition, not just the two end states. Most foldable bugs live in the change.

## Testing matrix

At minimum: Compact portrait, Medium (unfolded or small tablet), Expanded landscape. Add 200% font
scale and a right-to-left locale to the same matrix — layouts that survive width often fail on text
growth, and expressive display styles are where that shows first.
