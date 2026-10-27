# image-to-3d

A Claude Code skill that turns a concept into a web-ready 3D model:

```
idea → ChatGPT turnaround sheet → three cut views → Meshy (image to 3D) → Blender → desktop + phone GLBs
```

It was built while making a set of carved game-piece figures, a castle gate, a siege ram and an army soldier for a production website: each a 2-3 million triangle Meshy sculpt with 4K maps, shipped as a ~1-3 MB desktop GLB and a ~0.3-1.3 MB phone GLB with no visible loss.

## What the skill does

1. **Writes the turnaround prompt** for ChatGPT (front, true side profile, back; same scale; plain light-grey background; nothing cropped), using a proven template and your house style, then **checks the sheet** you get back.
2. **Cuts the sheet** into three square views for Meshy's multi-image upload (`scripts/cut_turnaround.py`, Pillow only).
3. **Guides Meshy:** the settings to use and what to check before downloading the GLB.
4. **Optimises in Blender** (`scripts/meshy_optimize.py`): decimates to a desktop and a phone budget, builds a tight UV atlas, bakes the sculpt's detail into colour / roughness-metal / normal maps, cleans Meshy's quirks (grey metal, bright colour), grades the colour toward your reference, exports Draco GLBs with WebP maps, and writes a report with silhouette and thin-part checks plus four-side renders.
5. **Helps you ship it on the web:** three.js loading, phone vs desktop files, GPU-memory budgets, optional KTX2 compression.

It pauses at each hand-off: you run ChatGPT and Meshy, it checks each result before going on.

## Install

**As a Claude Code plugin** (from inside Claude Code):

```
/plugin marketplace add skyeyesec333/image-to-3d
/plugin install image-to-3d@image-to-3d
```

**Or as a plain skill:** copy `skills/image-to-3d` into `~/.claude/skills/` (all your projects) or into a project's `.claude/skills/`.

## Use

Just ask, in any project:

- "Turn this concept into a 3D model for the site"
- "Write a turnaround prompt for an archer in the same style as the lineup"
- "Optimise this Meshy GLB for desktop and phone"

or call it directly: `/image-to-3d archer figure, light-grey background`.

Tweaks for one object (background colour, material, no base, a lighter phone version) go in the request. To change the defaults, edit the files in `skills/image-to-3d/` (the prompt template is `references/prompting.md`), or ask Claude to update the skill.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- ChatGPT (or any image model) and a [Meshy](https://www.meshy.ai) account, used by you in their own apps
- [Blender](https://www.blender.org) 4.x or 5.x for the optimiser (headless; the bakes use Cycles on the GPU)
- Python 3 with Pillow for the sheet cutter
- Optional: `cwebp` for sharper WebP maps; KTX-Software for KTX2

## Licence

MIT. See [LICENSE](LICENSE).
