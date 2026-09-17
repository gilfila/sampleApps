# Element library — reusable pieces for /animate

A growing catalog of components and assets you reuse across videos. The more you build
here, the faster and more consistent future renders get. Keep the actual files in
`../assets/` and index them below with the path the pipeline should reference.

Categories mirror how a video is assembled: **Layouts, Motion, Infographics, Hero text,
3D graphics, Images, Icons/Logos, Backgrounds, Sound.** (This is the same shape as
libraries like Rubric — getrubric.app — where you "add to cart" and copy an asset's
path into your prompt.)

## How to use
- Building a scene? Check here first and reuse instead of rebuilding.
- Reference an asset by its `assets/…` path so HyperFrames can include it.
- Made something reusable in a render? Save it to `assets/` and add a row here.

## Catalog

### Layouts
<!-- Reusable HTML/scene templates. -->
| Name | Path | Notes |
|------|------|-------|
| Browser mockup | `assets/layouts/browser-mockup.html` | TODO — shortened-URL variant per rules.md |

### Motion presets
| Name | Path | Notes |
|------|------|-------|
| Rise + fade in | `assets/motion/rise-fade.js` | TODO — GSAP snippet |

### Infographics / diagrams
| Name | Path | Notes |
|------|------|-------|
| _none yet_ | | |

### Hero text
| Name | Path | Notes |
|------|------|-------|
| Counting-up number | `assets/hero/count-up.html` | TODO — used by the "numbers → hero" rule |

### 3D graphics
| Name | Path | Notes |
|------|------|-------|
| _none yet_ | | |

### Images / Icons / Logos
| Name | Path | Notes |
|------|------|-------|
| Brand logo | `assets/brand/logo.svg` | TODO — drop your logo here |

### Backgrounds
| Name | Path | Notes |
|------|------|-------|
| _none yet_ | | |

### Sound / music
| Name | Path | Notes |
|------|------|-------|
| _none yet_ | | |

<!-- CHANGELOG
0.1.0 — empty catalog with the category structure. Populate assets/ and add rows as you build reusable pieces.
-->
