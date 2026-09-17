# assets/

Reusable files for the /animate element library (indexed in
`../references/element-library.md`): layouts, motion snippets, hero-text templates, 3D
graphics, images, icons/logos, backgrounds, and sound.

Suggested layout:

```
assets/
  layouts/     browser-mockup.html, split-screen.html, …
  motion/      rise-fade.js, …           (GSAP snippets)
  hero/        count-up.html, …
  brand/       logo.svg, …
  3d/          *.glb / *.png
  images/      …
  backgrounds/ …
  sound/       *.mp3
```

Add a row to `../references/element-library.md` whenever you drop a file here so the
pipeline knows to reuse it.
