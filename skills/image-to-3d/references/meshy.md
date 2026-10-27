# Stage 3: Meshy

The user runs this in Meshy's web app; menu names change over time, so describe the intent and let them find the current control.

## Settings

- **Image to 3D with multiple images:** upload `<name>-front.png`, `<name>-left.png`, `<name>-back.png` from the cutter. Multi-view input is what keeps the back and sides faithful; a single front image makes Meshy invent the back.
- **Texture:** on, PBR (base colour, roughness, metallic, normal), the highest resolution offered (4K).
- **Topology / polycount:** the highest detail. The optimiser decimates; it needs the detail to bake from. Typical sources were 2-3 million triangles.
- **Symmetry:** on for symmetric objects, off for figures holding something in one hand.
- **Export:** GLB, one mesh with one material. Save it as `<name>-meshy.glb` next to the project's art, never inside the shipped assets.

## Checks in Meshy's viewer

- Turn it all the way round: the back and sides match the sheet.
- Thin parts: spears, poles, crests and banners are separate and continuous, not fused into the body or broken into floating pieces.
- The base is flat and closed underneath.
- No holes or melted areas where the views disagreed.
- Texture: no baked-in strong lighting, no colour bleeding across parts.

Regenerate in Meshy (or fix the sheet) when these fail. The optimiser preserves what Meshy made; it cannot add missing detail.

## Known Meshy traits the optimiser corrects

- Its metallic map is grey noise on non-metals: remapped to clean 0/1, gold kept.
- Its de-lit colour runs bright, especially reds: graded toward the reference picture per hue band.
- Its UV charts are thousands of tiny islands: rebuilt into a tight atlas (about 60% coverage instead of ~40%).
- Small loose crumbs: dropped (logged); real detached parts such as a spear are kept.
