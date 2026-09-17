# Design system — the look /animate renders in

This is the **#1 lever** for quality. Fill it in with a real design system so renders
come out on-brand instead of generic. Two ways to seed it:

1. Grab a `DESIGN.md` from **https://styles.refero.design** (2,000+ AI-readable design
   systems) and paste/adapt the parts below.
2. Or describe your own brand. Take inspiration from a reference, then iterate the fonts
   and palette toward *yours* — don't ship a clone for real brand work.

Everything below is a **placeholder** — replace it. The pipeline reads this file when it
styles each scene.

## Brand voice / feel
Clean, warm, and calm — "Claude" aesthetic. Editorial, high-legibility, generous
whitespace, quiet confidence. Nothing flashy; the on-screen info is the star.

## Color palette
Claude's warm paper + clay accent. Light by default.

| Token        | Hex        | Use |
|--------------|------------|-----|
| Cream / bg   | `#F4F1EA`  | caption pill bg, page backdrop |
| Card         | `#FBF9F4`  | callout panels |
| Ink (text)   | `#26231C`  | headlines, captions |
| Muted text   | `#6B6558`  | secondary / detail lines |
| Clay accent  | `#D2795E`  | accent bar, kickers, highlights (Claude coral) |
| Clay alt     | `#CC785C`  | secondary accent |

Default mode: **light** (Claude paper). Captions = cream pill + ink text for legibility
over any footage (bright Finder windows or dark IDEs).

## Typography
| Role      | Font   | Weight | Notes |
|-----------|--------|--------|-------|
| Display   | Inter  | 700    | callout titles, hero numbers |
| Heading   | Inter  | 700    | kickers (uppercase, letter-spacing 0.14em) |
| Body      | Inter  | 400    | detail lines |
| Caption   | Inter  | 700    | ~44px, letter-spacing -0.01em, centered pill |

(Inter is bundled with the HyperFrames talking-head-recut skill — no external fonts.)

## Motion
- Callout entrance: fade + 18px rise, 0.45s, `power3.out`; accent bar scales in (`scaleY 0→1`, top origin).
- Callout exit: fade + 12px lift, 0.4s, `power2.in`.
- Captions: hard cut in/out on word timings (no animation) — legibility first.
- Rhythm: cut on the narration; keep one idea on screen at a time.

## Layout / safe areas
- Primary: 16:9 (1920×1080) for screen-recording tutorials — never crop screen content to 9:16.
- Captions live in the bottom band (~64px up); callouts in a top/side zone so they never cover
  the thing being explained or overlap the captions.

## Do / don't
- DO: keep captions short (≤7 words / ~40 chars), one idea per callout, lots of breathing room.
- DON'T: cover the on-screen UI element being explained; stack multiple callouts; use loud colors.

<!-- CHANGELOG
0.1.0 — starter template. Replace placeholders via `/animate calibrate` after your first renders.
-->
