# /animate — Claude Code skill

Turn a raw recording (or a plain script) into a short, edited, **on-brand** video:
a screen-recording recut, a vertical reel, a motion-graphics explainer, or a brand
asset. The skill transcribes the speech, tightens out filler/silences, adds
word-synced captions and informative on-screen callouts, styles everything to a
design system, and renders an MP4.

It's built to be **refined over time** — you review each render, give editor-style
feedback, and "calibrate" the skill so the next video is better. See
[`references/method.md`](references/method.md) for the full method.

## What it produces

Given a screen recording, `/animate` returns a finished MP4 with:

- **Captions** — word-synced, clean, high-contrast.
- **Filler-cut** — silences and disfluencies removed, timeline tightened.
- **Informative callouts** — designed cards on the key moments (titles, steps,
  "heads up" warnings, results), synced to the transcript.
- **On-brand styling** — palette / type / motion from
  [`references/design-system.md`](references/design-system.md) (ships with a warm,
  Claude-style light theme; swap for your own).
- **Optional low ambient music bed.**

## Install

```bash
# 1. Copy this folder to your Claude Code skills dir
cp -R animateSkill ~/.claude/skills/animate

# 2. Install the render engine (HeyGen HyperFrames suite) once
npx skills add heygen-com/hyperframes -g -y

# 3. System deps
#    - Node >= 22        (brew install node)
#    - ffmpeg / ffprobe  (brew install ffmpeg)
#    Transcription runs locally (no API key) via `hyperframes transcribe` (Whisper),
#    or faster-whisper / AssemblyAI if you prefer.
```

Then in Claude Code:

```
/animate path/to/recording.mp4  captions, cut filler, add callouts, clean look
```

## Layout

| Path | What |
|------|------|
| `SKILL.md` | The skill contract — pipeline, tool wiring, produce/refine modes |
| `references/method.md` | The method: refined vs unrefined, the 3 steps + loop |
| `references/design-system.md` | Palette / type / motion tokens (the "look") |
| `references/rules.md` | Accumulated editor-style rules |
| `references/element-library.md` | Reusable-component catalog index |
| `scripts/cut_and_caption.py` | Filler-cut + caption remap from a word transcript |
| `scripts/build_composition.py` | Assembles the styled HyperFrames composition HTML |
| `assets/` | Reusable asset files for the element library |

## Credit

The refinement method is adapted from RoboNuggets' walkthrough
("GPT6 Astra one-shots motion graphics like never before"),
re-implemented for Claude Code + HeyGen HyperFrames + local Whisper.
