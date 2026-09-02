# Wear OS — expressive on the wrist

Verified: 2026-08-23 against Wear Compose Material 3 guidance.

Read this only for a watch surface. Wear Compose Material 3 (`androidx.wear.compose:compose-material3`)
is a **separate library** from `androidx.compose.material3` with its own components and its own
version line — do not assume an API from the phone library exists here, and do not mix the two in one
module.

## Why Wear is different, not just smaller

The design language starts from constraints the phone does not have: a tiny round display, a viewing
distance of a few seconds, a user whose other hand is often busy, and a battery that punishes
brightness. Expression on Wear therefore concentrates in *motion and shape* rather than in size and
color, and the round display becomes an active layout element instead of a container to letterbox.

Consequences worth checking in a review:

- **Edge-hugging containers.** Components follow the display curve rather than sitting in a
  rectangle inset from it. A rectangular card centred on a round screen wastes the majority of the
  usable area.
- **Arc text.** Curved text along the bezel for titles and time — a Wear-specific affordance with no
  phone equivalent.
- **Physics-based motion carries more weight.** With less room for type hierarchy and color, springy
  motion is doing much of the work of signalling state and response.
- **Glanceability over density.** One primary piece of information per screen. A phone screen ported
  down is the most common Wear design failure.

## Levels of expression

The same three-level idea as the phone, but calibrated for the wrist:

- **Foundational** — standard components, minimal motion. Correct for utilities and complications.
- **Excellent** — shape and motion contrast on the primary action, edge-hugging containers.
- **Transformative** — bold shape morphing and prominent motion. Only for hero surfaces, and only
  where battery and glanceability can absorb it.

## Practical constraints

- **Touch targets** are at least 48×48dp here too, on a much smaller display — which means fewer
  targets per screen, not smaller ones.
- **Contrast** matters more: watches are read in direct sunlight. Prefer higher contrast than the
  phone minimum.
- **Motion scale and battery.** Honour the system animation scale, and remember that ambient mode
  freezes animation entirely — no state may depend only on motion.
- **Rotary input.** Support the rotating bezel and crown for scrolling where the device has one.
  Scroll that only responds to touch feels broken on hardware that has a crown.
- **Spring tokens resolve per device class**, so "fast" is fast relative to a watch. The token names
  are the same; the absolute values are not.

## Reviewing a Wear surface

1. Confirm the module uses `androidx.wear.compose:compose-material3`, not the phone library.
2. Check for rectangular layouts on round displays — the tell is content clipped or margins that
   grow toward the corners.
3. Check glanceability: can the primary information be read in about a second?
4. Check rotary input support on scrollable content.
5. Check ambient-mode behaviour, and that nothing depends on animation to be understood.
6. Then apply the phone checks that still hold: token usage over literals, contrast, touch targets,
   reduced motion.
