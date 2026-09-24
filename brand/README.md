# The Troi of Silo One logo

**The mark** is a silo capsule (Silo One) with one orbit around it (the One). The orbit passes behind the capsule and in front of it, and one satellite rides it: Troi, the presence that stays in orbit around you. In the wordmark, the O of TROI is that orbit and its satellite.

Everything is geometry, and the wordmark is set in [Sora](https://github.com/sora-xor/sora-font) (SIL Open Font License 1.1, `OFL.txt`). It is converted to outlines, so the files need no fonts to render.

## Files

`make_logo.py` writes these into `console/public/brand/`:

| File | Use |
|---|---|
| `mark.svg` | the mark in colour, for dark grounds |
| `mark-on-light.svg` | the mark in colour, for light grounds |
| `mark-white.svg`, `mark-ink.svg` | one-colour marks |
| `lockup-dark.svg`, `lockup-light.svg` | the mark and the wordmark side by side, for dark or light grounds |
| `lockup-stacked-dark.svg`, `lockup-stacked-light.svg` | the stacked lockups |
| `icon.svg` | the app icon (1024, the macOS corner) |
| `favicon.svg` | the icon for small sizes, with heavier strokes; also `console/app/icon.svg` |

The PNGs (`icon-1024.png`, `icon-512.png`, `lockup-*@2x.png`, `console/app/apple-icon.png`) are rendered from the SVGs. The Desktop shortcut wears `icon-1024.png` (set by `troi-console/setup.py shortcut`).

## Colours

Each palette keeps every colour at 3:1 or better against its ground.

| | On dark (`#05070F`) | On light (white) |
|---|---|---|
| Capsule, top to bottom | `#D6DCFF` → `#8C95F7` → `#6457F2` | `#7C84F2` → `#5B5CEB` → `#3527B8` |
| Orbit, left to right | `#FFE19A` → `#F4AE45` → `#D9761C` | `#C98016` → `#B0641A` → `#8E450B` |
| Satellite | `#FFF4DA` | `#BF7418` |
| Wordmark | `#F4F6FF` | `#0B1020` |
| Tagline | `#97A3D6` | `#4B5680` |

## Regenerating

The generator needs fontTools:

```bash
uv venv /tmp/brand && uv pip install --python /tmp/brand/bin/python fonttools
/tmp/brand/bin/python brand/make_logo.py console/public/brand
cp console/public/brand/favicon.svg console/app/icon.svg
```

The generator writes the SVGs only. Render the PNGs from them afterwards with any SVG renderer (Chrome headless works).
