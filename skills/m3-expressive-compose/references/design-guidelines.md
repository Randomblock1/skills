# Design guidelines — judgment, not API compliance

Verified: 2026-08-23 against m3.material.io expressive guidance.

Correct token usage does not make a good screen. This file is the judgment layer: how much expression
a product should carry, where to spend it, and how to recognise the failure modes. Reach for it when
the request is qualitative — "make this feel more modern", "does this look right", "the screen feels
cluttered" — or when an audit found every token correct and the screen still reads badly.

## Intensity levels

Pick one level for a product or a feature and hold it. Mixing levels across screens in the same flow
is more jarring than any single level, because the user reads the inconsistency as a bug.

**Foundational.** Clarity and familiarity first. Standard components, standard shapes, restrained
color. Correct for utilities, settings, enterprise tools, dense data, anything where the user's goal
is to get out quickly. Expressive motion still applies — springs feel better than tweens even here.

**Excellent.** Stronger color, type, and shape while preserving all standard patterns. Emphasized type
for headlines and selected states, container colors for emphasis, the increased corner tokens on hero
containers. This is the right default for most consumer apps.

**Transformative.** Bold layouts, large shape contrast, prominent motion, `MaterialShapes` for
non-rectangular containers. Usability and accessibility constraints get *stricter*, not looser, and
the burden of proof is on the design. Appropriate for onboarding, media, games, brand-led surfaces.

An audit finding worth making: a screen whose intensity does not match its job. A settings screen at
Transformative is wrong regardless of how well the tokens are used.

## Hero moments

**One to two per flow, not per screen.** A hero moment is where you spend expression — a large
emphasized headline, a shape-morphing primary action, an animated container, a vibrant floating
toolbar. Its power is entirely relative: three heroes on a screen is zero heroes, because nothing is
distinguished.

This is the most common failure in a technically-correct expressive implementation, and the most
common thing worth flagging. When you find six emphasized elements, the finding is not "reduce
expression" in the abstract — it is "these two are the hero moments this flow is actually about;
demote the other four to standard treatment."

Where a hero moment usually belongs: the primary action of the flow, the content the screen exists to
show, or the moment of completion. Where it usually does not: navigation, secondary actions, chrome,
anything the user passes through rather than arrives at.

## Levers, and what each costs

| Lever | How it creates emphasis | The cost when overused |
|---|---|---|
| Shape contrast | Bold corners on the primary element, restrained on the rest | Every corner bold reads as a toy; nothing is primary |
| Rich color | Container roles (`primaryContainer`, `secondaryContainer`) for emphasis | Contrast failures, and visual noise that hides hierarchy |
| Type hierarchy | Emphasized styles plus size steps | Bold everywhere is the same as bold nowhere; layouts break at 200% scale |
| Motion | Spring physics, shape morph on press and select | Perceived slowness, motion sickness, and animation that blocks input |
| Size | The XS–XL button and icon-button scale | Large targets crowd out content; L and XL buttons are 96dp and 136dp tall |

The general shape of good expressive design is high contrast between a few emphasized elements and a
calm majority. Uniform intensity — at any level — reads as flat.

## Common mistakes

| Mistake | Why it happens | Fix |
|---|---|---|
| Labels removed for a cleaner look | Icon-only looks tidier in a mockup | Keep labels. Icon-only navigation and primary actions measurably reduce task success. If space is short, that is a layout problem. |
| Everything is a hero | Each element looked better individually | Choose 1–2 per flow; demote the rest |
| Standard navigation patterns broken | Expression mistaken for licence to reinvent | Preserve back behaviour, nav placement, and gesture conventions. Novel navigation is the single fastest way to make an app feel broken rather than fresh. |
| No reduced-motion path | Springs feel exempt from motion settings | Honour the system animation scale; transition instantly at 0 |
| Shape morph as the only state signal | It is genuinely satisfying | Pair with color or icon change so it survives grayscale and low vision |
| Intensity varies screen to screen | Different screens built at different times | Pick a level per product; audit for drift |
| Window size classes ignored | Built and tested on one phone | Check Compact, Medium, Expanded. Hero moments in particular re-tune badly at width. |
| Expression added to dense data | The dashboard looked boring | Density and expression trade off directly. Foundational is the right answer for tables. |

## Accessibility as a gate

An expressive screen that fails these is worse than the stock screen it replaced — it has spent
attention and given back a regression. Treat them as gates rather than a checklist to score.

- **Contrast.** 4.5:1 body text, 3:1 large text and meaningful non-text. Measured on the container for
  filled, tonal, and elevated; on the label for outlined and text.
- **Touch targets.** 48×48dp minimum, independent of the visible container. The XS and S sizes shrink
  the container, not the target.
- **Motion.** Reduced-motion path present; nothing blocks input while animating.
- **Labels and descriptions.** Every interactive element has an accessible label matching its visible
  text. Decorative icons inside labelled buttons take `contentDescription = null` — the label already
  carries the meaning, and a duplicate description makes TalkBack read it twice.
- **200% font scale.** Button labels fit within two lines. Emphasized display styles are where layouts
  break first.
- **Keyboard and focus.** Tab reaches everything, focus order matches visual order, focus rings are
  visible. Expressive shapes must not clip the ring.
- **High contrast mode.** The screen still reads with a sharply reduced palette.

## Adapting expression across window sizes

Expression does not scale linearly with width. A hero treatment tuned for a 400dp phone screen often
looks thin and stretched at 1200dp.

- Constrain content width on Large and Extra-large windows (roughly 840–1040dp for text) rather than
  letting lines run the full width.
- Constrain button width, or pair buttons with adjacent content, so they do not become absurdly long.
- Icon and label stay centred and grouped as a button's width changes.
- Keep element order identical across sizes — screen readers and keyboard navigation follow it.
- Place no interactive content across a fold or hinge.
- Re-choose the navigation component per size class rather than scaling one; see `adaptive.md`.

## Content and copy

Small things, but they are what separate a screen that looks designed from one that looks assembled.

- Button labels: 1–3 words, sentence case ("Book with flights", not "BOOK WITH FLIGHTS"). Sentence
  case is what lets proper nouns read as proper nouns.
- Never truncate or wrap a button label. If it does not fit, the label is too long or the layout is
  wrong.
- Toggle buttons that change label between states: watch the character count, because a large change
  shifts the layout under the user's finger. Prefer an icon change plus a stable label.
- Toggle buttons should use an outlined icon when unselected and the filled version when selected. If
  no filled version exists, increase the weight instead.
- Buttons are not the only way to represent an action. Too many on a screen destroys hierarchy —
  consider chips, text links, icon buttons, a toolbar, or a menu.
- Reserve the filled style for one important, flow-completing action per screen. Text buttons belong
  in cards, dialogs, and snackbars where a container would compete with the content.
