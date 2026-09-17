# Rules — accumulated feedback the pipeline must honor

Each rule is a piece of feedback you'd give a video editor, written so the agent applies
it every time. After you watch a render and spot something to fix, add it here (or say
"calibrate my animate skill with this feedback" and let the agent add it).

Keep rules **specific and testable**. Format: a trigger → the required behavior.

## Active rules

### Content / text
- **Numbers → hero graphic.** When the narration says a number ("four free plugins"),
  show a big **hero number counting up** to it, not just inline text.
- **No filler eyebrow text.** Don't add decorative labels above the headline unless
  they carry meaning.

### Mockups / screen elements
- **Shorten URLs** in browser-mockup elements — don't let them truncate mid-address.
- **Vary the visual.** Don't default every scene to the same browser-mockup view; change
  the layout scene to scene.
- **Record on a mobile browser** when the footage is a screen recording destined for
  vertical (9:16) — desktop-width text is unreadable on a phone.

### Captions / timing
- Captions follow the word timings from transcription; keep them in the safe area and
  cut on the narration's rhythm.

<!-- Add your own below. Examples of good rules:
- When the speaker names a tool, show its logo from assets/ if we have it.
- Keep any single scene ≤ 4 seconds unless the narration needs longer.
- End every reel with the brand logo sting.
-->

## How to add a rule
1. Watch a render; note what's off.
2. Phrase it as trigger → behavior (above).
3. Add it here, or run `/animate calibrate my animate skill with this feedback`.

<!-- CHANGELOG
0.1.0 — seeded with the example rules from the source workflow. Add your own after each render.
-->
