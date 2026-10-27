---
name: image-to-3d
description: Turn a concept image into a web-ready 3D model through ChatGPT (image generation), Meshy (image-to-3D) and Blender (optimise, bake, export). Use when the user wants a figure, prop or building as a GLB for a website or three.js scene, mentions Meshy, a turnaround sheet, image-to-3D, or optimising a Meshy GLB; also for reprocessing an existing Meshy export into desktop and phone cuts.
---

# Image to 3D: ChatGPT → Meshy → Blender → web

A four-stage pipeline that produced the six carved figures, the gate, the ram and the foot soldier on a production site: each a 2-3 million triangle Meshy sculpt with 4K maps, shipped as a ~1-3 MB desktop GLB and a ~0.3-1.3 MB phone GLB with no visible loss.

```
1. ChatGPT      a three-view turnaround sheet (front, left side, back) on a plain backdrop
2. cut          scripts/cut_turnaround.py  →  three square views for Meshy
3. Meshy        multi-image to 3D  →  <name>-meshy.glb (one mesh, one PBR material)
4. Blender      scripts/meshy_optimize.py  →  <name>.glb (desktop) + <name>-m.glb (phone) + a report
5. web          load in three.js (Draco), check memory; optionally KTX2-compress the maps
```

Work through the stages in order and show the user the output of each one (the sheet, the three views, the Meshy turntable, the four-side renders) before moving on. Most failures are cheapest to fix at the stage where they appear: a bad sheet makes a bad mesh, and no optimiser fixes that.

## 1. The turnaround sheet (ChatGPT)

The user generates the image in ChatGPT (or another image model). Your job is the prompt and the review. Read [references/prompting.md](references/prompting.md) for the template and the checks. The essentials:

- **Open with the format:** "A three-view turnaround sheet (front, left side, back) of a single [object] carved as / made as [medium]: [design]".
- **Three views at the same scale and height:** straight front, a *true* left side profile (camera at 90 degrees, facing the right edge of the image), straight back. "Identical design in every view; only the camera angle changes." Orthographic.
- **A plain light-grey background,** soft even studio light, no shadows on the background (a soft contact shadow at most), no text or labels, clear space between views, nothing cropped (name the tallest part: "the top of the banner pole inside the frame").
- **House style repeated word for word across a set:** the material and finish, accents "only on" one place, "Sculpture, not a toy or CG character", "Bold simple silhouette that reads at thumbnail size".
- **Fixes for known failures:** faces (say what the face is instead), real heraldry ("Replace any family crest with a simple abstract geometric mark"), "no people" for props.
- To match an existing design, attach it in ChatGPT and say "exactly as designed in the lineup".
- The front view (from the sheet, or a separate hi-res one) becomes the colour reference in stage 4.

Review the sheet against the checklist in the reference before cutting. Regenerate rather than "fix it in Meshy".

## 2. Cut the sheet

```sh
python3 scripts/cut_turnaround.py "<sheet.png>" <name> <out_dir>
```

Writes `<name>-front.png`, `<name>-left.png`, `<name>-back.png` (1024 x 1024, figure centred on the sheet's own backdrop, 5% margin). Needs only Pillow. It finds the two emptiest vertical bands as the cuts, so a sheet whose figures touch will cut wrongly: look at the three outputs.

Keep the front view (or the separate hi-res front) as `refs/<name>-front.png` for the colour grade.

## 3. Meshy

The user runs Meshy. Read [references/meshy.md](references/meshy.md) for the settings and what to check in its preview. In short: **Image to 3D, multi-image** (upload the three views), PBR textures on, highest texture resolution, then download the **GLB** as `<name>-meshy.glb`. Look at it from all sides in Meshy's viewer: missing back detail, fused thin parts (spears, poles) and a base that is not flat are reasons to regenerate there.

## 4. Optimise in Blender

```sh
# Blender 4.x/5.x, headless. I3D_ROOT: the project (default: the current folder)
export I3D_OUT=<project>/assets/3d       # where the GLBs go (default <project>/assets/3d)
export I3D_BUILD=/tmp/i3d-build          # working files, maps, report, renders
export I3D_REFS=<project>/refs           # <name>-front.png references for the colour grade
blender -b --factory-startup --python scripts/meshy_optimize.py -- <name>-meshy.glb <name> --renders $I3D_BUILD/<name>-renders
```

What it does: imports with merged vertices, drops loose crumbs (never thin parts), scales and centres, decimates to a desktop and a phone budget, builds a tight UV atlas, bakes colour, roughness/metal and a tangent-space normal map from the full sculpt, cleans Meshy's maps (its metal is grey noise, its colour runs bright), grades the colour toward the reference, and exports Draco GLBs with WebP maps and the tangents the normals were baked against. It writes `<name>-report.json` and, with `--renders`, four-side renders and silhouette comparisons.

Read [references/optimize.md](references/optimize.md) for the budgets, the options that matter and how to read the report. Always check before shipping:

- **Silhouette match** (intersection over union per side): 0.99+ desktop, 0.98+ phone.
- **Thin parts kept:** 97%+ desktop, 94%+ phone; any WARNING names what was lost.
- **Facing:** the front toward the scene's front; `--yaw` turns it.
- **Warnings:** dropped parts, open edges, grey metal.

The script's defaults come from a tabletop game-piece scene (a 4.16 cm base, lacquer clear coat, a site-blue recolour). For other objects set `--height` (metres) or `--base-d`, and turn off what does not apply (`--coat 0`, `--ref none`, `--grade-strength 0`). Props and buildings need their own budgets (see the reference).

## 5. Web

- Load with three.js `GLTFLoader` plus `DRACOLoader` (decoder in a worker). Serve the phone cut to small screens and devices reporting 4 GB or less.
- GPU memory, not file size, is what crashes phones: a 2048 colour + 2048 normal + 1024 ORM set is about 48 MB on the GPU. Several figures: keep the maps at half size and give full size only to the one in focus.
- For more headroom, convert the maps to KTX2 (Basis UASTC) and load with `KTX2Loader`: about a quarter of the GPU memory, at the cost of a larger download; phones can keep the small WebP originals.
- For release/memory practices across a whole page (WebKit, context limits, iOS), use the `web-perf-audit` skill from web-perf-kit if installed.

## Files

- `scripts/cut_turnaround.py`: the sheet cutter (Pillow only).
- `scripts/meshy_optimize.py` + `scripts/common.py`: the Blender optimiser (run inside Blender). `--help` lists every option.
- `references/prompting.md`, `references/meshy.md`, `references/optimize.md`: the details for stages 1, 3 and 4.
