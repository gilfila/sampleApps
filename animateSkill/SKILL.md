---
name: animate
version: "0.1.0"
description: Turn a raw recording or a plain script into a short, edited, on-brand video — vertical reels, motion-graphics explainers, or brand video assets. Transcribes the recording with AssemblyAI (Whisper as a free fallback), builds an editable HTML composition with HeyGen HyperFrames, applies YOUR design system + rules + element library, previews it, and renders an mp4. Also handles refining/"calibrating" this skill from feedback. Trigger on "animate this footage", "make a reel from this", "motion graphics from this script", "turn this recording into a short video", or "calibrate/refine my animate skill".
argument-hint: "<video-or-script-path> [instructions]"
allowed-tools: Bash, Read, Write, Edit, WebFetch, AskUserQuestion
author: tony-gilfillan
license: MIT
user-invocable: true
---

# /animate

Give the agent a **video-production pipeline**. You hand it a raw recording (or just a
script) and it returns a short, edited, on-brand video: a vertical reel, a
motion-graphics explainer, or a brand asset. Under the hood it transcribes the
speech, plans scenes, builds an editable HTML composition, renders it to mp4, and
checks the file plays.

This skill is built to be **refined over time**, not perfect on day one. The whole
method — and *why* refinement is the point — lives in
[`references/method.md`](references/method.md). Read it once; it is short and it is
the actual value here.

## The two ways this skill is used

1. **Produce a video.** `/animate path/to/recording.mp4 make a 9:16 reel` → run the
   production pipeline below.
