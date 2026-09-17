# The /animate method — refine, don't one-shot

The point of `/animate` is not a clever one-shot prompt. It's a **skill you refine**
until it reliably produces on-brand video from raw footage. This file is the method,
distilled from the workflow the skill is based on.

## Refined vs unrefined skills

Both a refined and an unrefined `/animate` skill do the same job: raw footage in →
edited video out. The difference is **output quality and consistency**.

- **Unrefined** — created from a single prompt (see [first-version prompt](#the-first-version-prompt-unrefined-baseline)).
  Fast to make, but it produces the model's *default* aesthetic. Everyone who uses the
  same prompt gets the same look. That's how you end up with generic "vibecoded slop."
- **Refined** — put through the loop below so it's fine-tuned to your brand and
  standards. Same inputs, but consistently better and distinctly *yours*.

You start unrefined on purpose, then refine. The three steps:

## Step 1 — Be aware of the tools

You don't need to understand the tools internally; you need to know they exist so you
can invoke them. For `/animate` the minimum set is:

- **AssemblyAI** — transcribe the recording (word timings). Fast/cheap. Free local
  alternative: **Whisper** (slower). Also possible: **ElevenLabs Scribe**.
- **HeyGen HyperFrames** — the engine that turns HTML into video.
- **Your agent** (Claude Code here; Codex/others work too).

Ask the agent to create an initial `/animate` skill using these tools → you now have a
baseline to improve. See the exact prompt at the bottom.

## Step 2 — Review the output and give structured feedback (the most important step)

Most people give weak feedback. Three techniques, most impactful first:

### 2a. Reference designs — the #1 lever
Nothing moves a vibecoded look toward something unique faster than a real design
system. Best source: **`styles.refero.design`** — 2,000+ AI-readable `DESIGN.md` files
from leading product sites (colors, typography, spacing, components), usable in Claude
Code / Codex / Cursor / v0 / Lovable. Copy a `DESIGN.md` and hand it to the agent to
reference. Don't just clone it for real brand work — take inspiration and iterate the
fonts/palette toward your own. Record the result in `design-system.md`.

### 2b. Add new rules
After you watch a render, note the fixes like you're briefing a video editor, then turn
each into a rule. Real examples from the source workflow:
- When a number is spoken, always show a big **hero number counting-up** graphic (e.g.
  "four free plugins" → hero text "4").
- In the browser-mockup element, **shorten the URL** (it was truncating).
- Take screen recordings in a **mobile browser** for vertical video (desktop text is
  too small on a phone).

Pattern: make 1–2 videos → watch → write feedback → give the agent those rules **in the
same session**. Store them in `rules.md`.

### 2c. Build an element library
A reusable set of components/assets you accumulate as you work: 3D graphics, layouts
(e.g. browser mockup), motion presets (how things animate in), infographics/diagrams,
hero text, generated images, icons/logos, backgrounds, sound effects/music. The value
is **reuse** — the more you use the skill, the bigger the library, the faster and more
consistent future videos get. Index them in `element-library.md`; keep files in
`assets/`. (Rubric — getrubric.app — is one "add-to-cart → copy asset path" way to
manage this.)

## Step 3 — Ask the agent to update the skill

The simplest step. Once you've given enough feedback in a session:

> calibrate my /animate skill with the feedback we just talked about

The model folds the feedback into the skill's files so the next run is more refined
than the last.

## The loop (don't stop at Step 3)

If this skill matters to you or your business, keep going: **every time** you use it,
review the output and give structured feedback, then calibrate. Day by day the skill's
quality compounds, until sending it a raw video near-instantly yields a great result.

```
produce → review → structured feedback (design / rules / elements) → calibrate → repeat
```

## The first-version prompt (unrefined baseline)

The exact prompt used to scaffold the initial, unrefined skill — kept for reference and
re-scaffolding:

> create a skill called /animate that helps me turn a script or recording into a short
> video using HyperFrames and AssemblyAI.
> - use HyperFrames to build an editable video composition, preview it, and render an mp4
> - use AssemblyAI to transcribe speech and get word timings when i provide a recording;
>   when i only provide a script, use the script for captions
> - read the basic official guidance for both tools, connect what is available, and tell
>   me what i need to set up if something is missing
> - make the skill cover a simple flow: take the input, plan the scenes, add visuals and
>   captions, preview the result, export it, and check that the video plays properly
> - test the skill with one 10-second 9:16 video using this script: "This is prompts dot
>   chat, a free, open-source prompt library for writing, coding, images, video and
>   research. Find a starting point for your next project."
> - choose the visuals, type, colours, layouts and transitions yourself using the basic
>   tool guidance. save the editable source, final mp4, a poster, and a short note listing
>   what you used
> make this a good first version. leave the style choices open so i can improve the skill
> after watching the result.

_Source: "GPT6 Astra one-shots motion graphics like never before (NEW Skill)" by
Jay E | RoboNuggets — https://www.youtube.com/watch?v=Ce1Ym1HGyBA_
