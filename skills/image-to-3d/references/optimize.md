# Stage 4: meshy_optimize.py

Runs inside Blender (tested on 4.x/5.2 on Apple Silicon; the bakes use Cycles on the GPU). One run makes both cuts. About 90-160 s per object on an M4 Pro.

## Environment

| Variable | Meaning | Default |
| --- | --- | --- |
| `I3D_ROOT` | the project folder | the current folder |
| `I3D_OUT` | where the GLBs go | `<root>/assets/3d` |
| `I3D_BUILD` | working files, maps, report, renders | a temp folder |
| `I3D_REFS` | folder of `<name>-front.png` colour references | `<root>/refs` |

The reference is found from the input file's name before `-meshy` (`general-meshy.glb` → `general-front.png`); `--ref <path>` points elsewhere, `--ref none` skips the grade. A name the script did not make in `I3D_OUT` is never overwritten without `--force`.

## Budgets that shipped

| Object | Desktop tris / maps (colour, normal, ORM) | Phone tris / maps | Desktop / phone MB |
| --- | --- | --- | --- |
| Hero figure (in focus, close-ups) | 100,000 / 2048, 2048, 1024 | 38,000 / 1536, 1024, 512 | 2.2-3.0 / 1.0-1.3 |
| Gate (large building, mid distance) | `gate_optimize` budget, ~2048 maps | ~1024 maps | 2.4 / 1.0 |
| Ram (prop) | 30,000 / 1024, 1024, 512 | 12,000 / 512, 512, 256 | 1.0 / 0.37 |
| Army soldier (instanced many times) | 8,000 / 1024, 1024, 512 | 3,000 / 512, 512, 256 | 0.69 / 0.22 |

Each map size must divide the cut's bake size (its largest map, doubled when 1536 or less): 2048 → 2048/1024/512; 3072 → 1536/1024/512.

## Options that matter most

- `--tris`, `--tris-m` (0: no phone cut); `--tex --nrm --orm` and the `-m` versions.
- Scale: `--height <metres>` for anything; `--base-d` is the game-piece base diameter.
- `--yaw` if the front does not face the scene's front (check the renders).
- `--boost-top 0.26 --boost 1.6`: extra texel density where the eye goes (top of the height: face, raised object). 1 to turn off; for buildings move the emphasis or turn it off.
- Finish: `--coat` (clear coat, 0 for none), `--matte` (roughness floor for paint/cloth/wood), `--metal`, `--lacquer`; `--ground-matte 1` for a matte base ground; `--top-matte`, `--top-flatten`, `--white-gain` for specific fixes.
- Colour: `--ref`, `--grade-strength`, `--grade-clamp`; `--recolour site-blue` with `--recolour-v/-s/-max/-shift` moves one hue family onto a brand colour (written for one blue; adapt the hue constant for another brand).
- `--keep-parts` (percent of the height a detached part must span to be kept regardless of size).
- `--renders DIR` (four-side renders and silhouettes), `--renders-only` (re-render existing cuts).

## Reading the report (`<name>-report.json`)

- **material roles:** which source image was colour, roughness, metal, normal. If one is missing or misread, the finish will be wrong.
- **clean:** dropped crumbs (each with size and height) and kept detached parts; open edges in the source.
- **per cut:** triangles, charts, atlas coverage and texel-density spread, how far the cut strays from the source, map and file sizes, bounds.
- **metal:** what was taken for gold, steel and lacquer.
- **grade:** the gain per hue band against the reference.
- **with `--renders`:** silhouette IoU per side and `thin_kept` per side, with the lost pixels shown in `<name>-<cut>-sildiff-<side>.png`.

Ship when: IoU 0.99+ desktop / 0.98+ phone on every side, `thin_kept` 97%+ / 94%+, no unexplained WARNING, and the renders look right next to the reference.

## Specialising

For objects that need more than options (a building with a breach, an object that will be fractured), write a small wrapper that imports `meshy_optimize` as a library and adds steps before or after, rather than copying it. The production site did this for the gate (door cut-out and passage), the soldier and the ram.

## Web follow-up

- Draco geometry needs `DRACOLoader` with its decoder (worker) path set.
- KTX2: re-encode the WebP maps to UASTC with KTX-Software's `ktx create` (sRGB for colour, linear for normal/ORM, mipmaps), swap them into the GLB under `KHR_texture_basisu`, load with `KTX2Loader` and its Basis transcoder. Expect ~4x less GPU memory and a larger download; keep the WebP originals as a fallback.