2. **Refine this skill.** `/animate calibrate my animate skill with the feedback from
   this session` → jump to [Refining the skill](#refining-the-skill-the-loop). This is
   how the skill gets better; expect to do it often.

If the input is a video/script path (or a URL), you're producing. If it's an
instruction *about the skill itself* ("calibrate", "refine", "add a rule", "update
the design system"), you're refining.

## The three tools (be aware of them — Step 1)

You do **not** need to know how these work internally — just that they exist and are
**already installed here**, so you can invoke them and wire them together.

1. **HeyGen HyperFrames** — the render engine, installed as a suite of sibling
   skills. Turns plain HTML + CSS + GSAP timelines into a deterministic mp4 (seeks
   each frame in headless Chrome, encodes with FFmpeg). **`/hyperframes` is the
   mandatory entry point** — read it first for any make/edit/render request; it
   routes to the right workflow. The ones this skill leans on:
   - **`/talking-head-recut`** — package existing footage with designed graphic
     overlay cards (titles, lower-thirds, data callouts) synced to the transcript;
     the clip plays untouched underneath. Closest fit for editing a raw recording.
   - **`/motion-graphics`** — short, motion-first units (kinetic type, stat
     count-ups, logo stings, overlays).
   - **`/embedded-captions`** — plain spoken-word captions.
   - **`/media-use`** — source or generate BGM, SFX, images, icons, voice.
   - **`/hyperframes-cli`** — the CLI dev loop. Direct: `npx hyperframes …` (`--help`).
2. **Transcription** — so captions land on the right frames and you know what the
   footage says.
   - **Default (no key):** `npx hyperframes transcribe "<audio-or-video>" -d "<dir>" --json --model small.en`
     runs **Whisper locally** — no API key, no rate limit. Writes a word-level
     `transcript.json` (`[{text,start,end}, …]`).
   - **Optional upgrade:** **AssemblyAI** (`pip install assemblyai`,
     `ASSEMBLYAI_API_KEY`) — fast/cheap at scale with word timings; docs at
     https://www.assemblyai.com/docs. ElevenLabs Scribe also works if you pay for it.
   - **Script-only input:** skip transcription — use the script text directly for
     captions and timing.
3. **The agent** — you (Claude Code here; works the same in Codex or any host with
   the HyperFrames skills installed).

## Setup preflight (run once, silent on success)

```bash
node -v | grep -qE 'v(2[2-9]|[3-9][0-9])' || echo "WARN: HyperFrames needs Node >= 22 (you have $(node -v))"
ls ~/.claude/skills/hyperframes >/dev/null 2>&1 || echo "MISSING: hyperframes skills — install: npx skills add heygen-com/hyperframes -g -y"
npx hyperframes --version >/dev/null 2>&1 || echo "WARN: hyperframes CLI not resolving — check Node/npm"
```

The HyperFrames suite and CLI are expected to be installed already. Transcription
works with **no API key** (local Whisper via `hyperframes transcribe`), so a missing
`ASSEMBLYAI_API_KEY` is fine — AssemblyAI is only an optional upgrade.

## Producing a video (the pipeline)

Work in a clean output dir (e.g. `./animate-out/<slug>/`). Keep the editable source,
the mp4, a poster frame, and a short note of what you used.

1. **Parse the input.** Separate the source (recording or script path/URL) from any
   instructions ("9:16", "keep it under 20s", "use the Figma look"). Confirm aspect
   ratio and target length; default to **9:16, ≤ the footage length** for reels.
2. **Transcribe** (recording only). Default: `npx hyperframes transcribe` (local
   Whisper) → word-level `transcript.json`. Use AssemblyAI instead if a key is set.
   For script-only input, use the script as the caption track directly.
3. **Plan the scenes.** Break the transcript/script into beats. For each beat decide:
   the visual (layout / element), the on-screen text, and the transition. **Apply the
   rules** in [`references/rules.md`](references/rules.md) here — they encode hard-won
   feedback (e.g. numbers → hero counting-up graphic; shorten mockup URLs).
4. **Style it.** Pull colors, type, and spacing from
   [`references/design-system.md`](references/design-system.md) — this is what keeps
   output on-brand instead of generic. Reuse components from
   [`references/element-library.md`](references/element-library.md) instead of
   rebuilding them.
5. **Build the composition** via the HyperFrames skills — start at **`/hyperframes`**
   and let it route (usually `/talking-head-recut` for footage + graphic cards, or
   `/motion-graphics` for a motion-first piece; `/embedded-captions` for plain
   captions). Feed it the design system, rules, and reused elements from below.
6. **Preview**, then **render the mp4** through the chosen HyperFrames workflow (or
   the `hyperframes` CLI). Add captions timed to the transcript.
7. **Verify** the file exists and plays (e.g. `ffprobe` shows the expected duration,
   resolution, and an audio/video stream). Save source + mp4 + poster + a one-line
   "what I used" note.
8. **Show the user** the mp4 path and the poster, and invite feedback — feedback is
   the raw material for the next refinement (see below).

## Bundled scripts (`scripts/`)

Two small, dependency-free (stdlib + `ffmpeg`) helpers implement the parts of the
pipeline that are the same every time. Proven on a real 16:9 screen-recording recut.

- **`scripts/cut_and_caption.py`** — filler-cut + caption remap. Reads a flat word
  transcript (`[{text,start,end}, …]` — e.g. from `hyperframes transcribe --json` or
  faster-whisper), drops filler words + long silences, and writes:
  - `keep_segments.json` — kept spans on the **original** timeline (feed to ffmpeg)
  - `captions.json` — caption lines remapped to the **tightened** timeline
  - `cut_stats.json` — before/after durations
  ```bash
  python3 scripts/cut_and_caption.py transcript.json OUT_DIR \
    [--start S --end S] [--gap 0.55] [--pad 0.12] [--maxwords 8 --maxchars 46]
  ```
  Then cut the tightened video in one sample-accurate re-encode (dense keyframes so
  HyperFrames can seek every frame) using an ffmpeg `select`/`aselect` filter built
  from `keep_segments.json` → `public/input-video.mp4`.

- **`scripts/build_composition.py`** — assembles the Claude-styled
  `talking-head-recut` composition (`public/index.html`): full-bleed 16:9 video +
  word-synced caption band + informative callout cards, using the palette in
  `references/design-system.md`. Reads `captions.json` and an authored
  `callouts.json` (`[{id,start,end,x,y,w,h,accent,kicker,title,detail}]`).
  ```bash
  python3 scripts/build_composition.py WORK_DIR DURATION_SECONDS
  ```
  Then `npx hyperframes check public` (expect 0 errors) and render with
  `PRODUCER_BROWSER_GPU_MODE=hardware npx hyperframes render public --skill=talking-head-recut -o output.mp4 --fps 30`.

- **Music bed (optional).** Mix a low ambient track *after* render so voice stays
  full (`normalize=0`), looping + fading the track:
  ```bash
  ffmpeg -y -i output.mp4 -stream_loop -1 -i music.m4a \
    -filter_complex "[1:a]volume=0.085,afade=t=in:d=2.5,afade=t=out:st=<dur-3.5>:d=3.5[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac output_final.mp4
  ```

Defaults assume 16:9 / 1920×1080 / 30fps (edit the constants in `build_composition.py`
for other canvases). These scripts are a **starting point** — refine them like any
other part of the skill.

## Refined vs unrefined — why bother

An **unrefined** skill is what a single prompt gives you. It works, but it produces
the model's *default* aesthetic — the same look everyone else gets from the same
prompt ("vibecoded slop"). A **refined** skill is fine-tuned to your brand and your
standards, so it gives consistently good, distinctive output every time. Three levers
turn unrefined into refined — all detailed in
[`references/method.md`](references/method.md):

- **Reference designs** — the single biggest lever. Feed it a real design system.
  Browse `styles.refero.design` (2,000+ AI-readable `DESIGN.md` files) or use your own
  brand. Capture the chosen one in `references/design-system.md`.
- **New rules** — after watching output, write feedback like you would to a video
  editor, and record each as a rule in `references/rules.md`.
- **Element library** — a growing set of reusable assets (3D graphics, layouts, motion
  presets, infographics, hero text, icons, backgrounds, sound). Index them in
  `references/element-library.md` and drop files in `assets/`. Tools like Rubric
  (getrubric.app) let you "add to cart" and copy an asset's path into your prompt.

## Refining the skill (the loop)

This is Step 2 → Step 3 of the method, and it never really ends.

1. Produce one or two videos with the current skill.
2. Watch them. Write down concrete feedback — layouts, pacing, text, what looks
   off — as if briefing a video editor.
3. Fold that feedback in:
   - a recurring visual preference → add/adjust a **rule** in `references/rules.md`
   - an off-brand color/font → fix `references/design-system.md`
   - a component you keep needing → add it to `references/element-library.md` (+ `assets/`)
4. Then **calibrate the skill**: apply the session's feedback to these files (and this
   SKILL.md if the *process* changed). A request like *"calibrate my animate skill with
   the feedback we just discussed"* is enough — update the relevant reference files,
   summarize what changed, and note it in the changelog comment at the bottom of the
   changed file.

Every pass makes the next video better. Over time, handing this skill a raw recording
reliably returns a finished, on-brand video with little cleanup.

## Notes & limits

- Best results on short clips (reels/explainers). Long footage: cut to the segment you
  actually want before rendering.
- Never hardcode API keys in files — read them from the environment.
- If a tool's CLI has changed, trust its live docs over the commands sketched here and
  update this skill (that's a refinement too).
